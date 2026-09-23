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


def _stub_review_threads(
    monkeypatch: pytest.MonkeyPatch,
    mapping: dict[str, list[am.ReviewThread]] | None = None,
) -> list[str]:
    """Patch the per-closure `reviewThreads` fetch. Returns the URLs asked.

    Defaults every PR to "no unanswered thread", so a sweep test that is not
    about threads never reaches a real `gh api graphql`.
    """
    calls: list[str] = []
    threads = mapping or {}

    def fake(url: str) -> list[am.ReviewThread]:
        calls.append(url)
        return list(threads.get(url, []))

    monkeypatch.setattr(am, "unanswered_review_threads", fake)
    return calls


def _stub_pr_state(monkeypatch: pytest.MonkeyPatch, mapping: dict[str, str]) -> list[str]:
    """Patch `pr_state` to return states from `mapping`. Returns calls list.

    Also stubs the review-thread fetch to find nothing; a test about threads
    layers `_stub_review_threads` with a mapping on top.
    """
    calls: list[str] = []

    def fake(url: str) -> str:
        calls.append(url)
        if url not in mapping:
            raise am.GhError(f"unknown PR url: {url}")
        return mapping[url]

    monkeypatch.setattr(am, "pr_state", fake)
    _stub_review_threads(monkeypatch)
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
    _stub_review_threads(monkeypatch)
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
    pr_url: str = "https://github.com/o/r/pull/1",
    threads: tuple[am.ReviewThread, ...] = (),
) -> am.ClosedTicket:
    return am.ClosedTicket(
        slug=slug,
        title="Work",
        branch=branch,
        worktree=worktree,
        pr=pr_url,
        unanswered_threads=threads,
    )


def _thread(
    path: str = "src/coga/x.py",
    line: int | None = 42,
    *,
    author: str = "coderabbitai",
    url: str = "https://github.com/o/r/pull/1#discussion_r1",
    excerpt: str = "Consider a bound here.",
) -> am.ReviewThread:
    return am.ReviewThread(
        path=path, line=line, author=author, url=url, excerpt=excerpt
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


def test_render_retire_report_names_the_exact_retire_command_when_disposal_skipped() -> None:
    # The disposal phase never ran (off the control branch, sweep failure, no
    # git), so the report falls back to naming the manual command per ticket.
    report = am.render_retire_report(
        generated_at="2026-08-14T08:00:00+00:00",
        task_slug="recurring/autoclose-merged",
        checkouts=[],
        pending=[_closed("fix-thing", branch="fix-thing", worktree="/w/coga-fix")],
        skipped="checkout is on 'feature', not the control branch 'main'",
    )

    assert report.startswith(am.RETIRE_REPORT_HEADING)
    assert "Generated: 2026-08-14T08:00:00+00:00" in report
    assert "Task: `recurring/autoclose-merged`" in report
    assert "Checkout disposal skipped (checkout is on 'feature'" in report
    assert (
        '- `fix-thing` "Work": worktree `/w/coga-fix`, branch `fix-thing` — '
        "`coga retire fix-thing`" in report
    )


def _outcome(
    slug: str,
    *,
    title: str | None = "Work",
    ticket_exists: bool = True,
    worktree_removed: bool,
    branch_remains: bool,
    notes: list[str] | None = None,
) -> am.CheckoutOutcome:
    from coga.branchcleanup import WorktreeCleanupResult
    from coga.checkout_disposal import CheckoutDisposal

    worktree_result = WorktreeCleanupResult(
        worktree=f"/w/{slug}", removed=worktree_removed, notes=list(notes or [])
    )
    disposal = CheckoutDisposal(
        branch=slug,
        worktree=f"/w/{slug}",
        notes=list(notes or []),
        worktree_result=worktree_result,
        local_branch_remains=branch_remains,
    )
    return am.CheckoutOutcome(
        slug=slug,
        title=title,
        branch=slug,
        worktree=f"/w/{slug}",
        ticket_exists=ticket_exists,
        disposal=disposal,
    )


def test_render_retire_report_lists_disposed_and_preserved_with_reasons() -> None:
    disposed = _outcome("gone", worktree_removed=True, branch_remains=False)
    preserved = _outcome(
        "kept",
        title=None,
        ticket_exists=False,
        worktree_removed=False,
        branch_remains=True,
        notes=[
            "Worktree cleanup: '/w/kept' contains tracked or untracked local "
            "state ('?? scratch.txt') — left in place.",
        ],
    )

    report = am.render_retire_report(
        generated_at="2026-09-18T08:00:00+00:00",
        task_slug="recurring/autoclose-merged",
        checkouts=[disposed, preserved],
        worklist=Path("/repo/coga/recurring/autoclose-merged/retires.md"),
    )

    assert "1 checkout(s) disposed of" in report
    assert '- `gone` "Work": worktree `/w/gone`, branch `gone`' in report
    assert "1 checkout(s) preserved" in report
    # A backlog entry whose ticket is gone names the manual path, not a retire
    # command that no longer resolves; the proof note travels with it.
    assert (
        "- `kept` (worklist backlog, ticket already deleted): worktree `/w/kept`, "
        "branch `kept` — '/w/kept' contains tracked or untracked local state "
        "('?? scratch.txt') — left in place. (dispose of the recorded worktree "
        "and branch by hand)"
    ) in report
    assert "  - Worktree cleanup: '/w/kept' contains" in report
    assert "Recorded in the durable worklist `/repo/coga/recurring/autoclose-merged/retires.md`" in report


def test_render_disposed_and_preserved_summaries() -> None:
    disposed = _outcome("gone", worktree_removed=True, branch_remains=False)
    preserved = _outcome(
        "kept",
        worktree_removed=False,
        branch_remains=True,
        notes=["Worktree cleanup: '/w/kept' is a symlink — left in place."],
    )

    assert am.render_disposed_summary([disposed]) == (
        "🧹 Autoclose disposed of 1 feature checkout (worktree and branch): `gone`"
    )
    assert am.render_preserved_summary([preserved]) == (
        "⚠️ 1 feature checkout needs a human — autoclose could not dispose of it: "
        "`kept` (worktree `/w/kept`, branch `kept`): '/w/kept' is a symlink — "
        "left in place."
    )


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


def _graphql_page(
    nodes: list[dict[str, object]], *, next_cursor: str | None = None
) -> str:
    import json

    return json.dumps(
        {
            "data": {
                "repository": {
                    "pullRequest": {
                        "reviewThreads": {
                            "pageInfo": {
                                "hasNextPage": next_cursor is not None,
                                "endCursor": next_cursor,
                            },
                            "nodes": nodes,
                        }
                    }
                }
            }
        }
    )


def _thread_node(
    *,
    resolved: bool = False,
    outdated: bool = False,
    comments: int = 1,
    path: str = "src/coga/x.py",
    line: int | None = 42,
    original_line: int | None = 40,
    body: str = "Consider a bound here.",
    login: str | None = "coderabbitai",
    url: str = "https://github.com/o/r/pull/1#discussion_r1",
) -> dict[str, object]:
    return {
        "isResolved": resolved,
        "isOutdated": outdated,
        "path": path,
        "line": line,
        "originalLine": original_line,
        "comments": {
            "totalCount": comments,
            "nodes": [
                {
                    "body": body,
                    "url": url,
                    "author": {"login": login} if login is not None else None,
                }
            ],
        },
    }


def _stub_graphql(
    monkeypatch: pytest.MonkeyPatch, pages: list[str]
) -> list[list[str]]:
    """Serve `gh api graphql` one canned page per call. Returns the argvs."""
    calls: list[list[str]] = []
    remaining = list(pages)

    def fake_run(argv, **kwargs):  # type: ignore[no-untyped-def]
        calls.append(list(argv))
        assert argv[:3] == ["gh", "api", "graphql"]
        return subprocess.CompletedProcess(argv, 0, stdout=remaining.pop(0), stderr="")

    monkeypatch.setattr(am.subprocess, "run", fake_run)
    return calls


def test_unanswered_review_threads_keeps_only_unresolved_current_reply_less(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The four exclusions the decision names: a resolved thread is a human
    # verdict, an outdated one already moved, a replied-to one was seen. Only
    # the untouched thread is reported.
    _stub_graphql(
        monkeypatch,
        [
            _graphql_page(
                [
                    _thread_node(resolved=True, path="a.py"),
                    _thread_node(outdated=True, path="b.py"),
                    _thread_node(comments=2, path="c.py"),
                    _thread_node(path="d.py", line=7, body="  \nFirst line.\nSecond."),
                ]
            )
        ],
    )

    threads = am.unanswered_review_threads("https://github.com/o/r/pull/1")

    assert threads == [
        am.ReviewThread(
            path="d.py",
            line=7,
            author="coderabbitai",
            url="https://github.com/o/r/pull/1#discussion_r1",
            excerpt="First line.",
        )
    ]


@pytest.mark.parametrize(
    ("host", "owner", "repo_name"),
    [
        ("github.com", "o", "r"),
        ("ghe.example.com", "enterprise", "project"),
        ("github.com", "123", "true"),
        ("github.com", "true", "null"),
    ],
)
def test_unanswered_review_threads_paginates_and_passes_base_repo_coordinates(
    monkeypatch: pytest.MonkeyPatch, host: str, owner: str, repo_name: str,
) -> None:
    monkeypatch.setenv("GH_HOST", "another.example.com")
    calls = _stub_graphql(
        monkeypatch,
        [
            _graphql_page([_thread_node(path="first.py")], next_cursor="C1"),
            _graphql_page([_thread_node(path="second.py")]),
        ],
    )

    threads = am.unanswered_review_threads(
        f"https://{host}/{owner}/{repo_name}/pull/12"
    )

    assert [t.path for t in threads] == ["first.py", "second.py"]
    assert len(calls) == 2
    # Each page must use the URL's host even when GH_HOST differs. Owner and
    # repo are strings: gh's typed -F would turn names like 123/true into
    # non-string values rejected by GraphQL's String! variables.
    for argv in calls:
        assert argv[3:5] == ["--hostname", host]
        assert argv[5:11] == [
            "-f", f"owner={owner}", "-f", f"repo={repo_name}", "-F", "number=12",
        ]
    assert "-F" in calls[0] and "cursor=C1" not in calls[0]
    assert calls[1][-2:] == ["-F", "cursor=C1"]


def test_unanswered_review_threads_falls_back_to_original_line_and_unknown_author(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A thread on a line GitHub can no longer place reports `line: null`; a
    # deleted account reports `author: null`. Neither may hide the thread.
    _stub_graphql(
        monkeypatch,
        [_graphql_page([_thread_node(line=None, original_line=9, login=None)])],
    )

    [thread] = am.unanswered_review_threads("https://github.com/o/r/pull/1")

    assert thread.location == "src/coga/x.py:9"
    assert thread.author == "unknown"


def test_unanswered_review_threads_excerpt_strips_bot_badge_markup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The Codex reviewer's opening line, verbatim from PR 699: the badge's alt
    # text is the priority, the rest is markup.
    body = (
        "**<sub><sub>![P1 Badge](https://img.shields.io/badge/P1-orange?style=flat)"
        "</sub></sub>  Revalidate control before trusting the pre-scan ledger**\n\n"
        "When another checkout publishes…"
    )
    _stub_graphql(monkeypatch, [_graphql_page([_thread_node(body=body)])])

    [thread] = am.unanswered_review_threads("https://github.com/o/r/pull/1")

    assert thread.excerpt == (
        "P1 Badge Revalidate control before trusting the pre-scan ledger"
    )


def test_unanswered_review_threads_clips_a_long_opening_line(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_graphql(monkeypatch, [_graphql_page([_thread_node(body="x" * 200)])])

    [thread] = am.unanswered_review_threads("https://github.com/o/r/pull/1")

    assert len(thread.excerpt) == 80
    assert thread.excerpt.endswith("…")


def test_pr_review_threads_raises_gh_error_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def failing(argv, **kwargs):  # type: ignore[no-untyped-def]
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="gh: boom")

    monkeypatch.setattr(am.subprocess, "run", failing)

    with pytest.raises(am.GhError, match="reviewThreads of .*pull/1.*gh: boom"):
        am.pr_review_threads("https://github.com/o/r/pull/1")


def test_pr_review_threads_rejects_a_url_without_repository_coordinates() -> None:
    with pytest.raises(am.GhError, match="cannot derive owner/repo/number"):
        am.pr_review_threads("https://example.invalid/pull/1")


def test_sweep_fetches_threads_once_per_closed_pr_and_records_them(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    url = "https://github.com/o/r/pull/30"
    slug, _ = _make_task(repo, on_final=True, pr_url=url)
    _, open_path = _make_task(
        repo, title="Open", on_final=True, pr_url="https://github.com/o/r/pull/31"
    )
    _stub_pr_state(monkeypatch, {url: "MERGED", "https://github.com/o/r/pull/31": "OPEN"})
    asked = _stub_review_threads(monkeypatch, {url: [_thread()]})

    cfg = load_config(repo)
    result = am.sweep_merged(cfg, quiet=True)

    # One fetch, only for the PR that actually closed a ticket: an open PR's
    # threads are still the review step's business, not the sweep's.
    assert asked == [url]
    assert [
        (item.slug, item.unanswered_threads) for item in result.review_threads_pending
    ] == [(slug, (_thread(),))]
    assert Ticket.read(open_path).status == "active"
    # The audit line is the durable surface; it names the location.
    from coga.logfile import task_log_lines

    log = "\n".join(task_log_lines(cfg, slug))
    assert (
        "auto-bumped on merge of PR #30 → done; 1 unanswered review thread: "
        "src/coga/x.py:42" in log
    )


@pytest.mark.parametrize("status", ["done", "paused", "canceled"])
def test_sweep_preserves_a_transition_during_review_thread_lookup(
    repo: Path, monkeypatch: pytest.MonkeyPatch, status: str
) -> None:
    url = "https://github.com/o/r/pull/30"
    slug, path = _make_task(
        repo, status="in_progress", on_final=True, pr_url=url
    )
    _stub_pr_state(monkeypatch, {url: "MERGED"})

    def concurrent_transition(url: str) -> list[am.ReviewThread]:
        args = ["mark", status, slug]
        if status == "canceled":
            args.extend(["--message", "Obsolete work"])
        completed = CliRunner().invoke(app, args)
        assert completed.exit_code == 0, completed.output
        return [_thread()]

    monkeypatch.setattr(am, "unanswered_review_threads", concurrent_transition)

    cfg = load_config(repo)
    result = am.sweep_merged(cfg, quiet=True)

    assert Ticket.read(path).status == status
    assert result.closed == []
    from coga.logfile import task_log_lines

    assert "auto-bumped" not in "\n".join(task_log_lines(cfg, slug))


def test_sweep_audit_line_stays_plain_without_unanswered_threads(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    url = "https://github.com/o/r/pull/32"
    slug, _ = _make_task(repo, on_final=True, pr_url=url)
    _stub_pr_state(monkeypatch, {url: "MERGED"})

    cfg = load_config(repo)
    result = am.sweep_merged(cfg, quiet=True)

    assert result.review_threads_pending == []
    from coga.logfile import task_log_lines

    log = "\n".join(task_log_lines(cfg, slug))
    assert "auto-bumped on merge of PR #32 → done\n" in log + "\n"
    assert "review thread" not in log


def test_sweep_thread_fetch_failure_leaves_the_ticket_open(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The lookup runs before the close on purpose: failing it must not close
    # the ticket without its report, which is the silence this feature ends.
    # The ticket stays open and the next sweep retries.
    url = "https://github.com/o/r/pull/33"
    _, path = _make_task(repo, on_final=True, pr_url=url)
    _stub_pr_state(monkeypatch, {url: "MERGED"})

    def boom(url: str) -> list[am.ReviewThread]:
        raise am.GhError("graphql: boom")

    monkeypatch.setattr(am, "unanswered_review_threads", boom)

    with pytest.raises(am.GhError, match="graphql: boom"):
        am.sweep_merged(load_config(repo), quiet=False)

    assert Ticket.read(path).status == "active"


def test_render_review_threads_report_names_location_author_excerpt_and_link() -> None:
    report = am.render_review_threads_report(
        generated_at="2026-09-15T08:00:00+00:00",
        task_slug="recurring/autoclose-merged",
        pending=[
            _closed(
                "fix-thing",
                pr_url="https://github.com/o/r/pull/7",
                threads=(_thread(), _thread("b.py", None, excerpt="")),
            )
        ],
    )

    assert report.startswith(am.REVIEW_THREADS_REPORT_HEADING)
    assert "Generated: 2026-09-15T08:00:00+00:00" in report
    assert "Task: `recurring/autoclose-merged`" in report
    assert "Autoclose only names them" in report
    assert '- `fix-thing` "Work" — PR #7:\n' in report
    assert (
        '  - `src/coga/x.py:42` by @coderabbitai: "Consider a bound here." — '
        "https://github.com/o/r/pull/1#discussion_r1\n" in report
    )
    assert "  - `b.py` by @coderabbitai: — https://github.com/o/r/pull/1#discussion_r1\n" in report


def test_render_review_threads_summary_is_one_line_linking_every_thread() -> None:
    summary = am.render_review_threads_summary(
        [
            _closed(
                "alpha",
                pr_url="https://github.com/o/r/pull/7",
                threads=(
                    _thread("a.py", 1, url="https://github.com/o/r/pull/7#discussion_r1"),
                    _thread("b.py", 2, url="https://github.com/o/r/pull/7#discussion_r2"),
                ),
            ),
            _closed(
                "beta",
                pr_url="https://github.com/o/r/pull/8",
                threads=(_thread("c.py", 3, url="https://github.com/o/r/pull/8#discussion_r3"),),
            ),
        ]
    )

    assert summary == (
        "🧵 2 auto-closed tickets merged with unanswered review threads: "
        "<https://github.com/o/r/pull/7|PR #7> "
        "<https://github.com/o/r/pull/7#discussion_r1|a.py:1>, "
        "<https://github.com/o/r/pull/7#discussion_r2|b.py:2>; "
        "<https://github.com/o/r/pull/8|PR #8> "
        "<https://github.com/o/r/pull/8#discussion_r3|c.py:3>"
    )


def test_render_review_threads_summary_reads_naturally_for_one_ticket() -> None:
    assert am.render_review_threads_summary(
        [_closed("alpha", pr_url="https://github.com/o/r/pull/7", threads=(_thread(),))]
    ) == (
        "🧵 1 auto-closed ticket merged with an unanswered review thread: "
        "<https://github.com/o/r/pull/7|PR #7> "
        "<https://github.com/o/r/pull/1#discussion_r1|src/coga/x.py:42>"
    )


def test_recipe_reports_unanswered_threads_on_stdout_and_slack_without_touching_them(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    url = "https://github.com/o/r/pull/34"
    slug, path = _make_task(repo, on_final=True, pr_url=url, branch=None)
    _stub_pr_state(monkeypatch, {url: "MERGED"})
    _stub_review_threads(monkeypatch, {url: [_thread()]})
    posts = _capture_posts(monkeypatch)
    gh_calls: list[list[str]] = []
    real_run = subprocess.run

    def record_gh(argv, **kwargs):  # type: ignore[no-untyped-def]
        if argv and argv[0] == "gh":
            gh_calls.append(list(argv))
        return real_run(argv, **kwargs)

    monkeypatch.setattr(am.subprocess, "run", record_gh)

    assert am.run_autoclose_recipe(load_config(repo), []) == 0

    out = capsys.readouterr().out
    assert am.REVIEW_THREADS_REPORT_HEADING in out
    assert f'- `{slug}` "Work" — PR #34:' in out
    assert "`src/coga/x.py:42` by @coderabbitai" in out
    # No checkout was recorded, so the retire section stays silent: the two
    # follow-ups are independent.
    assert am.RETIRE_REPORT_HEADING not in out
    assert Ticket.read(path).status == "done"
    summaries = [p for p in posts if "🧵" in p]
    assert len(summaries) == 1
    assert summaries[0].endswith(
        "🧵 1 auto-closed ticket merged with an unanswered review thread: "
        f"<{url}|PR #34> <https://github.com/o/r/pull/1#discussion_r1|src/coga/x.py:42>"
    )
    # Report-only: nothing resolved, nothing replied — no `gh` mutation ran.
    assert gh_calls == []


def test_recipe_reports_both_followups_when_a_closure_has_both(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    url = "https://github.com/o/r/pull/35"
    slug, _ = _make_task(repo, on_final=True, pr_url=url, branch="feature-y")
    _stub_pr_state(monkeypatch, {url: "MERGED"})
    _stub_review_threads(monkeypatch, {url: [_thread()]})
    posts = _capture_posts(monkeypatch)

    assert am.run_autoclose_recipe(load_config(repo), []) == 0

    out = capsys.readouterr().out
    assert out.index(am.RETIRE_REPORT_HEADING) < out.index(
        am.REVIEW_THREADS_REPORT_HEADING
    )
    assert f"`coga retire {slug}`" in out
    # One trailing line per follow-up, in the same order as the report.
    followups = [p for p in posts if "🧹" in p or "🧵" in p]
    assert len(followups) == 2
    assert "🧹" in followups[0] and "🧵" in followups[1]


def test_recipe_appends_the_review_threads_report_to_the_task_blackboard(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    url = "https://github.com/o/r/pull/36"
    slug, _ = _make_task(repo, on_final=True, pr_url=url, branch=None)
    _, host = _make_task(repo, title="Autoclose merged", status="draft")
    monkeypatch.setenv("COGA_TASK_BLACKBOARD", str(host))
    monkeypatch.setenv("COGA_TASK_SLUG", "autoclose-merged")
    _stub_pr_state(monkeypatch, {url: "MERGED"})
    _stub_review_threads(monkeypatch, {url: [_thread()]})
    _capture_posts(monkeypatch)

    assert am.run_autoclose_recipe(load_config(repo), []) == 0

    report = host.read_text()
    assert am.REVIEW_THREADS_REPORT_HEADING in report
    assert f'- `{slug}` "Work" — PR #36:' in report
    assert "Task: `autoclose-merged`" in report
    assert am.REVIEW_THREADS_REPORT_HEADING not in capsys.readouterr().out


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
    _stub_review_threads(monkeypatch)

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
    _stub_review_threads(monkeypatch)
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


@pytest.mark.parametrize("failure", [OSError("disk full"), UnicodeError("bad text")])
def test_review_report_write_failure_keeps_stdout_and_slack_and_fails_recipe(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
    failure: Exception,
) -> None:
    url = "https://github.com/o/r/pull/36"
    _, path = _make_task(repo, on_final=True, pr_url=url, branch=None)
    _, host = _make_task(repo, title="Autoclose merged", status="draft")
    monkeypatch.setenv("COGA_TASK_BLACKBOARD", str(host))
    _stub_pr_state(monkeypatch, {url: "MERGED"})
    _stub_review_threads(monkeypatch, {url: [_thread()]})
    posts = _capture_posts(monkeypatch)

    def fail_append(*args, **kwargs):
        raise failure

    monkeypatch.setattr(am, "_append_blackboard_report", fail_append)
    assert am.run_autoclose_recipe(load_config(repo), []) == 2
    output = capsys.readouterr()
    assert am.REVIEW_THREADS_REPORT_HEADING in output.out
    assert "could not write review thread report" in output.err
    assert any("🧵" in post for post in posts)
    assert Ticket.read(path).status == "done"


def test_retire_reporting_failure_does_not_suppress_review_threads(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    url = "https://github.com/o/r/pull/36"
    _make_task(repo, on_final=True, pr_url=url, branch=None)
    _stub_pr_state(monkeypatch, {url: "MERGED"})
    _stub_review_threads(monkeypatch, {url: [_thread()]})
    posts = _capture_posts(monkeypatch)
    monkeypatch.setattr(am, "_report_retire_followups", lambda *args: False)
    assert am.run_autoclose_recipe(load_config(repo), []) == 2
    assert am.REVIEW_THREADS_REPORT_HEADING in capsys.readouterr().out
    assert any("🧵" in post for post in posts)
