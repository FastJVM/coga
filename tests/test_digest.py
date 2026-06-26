"""Tests for the daily-digest pipeline: spool primitive, notify routing,
outcome rendering, git high-water scanning, and the `coga digest` flush."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from coga import notification, spool
from coga.commands.digest import run_digest
from coga.config import load_config


# --- repo fixture -------------------------------------------------------------


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    coga_os = tmp_path / "coga-os"
    _write(
        coga_os / "coga.toml",
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
    _write(coga_os / "coga.local.toml", 'user = "nick"\n')
    (coga_os / "tasks").mkdir(parents=True)
    monkeypatch.chdir(coga_os)
    return coga_os


def _install_digest(coga_os: Path) -> Path:
    """Install the recurring/digest spool + ticket; return the `spool.md` path.

    The pending-record spool lives in the dedicated, `merge=union`
    `recurring/digest/spool.md` file; the git high-water mark (`### Digest State`)
    lives in the sibling `ticket.md`. Most assertions read the spool, so the
    spool path is returned; the state file is `_state_path(spool_path)`.
    """
    digest = coga_os / "recurring" / "digest"
    _write(
        digest / "spool.md",
        "# Digest spool\n\n## Spool (pending)\n\nconsumed_through:\n",
    )
    _write(
        digest / "ticket.md",
        "## Description\n\n"
        "<!-- coga:blackboard -->\n\n"
        "Digest state.\n\n### Digest State\n\nlast_commit:\nrange:\nposted:\n",
    )
    return digest / "spool.md"


def _state_path(spool_path: Path) -> Path:
    """The digest ticket holding `### Digest State`, sibling of the spool file."""
    return spool_path.parent / "ticket.md"


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

    monkeypatch.setattr("coga.notification.slack.requests.post", _capture)
    return posts


# --- spool primitive ----------------------------------------------------------


def _spool_file(tmp_path: Path) -> Path:
    sp = tmp_path / "spool.md"
    sp.write_text("# Digest spool\n\n## Spool (pending)\n\nconsumed_through:\n")
    return sp


def test_append_stamps_id_and_tails(tmp_path: Path) -> None:
    sp = _spool_file(tmp_path)
    spool.append_record(sp, {"kind": "bump", "detail": "→ step 2"})
    spool.append_record(sp, {"kind": "done", "detail": "→ done"})

    records = spool.read_records(sp)
    assert [r["kind"] for r in records] == ["bump", "done"]  # append order
    # Every record is id-stamped, and the ids are unique.
    ids = [r["id"] for r in records]
    assert all(ids) and len(set(ids)) == 2
    # Header prose is untouched; records sit below the watermark line.
    text = sp.read_text()
    assert text.index("consumed_through:") < text.index('"kind":"bump"')


def test_append_creates_section_when_absent(tmp_path: Path) -> None:
    sp = tmp_path / "spool.md"
    sp.write_text("# Digest spool\n\nno section yet\n")
    spool.append_record(sp, {"kind": "draft", "detail": "created"})
    records = spool.read_records(sp)
    assert [r["kind"] for r in records] == ["draft"]
    assert "## Spool (pending)" in sp.read_text()


def test_drain_keeps_anchor_and_advances_watermark(tmp_path: Path) -> None:
    sp = _spool_file(tmp_path)
    spool.append_record(sp, {"id": "a1", "kind": "bump", "detail": "a"})
    spool.append_record(sp, {"id": "a2", "kind": "done", "detail": "b"})

    drained = spool.drain(sp)
    assert [r["kind"] for r in drained] == ["bump", "done"]
    # Newest record stays as the anchor; watermark names it; nothing unconsumed.
    assert "consumed_through: a2" in sp.read_text()
    assert [r["id"] for r in spool.read_records(sp)] == ["a2"]
    assert spool.read_unconsumed(sp) == []

    # A later append is unconsumed; a re-drain leaves only the new anchor.
    spool.append_record(sp, {"id": "a3", "kind": "done", "detail": "c"})
    assert [r["id"] for r in spool.read_unconsumed(sp)] == ["a3"]
    assert [r["kind"] for r in spool.drain(sp)] == ["done"]
    assert "consumed_through: a3" in sp.read_text()
    assert [r["id"] for r in spool.read_records(sp)] == ["a3"]


def test_drain_empty_missing_and_already_consumed_are_noops(tmp_path: Path) -> None:
    missing = tmp_path / "nope.md"
    assert spool.drain(missing) == []

    sp = _spool_file(tmp_path)
    before = sp.read_text()
    assert spool.drain(sp) == []
    assert sp.read_text() == before  # empty spool untouched

    spool.append_record(sp, {"id": "a1", "kind": "done", "detail": "a"})
    spool.drain(sp)
    consumed = sp.read_text()
    # Nothing new since the last drain → no-op, file untouched.
    assert spool.drain(sp) == []
    assert sp.read_text() == consumed


def test_drain_vs_append_merge_without_conflict(tmp_path: Path) -> None:
    """The structural invariant: a concurrent consumer drain (top-trim) and a
    producer append (bottom) 3-way merge cleanly, with no conflict, no
    resurrection of consumed records, and the anchor not re-posted.

    This reproduces the contended-push → rebase recovery that left conflict
    markers before, using `git merge-file` as the 3-way merger.
    """
    base = tmp_path / "base.md"
    base.write_text("# Digest spool\n\n## Spool (pending)\n\nconsumed_through:\n")
    for rid in ("r1", "r2", "r3"):
        spool.append_record(base, {"id": rid, "kind": "done", "detail": rid})

    consumer = tmp_path / "consumer.md"  # the digest drains
    producer = tmp_path / "producer.md"  # a clone appends r4
    consumer.write_text(base.read_text())
    producer.write_text(base.read_text())
    spool.drain(consumer)  # trims r1,r2 from the top; keeps r3 as anchor
    spool.append_record(producer, {"id": "r4", "kind": "done", "detail": "r4"})

    # 3-way merge consumer (ours) + base + producer (theirs).
    import subprocess

    merged = subprocess.run(
        ["git", "merge-file", "-p", str(consumer), str(base), str(producer)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert merged.returncode == 0, merged.stdout + merged.stderr  # clean merge
    out = merged.stdout
    assert "<<<<<<<" not in out and ">>>>>>>" not in out
    # Consumed records were trimmed, NOT resurrected by the merge.
    assert '"id":"r1"' not in out and '"id":"r2"' not in out
    # The anchor (r3) and the new append (r4) both survive; watermark advanced.
    assert "consumed_through: r3" in out
    assert '"id":"r3"' in out and '"id":"r4"' in out

    # And the merged file presents exactly r4 as the next unconsumed record.
    result = tmp_path / "merged.md"
    result.write_text(out)
    assert [r["id"] for r in spool.read_unconsumed(result)] == ["r4"]


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


def test_notify_migrates_legacy_digest_ticket_spool(
    repo: Path, captured_posts: list[dict]
) -> None:
    digest = repo / "recurring" / "digest"
    _write(
        digest / "ticket.md",
        """
        ## Description

        <!-- coga:blackboard -->

        Digest state.

        ### Digest State

        last_commit:
        range:
        posted:

        ## Spool (pending)

        {"ts":"2026-06-18T14:53","project":"coga","kind":"done","detail":"old done","ticket":"old","owner":"nick"}
        """,
    )

    cfg = load_config()
    notification.notify(
        cfg,
        "🎉 live text",
        kind="done",
        detail="new done",
        ticket="new",
        owner="nick",
    )

    migrated = digest / "spool.md"
    assert captured_posts == []
    assert migrated.is_file()
    records = spool.read_unconsumed(migrated)
    assert [rec["ticket"] for rec in records] == ["old", "new"]
    assert all(rec["id"] for rec in records)
    assert "## Spool (pending)" in (digest / "ticket.md").read_text()


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


# --- de-dup -------------------------------------------------------------------


def test_dedupe_collapses_same_event_from_two_clones() -> None:
    # Two clones recorded the same done event: distinct random ids, ts seconds
    # apart, identical content. id alone can't collapse them; the content key does.
    records = [
        {"id": "a", "project": "coga", "kind": "done", "ticket": "t",
         "detail": "→ done ✅", "ts": "2026-06-24T11:00"},
        {"id": "b", "project": "coga", "kind": "done", "ticket": "t",
         "detail": "→ done ✅", "ts": "2026-06-24T11:01"},
        {"id": "c", "project": "coga", "kind": "done", "ticket": "u",
         "detail": "→ done ✅", "ts": "2026-06-24T11:00"},
    ]
    out = notification.dedupe_records(records)
    assert [r["ticket"] for r in out] == ["t", "u"]  # one t (first-seen), one u


def test_run_digest_posts_a_duplicated_event_once(
    repo: Path, captured_posts: list[dict]
) -> None:
    bb = _install_digest(repo)
    cfg = load_config()
    # The same event, spooled twice (as two racing clones would).
    for _ in range(2):
        notification.notify(
            cfg, "y", kind="done", detail="→ done ✅", ticket="dup", owner="nick"
        )
    assert len(spool.read_unconsumed(bb)) == 2  # both records are on the spool

    assert run_digest(cfg) is True
    assert captured_posts[0]["text"].count(" • dup ") == 1  # posted once


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

    # Spool drained (watermark advanced past the legacy lifecycle record too);
    # nothing left unconsumed, so a same-day re-run is a silent no-op here.
    assert spool.read_unconsumed(bb) == []
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


def _install_digest_with_state(coga_os: Path, last_commit: str) -> Path:
    """Install the spool + ticket and seed `### Digest State` with `last_commit`.

    Returns the spool.md path; the high-water mark lives in `_state_path(bb)`.
    """
    bb = _install_digest(coga_os)
    state = _state_path(bb)
    state.write_text(
        state.read_text().replace("last_commit:\n", f"last_commit: {last_commit}\n")
    )
    return bb


def test_run_digest_posts_also_merged_from_git_high_water(
    git_repo, captured_posts: list[dict]
) -> None:
    start = git_repo.git("rev-parse", "HEAD").strip()
    bb = _install_digest_with_state(git_repo.coga_os, start)
    cfg = load_config(git_repo.coga_os)

    _commit_and_push(
        git_repo,
        "coga-os/docs/state-sync.md",
        "sync\n",
        "Ticket: sync-task-state — done",
    )
    _commit_and_push(
        git_repo,
        "coga-os/docs/pr-42.md",
        "done\n",
        "Improve digest rendering (#42)",
    )
    reported_sha = _commit_and_push(
        git_repo,
        "coga-os/docs/no-ticket.md",
        "merged\n",
        "Fix typo in compose docstring",
    )
    _commit_and_push(
        git_repo,
        "coga-os/docs/sync-helper.md",
        "sync\n",
        "Sync task state: add-coga-skill-search-with-candidate-eval",
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
    assert spool.read_unconsumed(bb) == []
    head = git_repo.git("rev-parse", "origin/main").strip()
    assert f"last_commit: {head}" in _state_path(bb).read_text()


def test_run_digest_posts_git_commits_even_with_empty_spool(
    git_repo, captured_posts: list[dict]
) -> None:
    start = git_repo.git("rev-parse", "HEAD").strip()
    bb = _install_digest_with_state(git_repo.coga_os, start)
    cfg = load_config(git_repo.coga_os)
    sha = _commit_and_push(
        git_repo,
        "coga-os/docs/commit-only.md",
        "merged\n",
        "Add digest high-water scan",
    )

    assert run_digest(cfg) is True

    text = captured_posts[0]["text"]
    assert "Done:" not in text
    assert "Also merged (no ticket):" in text
    assert f" • {sha[:7]} Add digest high-water scan" in text
    assert "last_commit:" in _state_path(bb).read_text()


def test_run_digest_flushes_done_when_git_disabled(
    git_repo, captured_posts: list[dict]
) -> None:
    bb = _install_digest(git_repo.coga_os)
    _write(
        git_repo.coga_os / "coga.local.toml",
        'user = "nick"\n[git]\nenabled = false\n',
    )
    cfg = load_config(git_repo.coga_os)
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
    assert spool.read_unconsumed(bb) == []
    # git disabled → no high-water scan, so the seeded last_commit stays empty.
    assert "last_commit:\n" in _state_path(bb).read_text()


def test_run_digest_skips_filtered_commits_but_advances_high_water(
    git_repo, captured_posts: list[dict]
) -> None:
    start = git_repo.git("rev-parse", "HEAD").strip()
    bb = _install_digest_with_state(git_repo.coga_os, start)
    cfg = load_config(git_repo.coga_os)
    _commit_and_push(
        git_repo,
        "coga-os/docs/filtered.md",
        "sync\n",
        "Ticket: filtered — active",
    )

    assert run_digest(cfg) is False
    assert captured_posts == []
    head = git_repo.git("rev-parse", "origin/main").strip()
    assert f"last_commit: {head}" in _state_path(bb).read_text()


def test_run_digest_noop_without_digest_ticket(
    repo: Path, captured_posts: list[dict]
) -> None:
    cfg = load_config()
    assert run_digest(cfg) is False
    assert captured_posts == []
