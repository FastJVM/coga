"""Tests for the daily-digest pipeline: spool primitive, notify routing,
outcome rendering, git high-water scanning, and the `relay digest` flush."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from relay import notification, spool
from relay.commands.digest import run_digest
from relay.config import load_config


# --- repo fixture -------------------------------------------------------------


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    relay_os = tmp_path / "relay-os"
    _write(
        relay_os / "relay.toml",
        """
        version = 1
        default_status = "draft"

        [notification]
        channels = ["slack"]

        [notification.slack]
        webhook = "env:SLACK_WEBHOOK_URL"

        [notification.slack.users]
        nick = "Unick"
        bob = "Ubob"

        [agents.claude]
        cli = "claude"
        auto = "-p"
        file = "CLAUDE.md"
        """,
    )
    _write(relay_os / "relay.local.toml", 'user = "nick"\n')
    (relay_os / "tasks").mkdir(parents=True)
    monkeypatch.chdir(relay_os)
    return relay_os


def _install_digest(relay_os: Path) -> Path:
    """Create the recurring/digest spool blackboard and return its path."""
    bb = relay_os / "recurring" / "digest" / "blackboard.md"
    _write(bb, "Digest spool.\n\n## Spool (pending)\n")
    return bb


@pytest.fixture
def captured_posts(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    """Capture Slack webhook payloads instead of the conftest no-op."""
    posts: list[dict] = []

    def _capture(url, json=None, timeout=None):  # noqa: A002
        posts.append(json)

        class R:
            status_code = 200
            text = "ok"

        return R()

    monkeypatch.setattr("relay.notification.slack.requests.post", _capture)
    return posts


# --- spool primitive ----------------------------------------------------------


def test_spool_roundtrip_and_preserves_non_spool_state(tmp_path: Path) -> None:
    bb = tmp_path / "blackboard.md"
    bb.write_text(
        "Seed text.\n\n## Spool (pending)\n\n## State\n\nlast_serviced_period: 2026-06-03\n"
    )

    spool.append_record(bb, {"kind": "bump", "detail": "→ step 2"})
    spool.append_record(bb, {"kind": "done", "detail": "→ done"})

    assert spool.read_records(bb) == [
        {"kind": "bump", "detail": "→ step 2"},
        {"kind": "done", "detail": "→ done"},
    ]

    drained = spool.drain(bb)
    assert [r["kind"] for r in drained] == ["bump", "done"]

    text = bb.read_text()
    # State + seed survive; spool section is emptied.
    assert "last_serviced_period: 2026-06-03" in text
    assert "Seed text." in text
    assert "## State" in text
    assert spool.read_records(bb) == []


def test_spool_creates_section_when_absent(tmp_path: Path) -> None:
    bb = tmp_path / "blackboard.md"
    bb.write_text("Just a seed line, no spool section yet.\n")
    spool.append_record(bb, {"kind": "draft", "detail": "created"})
    assert spool.read_records(bb) == [{"kind": "draft", "detail": "created"}]
    assert "## Spool (pending)" in bb.read_text()


def test_drain_returns_records_and_preserves_non_record_lines(tmp_path: Path) -> None:
    bb = tmp_path / "blackboard.md"
    bb.write_text(
        "## Spool (pending)\n\n"
        '{"kind":"bump","detail":"a"}\n'
        "last_serviced_period: 2026-06-03\n"  # stray high-water line
        '{"kind":"done","detail":"b"}\n'
    )
    drained = spool.drain(bb)
    assert [r["kind"] for r in drained] == ["bump", "done"]
    # JSON records are cleared; the non-record high-water line is preserved.
    text = bb.read_text()
    assert "last_serviced_period: 2026-06-03" in text
    assert spool.read_records(bb) == []


def test_drain_empty_and_missing_are_noops(tmp_path: Path) -> None:
    missing = tmp_path / "nope.md"
    assert spool.drain(missing) == []

    bb = tmp_path / "blackboard.md"
    bb.write_text("## Spool (pending)\n\n")
    before = bb.read_text()
    assert spool.drain(bb) == []
    assert bb.read_text() == before  # untouched on empty


# --- notify routing -----------------------------------------------------------


def test_notify_falls_back_to_live_post_without_digest(
    repo: Path, captured_posts: list[dict]
) -> None:
    cfg = load_config()
    notification.notify(
        cfg, "🎉 live text", kind="done", detail="→ done ✅", ticket="t-1", owner="nick"
    )
    assert len(captured_posts) == 1
    assert "🎉 live text" in captured_posts[0]["text"]


def test_notify_spools_when_digest_installed(
    repo: Path, captured_posts: list[dict]
) -> None:
    bb = _install_digest(repo)
    cfg = load_config()
    notification.notify(
        cfg,
        "🎉 live text",
        kind="done",
        detail="auto-bumped: merge → done — <https://example/pr|PR #4> merged ✅",
        ticket="t-1",
        owner="nick",
        watchers=["bob"],
    )
    # No live post — it was spooled instead.
    assert captured_posts == []
    records = spool.read_records(bb)
    assert len(records) == 1
    assert records[0]["kind"] == "done"
    assert records[0]["owner"] == "nick"
    assert records[0]["watchers"] == ["bob"]
    assert records[0]["detail"] == (
        "auto-bumped: merge → done — <https://example/pr|PR #4> merged ✅"
    )


def test_notify_rejects_lifecycle_kinds(repo: Path) -> None:
    cfg = load_config()
    with pytest.raises(ValueError, match="outcome kinds"):
        notification.notify(
            cfg,
            "👉 live text",
            kind="bump",
            detail="advanced → step 2",
            ticket="t-1",
            owner="nick",
        )


def test_post_always_posts_even_with_digest_installed(
    repo: Path, captured_posts: list[dict]
) -> None:
    # Urgent events use `post` directly, which must bypass the spool.
    _install_digest(repo)
    cfg = load_config()
    notification.post(cfg, "🚨 panic!", owner="nick")
    assert len(captured_posts) == 1
    assert "🚨 panic!" in captured_posts[0]["text"]


# --- render -------------------------------------------------------------------


def test_render_digest_groups_and_mentions(repo: Path) -> None:
    cfg = load_config()
    records = [
        {"project": cfg.project_name, "owner": "nick", "ticket": "alpha",
         "kind": "done", "detail": "auto-bumped: merge → done — <https://example/pr|PR #4> merged ✅",
         "watchers": ["bob"]},
        {"project": cfg.project_name, "owner": "nick", "ticket": "alpha",
         "kind": "done", "detail": "nick finished → done ✅"},
        {"project": cfg.project_name, "owner": "alice", "ticket": "beta",
         "kind": "done", "detail": "→ done ✅"},
        {"project": cfg.project_name, "kind": "recurring-error",
         "detail": "⚠️ recurring scan skipped 1 template"},
    ]
    out = notification.render_digest(
        cfg,
        records,
        date_label="2026-06-03",
        also_merged=[{"sha": "abcdef012345", "subject": "Fix typo"}],
    )

    assert out.splitlines()[0] == f"📋 Daily digest · 2026-06-03 · {cfg.project_name}"
    assert "Done:" in out
    assert "<@Unick>" in out                 # nick is mapped → pinged
    assert "alice" in out and "<@" not in out.split("alice")[1].split("\n")[0]
    assert " • alpha (cc <@Ubob>) — <https://example/pr|PR #4> merged ✅" in out
    assert " • alpha — nick finished → done ✅" in out
    assert "Also merged (no ticket):" in out
    assert " • abcdef0 Fix typo" in out
    assert "Recurring errors:" in out
    assert "recurring scan skipped 1 template" in out
    assert out.index("Done:") < out.index("Also merged")
    assert out.index("Also merged") < out.index("Recurring errors")


# --- flush --------------------------------------------------------------------


def test_run_digest_flushes_then_empties(
    repo: Path, captured_posts: list[dict]
) -> None:
    bb = _install_digest(repo)
    cfg = load_config()
    spool.append_record(
        bb,
        {"project": cfg.project_name, "kind": "active", "detail": "→ active",
         "ticket": "alpha", "owner": "nick"},
    )
    notification.notify(cfg, "y", kind="done", detail="→ done ✅", ticket="alpha", owner="nick")

    posted = run_digest(cfg)
    assert posted is True
    assert len(captured_posts) == 1
    text = captured_posts[0]["text"]
    assert text.startswith(f"[{cfg.project_name}] 📋 Daily digest")
    assert "Done:" in text
    assert "done ✅" in text
    assert "→ active" not in text

    # Spool emptied, including legacy lifecycle records; a same-day re-run is
    # a silent no-op in this non-git test repo.
    assert spool.read_records(bb) == []
    assert run_digest(cfg) is False
    assert len(captured_posts) == 1


def _commit_and_push(git_repo, relpath: str, text: str, subject: str) -> str:
    path = git_repo.root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    git_repo.git("add", "--", relpath)
    git_repo.git("commit", "-m", subject)
    sha = git_repo.git("rev-parse", "HEAD").strip()
    git_repo.git("push", "origin", "main")
    return sha


def _install_digest_with_state(relay_os: Path, last_commit: str) -> Path:
    bb = _install_digest(relay_os)
    text = bb.read_text()
    bb.write_text(
        text.replace(
            "## Spool (pending)\n",
            (
                "### Digest State\n\n"
                f"last_commit: {last_commit}\n"
                "range:\n"
                "posted:\n\n"
                "## Spool (pending)\n"
            ),
        )
    )
    return bb


def test_run_digest_posts_also_merged_from_git_high_water(
    git_repo, captured_posts: list[dict]
) -> None:
    start = git_repo.git("rev-parse", "HEAD").strip()
    bb = _install_digest_with_state(git_repo.relay_os, start)
    cfg = load_config(git_repo.relay_os)

    _commit_and_push(
        git_repo,
        "relay-os/docs/state-sync.md",
        "sync\n",
        "Ticket: sync-task-state — done",
    )
    _commit_and_push(
        git_repo,
        "relay-os/docs/pr-42.md",
        "done\n",
        "Improve digest rendering (#42)",
    )
    reported_sha = _commit_and_push(
        git_repo,
        "relay-os/docs/no-ticket.md",
        "merged\n",
        "Fix typo in compose docstring",
    )
    _commit_and_push(
        git_repo,
        "relay-os/docs/sync-helper.md",
        "sync\n",
        "Sync task state: add-relay-skill-search-with-candidate-eval",
    )
    notification.notify(
        cfg,
        "done",
        kind="done",
        detail="auto-bumped: review → done — <https://example/pr|PR #42> merged ✅",
        ticket="digest-ticket",
        owner="nick",
    )

    assert run_digest(cfg) is True

    text = captured_posts[0]["text"]
    assert "Done:" in text
    assert " • digest-ticket — <https://example/pr|PR #42> merged ✅" in text
    assert "Also merged (no ticket):" in text
    assert f" • {reported_sha[:7]} Fix typo in compose docstring" in text
    assert "Improve digest rendering (#42)" not in text
    assert "Ticket: sync-task-state" not in text
    assert "Sync task state:" not in text
    assert spool.read_records(bb) == []
    assert f"last_commit: {git_repo.git('rev-parse', 'origin/main').strip()}" in bb.read_text()


def test_run_digest_posts_git_commits_even_with_empty_spool(
    git_repo, captured_posts: list[dict]
) -> None:
    start = git_repo.git("rev-parse", "HEAD").strip()
    bb = _install_digest_with_state(git_repo.relay_os, start)
    cfg = load_config(git_repo.relay_os)
    sha = _commit_and_push(
        git_repo,
        "relay-os/docs/commit-only.md",
        "merged\n",
        "Add digest high-water scan",
    )

    assert run_digest(cfg) is True

    text = captured_posts[0]["text"]
    assert "Done:" not in text
    assert "Also merged (no ticket):" in text
    assert f" • {sha[:7]} Add digest high-water scan" in text
    assert "last_commit:" in bb.read_text()


def test_run_digest_flushes_done_when_git_disabled(
    git_repo, captured_posts: list[dict]
) -> None:
    bb = _install_digest(git_repo.relay_os)
    _write(
        git_repo.relay_os / "relay.local.toml",
        'user = "nick"\n[git]\nenabled = false\n',
    )
    cfg = load_config(git_repo.relay_os)
    git_repo.git("remote", "remove", "origin")
    notification.notify(
        cfg,
        "done",
        kind="done",
        detail="nick finished → done ✅",
        ticket="manual-done",
        owner="nick",
    )

    assert run_digest(cfg) is True

    text = captured_posts[0]["text"]
    assert "Done:" in text
    assert "manual-done" in text
    assert "Also merged" not in text
    assert spool.read_records(bb) == []
    assert "last_commit:" not in bb.read_text()


def test_run_digest_skips_filtered_commits_but_advances_high_water(
    git_repo, captured_posts: list[dict]
) -> None:
    start = git_repo.git("rev-parse", "HEAD").strip()
    bb = _install_digest_with_state(git_repo.relay_os, start)
    cfg = load_config(git_repo.relay_os)
    _commit_and_push(
        git_repo,
        "relay-os/docs/filtered.md",
        "sync\n",
        "Ticket: filtered — active",
    )

    assert run_digest(cfg) is False
    assert captured_posts == []
    assert f"last_commit: {git_repo.git('rev-parse', 'origin/main').strip()}" in bb.read_text()


def test_run_digest_noop_without_digest_ticket(
    repo: Path, captured_posts: list[dict]
) -> None:
    cfg = load_config()
    assert run_digest(cfg) is False
    assert captured_posts == []
