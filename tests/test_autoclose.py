from __future__ import annotations

import subprocess
from pathlib import Path
from textwrap import dedent

import pytest
import requests
import typer
from typer.testing import CliRunner

from coga import autoclose as am
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
        slug: {slug}
        title: Work
        status: {status}
        owner: marc
        human: marc
        agent: claude
        assignee: claude
        contexts: []
        skills: []
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
          - name: review
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
            cfg=cfg, title=title, workflow_name=workflow,
            contexts=[], owner="marc", assignee="claude",
            watchers=[], status=status,
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
    "value", ["(not opened yet)", "none - blocked on CI", "TBD", "see the other ticket"]
)
def test_parse_pr_url_placeholder_value_is_none(value: str) -> None:
    # `parse_worktree_path` rejects placeholders the same way. Unguarded, the
    # unanchored capture would hand `(not` / `none` to `gh pr view`, whose
    # GhError aborts the whole sweep (exit 2) — trading one silently skipped
    # ticket for a failure on every remaining one.
    text = f"## Dev\n\npr: {value}\n"
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
    slug: str, *, branch: str | None = None, worktree: str | None = None
) -> am.ClosedTicket:
    return am.ClosedTicket(slug=slug, title="Work", branch=branch, worktree=worktree)


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

    am._append_blackboard_report(host, "## Report\n\nbody\n")

    assert host.read_bytes() == original + b"\r\n## Report\r\n\r\nbody\r\n"


def test_append_report_refuses_to_overwrite_a_concurrent_ticket_change(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, host = _make_task(repo, title="Racing host", status="draft")
    original_replace = am.replace_blackboard

    def race_then_replace(
        path: Path, new_blackboard: str, *, expected_bytes: bytes | None = None
    ) -> bytes:
        path.write_bytes(path.read_bytes() + b"\nconcurrent update\n")
        return original_replace(
            path, new_blackboard, expected_bytes=expected_bytes
        )

    monkeypatch.setattr(am, "replace_blackboard", race_then_replace)

    with pytest.raises(TaskFileError, match="ticket changed"):
        am._append_blackboard_report(host, "## Report\n")

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
