from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

from relay import autoclose as am
from relay.cli import app
from relay.config import load_config
from relay.create import create_task
from relay.ticket import Ticket


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
        autonomy: interactive
        owner: marc
        human: marc
        agent: claude
        assignee: claude
        contexts: []
        skills: []
        workflow: null
        ---

        ## Description

        <!-- relay:blackboard -->

        # Blackboard
    """).lstrip())
    return slug, task_dir


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    company = tmp_path / "relay-os"
    _write(
        company / "relay.toml",
        """
        version = 1
        default_status = "draft"
        [slack]
        webhook = "env:SLACK_WEBHOOK_URL"
        [agents.claude]
        cli = "claude"
        auto = "-p"
        file = "CLAUDE.md"
        """,
    )
    _write(company / "relay.local.toml", 'user = "marc"\n')
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
        """,
    )
    monkeypatch.chdir(company)
    return company


def _make_task(
    repo: Path,
    *,
    workflow: str | None = "code",
    status: str = "active",
    on_final: bool = False,
    pr_url: str | None = None,
) -> tuple[str, Path]:
    cfg = load_config(repo)
    if workflow is None and status != "draft":
        # `create_task` refuses to create a workflow-less non-draft task now,
        # so the workflow-less mark-done tests construct that shape on disk.
        slug, path = _write_workflow_less_task(repo, status=status)
        ref = {"slug": slug, "path": path}
    else:
        ref = create_task(
            cfg=cfg, title="Work", workflow_name=workflow,
            contexts=[], autonomy="interactive", owner="marc", assignee="claude",
            watchers=[], status=status,
        )
    path = ref["path"]
    if workflow and on_final:
        t = Ticket.read(path / "ticket.md")
        steps = t.workflow["steps"]
        last = len(steps)
        t.frontmatter["step"] = f"{last} ({steps[last - 1]['name']})"
        t.write(path / "ticket.md")
    if pr_url is not None:
        from relay.taskfile import read_blackboard, replace_blackboard

        ticket = path / "ticket.md"
        bb = read_blackboard(ticket, blackboard_required=False).rstrip()
        replace_blackboard(
            ticket, bb + f"\n\n## Dev\n\nbranch: foo\npr: {pr_url}\n"
        )
    return ref["slug"], path


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


def test_parse_pr_number() -> None:
    assert am.parse_pr_number("https://github.com/o/r/pull/74") == 74
    assert am.parse_pr_number("not-a-url") is None


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
    count = am.sweep_merged(cfg, quiet=True)

    assert count == 1
    t = Ticket.read(path / "ticket.md")
    assert t.status == "done"
    from relay.logfile import task_log_lines

    log = "\n".join(task_log_lines(cfg, slug))
    assert "auto-bumped on merge of PR #7" in log


def test_sweep_merged_skips_non_final_step(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Default creates at step 1 (implement) of a 2-step workflow.
    slug, path = _make_task(repo, pr_url="https://github.com/o/r/pull/8")
    _stub_pr_state(monkeypatch, {"https://github.com/o/r/pull/8": "MERGED"})

    cfg = load_config(repo)
    count = am.sweep_merged(cfg, quiet=True)

    assert count == 0
    t = Ticket.read(path / "ticket.md")
    assert t.status == "active"


def test_sweep_merged_no_workflow_marks_done(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    slug, path = _make_task(
        repo, workflow=None, pr_url="https://github.com/o/r/pull/9"
    )
    _stub_pr_state(monkeypatch, {"https://github.com/o/r/pull/9": "MERGED"})

    cfg = load_config(repo)
    count = am.sweep_merged(cfg, quiet=True)

    assert count == 1
    t = Ticket.read(path / "ticket.md")
    assert t.status == "done"


def test_sweep_merged_skips_open_pr(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    slug, path = _make_task(
        repo, on_final=True, pr_url="https://github.com/o/r/pull/10"
    )
    _stub_pr_state(monkeypatch, {"https://github.com/o/r/pull/10": "OPEN"})

    cfg = load_config(repo)
    count = am.sweep_merged(cfg, quiet=True)

    assert count == 0
    t = Ticket.read(path / "ticket.md")
    assert t.status == "active"


def test_sweep_merged_skips_ticket_without_pr(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    slug, path = _make_task(repo, on_final=True)  # no pr_url
    calls = _stub_pr_state(monkeypatch, {})

    cfg = load_config(repo)
    count = am.sweep_merged(cfg, quiet=True)

    assert count == 0
    assert calls == []  # pr_state never called


def test_sweep_merged_skips_already_done(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    slug, path = _make_task(
        repo, on_final=True, status="done", pr_url="https://github.com/o/r/pull/11"
    )
    calls = _stub_pr_state(monkeypatch, {"https://github.com/o/r/pull/11": "MERGED"})

    cfg = load_config(repo)
    count = am.sweep_merged(cfg, quiet=True)

    assert count == 0
    # `done` filtered before any gh call.
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

    assert first == 1
    assert second == 0


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
    count = am.sweep_merged(cfg, quiet=True)

    assert count == 0
    t = Ticket.read(path / "ticket.md")
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


# --- status stays read-only --------------------------------------------------


def test_relay_status_does_not_auto_bump(
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
    assert Ticket.read(path / "ticket.md").status == "active"


def test_relay_status_never_calls_gh(
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
    assert Ticket.read(path / "ticket.md").status == "active"
