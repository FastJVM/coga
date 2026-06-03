"""Tests for the daily-digest pipeline: spool primitive, notify routing,
render grouping, and the `relay digest` flush."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from relay import slack, spool
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

        [slack.users]
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

    monkeypatch.setattr("relay.slack.requests.post", _capture)
    return posts


# --- spool primitive ----------------------------------------------------------


def test_spool_roundtrip_and_preserves_ledger(tmp_path: Path) -> None:
    bb = tmp_path / "blackboard.md"
    bb.write_text(
        "Seed text.\n\n## Spool (pending)\n\n## Ledger\n\n[2026-06-03] scaffolded x\n"
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
    # Ledger + seed survive; spool section is emptied.
    assert "scaffolded x" in text
    assert "Seed text." in text
    assert "## Ledger" in text
    assert spool.read_records(bb) == []


def test_spool_creates_section_when_absent(tmp_path: Path) -> None:
    bb = tmp_path / "blackboard.md"
    bb.write_text("Just a seed line, no spool section yet.\n")
    spool.append_record(bb, {"kind": "draft", "detail": "created"})
    assert spool.read_records(bb) == [{"kind": "draft", "detail": "created"}]
    assert "## Spool (pending)" in bb.read_text()


def test_drain_returns_records_and_preserves_ledger_lines(tmp_path: Path) -> None:
    bb = tmp_path / "blackboard.md"
    bb.write_text(
        "## Spool (pending)\n\n"
        '{"kind":"bump","detail":"a"}\n'
        "[2026-06-03 09:00] scaffolded digest-2026-06-03\n"  # stray ledger line
        '{"kind":"done","detail":"b"}\n'
    )
    drained = spool.drain(bb)
    assert [r["kind"] for r in drained] == ["bump", "done"]
    # JSON records are cleared; the non-record ledger line is preserved (this is
    # the case where `recurring._record_run` appends into the spool section
    # because it is the last section in the file).
    text = bb.read_text()
    assert "scaffolded digest-2026-06-03" in text
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
    slack.notify(
        cfg, "✨ live text", kind="draft", detail="created", ticket="t-1", owner="nick"
    )
    assert len(captured_posts) == 1
    assert "✨ live text" in captured_posts[0]["text"]


def test_notify_spools_when_digest_installed(
    repo: Path, captured_posts: list[dict]
) -> None:
    bb = _install_digest(repo)
    cfg = load_config()
    slack.notify(
        cfg,
        "👉 live text",
        kind="bump",
        detail="advanced → step 2 (pr)",
        ticket="t-1",
        owner="nick",
        watchers=["bob"],
    )
    # No live post — it was spooled instead.
    assert captured_posts == []
    records = spool.read_records(bb)
    assert len(records) == 1
    assert records[0]["kind"] == "bump"
    assert records[0]["owner"] == "nick"
    assert records[0]["watchers"] == ["bob"]
    assert records[0]["detail"] == "advanced → step 2 (pr)"


def test_post_always_posts_even_with_digest_installed(
    repo: Path, captured_posts: list[dict]
) -> None:
    # Urgent events use `post` directly, which must bypass the spool.
    _install_digest(repo)
    cfg = load_config()
    slack.post(cfg, "🚨 panic!", owner="nick")
    assert len(captured_posts) == 1
    assert "🚨 panic!" in captured_posts[0]["text"]


# --- render -------------------------------------------------------------------


def test_render_digest_groups_and_mentions(repo: Path) -> None:
    cfg = load_config()
    records = [
        {"project": cfg.project_name, "owner": "nick", "ticket": "alpha",
         "kind": "active", "detail": "→ active", "watchers": ["bob"]},
        {"project": cfg.project_name, "owner": "nick", "ticket": "alpha",
         "kind": "bump", "detail": "advanced → step 2"},
        {"project": cfg.project_name, "owner": "alice", "ticket": "beta",
         "kind": "done", "detail": "→ done ✅"},
        {"project": cfg.project_name, "kind": "recurring-error",
         "detail": "⚠️ recurring scan skipped 1 template"},
    ]
    out = slack.render_digest(cfg, records, date_label="2026-06-03")

    assert out.splitlines()[0] == "📋 Daily digest · 2026-06-03"
    assert "<@Unick>" in out                 # nick is mapped → pinged
    assert "alice" in out and "<@" not in out.split("alice")[1].split("\n")[0]
    assert " • alpha (cc <@Ubob>)" in out    # watcher cc on the ticket line
    assert "     → active" in out
    assert "     advanced → step 2" in out
    assert "(no owner)" in out               # ownerless recurring-error bucket
    assert "recurring scan skipped 1 template" in out
    # nick's section comes before the ownerless bucket.
    assert out.index("<@Unick>") < out.index("(no owner)")


# --- flush --------------------------------------------------------------------


def test_run_digest_flushes_then_empties(
    repo: Path, captured_posts: list[dict]
) -> None:
    bb = _install_digest(repo)
    cfg = load_config()
    slack.notify(cfg, "x", kind="active", detail="→ active", ticket="alpha", owner="nick")
    slack.notify(cfg, "y", kind="done", detail="→ done ✅", ticket="alpha", owner="nick")

    posted = run_digest(cfg)
    assert posted is True
    assert len(captured_posts) == 1
    text = captured_posts[0]["text"]
    assert text.startswith(f"[{cfg.project_name}] 📋 Daily digest")
    assert "→ active" in text and "→ done ✅" in text

    # Spool emptied; a same-day re-run is a silent no-op.
    assert spool.read_records(bb) == []
    assert run_digest(cfg) is False
    assert len(captured_posts) == 1


def test_run_digest_noop_without_digest_ticket(
    repo: Path, captured_posts: list[dict]
) -> None:
    cfg = load_config()
    assert run_digest(cfg) is False
    assert captured_posts == []
