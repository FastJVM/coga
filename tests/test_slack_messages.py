"""Format snapshots for the per-ticket Slack messages.

Every per-ticket post is built at its call site (not in `slack.py`), so these
tests drive each command/scanner end-to-end and capture the text handed to
`requests.post`. They lock the remaining live conventions: Done messages still
include a `"title"` after every `*slug*`, `prev → done` transitions, and the
`<url|PR #N>` automerge link. Routine lifecycle transitions are intentionally
silent unless the operator supplies an explicit FYI such as `bump --message`.

The `[project] [owner]` prefix that `post()`/`notify()` prepend is covered by
`test_slack.py`; here we assert the message *body* with `endswith`, so the
prefix (whose project name is the tmp dir) is intentionally out of scope.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

from relay import automerge as am
from relay import spool
from relay.cli import app
from relay.config import load_config
from relay.scaffold import scaffold_task
from relay.ticket import Ticket


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


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
          - name: pr
          - name: merge
        ---
        """,
    )
    monkeypatch.chdir(company)
    return company


def _make_task(
    repo: Path,
    *,
    workflow: str | None = "code",
    status: str = "draft",
    assignee: str | None = "claude",
    on_final: bool = False,
    pr_url: str | None = None,
) -> tuple[str, Path]:
    cfg = load_config(repo)
    ref = scaffold_task(
        cfg=cfg, title="Work", workflow_name=workflow,
        contexts=[], mode="interactive", owner="marc", assignee=assignee,
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
        bb = path / "blackboard.md"
        bb.write_text(
            bb.read_text().rstrip() + f"\n\n## Dev\n\nbranch: foo\npr: {pr_url}\n"
        )
    return ref["slug"], path


def _capture(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Capture the text of every live Slack post made during the test."""
    posts: list[str] = []

    def fake(url, json=None, timeout=None):  # type: ignore[no-untyped-def]
        posts.append(json["text"])

        class R:
            status_code = 200
            text = "ok"

        return R()

    monkeypatch.setattr("relay.slack.requests.post", fake)
    return posts


def _body(posts: list[str], emoji: str) -> str:
    """Return the post containing `emoji`, with the `[project] [owner] ` prefix
    stripped so assertions can pin the message body exactly."""
    matches = [p for p in posts if emoji in p]
    assert matches, f"no post containing {emoji!r}; got {posts}"
    msg = matches[-1]
    return msg[msg.index(emoji):]


# --- mark active / done -------------------------------------------------------


def test_mark_active_is_silent(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    slug, _ = _make_task(repo, status="draft")
    posts = _capture(monkeypatch)
    result = CliRunner().invoke(app, ["mark", "active", slug])
    assert result.exit_code == 0, result.output
    assert posts == []


# Note: the `(assignee: unassigned)` fallback is unreachable on a valid ticket
# — `assignee` is a required non-empty frontmatter key (see validate.py), so
# `mark active` fails validation before posting if it is empty. The fallback is
# defensive only, so there is no live-path test for it.


def test_mark_done_with_workflow_shows_prev_to_done(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    slug, _ = _make_task(repo, status="in_progress")
    posts = _capture(monkeypatch)
    result = CliRunner().invoke(app, ["mark", "done", slug])
    assert result.exit_code == 0, result.output
    assert _body(posts, "🎉") == (
        f"🎉 claude finished *{slug}* \"Work\": implement → done"
    )


def test_mark_done_workflowless_collapses_transition(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    slug, _ = _make_task(repo, workflow=None, status="active")
    posts = _capture(monkeypatch)
    result = CliRunner().invoke(app, ["mark", "done", slug])
    assert result.exit_code == 0, result.output
    msg = _body(posts, "🎉")
    assert msg == f"🎉 claude finished *{slug}* \"Work\""
    assert "→ done" not in msg


# --- bump ---------------------------------------------------------------------


def test_bump_without_message_is_silent(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    slug, _ = _make_task(repo, status="in_progress")
    posts = _capture(monkeypatch)
    result = CliRunner().invoke(app, ["bump", slug])
    assert result.exit_code == 0, result.output
    assert posts == []


def test_bump_message_posts_live_fyi(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    slug, _ = _make_task(repo, status="in_progress")
    posts = _capture(monkeypatch)
    result = CliRunner().invoke(
        app, ["bump", slug, "--message", "PR opened: https://example/pr"]
    )
    assert result.exit_code == 0, result.output
    assert _body(posts, "👉") == (
        f"👉 claude advanced *{slug}* \"Work\": implement → pr "
        "(step 2/3) — PR opened: https://example/pr"
    )


# --- panic / slack FYI --------------------------------------------------------


def test_panic_uses_colon_and_drops_quotes_around_reason(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    slug, _ = _make_task(repo, status="in_progress")
    posts = _capture(monkeypatch)
    result = CliRunner().invoke(
        app, ["panic", "--task", slug, "--reason", "retry ceiling unspecified"]
    )
    assert result.exit_code == 1  # panic exits non-zero by design
    assert _body(posts, "🚨") == (
        f"🚨 claude needs help on *{slug}* \"Work\": retry ceiling unspecified"
    )


def test_slack_fyi_includes_title(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    slug, _ = _make_task(repo, status="in_progress")
    posts = _capture(monkeypatch)
    result = CliRunner().invoke(
        app, ["slack", "--task", slug, "--message", "tests still flaky"]
    )
    assert result.exit_code == 0, result.output
    assert _body(posts, "💬") == (
        f"💬 claude on *{slug}* \"Work\": tests still flaky"
    )


# --- automerge ----------------------------------------------------------------


def test_automerge_links_pr_and_shows_prev_to_done(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    url = "https://github.com/o/r/pull/7"
    slug, _ = _make_task(repo, status="active", on_final=True, pr_url=url)
    monkeypatch.setattr(am, "pr_state", lambda u: "MERGED")
    posts = _capture(monkeypatch)

    count = am.auto_bump_merged(load_config(repo), quiet=True)
    assert count == 1
    assert _body(posts, "🎉") == (
        f"🎉 *{slug}* \"Work\": merge → done — <{url}|PR #7> merged"
    )


def test_automerge_workflowless_collapses_and_links(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    url = "https://github.com/o/r/pull/9"
    slug, _ = _make_task(repo, workflow=None, status="active", pr_url=url)
    monkeypatch.setattr(am, "pr_state", lambda u: "MERGED")
    posts = _capture(monkeypatch)

    count = am.auto_bump_merged(load_config(repo), quiet=True)
    assert count == 1
    assert _body(posts, "🎉") == (
        f"🎉 *{slug}* \"Work\" finished — <{url}|PR #9> merged"
    )


def test_automerge_digest_preserves_transition_and_pr_link(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    url = "https://github.com/o/r/pull/7"
    slug, _ = _make_task(repo, status="active", on_final=True, pr_url=url)
    monkeypatch.setattr(am, "pr_state", lambda u: "MERGED")
    posts = _capture(monkeypatch)
    digest_blackboard = repo / "recurring" / "digest" / "blackboard.md"
    _write(digest_blackboard, "## Spool (pending)\n")

    count = am.auto_bump_merged(load_config(repo), quiet=True)

    assert count == 1
    assert posts == []
    records = spool.read_records(digest_blackboard)
    assert len(records) == 1
    assert records[0]["ticket"] == slug
    assert records[0]["kind"] == "done"
    assert records[0]["detail"] == (
        f"auto-bumped: merge → done — <{url}|PR #7> merged ✅"
    )


# --- recurring scaffold -------------------------------------------------------


def test_recurring_scaffold_is_silent(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from relay.commands.recurring import _broadcast_scan
    from relay.recurring import DueScan, DueTask
    from relay.tasks import TaskRef

    slug, path = _make_task(repo, status="active")
    posts = _capture(monkeypatch)
    cfg = load_config(repo)

    scan = DueScan(
        tasks=[
            DueTask(
                template="weekly",
                ref=TaskRef(slug=slug, path=path),
                last_fire=datetime(2026, 6, 9),
                created=True,
                status="active",
            )
        ],
        errors=[],
    )
    _broadcast_scan(cfg, scan)
    assert posts == []
