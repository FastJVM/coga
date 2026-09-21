from __future__ import annotations

import subprocess
from pathlib import Path
from textwrap import dedent
from typing import Any

import pytest
import requests
import typer
from typer.testing import CliRunner

from coga import autoclose as am
from coga import blackboard as blackboard_module
from coga import retire_worklist as rw
from coga.cli import app
from coga.config import load_config
from coga.create import create_task
from coga.taskfile import TaskFileError
from coga.ticket import Ticket


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


def _write_workflow_less_task(
    repo: Path, *, slug: str = "work", status: str = "active"
) -> tuple[str, Path]:
    """Write a workflow-less task directly to disk. `create_task` refuses to
    create a workflow-less non-draft task now, so on-disk construction is the
    only way to exercise the workflow-less automerge → mark-done path."""
    task_dir = repo / "tasks" / slug
    task_dir.mkdir(parents=True)
    (task_dir / "ticket.md").write_text(dedent(f"""
        ---
        title: Work
        status: {status}
        owner: marc
        agent: claude
        workflow: null
        ---

        ## Description

        <!-- coga:blackboard -->

        # Blackboard
    """).lstrip())
    return slug, task_dir


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    company = tmp_path / "coga"
    _write(
        company / "coga.toml",
        """
        version = 1
        default_status = "draft"
        [notification.slack]
        webhook = "env:SLACK_WEBHOOK_URL"
        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        """,
    )
    _write(company / "coga.local.toml", 'user = "marc"\n')
    _write(
        company / "workflows" / "code.md",
        """
        ---
        name: code
        description: tiny.
        steps:
          - name: implement
            assignee: agent
          - name: review
            assignee: agent
        ---

        ## implement
        Write the code.

        ## review
        Review the code.
        """,
    )
    monkeypatch.chdir(company)
    return company


def _make_task(
    repo: Path,
    *,
    title: str = "Work",
    workflow: str | None = "code",
    status: str = "active",
    on_final: bool = False,
    pr_url: str | None = None,
    branch: str | None = "foo",
    worktree: str | None = None,
) -> tuple[str, Path]:
    cfg = load_config(repo)
    if workflow is None and status != "draft":
        # `create_task` refuses to create a workflow-less non-draft task now,
        # so the workflow-less mark-done tests construct that shape on disk
        # (directory form, so `ticket.md` lives under the returned dir).
        slug, path = _write_workflow_less_task(repo, status=status)
        ref = {"slug": slug, "path": path}
        ticket = path / "ticket.md"
    else:
        ref = create_task(
            cfg=cfg,
            title=title,
            workflow_name=workflow,
            contexts=[],
            owner="marc",
            agent="claude",
            status=status,
        )
        # File-form default: `ref["path"]` is the `tasks/<slug>.md` ticket itself.
        ticket = ref["path"]
    if workflow and on_final:
        t = Ticket.read(ticket)
        steps = t.workflow["steps"]
        last = len(steps)
        t.frontmatter["step"] = f"{last} ({steps[last - 1]['name']})"
        t.write(ticket)
    if pr_url is not None:
        from coga.taskfile import read_blackboard, replace_blackboard

        dev = ["## Dev", ""]
        if branch is not None:
            dev.append(f"branch: {branch}")
        if worktree is not None:
            dev.append(f"worktree: {worktree}")
        dev.append(f"pr: {pr_url}")
        bb = read_blackboard(ticket, blackboard_required=False).rstrip()
        replace_blackboard(ticket, bb + "\n\n" + "\n".join(dev) + "\n")
    return ref["slug"], ticket


# --- pure parsers -------------------------------------------------------------


def test_parse_pr_url_finds_under_dev() -> None:
    text = dedent(
        """
        Some preamble.

        ## Plan

        Stuff.

        ## Dev

        branch: feature-x
        pr: https://github.com/owner/repo/pull/42
        """
    )
    assert am.parse_pr_url(text) == "https://github.com/owner/repo/pull/42"


def test_parse_pr_url_returns_none_without_dev_section() -> None:
    assert am.parse_pr_url("## Plan\n\nNo dev here.\n") is None


def test_parse_pr_url_returns_none_when_dev_lacks_pr_line() -> None:
    text = "## Dev\n\nbranch: only-a-branch\n"
    assert am.parse_pr_url(text) is None


def test_parse_pr_url_ignores_pr_outside_dev_section() -> None:
    text = "## Notes\n\npr: https://example.com/x\n"
    assert am.parse_pr_url(text) is None


def test_parse_pr_url_list_item_form() -> None:
    # `- pr: <url>` — the bulleted shape `_BRANCH_LINE_RE` already tolerated but
    # `_PR_LINE_RE` did not, so a merged final-step ticket written this way was
    # silently skipped by the sweep and left stranded `in_progress`.
    text = "## Dev\n\n- branch: `trim-prompt`\n- pr: https://github.com/o/r/pull/416\n"
    assert am.parse_pr_url(text) == "https://github.com/o/r/pull/416"


def test_parse_pr_url_trailing_annotation_form() -> None:
    # `pr: <url> (annotation)` — the shape `_BRANCH_LINE_RE` / `_WORKTREE_LINE_RE`
    # already tolerated but the `$`-anchored `_PR_LINE_RE` did not, so a merged
    # final-step ticket annotated this way was silently skipped by the sweep.
    text = (
        "## Dev\n\n- pr: https://github.com/o/r/pull/55 "
        "(no CI configured on the repo)\n"
    )
    assert am.parse_pr_url(text) == "https://github.com/o/r/pull/55"


def test_parse_pr_url_backtick_wrapped_with_annotation() -> None:
    text = "## Dev\n\npr: `https://github.com/o/r/pull/56` (Magicator repo)\n"
    assert am.parse_pr_url(text) == "https://github.com/o/r/pull/56"


def test_parse_pr_url_unclosed_backtick_falls_back_to_bare_form() -> None:
    text = "## Dev\n\npr: `https://github.com/o/r/pull/57\n"
    assert am.parse_pr_url(text) == "https://github.com/o/r/pull/57"


@pytest.mark.parametrize(
    "value",
    [
        "(not opened yet)",
        "none - blocked on CI",
        "TBD",
        "see the other ticket",
        "https://github.com/o/r/issues/58",
    ],
)
def test_parse_pr_url_placeholder_or_non_pr_value_is_none(value: str) -> None:
    # `parse_worktree_path` rejects placeholders the same way. Unguarded, the
    # unanchored capture would hand `(not` / `none` to `gh pr view`, whose
    # GhError aborts the whole sweep (exit 2) — trading one silently skipped
    # ticket for a failure on every remaining one.
    text = f"## Dev\n\npr: {value}\n"
    assert am.parse_pr_url(text) is None


def test_parse_pr_url_skips_a_placeholder_line_above_the_real_one() -> None:
    # The guard rejects a value the regex now happily matches, so the scan has
    # to keep going. Anchoring on the first `pr:` line would strand a ticket
    # that recorded a placeholder and appended the real link underneath it.
    text = (
        "## Dev\n\npr: (not opened yet)\npr: https://github.com/o/r/pull/8\n"
    )
    assert am.parse_pr_url(text) == "https://github.com/o/r/pull/8"


def test_parse_pr_url_does_not_bleed_past_an_empty_pr_line() -> None:
    # `\s` matches newlines, so a `\s*$` tail on the non-greedy capture would
    # let an empty `pr:` line swallow the next non-blank line.
    text = "## Dev\n\npr:\n\nhttps://github.com/o/r/pull/99\n"
    assert am.parse_pr_url(text) is None


def test_parse_branch_name_bare_form() -> None:
    text = "## Dev\n\nbranch: feature-x\npr: https://github.com/o/r/pull/1\n"
    assert am.parse_branch_name(text) == "feature-x"


def test_parse_branch_name_list_item_form() -> None:
    # `- branch: \`name\`` — list prefix + backticks, the trap form.
    text = "## Dev\n\n- branch: `first-run-no-slack`\n- pr: `https://x/pull/2`\n"
    assert am.parse_branch_name(text) == "first-run-no-slack"


def test_parse_branch_name_backtick_wrapped_form() -> None:
    text = "## Dev\n\nbranch: `drop-debug-all`\n"
    assert am.parse_branch_name(text) == "drop-debug-all"


def test_parse_branch_name_backtick_wrapped_with_annotation() -> None:
    text = "## Dev\n\nbranch: `feature/name` (other repo)\n"
    assert am.parse_branch_name(text) == "feature/name"


def test_parse_branch_name_unclosed_backtick_falls_back_to_bare_form() -> None:
    text = "## Dev\n\nbranch: `feature/name (other repo)\n"
    assert am.parse_branch_name(text) == "feature/name (other repo)"


def test_parse_branch_name_none_without_dev_section() -> None:
    assert am.parse_branch_name("## Plan\n\nbranch: nope\n") is None


def test_parse_branch_name_none_when_dev_lacks_branch_line() -> None:
    assert am.parse_branch_name("## Dev\n\npr: https://x/pull/3\n") is None


def test_parse_branch_name_empty_value_is_none() -> None:
    assert am.parse_branch_name("## Dev\n\nbranch: ``\n") is None


def test_parse_worktree_path_bare_form_preserves_spaces() -> None:
    text = "## Dev\n\nworktree: /tmp/path with spaces\n"
    assert am.parse_worktree_path(text) == "/tmp/path with spaces"


def test_parse_worktree_path_list_item_backtick_wrapped_form() -> None:
    text = "## Dev\n\n- worktree: `/tmp/path with spaces`\n"
    assert am.parse_worktree_path(text) == "/tmp/path with spaces"


def test_parse_worktree_path_backtick_wrapped_with_annotation() -> None:
    text = "## Dev\n\nworktree: `/tmp/path with spaces` (other repo)\n"
    assert am.parse_worktree_path(text) == "/tmp/path with spaces"


def test_parse_worktree_path_unclosed_backtick_falls_back_to_bare_form() -> None:
    text = "## Dev\n\nworktree: `/tmp/path with spaces (other repo)\n"
    assert am.parse_worktree_path(text) == "/tmp/path with spaces (other repo)"


def test_parse_worktree_path_annotated_placeholder_is_none() -> None:
    text = "## Dev\n\nworktree: `(not yet created)` (other repo)\n"
    assert am.parse_worktree_path(text) is None


def test_parse_pr_number() -> None:
    assert am.parse_pr_number("https://github.com/o/r/pull/74") == 74
    assert am.parse_pr_number("not-a-url") is None


def test_pr_head_reads_exact_branch_and_oid(monkeypatch) -> None:
    def fake_run(argv, **kwargs):  # type: ignore[no-untyped-def]
        assert argv == [
            "gh",
            "pr",
            "view",
            "https://github.com/o/r/pull/7",
            "--json",
            "headRefName,headRefOid",
        ]
        return subprocess.CompletedProcess(
            argv,
            0,
            stdout='{"headRefName":"feat","headRefOid":"abc123"}',
            stderr="",
        )

    monkeypatch.setattr(am.subprocess, "run", fake_run)

    assert am.pr_head("https://github.com/o/r/pull/7") == ("feat", "abc123")


def test_prs_for_head_lists_requested_state(monkeypatch) -> None:
    def fake_run(argv, **kwargs):  # type: ignore[no-untyped-def]
        assert argv == [
            "gh",
            "pr",
            "list",
            "--head",
            "feat",
            "--state",
            "open",
            "--json",
            "number,headRefOid",
        ]
        return subprocess.CompletedProcess(
            argv,
            0,
            stdout='[{"number":12,"headRefOid":"abc123"}]',
            stderr="",
        )

    monkeypatch.setattr(am.subprocess, "run", fake_run)

    assert am.prs_for_head("feat", "open") == [
        {"number": 12, "headRefOid": "abc123"}
    ]


# --- scanner ------------------------------------------------------------------


def _stub_pr_state(monkeypatch: pytest.MonkeyPatch, mapping: dict[str, str]) -> list[str]:
    """Patch `pr_state` to return states from `mapping`. Returns calls list."""
    calls: list[str] = []

    def fake(url: str) -> str:
        calls.append(url)
        if url not in mapping:
            raise am.GhError(f"unknown PR url: {url}")
        return mapping[url]

    monkeypatch.setattr(am, "pr_state", fake)
    return calls


def test_sweep_merged_bumps_final_step_with_merged_pr(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    slug, path = _make_task(
        repo, on_final=True, pr_url="https://github.com/o/r/pull/7"
    )
    _stub_pr_state(monkeypatch, {"https://github.com/o/r/pull/7": "MERGED"})

    cfg = load_config(repo)
    result = am.sweep_merged(cfg, quiet=True)

    assert len(result.closed) == 1
    t = Ticket.read(path)
    assert t.status == "done"
    from coga.logfile import task_log_lines

    log = "\n".join(task_log_lines(cfg, slug))
    assert "auto-bumped on merge of PR #7" in log


def test_sweep_merged_bumps_final_step_with_annotated_pr_line(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The live casualty: a final-step ticket whose `pr:` line carried a trailing
    # note sat stranded `in_progress` after its PR merged, because the sweep
    # read the annotated line as "no PR".
    slug, path = _make_task(
        repo,
        on_final=True,
        pr_url="https://github.com/o/r/pull/70 (no CI configured on the repo)",
    )
    _stub_pr_state(monkeypatch, {"https://github.com/o/r/pull/70": "MERGED"})

    cfg = load_config(repo)
    result = am.sweep_merged(cfg, quiet=True)

    assert len(result.closed) == 1
    assert Ticket.read(path).status == "done"


def test_sweep_merged_skips_non_final_step(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Default creates at step 1 (implement) of a 2-step workflow.
    slug, path = _make_task(repo, pr_url="https://github.com/o/r/pull/8")
    _stub_pr_state(monkeypatch, {"https://github.com/o/r/pull/8": "MERGED"})

    cfg = load_config(repo)
    result = am.sweep_merged(cfg, quiet=True)

    assert len(result.closed) == 0
    t = Ticket.read(path)
    assert t.status == "active"


def test_sweep_merged_no_workflow_marks_done(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    slug, path = _make_task(
        repo, workflow=None, pr_url="https://github.com/o/r/pull/9"
    )
    _stub_pr_state(monkeypatch, {"https://github.com/o/r/pull/9": "MERGED"})

    cfg = load_config(repo)
    result = am.sweep_merged(cfg, quiet=True)

    assert len(result.closed) == 1
    t = Ticket.read(path)
    assert t.status == "done"


def test_sweep_merged_skips_open_pr(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    slug, path = _make_task(
        repo, on_final=True, pr_url="https://github.com/o/r/pull/10"
    )
    _stub_pr_state(monkeypatch, {"https://github.com/o/r/pull/10": "OPEN"})

    cfg = load_config(repo)
    result = am.sweep_merged(cfg, quiet=True)

    assert len(result.closed) == 0
    t = Ticket.read(path)
    assert t.status == "active"


def test_sweep_merged_skips_ticket_without_pr(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    slug, path = _make_task(repo, on_final=True)  # no pr_url
    calls = _stub_pr_state(monkeypatch, {})

    cfg = load_config(repo)
    result = am.sweep_merged(cfg, quiet=True)

    assert len(result.closed) == 0
    assert calls == []  # pr_state never called


@pytest.mark.parametrize("terminal_status", ["done", "canceled"])
def test_sweep_merged_skips_terminal_ticket(
    repo: Path, monkeypatch: pytest.MonkeyPatch, terminal_status: str
) -> None:
    slug, path = _make_task(
        repo,
        on_final=True,
        status=terminal_status,
        pr_url="https://github.com/o/r/pull/11",
    )
    calls = _stub_pr_state(monkeypatch, {"https://github.com/o/r/pull/11": "MERGED"})

    cfg = load_config(repo)
    result = am.sweep_merged(cfg, quiet=True)

    assert len(result.closed) == 0
    # Terminal statuses are filtered before any gh call.
    assert calls == []


def test_sweep_merged_idempotent(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    slug, path = _make_task(
        repo, on_final=True, pr_url="https://github.com/o/r/pull/12"
    )
    _stub_pr_state(monkeypatch, {"https://github.com/o/r/pull/12": "MERGED"})

    cfg = load_config(repo)
    first = am.sweep_merged(cfg, quiet=True)
    second = am.sweep_merged(cfg, quiet=True)

    assert len(first.closed) == 1
    assert len(second.closed) == 0


def test_sweep_rechecks_after_concurrent_manual_final_bump(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A manual final-step bump during the PR lookup wins exactly once.

    The sweep's second ticket read must observe `done` and skip its own
    `mark_done`, avoiding a duplicate terminal audit entry.
    """
    slug, path = _make_task(
        repo,
        status="in_progress",
        on_final=True,
        pr_url="https://github.com/o/r/pull/15",
    )

    def finish_while_checking(url: str) -> str:
        result = CliRunner().invoke(app, ["bump", slug])
        assert result.exit_code == 0, result.output
        return "MERGED"

    monkeypatch.setattr(am, "pr_state", finish_while_checking)
    cfg = load_config(repo)

    result = am.sweep_merged(cfg, quiet=True)

    assert len(result.closed) == 0
    assert Ticket.read(path).status == "done"
    from coga.logfile import task_log_lines

    log = "\n".join(task_log_lines(cfg, slug))
    assert log.count("task done") == 1
    assert "auto-bumped on merge" not in log


def test_sweep_merged_quiet_swallows_gh_error(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    slug, path = _make_task(
        repo, on_final=True, pr_url="https://github.com/o/r/pull/13"
    )

    def boom(url: str) -> str:
        raise am.GhError("gh missing")

    monkeypatch.setattr(am, "pr_state", boom)

    cfg = load_config(repo)
    result = am.sweep_merged(cfg, quiet=True)

    assert len(result.closed) == 0
    t = Ticket.read(path)
    assert t.status == "active"


def test_sweep_merged_loud_raises_gh_error(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    slug, path = _make_task(
        repo, on_final=True, pr_url="https://github.com/o/r/pull/14"
    )

    def boom(url: str) -> str:
        raise am.GhError("gh missing")

    monkeypatch.setattr(am, "pr_state", boom)

    cfg = load_config(repo)
    with pytest.raises(am.GhError):
        am.sweep_merged(cfg, quiet=False)


# --- retire follow-ups --------------------------------------------------------


def _closed(
    slug: str,
    *,
    branch: str | None = None,
    worktree: str | None = None,
    home: am.CheckoutHome | None = None,
) -> am.ClosedTicket:
    return am.ClosedTicket(
        slug=slug,
        title="Work",
        branch=branch,
        worktree=worktree,
        home=home or am.CheckoutHome("unknown"),
    )


def _capture_posts(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Capture the text of every live Slack notification made during the test."""
    posts: list[str] = []

    def fake(url, json=None, timeout=None):  # type: ignore[no-untyped-def]
        posts.append(json["text"])

        class R:
            status_code = 200
            text = "ok"

        return R()

    monkeypatch.setattr("coga.notification.slack.requests.post", fake)
    return posts


def test_sweep_records_the_checkout_state_of_each_closed_ticket(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The `## Dev` lines must be captured during the sweep: they are the only
    # trace of which checkout belongs to the ticket, and retire (or a task
    # deletion) takes them away.
    slug, _ = _make_task(
        repo,
        on_final=True,
        pr_url="https://github.com/o/r/pull/20",
        branch="feature-x",
        worktree="/w/coga-feature-x",
    )
    _stub_pr_state(monkeypatch, {"https://github.com/o/r/pull/20": "MERGED"})

    result = am.sweep_merged(load_config(repo), quiet=True)

    assert [
        (item.slug, item.branch, item.worktree) for item in result.retire_pending
    ] == [(slug, "feature-x", "/w/coga-feature-x")]


def test_sweep_omits_a_closed_ticket_that_recorded_no_checkout(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _make_task(
        repo,
        on_final=True,
        pr_url="https://github.com/o/r/pull/21",
        branch=None,
    )
    _stub_pr_state(monkeypatch, {"https://github.com/o/r/pull/21": "MERGED"})

    result = am.sweep_merged(load_config(repo), quiet=True)

    assert len(result.closed) == 1
    assert result.retire_pending == []


def test_render_retire_report_names_the_exact_retire_command() -> None:
    report = am.render_retire_report(
        generated_at="2026-08-14T08:00:00+00:00",
        task_slug="recurring/autoclose-merged",
        pending=[_closed("fix-thing", branch="fix-thing", worktree="/w/coga-fix")],
    )

    assert report.startswith(am.RETIRE_REPORT_HEADING)
    assert "Generated: 2026-08-14T08:00:00+00:00" in report
    assert "Task: `recurring/autoclose-merged`" in report
    assert (
        '- `fix-thing` "Work": worktree `/w/coga-fix`, branch `fix-thing` — '
        "`coga retire fix-thing`" in report
    )


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    return proc


def _init_repo(root: Path) -> Path:
    """A real repo with one commit, so `git worktree add` has a head to branch from."""
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "-b", "main", ".")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "Tester")
    (root / "seed.txt").write_text("seed")
    _git(root, "add", "seed.txt")
    _git(root, "commit", "-q", "-m", "seed")
    return root


def test_locate_checkout_recognises_a_linked_worktree_of_the_ticket_repo(
    tmp_path: Path,
) -> None:
    root = _init_repo(tmp_path / "ticket-repo")
    feature = tmp_path / "ticket-repo-feature"
    _git(root, "worktree", "add", str(feature), "-b", "feature-x")

    home = am.locate_checkout(root, _closed("t", branch="feature-x", worktree=str(feature)))
    assert (home.kind, home.path) == ("same", feature.resolve())
    # A relative `worktree:` resolves against the ticket repo's root, as retire
    # and the worklist discharge rule do — never against the process cwd.
    relative = am.locate_checkout(
        root, _closed("t", branch="feature-x", worktree="../ticket-repo-feature")
    )
    assert (relative.kind, relative.path) == ("same", feature.resolve())


def test_locate_checkout_names_the_repo_that_owns_a_cross_repo_worktree(
    tmp_path: Path,
) -> None:
    # The recorded checkout is a linked worktree of *another* repository — the
    # shape a Coga workspace tracking code that lives elsewhere produces.
    root = _init_repo(tmp_path / "ticket-repo")
    owner = _init_repo(tmp_path / "other-repo")
    feature = tmp_path / "other-repo-feature"
    _git(owner, "worktree", "add", str(feature), "-b", "feature-x")

    home = am.locate_checkout(root, _closed("t", branch="feature-x", worktree=str(feature)))

    assert home.kind == "other"
    assert home.path == feature.resolve()
    assert home.owner is not None
    assert home.owner.resolve() == owner.resolve()


def test_locate_checkout_reports_what_retire_preserves(tmp_path: Path) -> None:
    # Every static refusal `remove_ticket_worktree` makes is predicted here, so
    # the report never names a plain `coga retire` that leaves the checkout in
    # place: not a worktree, the ticket repo's own checkout, an independent
    # clone, a symlink, and a worktree with no `branch:` to prove it by.
    root = _init_repo(tmp_path / "ticket-repo")
    plain = tmp_path / "plain-dir"
    plain.mkdir()
    clone = tmp_path / "clone"
    _git(root, "clone", "-q", str(root), str(clone))
    feature = tmp_path / "ticket-repo-feature"
    _git(root, "worktree", "add", str(feature), "-b", "feature-x")
    link = tmp_path / "link"
    link.symlink_to(feature)

    def kind(worktree: str, branch: str | None = "feature-x") -> tuple[str, str]:
        home = am.locate_checkout(root, _closed("t", branch=branch, worktree=worktree))
        return home.kind, home.reason or ""

    assert kind(str(plain)) == ("preserved", "it is not a git worktree")
    assert kind(str(root)) == ("preserved", "it is the checkout retire runs from")
    (root / "sub").mkdir()
    assert kind(str(root / "sub")) == (
        "preserved",
        "it is this repository's own checkout, not a linked worktree",
    )
    assert kind(str(clone)) == (
        "preserved",
        f"it is an independent checkout owned by `{clone.resolve()}`, not a "
        "linked worktree of this repository",
    )
    assert kind(str(link)) == ("preserved", "the recorded path is a symlink")
    assert kind(str(feature), branch=None) == (
        "preserved",
        "no `branch:` is recorded, so retire cannot prove which checkout it "
        "belongs to",
    )


def test_locate_checkout_distinguishes_gone_and_unjudged(tmp_path: Path) -> None:
    root = _init_repo(tmp_path / "ticket-repo")
    plain = tmp_path / "plain-dir"
    plain.mkdir()

    gone = am.locate_checkout(
        root, _closed("t", branch="b", worktree=str(tmp_path / "nowhere"))
    )
    assert (gone.kind, gone.path) == ("gone", (tmp_path / "nowhere").resolve())
    # Nothing to judge: no worktree recorded, or no git root to judge against.
    assert am.locate_checkout(root, _closed("t", branch="b")) == am.CheckoutHome(
        "unknown"
    )
    assert am.locate_checkout(
        None, _closed("t", branch="b", worktree=str(plain))
    ) == am.CheckoutHome("unknown")


def test_render_retire_report_names_the_owner_of_a_cross_repo_checkout() -> None:
    # `coga retire <slug>` resolves the task in the current repo and requires a
    # same-repo linked worktree, so for a cross-repo checkout no invocation can
    # dispose of it: the line must say so and name the by-hand cleanup.
    item = _closed(
        "fix-thing",
        branch="fix-thing",
        worktree="/w/other-fix",
        home=am.CheckoutHome(
            "other", path=Path("/w/other-fix"), owner=Path("/src/other")
        ),
    )
    report = am.render_retire_report(
        generated_at="2026-09-21T08:00:00+00:00",
        task_slug=None,
        pending=[item],
    )

    line = next(ln for ln in report.splitlines() if ln.startswith("- `fix-thing`"))
    assert line.startswith(
        '- `fix-thing` "Work": worktree `/w/other-fix`, branch `fix-thing` — '
        "the worktree belongs to `/src/other`, not this repository: "
        "`coga retire fix-thing` from here fails its same-repo worktree proof"
    )
    assert "the task does not exist there" in line
    assert (
        "`git -C /src/other worktree remove /w/other-fix`, then "
        "`git -C /src/other branch -d fix-thing`." in line
    )


def test_render_retire_report_says_when_the_worktree_is_gone_or_preserved() -> None:
    gone = _closed(
        "gone-thing",
        branch="gone-thing",
        worktree="/w/gone",
        home=am.CheckoutHome("gone", path=Path("/w/gone")),
    )
    preserved = _closed(
        "plain-thing",
        branch="plain-thing",
        worktree="/w/plain",
        home=am.CheckoutHome(
            "preserved", path=Path("/w/plain"), reason="it is not a git worktree"
        ),
    )
    report = am.render_retire_report(
        generated_at="2026-09-21T08:00:00+00:00",
        task_slug=None,
        pending=[gone, preserved],
    )

    assert (
        "— the worktree is no longer on disk; `coga retire gone-thing` reports "
        "it already gone and disposes of branch `gone-thing` only, if this "
        "repository holds it" in report
    )
    assert "`git worktree prune` first" in report
    assert (
        "— `coga retire plain-thing` leaves `/w/plain` in place (it is not a git "
        "worktree) and disposes of branch `plain-thing` only. Inspect and "
        "remove the directory by hand." in report
    )


def test_render_retire_report_keeps_the_plain_command_for_same_repo_checkouts() -> None:
    report = am.render_retire_report(
        generated_at="2026-09-21T08:00:00+00:00",
        task_slug=None,
        pending=[
            _closed(
                "fix-thing",
                branch="fix-thing",
                worktree="/w/coga-fix",
                home=am.CheckoutHome("same", path=Path("/w/coga-fix")),
            )
        ],
    )

    assert (
        '- `fix-thing` "Work": worktree `/w/coga-fix`, branch `fix-thing` — '
        "`coga retire fix-thing`\n" in report
    )


def test_render_retire_summary_names_the_owner_instead_of_an_unrunnable_command() -> None:
    summary = am.render_retire_summary(
        [
            _closed("alpha", branch="alpha"),
            _closed(
                "beta",
                worktree="/w/beta",
                home=am.CheckoutHome(
                    "other", path=Path("/w/beta"), owner=Path("/src/other")
                ),
            ),
        ]
    )

    assert summary == (
        "🧹 2 auto-closed tickets still have a feature checkout: "
        "`coga retire alpha`, `beta` (worktree owned by `/src/other` — clean up "
        "by hand there)"
    )


def test_recipe_reports_the_owner_of_a_cross_repo_checkout(
    repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # End to end: the ticket repo is a real git repo, the closed ticket's
    # checkout is a linked worktree of a different one.
    _init_repo(repo)
    owner = _init_repo(tmp_path / "other-repo")
    feature = tmp_path / "other-repo-feature"
    _git(owner, "worktree", "add", str(feature), "-b", "feature-x")
    slug, _ = _make_task(
        repo,
        on_final=True,
        pr_url="https://github.com/o/r/pull/24",
        branch="feature-x",
        worktree=str(feature),
    )
    _stub_pr_state(monkeypatch, {"https://github.com/o/r/pull/24": "MERGED"})
    posts = _capture_posts(monkeypatch)

    assert am.run_autoclose_recipe(load_config(repo), []) == 0

    out = capsys.readouterr().out
    assert f"the worktree belongs to `{owner.resolve()}`, not this repository" in out
    assert f"`git -C {owner.resolve()} worktree remove {feature}`" in out
    summaries = [p for p in posts if "🧹" in p]
    assert len(summaries) == 1
    assert f"`{slug}` (worktree owned by `{owner.resolve()}`" in summaries[0]
    assert f"`coga retire {slug}`" not in summaries[0]


def test_render_retire_summary_is_one_line_naming_every_command() -> None:
    summary = am.render_retire_summary(
        [_closed("alpha", branch="alpha"), _closed("beta", worktree="/w/beta")]
    )

    assert summary == (
        "🧹 2 auto-closed tickets still have a feature checkout: "
        "`coga retire alpha`, `coga retire beta`"
    )


def test_render_retire_summary_reads_naturally_for_one_ticket() -> None:
    assert am.render_retire_summary([_closed("alpha", branch="alpha")]) == (
        "🧹 1 auto-closed ticket still has a feature checkout: `coga retire alpha`"
    )


def test_recipe_reports_the_retire_followup_on_stdout_and_slack(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    slug, path = _make_task(
        repo,
        on_final=True,
        pr_url="https://github.com/o/r/pull/22",
        branch="feature-x",
        worktree="/w/coga-feature-x",
    )
    _stub_pr_state(monkeypatch, {"https://github.com/o/r/pull/22": "MERGED"})
    posts = _capture_posts(monkeypatch)

    assert am.run_autoclose_recipe(load_config(repo), []) == 0

    out = capsys.readouterr().out
    assert am.RETIRE_REPORT_HEADING in out
    assert f"`coga retire {slug}`" in out
    # Reporting the debt is not disposing of it: the ticket closes, the
    # checkout stays recorded and untouched.
    assert Ticket.read(path).status == "done"
    assert "worktree: /w/coga-feature-x" in path.read_text()
    # One trailing line for the whole sweep, addressed to the channel rather
    # than to one ticket's owner. (The `[project]` prefix `post()` prepends is
    # covered in test_notification.py, so pin the body with `endswith`.)
    summaries = [p for p in posts if "🧹" in p]
    assert len(summaries) == 1
    assert summaries[0].endswith(
        f"🧹 1 auto-closed ticket still has a feature checkout: `coga retire {slug}`"
    )


def test_recipe_says_nothing_when_no_closed_ticket_left_a_checkout(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _make_task(
        repo,
        on_final=True,
        pr_url="https://github.com/o/r/pull/23",
        branch=None,
    )
    _stub_pr_state(monkeypatch, {"https://github.com/o/r/pull/23": "MERGED"})
    posts = _capture_posts(monkeypatch)

    assert am.run_autoclose_recipe(load_config(repo), []) == 0

    assert am.RETIRE_REPORT_HEADING not in capsys.readouterr().out
    assert [p for p in posts if "🧹" in p] == []


def test_recipe_hands_back_the_result_it_already_builds(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    held, _ = _make_task(
        repo,
        title="Held",
        on_final=True,
        pr_url="https://github.com/o/r/pull/40",
        branch="feature-x",
        worktree="/w/coga-feature-x",
    )
    plain, _ = _make_task(
        repo,
        title="Plain",
        on_final=True,
        pr_url="https://github.com/o/r/pull/41",
        branch=None,
    )
    _stub_pr_state(
        monkeypatch,
        {
            "https://github.com/o/r/pull/40": "MERGED",
            "https://github.com/o/r/pull/41": "MERGED",
        },
    )
    _capture_posts(monkeypatch)

    result = am.AutocloseResult()
    assert am.run_autoclose_recipe(load_config(repo), [], result=result) == 0

    # The accumulator the wrapper used to keep private: exactly what it closed,
    # and the subset that still holds a checkout.
    assert sorted(item.slug for item in result.closed) == sorted([held, plain])
    assert [item.slug for item in result.retire_pending] == [held]
    capsys.readouterr()


def test_recipe_result_counts_the_open_tickets_it_scanned(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # The denominator for `closed`, counted in the walk the sweep already
    # makes — the caller does not enumerate every ticket a second time.
    # `done` and not-on-final tickets are outside the open set.
    merged, _ = _make_task(
        repo, title="Merged", on_final=True, pr_url="https://github.com/o/r/pull/50"
    )
    _make_task(
        repo, title="Open early", on_final=False, pr_url="https://github.com/o/r/pull/51"
    )
    _make_task(repo, title="No PR", on_final=True, pr_url=None)
    _, finished_path = _make_task(
        repo, title="Finished", on_final=True, pr_url="https://github.com/o/r/pull/52"
    )
    ticket = Ticket.read(finished_path)
    ticket.frontmatter["status"] = "done"
    ticket.write(finished_path)

    _stub_pr_state(monkeypatch, {"https://github.com/o/r/pull/50": "MERGED"})
    _capture_posts(monkeypatch)

    result = am.AutocloseResult()
    assert am.run_autoclose_recipe(load_config(repo), [], result=result) == 0

    # Three open tickets walked; the already-`done` one is not one of them.
    assert result.scanned == 3
    assert [item.slug for item in result.closed] == [merged]
    assert Ticket.read(finished_path).status == "done"
    capsys.readouterr()


def test_recipe_result_excludes_a_closure_this_sweep_did_not_make(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # A global before/after status diff would name `elsewhere` too: it is open
    # when the sweep starts and `done` when it ends. The accumulator names only
    # what this sweep closed.
    swept, _ = _make_task(
        repo, title="Swept", on_final=True, pr_url="https://github.com/o/r/pull/42"
    )
    elsewhere, elsewhere_path = _make_task(
        repo, title="Elsewhere", on_final=True, pr_url="https://github.com/o/r/pull/43"
    )
    _capture_posts(monkeypatch)

    states = {
        "https://github.com/o/r/pull/42": "MERGED",
        "https://github.com/o/r/pull/43": "OPEN",
    }

    def fake(url: str) -> str:
        if url.endswith("/42"):
            # `elsewhere` was already skipped as unmerged; a `coga mark done`
            # run by someone else lands while this sweep is still walking.
            ticket = Ticket.read(elsewhere_path)
            ticket.frontmatter["status"] = "done"
            ticket.write(elsewhere_path)
        return states[url]

    monkeypatch.setattr(am, "pr_state", fake)

    result = am.AutocloseResult()
    assert am.run_autoclose_recipe(load_config(repo), [], result=result) == 0

    assert [item.slug for item in result.closed] == [swept]
    assert Ticket.read(elsewhere_path).status == "done"
    capsys.readouterr()


def test_recipe_appends_the_report_to_the_task_blackboard(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    slug, _ = _make_task(
        repo,
        on_final=True,
        pr_url="https://github.com/o/r/pull/24",
        branch="feature-x",
    )
    # The recurring task the sweep runs under; its ticket is the blackboard
    # `coga launch` exports, and stays a draft so the sweep skips it.
    _, host = _make_task(repo, title="Autoclose merged", status="draft")
    monkeypatch.setenv("COGA_TASK_BLACKBOARD", str(host))
    monkeypatch.setenv("COGA_TASK_SLUG", "autoclose-merged")
    _stub_pr_state(monkeypatch, {"https://github.com/o/r/pull/24": "MERGED"})
    _capture_posts(monkeypatch)

    assert am.run_autoclose_recipe(load_config(repo), []) == 0

    report = host.read_text()
    assert am.RETIRE_REPORT_HEADING in report
    assert f"`coga retire {slug}`" in report
    assert "Task: `autoclose-merged`" in report
    # The blackboard is the report surface when there is one — not both.
    assert am.RETIRE_REPORT_HEADING not in capsys.readouterr().out


def test_recipe_reports_earlier_closure_when_a_later_pr_lookup_fails(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    first_slug, first_path = _make_task(
        repo,
        title="Alpha",
        on_final=True,
        pr_url="https://github.com/o/r/pull/25",
        branch="alpha-branch",
    )
    _, second_path = _make_task(
        repo,
        title="Beta",
        on_final=True,
        pr_url="https://github.com/o/r/pull/26",
        branch="beta-branch",
    )

    def state(url: str) -> str:
        if url.endswith("/25"):
            return "MERGED"
        raise am.GhError("later lookup failed")

    monkeypatch.setattr(am, "pr_state", state)
    _capture_posts(monkeypatch)

    assert am.run_autoclose_recipe(load_config(repo), []) == 2

    captured = capsys.readouterr()
    assert f"`coga retire {first_slug}`" in captured.out
    assert "[autoclose] later lookup failed" in captured.err
    assert Ticket.read(first_path).status == "done"
    assert Ticket.read(second_path).status == "active"


def test_recipe_reports_a_close_when_mark_done_fails_after_its_write(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    slug, path = _make_task(
        repo,
        on_final=True,
        pr_url="https://github.com/o/r/pull/27",
        branch="committed-branch",
    )
    _stub_pr_state(monkeypatch, {"https://github.com/o/r/pull/27": "MERGED"})
    _capture_posts(monkeypatch)
    real_mark_done = am.mark_done

    def committed_then_fails(*args, **kwargs):  # type: ignore[no-untyped-def]
        real_mark_done(*args, **kwargs)
        raise RuntimeError("failed after terminal write")

    monkeypatch.setattr(am, "mark_done", committed_then_fails)

    with pytest.raises(RuntimeError, match="failed after terminal write"):
        am.run_autoclose_recipe(load_config(repo), [])

    assert f"`coga retire {slug}`" in capsys.readouterr().out
    assert Ticket.read(path).status == "done"


def test_recipe_preflights_live_summary_before_closing(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    slug, path = _make_task(
        repo,
        on_final=True,
        pr_url="https://github.com/o/r/pull/28",
        branch="needs-summary",
    )
    _stub_pr_state(monkeypatch, {"https://github.com/o/r/pull/28": "MERGED"})
    config = repo / "coga.toml"
    config.write_text(
        config.read_text().replace("SLACK_WEBHOOK_URL", "UNSET_SLACK_WEBHOOK")
    )
    monkeypatch.delenv("UNSET_SLACK_WEBHOOK", raising=False)

    with pytest.raises(typer.Exit):
        am.run_autoclose_recipe(load_config(repo), [])

    captured = capsys.readouterr()
    assert "no webhook is configured" in captured.err
    assert am.RETIRE_REPORT_HEADING not in captured.out
    assert Ticket.read(path).status == "active"
    assert slug not in captured.out


def test_append_report_preserves_crlf_and_uses_atomic_blackboard_replace(
    repo: Path,
) -> None:
    _, host = _make_task(repo, title="CRLF host", status="draft")
    original = host.read_bytes().replace(b"\n", b"\r\n")
    host.write_bytes(original)

    am._append_blackboard_report(
        load_config(repo),
        host,
        "## Report\n\nbody\n",
    )

    assert host.read_bytes() == original + b"\r\n## Report\r\n\r\nbody\r\n"


def test_append_report_refuses_to_overwrite_a_concurrent_ticket_change(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, host = _make_task(repo, title="Racing host", status="draft")
    original_replace = blackboard_module.replace_blackboard

    def race_then_replace(
        path: Path, new_blackboard: str, *, expected_bytes: bytes | None = None
    ) -> bytes:
        path.write_bytes(path.read_bytes() + b"\nconcurrent update\n")
        return original_replace(
            path, new_blackboard, expected_bytes=expected_bytes
        )

    monkeypatch.setattr(blackboard_module, "replace_blackboard", race_then_replace)

    with pytest.raises(TaskFileError, match="ticket changed"):
        am._append_blackboard_report(load_config(repo), host, "## Report\n")

    assert host.read_text().endswith("\nconcurrent update\n")
    assert "## Report" not in host.read_text()


def test_failed_summary_delivery_is_logged_against_the_host_task(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _make_task(
        repo,
        on_final=True,
        pr_url="https://github.com/o/r/pull/29",
        branch="offline-summary",
    )
    host_slug, host = _make_task(repo, title="Autoclose host", status="draft")
    monkeypatch.setenv("COGA_TASK_BLACKBOARD", str(host))
    monkeypatch.setenv("COGA_TASK_SLUG", host_slug)
    _stub_pr_state(monkeypatch, {"https://github.com/o/r/pull/29": "MERGED"})

    def offline(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise requests.ConnectionError("offline")

    monkeypatch.setattr("coga.notification.slack.requests.post", offline)

    assert am.run_autoclose_recipe(load_config(repo), []) == 0

    from coga.logfile import task_log_lines

    assert any(
        "post failed: ConnectionError: connection failure" in line
        for line in task_log_lines(load_config(repo), host_slug)
    )


# --- the durable retire worklist ---------------------------------------------


def _make_recurring_sweep(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    template: str = "autoclose-merged",
    worktree: str = "/nowhere/coga-feature-x",
) -> tuple[str, Path, Path]:
    """Stage a merged ticket swept by a recurring *period* task.

    Mirrors the real shape: the template directory under `coga/recurring/`
    survives every period, while the period task at
    `coga/tasks/recurring/<name>/ticket.md` is deleted at the next boundary
    and is what `coga launch` exports as the blackboard.
    """
    slug, _ = _make_task(
        repo,
        on_final=True,
        pr_url="https://github.com/o/r/pull/24",
        branch="feature-x",
        worktree=worktree,
    )
    template_dir = repo / "recurring" / template
    template_dir.mkdir(parents=True)
    (template_dir / "ticket.md").write_text("template\n")
    _, period_dir = _write_workflow_less_task(
        repo, slug=f"recurring/{template}", status="in_progress"
    )
    period = period_dir / "ticket.md"
    monkeypatch.setenv("COGA_TASK_BLACKBOARD", str(period))
    monkeypatch.setenv("COGA_TASK_SLUG", f"recurring/{template}")
    _stub_pr_state(monkeypatch, {"https://github.com/o/r/pull/24": "MERGED"})
    _capture_posts(monkeypatch)
    return slug, period, template_dir / rw.RETIRE_WORKLIST_FILENAME


def test_recipe_records_the_followup_in_the_durable_worklist(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    slug, period, worklist = _make_recurring_sweep(repo, monkeypatch)

    assert am.run_autoclose_recipe(load_config(repo), []) == 0

    _, entries = rw.parse_worklist(worklist.read_text())
    assert [(e.slug, e.branch, e.worktree) for e in entries] == [
        (slug, "feature-x", "/nowhere/coga-feature-x")
    ]
    # The per-run report still lands on the period task for the run record
    # and the autofix analyst, and it names where the durable copy went.
    report = period.read_text()
    assert am.RETIRE_REPORT_HEADING in report
    assert f"`coga retire {slug}`" in report
    assert str(worklist) in report
    out = capsys.readouterr().out
    assert am.RETIRE_REPORT_HEADING not in out
    assert f"retire worklist {worklist}: 1 open, 1 recorded" in out


def test_the_worklist_survives_deleting_and_recreating_the_period_task(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    slug, period, worklist = _make_recurring_sweep(repo, monkeypatch)
    assert am.run_autoclose_recipe(load_config(repo), []) == 0
    capsys.readouterr()

    # What `coga recurring` does at the next period boundary: delete the
    # prior-period task, then create a fresh one at the same stable path.
    period.unlink()
    period.parent.rmdir()
    assert slug in worklist.read_text()
    _write_workflow_less_task(
        repo, slug="recurring/autoclose-merged", status="in_progress"
    )

    # The next period closes nothing, so it only reconciles: the entry is
    # still live (its branch cannot be checked here, so it is kept) and the
    # fresh period task gets no report.
    assert am.run_autoclose_recipe(load_config(repo), []) == 0

    assert slug in worklist.read_text()
    assert am.RETIRE_REPORT_HEADING not in period.read_text()
    assert f"retire worklist {worklist}: 1 open" in capsys.readouterr().out


def test_a_rerun_that_strands_the_same_slug_keeps_one_entry_and_its_date(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    slug, _, worklist = _make_recurring_sweep(repo, monkeypatch)
    assert am.run_autoclose_recipe(load_config(repo), []) == 0
    first = worklist.read_bytes()
    capsys.readouterr()

    # The same ticket, stranded again by a later sweep with a different date.
    change = rw.reconcile_worklist(
        load_config(repo),
        worklist,
        root=repo,
        pending=[
            rw.RetireFollowUp(
                slug=slug,
                branch="feature-x",
                worktree="/nowhere/coga-feature-x",
                recorded="2099-01-01",
            )
        ],
    )

    assert not change.written
    assert worklist.read_bytes() == first
    assert worklist.read_text().count(f"`{slug}`") == 1


def test_a_recurring_run_drops_discharged_debt_and_keeps_live_debt(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    slug, _, worklist = _make_recurring_sweep(repo, monkeypatch)
    still_here = tmp_path / "still-here"
    still_here.mkdir()
    worklist.write_text(
        rw.RETIRE_WORKLIST_HEADER
        + "\n"
        + rw.RetireFollowUp("retired", "", str(tmp_path / "absent"), "2026-09-01").render()
        + "\n"
        + rw.RetireFollowUp("stranded", "", str(still_here), "2026-09-01").render()
        + "\n"
    )

    assert am.run_autoclose_recipe(load_config(repo), []) == 0

    _, entries = rw.parse_worklist(worklist.read_text())
    assert sorted(e.slug for e in entries) == sorted([slug, "stranded"])
    out = capsys.readouterr().out
    assert "2 open, 1 recorded, 1 discharged (`retired`)" in out


def test_a_non_recurring_task_keeps_the_ordinary_blackboard_surface(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    slug, _ = _make_task(
        repo,
        on_final=True,
        pr_url="https://github.com/o/r/pull/24",
        branch="feature-x",
    )
    (repo / "recurring" / "autoclose-merged").mkdir(parents=True)
    (repo / "recurring" / "autoclose-merged" / "ticket.md").write_text("t\n")
    _, host = _make_task(repo, title="Autoclose merged", status="draft")
    monkeypatch.setenv("COGA_TASK_BLACKBOARD", str(host))
    monkeypatch.setenv("COGA_TASK_SLUG", "autoclose-merged")
    _stub_pr_state(monkeypatch, {"https://github.com/o/r/pull/24": "MERGED"})
    _capture_posts(monkeypatch)

    assert am.run_autoclose_recipe(load_config(repo), []) == 0

    assert f"`coga retire {slug}`" in host.read_text()
    assert not (repo / "recurring" / "autoclose-merged" / "retires.md").exists()
    assert "retire worklist" not in capsys.readouterr().out


def test_a_run_with_no_task_keeps_stdout_and_touches_no_worklist(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    slug, _ = _make_task(
        repo, on_final=True, pr_url="https://github.com/o/r/pull/24", branch="feature-x"
    )
    (repo / "recurring" / "autoclose-merged").mkdir(parents=True)
    (repo / "recurring" / "autoclose-merged" / "ticket.md").write_text("t\n")
    _stub_pr_state(monkeypatch, {"https://github.com/o/r/pull/24": "MERGED"})
    _capture_posts(monkeypatch)

    assert am.run_autoclose_recipe(load_config(repo), []) == 0

    out = capsys.readouterr().out
    assert f"`coga retire {slug}`" in out
    assert "retire worklist" not in out
    assert not (repo / "recurring" / "autoclose-merged" / "retires.md").exists()


def test_a_period_task_inherited_from_another_checkout_selects_no_worklist(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    # A nested `coga run autoclose` inherits the outer session's period task;
    # `blackboard_from_env` already refuses it as outside this root, and the
    # worklist derivation follows that verdict rather than the slug.
    slug, _ = _make_task(
        repo, on_final=True, pr_url="https://github.com/o/r/pull/24", branch="feature-x"
    )
    (repo / "recurring" / "autoclose-merged").mkdir(parents=True)
    (repo / "recurring" / "autoclose-merged" / "ticket.md").write_text("t\n")
    other = tmp_path / "other" / "coga" / "tasks" / "recurring" / "autoclose-merged"
    other.mkdir(parents=True)
    (other / "ticket.md").write_text("outer\n")
    monkeypatch.setenv("COGA_TASK_BLACKBOARD", str(other / "ticket.md"))
    monkeypatch.setenv("COGA_TASK_SLUG", "recurring/autoclose-merged")
    _stub_pr_state(monkeypatch, {"https://github.com/o/r/pull/24": "MERGED"})
    _capture_posts(monkeypatch)

    assert am.run_autoclose_recipe(load_config(repo), []) == 0

    assert f"`coga retire {slug}`" in capsys.readouterr().out
    assert not (repo / "recurring" / "autoclose-merged" / "retires.md").exists()


def test_a_corrupt_worklist_fails_the_run_loudly_after_closing(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    slug, period, worklist = _make_recurring_sweep(repo, monkeypatch)
    posts = _capture_posts(monkeypatch)
    worklist.write_text("# Someone else's file\n")

    assert am.run_autoclose_recipe(load_config(repo), []) == 2

    captured = capsys.readouterr()
    assert "retire worklist has no" in captured.err
    assert worklist.read_text() == "# Someone else's file\n"
    # The closure itself is not undone by a reporting failure.
    from coga.tasks import resolve_task

    assert Ticket.read(resolve_task(load_config(repo), slug).ticket_path).status == "done"
    # The per-run surfaces the durable one was added *beside* still get the
    # follow-up: the ticket is done on disk, so a refused worklist must not
    # leave the retire recorded nowhere. The report does not claim a durable
    # copy that was never written.
    report = period.read_text()
    assert f"`coga retire {slug}`" in report
    assert str(worklist) not in report
    assert any(f"`coga retire {slug}`" in text for text in posts)


def test_a_corrupt_worklist_is_reported_when_the_sweep_itself_fails(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The worklist failure must not escape the handler reporting a gh error."""
    slug, period, worklist = _make_recurring_sweep(repo, monkeypatch)
    worklist.write_text("# Someone else's file\n")
    real_bump = am.mark_done

    def close_then_break(*args, **kwargs):
        result = real_bump(*args, **kwargs)
        raise am.GhError("gh fell over after the close")

    monkeypatch.setattr(am, "mark_done", close_then_break)

    assert am.run_autoclose_recipe(load_config(repo), []) == 2

    captured = capsys.readouterr()
    assert "retire worklist has no" in captured.err
    assert "gh fell over after the close" in captured.err
    assert f"`coga retire {slug}`" in period.read_text()


@pytest.mark.parametrize("failure", ["read", "write", "decode", "disk-full"])
@pytest.mark.parametrize("sweep_error", [None, am.GhError, RuntimeError])
def test_worklist_io_failure_preserves_followups_and_original_sweep_error(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    failure: str,
    sweep_error: type[Exception] | None,
) -> None:
    slug, period, worklist = _make_recurring_sweep(repo, monkeypatch)
    posts = _capture_posts(monkeypatch)
    if failure == "read":
        worklist.write_text(rw.RETIRE_WORKLIST_HEADER)
        read_bytes = Path.read_bytes

        def denied_read(path: Path) -> bytes:
            if path == worklist:
                raise PermissionError("worklist read denied")
            return read_bytes(path)

        monkeypatch.setattr(Path, "read_bytes", denied_read)
        diagnostic = "worklist read denied"
    elif failure in {"write", "disk-full"}:
        def failed_write(*args: Any, **kwargs: Any) -> None:
            raise OSError("worklist disk full")

        monkeypatch.setattr(rw, "atomic_write_text", failed_write)
        if failure == "disk-full":
            monkeypatch.setattr(am, "_append_blackboard_report", failed_write)
        diagnostic = "worklist disk full"
    else:
        worklist.write_bytes(b"\xff")
        diagnostic = "utf-8"

    if sweep_error is not None:
        mark_done = am.mark_done

        def close_then_fail(*args: Any, **kwargs: Any) -> None:
            mark_done(*args, **kwargs)
            raise sweep_error("original sweep failure")

        monkeypatch.setattr(am, "mark_done", close_then_fail)

    cfg = load_config(repo)
    if sweep_error is RuntimeError:
        with pytest.raises(RuntimeError, match="original sweep failure"):
            am.run_autoclose_recipe(cfg, [])
    else:
        assert am.run_autoclose_recipe(cfg, []) == 2

    from coga.tasks import resolve_task

    assert Ticket.read(resolve_task(cfg, slug).ticket_path).status == "done"
    captured = capsys.readouterr()
    assert diagnostic in captured.err
    if sweep_error is am.GhError:
        assert "original sweep failure" in captured.err
    report = captured.out if failure == "disk-full" else period.read_text()
    assert f"`coga retire {slug}`" in report
    assert "Recorded in the durable worklist" not in report
    assert any(f"`coga retire {slug}`" in text for text in posts)


# --- status stays read-only --------------------------------------------------


def test_coga_status_does_not_auto_bump(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # `status` is read-only: a merged PR on a final-step ticket must NOT be
    # bumped as a side effect of rendering. Catching up is the autoclose
    # sweep's job (principle 6, fail loud — `status` never mutates state).
    slug, path = _make_task(
        repo, on_final=True, pr_url="https://github.com/o/r/pull/40"
    )
    _stub_pr_state(monkeypatch, {"https://github.com/o/r/pull/40": "MERGED"})

    runner = CliRunner()
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0, result.output
    # Ticket is untouched — still active, never marked done.
    assert Ticket.read(path).status == "active"


def test_coga_status_never_calls_gh(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # `status` must never hit the network — even a final-step ticket with a
    # PR link should not trigger a `gh` lookup. If it did, this stub would
    # raise and the ticket would still be left untouched.
    slug, path = _make_task(
        repo, on_final=True, pr_url="https://github.com/o/r/pull/50"
    )

    def boom(url: str) -> str:
        raise AssertionError("status must not call gh / pr_state")

    monkeypatch.setattr(am, "pr_state", boom)

    runner = CliRunner()
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0, result.output
    assert Ticket.read(path).status == "active"
