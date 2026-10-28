from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from dataclasses import replace
from datetime import date, datetime
from pathlib import Path
from uuid import UUID

import pytest

from coga import git, log_transaction
from coga.config import load_config
from coga.log_publication import archived_events
from coga.log_retention import RetentionError
from coga.logfile import LogMutation, append_log, parse_events, replace_log
from coga.paths import packaged_template_path
from coga.taskfile import read_blackboard, replace_blackboard
from coga_edge import phone_home, trim_log

TODAY = date(2026, 10, 27)
REPO_ID = "dd2433c0-7277-4a63-8640-c73089700480"


@pytest.fixture(autouse=True)
def fixed_log_clock(monkeypatch):
    from coga import logfile, log_publication
    class FixedDate(date):
        @classmethod
        def today(cls):
            return TODAY
    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 10, 27, 12, tzinfo=tz)
    monkeypatch.setattr(git, "date", FixedDate)
    monkeypatch.setattr(log_publication, "date", FixedDate)
    monkeypatch.setattr(logfile, "datetime", FixedDatetime)


def _line(ref="retired", stamp="2020-01-01 00:00", message="task done"):
    return f"{stamp} v1 [{ref}] [human:a] {message}\n".encode()


def _seed(git_repo, raw=None):
    path = git_repo.coga_os / "log.md"
    path.write_bytes(raw if raw is not None else _line() + _line("recent", "2026-10-26 12:00"))
    git_repo.git("add", "coga/log.md")
    git_repo.git("commit", "-m", "seed archived history")
    git_repo.git("push", "origin", "main")
    return load_config(git_repo.coga_os), path


def _clone(git_repo, tmp_path):
    dest = tmp_path / "stale"
    git_repo.git("clone", "--branch", "main", str(git_repo.origin), str(dest), cwd=tmp_path)
    git_repo.git("config", "user.name", "Peer", cwd=dest)
    git_repo.git("config", "user.email", "peer@example.test", cwd=dest)
    shutil.copyfile(git_repo.coga_os / "coga.local.toml", dest / "coga/coga.local.toml")
    return load_config(dest / "coga"), dest


def _phone(git_repo, raw):
    parent = git_repo.coga_os / "recurring/phone-home/ticket.md"
    parent.parent.mkdir(parents=True)
    for name in ("ticket.md", "ticket.py"):
        shutil.copyfile(packaged_template_path("recurring", "phone-home", name), parent.with_name(name))
    state = {"schema": 1, "run": 7, "repo_id": REPO_ID, "offset": len(raw), "digest": hashlib.sha256(raw).hexdigest()}
    region = read_blackboard(parent)
    _, match = phone_home._state(region)
    replace_blackboard(parent, region[:match.start()] + "period_state: " + json.dumps(state) + region[match.end():])
    git_repo.git("add", "coga/recurring/phone-home")
    git_repo.git("commit", "-m", "seed consumed movement")
    git_repo.git("push", "origin", "main")
    return parent


def _report(cfg, monkeypatch):
    monkeypatch.setattr(phone_home, "_admitted", lambda cfg: True)
    sent = []
    def sender(cfg, kind, data):
        if kind == "capture":
            sent.append(data)
        return "accepted"
    assert phone_home.run_phone_home(cfg, [], sender=sender, identity=lambda: UUID(REPO_ID)) == 0
    return sent[0]["properties"]["movement_count"]


def test_trim_archives_pending_events_and_repeats_without_maintenance_commit(git_repo):
    cfg, path = _seed(git_repo)
    path.write_bytes(path.read_bytes() + _line("pending"))
    result = trim_log.trim(cfg, clock=lambda: TODAY)
    assert "Removed 2 events" in result
    assert path.read_bytes() == _line("recent", "2026-10-26 12:00")
    assert not log_transaction.pending(cfg)
    head = git_repo.git("rev-parse", "HEAD")
    assert "unchanged" in trim_log.trim(cfg, clock=lambda: TODAY)
    assert git_repo.git("rev-parse", "HEAD") == head
    assert archived_events(git_repo.root, head.strip(), "coga/log.md", {_line("pending")}) == {_line("pending")}
    from coga.recurring_activity import is_machine_commit
    assert is_machine_commit(git_repo.origin_subjects()[0])


@pytest.mark.parametrize("mode", ["disabled", "zero", "empty", "missing", "remote-less"])
def test_trim_disabled_empty_missing_remote_less(git_repo, mode):
    cfg, path = _seed(git_repo)
    if mode == "disabled":
        cfg = replace(cfg, git_enabled=False)
    elif mode == "zero":
        cfg = replace(cfg, log_retention_days=0)
    elif mode == "empty":
        path.write_bytes(b"")
    elif mode == "missing":
        path.unlink()
    else:
        git_repo.git("remote", "remove", "origin")
    before = path.read_bytes() if path.exists() else None
    result = trim_log.trim(cfg, clock=lambda: TODAY)
    if mode == "remote-less":
        assert "Removed 1 events" in result
        assert git_repo.git("show", "HEAD:coga/log.md").encode() == path.read_bytes()
    else:
        assert (path.read_bytes() if path.exists() else None) == before


def test_stale_clone_cannot_resurrect_consumed_movement_but_new_backdated_counts(git_repo, tmp_path, monkeypatch):
    # The clone's HEAD predates A's publication, the difficult replay case.
    cfg, path = _seed(git_repo, _line("recent", "2026-10-26 12:00", "created"))
    peer, peer_root = _clone(git_repo, tmp_path)
    event = _line("A")
    path.write_bytes(path.read_bytes() + event)
    assert git.publish(cfg, [path], "Log: publish A")
    parent = _phone(git_repo, path.read_bytes())
    assert "Removed 1 events" in trim_log.trim(cfg, clock=lambda: TODAY)
    assert _report(cfg, monkeypatch) == 0  # drops A's consumed fingerprint
    stale = peer.repo_root / "log.md"
    stale.write_bytes(stale.read_bytes() + event)
    assert git.publish(peer, [stale], "Log: stale replay") is False
    git_repo.git("fetch", "origin", "main")
    assert event not in git.tree_bytes(git_repo.root, "origin/main", "coga/log.md")
    # Repeated publication from an unmoving source HEAD stays harmless.
    assert git.publish(peer, [stale], "Log: repeated stale replay") is False
    new = _line("new-backdated")
    stale.write_bytes(stale.read_bytes() + new)
    assert git.publish(peer, [stale], "Log: genuine backdated event")
    git_repo.git("fetch", "origin", "main")
    git.fast_forward_control(cfg, git_repo.root, git_repo.git("rev-parse", "origin/main").strip())
    assert _report(cfg, monkeypatch) == 1
    assert event not in path.read_bytes() and new in path.read_bytes()
    assert "Removed 1 events" in trim_log.trim(cfg, clock=lambda: TODAY)
    assert _report(cfg, monkeypatch) == 0
    assert phone_home._state(read_blackboard(parent))[0]["run"] == 10


@pytest.mark.parametrize("order", ["append-first", "trim-first"])
def test_two_clones_append_and_trim_keep_peer_events(git_repo, tmp_path, order):
    cfg, path = _seed(git_repo)
    peer, _ = _clone(git_repo, tmp_path)
    other = peer.repo_root / "log.md"
    added = append_log(peer, "peer", "human:b", "peer event")
    if order == "append-first":
        assert git.publish(peer, [other], "Log: peer")
    trim_log.trim(cfg, clock=lambda: TODAY)
    if order == "trim-first":
        assert git.publish(peer, [other], "Log: peer")
    git_repo.git("fetch", "origin", "main")
    control = git.tree_bytes(git_repo.root, "origin/main", "coga/log.md")
    assert added in control and _line() not in control


@pytest.mark.parametrize("phase", ["intent", "parent", "log"])
def test_crash_receipt_blocks_sweep_and_unrelated_command_until_recovery(git_repo, phase):
    cfg, path = _seed(git_repo)
    parent = _phone(git_repo, _line())
    before = path.read_bytes()
    parent_before = parent.read_bytes()
    region = read_blackboard(parent)
    from coga.movement_cursor import migrate, replace_state
    state = migrate(before, phone_home._state(region)[0])[0]
    replacement = parent_before.split(b"<!-- coga:blackboard -->", 1)[0] + b"<!-- coga:blackboard -->" + replace_state(region, state).encode()
    mutation = LogMutation(before, (0,))
    rev = git_repo.git("rev-parse", "HEAD").strip()
    log_transaction.begin(cfg, rev, mutation, {parent: replacement}, "Log: recurring/trim-log — test")
    if phase in {"parent", "log"}:
        replace_blackboard(parent, replace_state(region, state), expected_bytes=parent_before)
    if phase == "log":
        replace_log(cfg, mutation)
    with pytest.raises(git.UncertainPublishError, match="pending audit mutation"):
        git.publish(cfg, [path], "unrelated")
    assert git.sync_coga_state(cfg) is None
    assert log_transaction.pending(cfg)
    proof = git.prepare_control_checkout(cfg)
    assert proof.kind == "refused"
    assert log_transaction.recover(cfg) == "restored"
    assert path.read_bytes().startswith(before)  # any failure diagnostics remain
    assert parent.read_bytes() == parent_before
    assert not log_transaction.pending(cfg)


@pytest.mark.parametrize("accepted", [False, True])
def test_uncertain_push_recovers_from_reachable_commit(git_repo, monkeypatch, accepted):
    cfg, path = _seed(git_repo)
    before = path.read_bytes()
    push = git._push
    def broken(root, remote, refspec):
        if accepted:
            assert push(root, remote, refspec) is None
        return "connection closed"
    monkeypatch.setattr(git, "_push", broken)
    monkeypatch.setattr(git, "_control_carries", lambda *a: (_ for _ in ()).throw(git.GitError("offline")))
    with pytest.raises(git.UncertainPublishError):
        trim_log.trim(cfg, clock=lambda: TODAY)
    assert log_transaction.pending(cfg)
    appended = append_log(cfg, "peer", "git", "retained diagnostic")
    assert log_transaction.recover(cfg) == ("accepted" if accepted else "restored")
    assert appended in path.read_bytes()
    assert (_line() not in path.read_bytes()) is accepted
    assert not log_transaction.pending(cfg)


def test_unreceipted_truncation_is_refused(git_repo):
    cfg, path = _seed(git_repo)
    path.write_bytes(_line("recent", "2026-10-26 12:00"))
    with pytest.raises(git.StateRegressionError, match="without a LogMutation"):
        git.publish(cfg, [path], "not a deletion receipt")


def test_archive_proof_includes_events_introduced_only_by_a_merge(git_repo):
    cfg, path = _seed(git_repo)
    git_repo.git("checkout", "-b", "side")
    (git_repo.root / "side.txt").write_text("side\n")
    git_repo.git("add", "side.txt")
    git_repo.git("commit", "-m", "side")
    git_repo.git("checkout", "main")
    (git_repo.root / "main.txt").write_text("main\n")
    git_repo.git("add", "main.txt")
    git_repo.git("commit", "-m", "main")
    git_repo.git("merge", "--no-commit", "--no-ff", "side")
    event = _line("merge-only")
    path.write_bytes(path.read_bytes() + event)
    git_repo.git("add", "coga/log.md")
    git_repo.git("commit", "-m", "merge with new audit evidence")
    git_repo.git("push", "origin", "main")
    trim_log.trim(cfg, clock=lambda: TODAY)
    assert event not in path.read_bytes()
    assert archived_events(git_repo.root, "HEAD", "coga/log.md", {event}) == {event}
    path.write_bytes(path.read_bytes() + event)
    assert git.publish(cfg, [path], "Log: stale merge replay") is False
    assert event not in git.tree_bytes(git_repo.root, "origin/main", "coga/log.md")


@pytest.mark.parametrize("obstacle", ["fork", "parked", "attribute", "info-attribute", "symlink"])
def test_install_validates_all_files_before_writing(git_repo, obstacle):
    cfg = load_config(git_repo.coga_os)
    path = cfg.repo_root / "workflows/trim-log/run.md"
    if obstacle == "fork":
        path.parent.mkdir(parents=True)
        path.write_text("custom workflow")
    elif obstacle == "parked":
        (cfg.repo_root / "recurring/_trim-log").mkdir(parents=True)
    elif obstacle == "attribute":
        (cfg.repo_root / ".gitattributes").write_text("/log.md merge=custom\n")
    elif obstacle == "info-attribute":
        (git_repo.root / ".git/info/attributes").write_text("coga/log.md merge=custom\n")
    else:
        path.parent.mkdir(parents=True)
        path.symlink_to(cfg.repo_root / "coga.toml")
    before = {str(p): p.read_bytes() for p in cfg.repo_root.rglob("*") if p.is_file()}
    with pytest.raises(RetentionError):
        trim_log.install(cfg)
    assert before == {str(p): p.read_bytes() for p in cfg.repo_root.rglob("*") if p.is_file()}


def test_install_idempotence_and_exact_allowlist(git_repo):
    cfg = load_config(git_repo.coga_os)
    attrs = cfg.repo_root / ".gitattributes"
    attrs.write_bytes(b"# preserve\r\n**/log.md merge=union\r\n**/retires.md merge=union\r\n")
    expected = {cfg.repo_root / rel for rel in trim_log._INSTALL_FILES} | {attrs}
    assert set(trim_log.install(cfg)) == expected
    assert attrs.read_bytes() == b"# preserve\r\n/log.md -merge\r\n**/retires.md merge=union\r\n"
    assert trim_log.install(cfg) == []


def test_native_merge_conflicts_preserve_both_index_stages(git_repo):
    cfg, path = _seed(git_repo)
    trim_log.install(cfg)
    git_repo.git("add", "coga/.gitattributes")
    git_repo.git("commit", "-m", "adopt binary audit merge")
    git_repo.git("branch", "native-peer")
    path.write_bytes(_line("recent", "2026-10-26 12:00"))
    git_repo.git("add", "coga/log.md")
    git_repo.git("commit", "-m", "trim")
    trimmed = path.read_bytes()
    git_repo.git("checkout", "native-peer")
    peer = append_log(cfg, "peer", "human:b", "native append")
    git_repo.git("add", "coga/log.md")
    git_repo.git("commit", "-m", "peer")
    result = subprocess.run(["git", "-C", str(git_repo.root), "merge", "main"], capture_output=True)
    assert result.returncode == 1
    assert peer in git_repo.git("show", ":2:coga/log.md").encode()
    assert git_repo.git("show", ":3:coga/log.md").encode() == trimmed
    assert len(git_repo.git("ls-files", "-u", "coga/log.md").splitlines()) == 3
    git_repo.git("merge", "--abort")
    assert peer in path.read_bytes()
    # Explicit recovery from the saved sides retains the peer append without
    # restoring the expired event, then records both parents in native Git.
    result = subprocess.run(["git", "-C", str(git_repo.root), "merge", "main"], capture_output=True)
    assert result.returncode == 1
    path.write_bytes(trimmed + peer)
    git_repo.git("add", "coga/log.md")
    git_repo.git("commit", "-m", "resolve audit retention and peer append")
    assert path.read_bytes() == trimmed + peer
    assert len(git_repo.git("rev-list", "--parents", "-n", "1", "HEAD").split()) == 3


def test_trim_and_phone_home_alternate_preserving_delayed_unread_movement(git_repo, monkeypatch):
    cfg, path = _seed(git_repo, _line("consumed"))
    parent = _phone(git_repo, path.read_bytes())
    delayed = _line("unread")
    path.write_bytes(path.read_bytes() + delayed)
    assert git.publish(cfg, [path], "Log: delayed work")
    assert "Removed 1 events" in trim_log.trim(cfg, clock=lambda: TODAY)
    assert path.read_bytes() == delayed
    assert _report(cfg, monkeypatch) == 1
    for index in range(3):
        assert "Removed 1 events" in trim_log.trim(cfg, clock=lambda: TODAY)
        assert _report(cfg, monkeypatch) == 0
        path.write_bytes(path.read_bytes() + _line(f"unread-{index}"))
        assert git.publish(cfg, [path], "Log: backdated work")
        assert "unchanged" in trim_log.trim(cfg, clock=lambda: TODAY)
        assert _report(cfg, monkeypatch) == 1
    assert phone_home._state(read_blackboard(parent))[0]["run"] == 14


def test_parked_phone_home_preserves_unread_movement_and_cursor_identity(git_repo):
    cfg, path = _seed(git_repo, _line("consumed"))
    parent = _phone(git_repo, path.read_bytes())
    unread = _line("delayed")
    path.write_bytes(path.read_bytes() + unread)
    parked = parent.parent.with_name("_phone-home")
    parent.parent.rename(parked)
    git_repo.git("add", "coga/log.md", "coga/recurring")
    git_repo.git("commit", "-m", "park reporting with an unread suffix")
    git_repo.git("push", "origin", "main")
    parent = parked / "ticket.md"
    prefix = parent.read_bytes().split(b"<!-- coga:blackboard -->")[0]
    assert "Removed 1 events" in trim_log.trim(cfg, clock=lambda: TODAY)
    assert path.read_bytes() == unread
    state = phone_home._state(read_blackboard(parent))[0]
    assert state["schema"] == 2 and state["repo_id"] == REPO_ID and state["run"] == 7
    assert parent.read_bytes().split(b"<!-- coga:blackboard -->")[0] == prefix
    assert not (cfg.repo_root / "recurring/phone-home").exists()
    assert "unchanged" in trim_log.trim(cfg, clock=lambda: TODAY)


def test_cursor_reservation_during_rejected_trim_is_replanned(git_repo, monkeypatch):
    from coga.movement_cursor import movements, replace_state
    cfg, path = _seed(git_repo, _line("consumed"))
    parent = _phone(git_repo, path.read_bytes())
    path.write_bytes(path.read_bytes() + _line("unread"))
    assert git.publish(cfg, [path], "Log: unread movement")
    region = read_blackboard(parent)
    state = {"schema": 2, "run": 8, "repo_id": REPO_ID, "seen_movements": sorted(movements(path.read_bytes()))}
    reserved = parent.read_bytes()[:-len(region.encode())] + replace_state(region, state).encode()
    original_push = git._push
    raced = False
    def reserve(root, remote, refspec):
        nonlocal raced
        if not raced:
            raced = True
            git_repo.push_competing_commit("coga/recurring/phone-home/ticket.md", reserved.decode())
        return original_push(root, remote, refspec)
    monkeypatch.setattr(git, "_push", reserve)
    assert "Removed 2 events" in trim_log.trim(cfg, clock=lambda: TODAY)
    assert phone_home._state(read_blackboard(parent))[0] == state
    assert _report(cfg, monkeypatch) == 0
    assert not log_transaction.pending(cfg)


@pytest.mark.parametrize("problem", ["bad-prefix", "malformed", "dual-parent", "missing-parent", "fork"])
def test_incompatible_installed_cursor_refuses_before_changing_history(git_repo, problem):
    from coga.movement_cursor import replace_state
    cfg, path = _seed(git_repo)
    parent = _phone(git_repo, path.read_bytes())
    if problem in {"bad-prefix", "malformed"}:
        region = read_blackboard(parent)
        state = phone_home._state(region)[0]
        if problem == "bad-prefix":
            state["digest"] = "0" * 64
        else:
            state["schema"] = 99
        replace_blackboard(parent, replace_state(region, state))
    elif problem == "dual-parent":
        shutil.copytree(parent.parent, parent.parent.with_name("_phone-home"))
    elif problem == "missing-parent":
        parent.unlink()
    else:
        parent.with_name("ticket.py").write_text("# local fork\n")
    git_repo.git("add", "coga/recurring")
    git_repo.git("commit", "-m", "seed incompatible reporting state")
    git_repo.git("push", "origin", "main")
    before = path.read_bytes()
    parents = {p: p.read_bytes() for p in (cfg.repo_root / "recurring").rglob("ticket.md")}
    with pytest.raises(ValueError, match="phone-home"):
        trim_log.trim(cfg, clock=lambda: TODAY)
    assert path.read_bytes() == before
    assert all(p.read_bytes() == raw for p, raw in parents.items())
    assert not log_transaction.pending(cfg)


def test_local_append_waits_until_trim_replacement_closes(git_repo, monkeypatch):
    import threading
    from coga import atomicio
    cfg, path = _seed(git_repo)
    attempted = threading.Event()
    finished = threading.Event()
    writer = None
    original = atomicio.atomic_write_bytes
    def append():
        attempted.set()
        append_log(cfg, "local-peer", "human:b", "survives atomic replacement")
        finished.set()
    def replace_with_peer(target, data):
        nonlocal writer
        if target == path and writer is None:
            writer = threading.Thread(target=append)
            writer.start()
            assert attempted.wait(5)
            assert not finished.is_set()
        original(target, data)
    monkeypatch.setattr(atomicio, "atomic_write_bytes", replace_with_peer)
    trim_log.trim(cfg, clock=lambda: TODAY)
    writer.join(5)
    assert finished.is_set()
    assert b"survives atomic replacement" in path.read_bytes()


def test_trim_retry_replans_inventory_after_rejected_push(git_repo, monkeypatch):
    cfg, path = _seed(git_repo)
    push = git._push
    raced = False
    def race(root, remote, refspec):
        nonlocal raced
        if not raced:
            raced = True
            git_repo.push_competing_commit("coga/tasks/retired.md", "---\ntitle: Back on disk\nstatus: draft\nowner: marc\nworkflow: null\n---\n\n<!-- coga:blackboard -->\n")
        return push(root, remote, refspec)
    monkeypatch.setattr(git, "_push", race)
    result = trim_log.trim(cfg, clock=lambda: TODAY)
    assert "unchanged" in result
    assert _line() in path.read_bytes()
    assert b"sync refused" not in path.read_bytes() or b"sync refused" in git.tree_bytes(git_repo.root, "HEAD", "coga/log.md")
    assert not log_transaction.pending(cfg)


@pytest.mark.parametrize("writer", ["ref", "returned-append"])
def test_retraction_and_trim_share_transaction_lock(git_repo, monkeypatch, writer):
    import threading
    from coga import atomicio
    from coga.logfile import retract_log_append, retract_log_lines
    cfg, path = _seed(git_repo)
    before = path.read_bytes()
    refused = b"2026-10-26 12:00 [refused] [git] rejected\nlegacy continuation\n"
    peer = _line("peer", "2026-10-26 12:01", "peer event")
    started = threading.Event()
    finished = threading.Event()
    failures = []
    def maintenance():
        started.set()
        try:
            trim_log.trim(cfg, clock=lambda: TODAY)
        except BaseException as exc:
            failures.append(exc)
        finally:
            finished.set()
    thread = threading.Thread(target=maintenance)
    original = atomicio.atomic_write_bytes
    first = True
    def competing_trim(target, raw, **kwargs):
        nonlocal first
        if first and target == path:
            first = False
            thread.start()
            assert started.wait(5)
            assert not finished.is_set()
        return original(target, raw, **kwargs)
    monkeypatch.setattr(atomicio, "atomic_write_bytes", competing_trim)
    with git.state_lock(cfg):
        path.write_bytes(before + refused + peer)
        if writer == "ref":
            retract_log_lines(cfg, "refused", before)
        else:
            assert retract_log_append(cfg, before, refused)
    thread.join(10)
    assert finished.is_set() and not failures
    assert path.read_bytes() == _line("recent", "2026-10-26 12:00") + peer


def test_retention_refuses_bad_ledger_before_any_delete(git_repo):
    raw = _line("recurring/absent", message="reused recurring/absent for nonsense") + _line()
    cfg, path = _seed(git_repo, raw)
    with pytest.raises(RetentionError, match="invalid serviced period"):
        trim_log.trim(cfg, clock=lambda: TODAY)
    assert path.read_bytes() == raw
    assert not log_transaction.pending(cfg)


def test_trim_preserves_all_discovered_statuses(git_repo):
    from coga.lifecycle import VALID_STATUSES
    raw = b"".join(_line(status) for status in sorted(VALID_STATUSES)) + _line("removed")
    cfg, path = _seed(git_repo, raw)
    for status in VALID_STATUSES:
        (cfg.repo_root / "tasks" / f"{status}.md").write_text(
            f"---\ntitle: Retained {status}\nstatus: {status}\nowner: marc\nworkflow: null\n---\n\n<!-- coga:blackboard -->\n"
        )
    git_repo.git("add", "coga/tasks")
    git_repo.git("commit", "-m", "seed every task status")
    git_repo.git("push", "origin", "main")
    assert "Removed 1 events" in trim_log.trim(cfg, clock=lambda: TODAY)
    assert path.read_bytes() == raw.removesuffix(_line("removed"))


def test_trim_refuses_local_inventory_edit_during_rejected_push(git_repo, monkeypatch):
    cfg, path = _seed(git_repo)
    before = path.read_bytes()
    def reject(root, remote, refspec):
        (cfg.repo_root / "tasks/retired.md").write_text(
            "---\ntitle: Local draft\nstatus: draft\nowner: marc\nworkflow: null\n---\n"
        )
        return "rejected (fetch first)"
    monkeypatch.setattr(git, "_push", reject)
    with pytest.raises(RetentionError, match="unpublished edits"):
        trim_log.trim(cfg, clock=lambda: TODAY)
    assert path.read_bytes() == before
    assert (cfg.repo_root / "tasks/retired.md").exists()
    assert not log_transaction.pending(cfg)


def test_trim_honors_crlf_clean_conversion(git_repo):
    cfg, path = _seed(git_repo)
    git_repo.git("config", "core.autocrlf", "true")
    path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
    assert "Removed 1 events" in trim_log.trim(cfg, clock=lambda: TODAY)
    assert path.read_bytes().replace(b"\r\n", b"\n") == _line("recent", "2026-10-26 12:00")


def test_ledger_cache_accepts_only_semantically_unchanged_deletions(git_repo):
    from coga import recurring_runner as r
    ref = "recurring/missing"
    old = _line(ref, message="created recurring/missing for 2020-01-01")
    high = _line(ref, message="reused recurring/missing for 2025-12-31")
    cfg, path = _seed(git_repo, old + high)
    before = git_repo.git("rev-parse", "HEAD").strip()
    cache = {r._LEDGER_REVISION: before, r._LEDGER_PUBLISHED: "yes", r._LEDGER_LOADED: "yes", ref: "2025-12-31"}
    trim_log.trim(cfg, clock=lambda: TODAY)
    after = git_repo.git("rev-parse", "HEAD").strip()
    assert r._control_serviced_period_cached(git_repo.root, after, "coga/log.md", ref, cache) == "2025-12-31"
    path.write_bytes(path.read_bytes() + _line(ref, message="reused recurring/missing for 2026-12-31"))
    git_repo.git("add", "coga/log.md")
    git_repo.git("commit", "-m", "competitor services later period")
    with pytest.raises(r._ControlLedgerChanged):
        r._control_serviced_period_cached(git_repo.root, git_repo.git("rev-parse", "HEAD").strip(), "coga/log.md", ref, cache)


def test_archived_replay_is_subsumed_for_checkout_and_warning(git_repo, tmp_path, capsys):
    from coga.cli import _log_mark, _warn_unpublished_log_lines
    cfg, path = _seed(git_repo)
    peer, peer_root = _clone(git_repo, tmp_path)
    mark = _log_mark(peer)
    trim_log.trim(cfg, clock=lambda: TODAY)
    git_repo.git("fetch", "origin", "main", cwd=peer_root)
    peer_log = peer.repo_root / "log.md"
    peer_log.write_bytes(_line() + _line("recent", "2026-10-26 12:00") + _line())
    _warn_unpublished_log_lines(peer, mark)
    assert "not on" not in capsys.readouterr().err
    result = git.prepare_control_checkout(peer)
    assert result.kind != "refused"
    mark = _log_mark(peer)
    peer_log.write_bytes(_line("new", "2020-01-02 00:00"))
    _warn_unpublished_log_lines(peer, mark)
    assert "new" in capsys.readouterr().err
