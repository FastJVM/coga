from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

import pytest

from coga.config import ConfigError, load_config
from coga.log_retention import RetentionError, RetentionSnapshot, cutoff_at, select
from coga.logfile import parse_events
from coga.movement_cursor import MovementError, cursor, migrate, movements


def _line(stamp="2020-01-01 00:00", ref="retired", message="task done", version="v1 "):
    return f"{stamp} {version}[{ref}] [human:a] {message}\n".encode()


def test_selection_cutoff_existing_history_opaque_and_exact_bytes():
    old = _line("2026-09-26 23:59")
    existing = _line(ref="live", version="") + b"legacy\\n continuation\n"
    boundary = _line("2026-09-27 00:00")
    after = _line("2026-09-27 00:01")
    future = _line("2030-01-01 00:00")
    raw = old + existing + boundary + after + future
    plan = select(raw, RetentionSnapshot(frozenset({"live"})), cutoff_at(date(2026, 10, 27), 30))
    assert plan.mutation.postimage == existing + boundary + after + future
    assert plan.mutation.removed == (0,)
    assert select(plan.mutation.postimage, RetentionSnapshot(frozenset({"live"})), datetime(2026, 9, 27)).mutation.postimage == plan.mutation.postimage
    assert cutoff_at(date(2026, 10, 27), 10**100) == datetime.min
    assert cutoff_at(date(2026, 3, 9), 1) == datetime(2026, 3, 8)


@pytest.mark.parametrize("tail", [b"opaque\n", b"2020-99-01 12:00 v1 [other] [x] bad\n", b"\xff\n", b"unfinished"])
def test_opaque_blocks_preserve_display_boundary(tail):
    recent = _line("2030-01-01 00:00", ref="existing")
    old = _line(ref="removed")
    raw = recent + old + tail
    assert select(raw, RetentionSnapshot(frozenset({"existing"})), datetime(2026, 1, 1)).mutation.postimage == raw


@pytest.mark.parametrize("raw", [
    b"orphan\n", _line()[:-1], _line(version="") + b"partial",
    _line(version="v2 "), _line(stamp="2020-02-31 00:00"), b"\xff\n",
])
def test_uncertain_events_are_preserved(raw):
    assert b"".join(e.raw for e in parse_events(raw)) == raw
    assert select(raw, RetentionSnapshot(frozenset()), datetime(2026, 1, 1)).mutation.postimage == raw


def test_legacy_continuations_and_v1_escaping_remain_byte_exact():
    legacy = _line(version="") + b"[tag] continuation\n"
    retained = _line("2030-01-01 00:00", message=r"literal \\n escaped \n")
    raw = (legacy + retained).replace(b"\n", b"\r\n")
    assert select(raw, RetentionSnapshot(frozenset()), datetime(2026, 1, 1)).mutation.postimage == retained.replace(b"\n", b"\r\n")


def test_ledger_greatest_period_duplicates_pause_ties_and_reset_survive():
    earlier = _line(ref="recurring/parked", message="reused recurring/parked for 2025-W01")
    greatest = _line(ref="recurring/parked", message="created recurring/parked for 2025-12-31")
    pause = _line(ref="recurring/parked", message="paused (in_progress → paused)")
    reset = _line(ref="recurring/parked", message="created (status=active)")
    raw = greatest + earlier + greatest + pause + reset
    kept = select(raw, RetentionSnapshot(frozenset()), datetime(2026, 1, 1)).mutation.postimage
    assert kept == greatest + greatest + reset
    bad = _line(ref="recurring/parked", message="reused recurring/parked for invalid")
    with pytest.raises(RetentionError, match="invalid serviced period"):
        select(bad + raw, RetentionSnapshot(frozenset()), datetime(2026, 1, 1))


def test_cursor_migration_unread_dedup_crlf_and_repeated_removal():
    import hashlib
    first, second = _line(ref="a"), _line(ref="b")
    seed = {"schema": 1, "run": 7, "repo_id": "dd2433c0-7277-4a63-8640-c73089700480", "offset": len(first), "digest": hashlib.sha256(first).hexdigest()}
    migrated, reset = migrate(first + second, seed)
    assert migrated["run"] == 7 and not reset
    assert set(migrated["seen_movements"]) == movements(first)
    hashes, count, reset = cursor(first + second + second, migrated, baseline=False)
    assert count == 1 and not reset
    state = {**migrated, "seen_movements": hashes}
    assert cursor(second.replace(b"\n", b"\r\n"), state, baseline=False)[1:] == (0, False)
    assert cursor(b"", state, baseline=False)[1:] == (0, False)
    with pytest.raises(MovementError, match="prefix is invalid"):
        migrate(second, seed)



def test_inventory_ignores_root_ticket_like_list_tasks():
    from coga.log_publication import inventory
    ticket = b"---\nstatus: draft\n---\nbody\n"
    files = {"ticket.md": b"not a ticket", "a.md": ticket, "b/ticket.md": ticket, "c/d.md": ticket}
    assert inventory(files) == frozenset({"a", "b", "c/d"})


def test_publication_cursor_accepts_legacy_crlf_prefix():
    import hashlib
    from coga.log_publication import cursor_state
    from coga.taskfile import BLACKBOARD_FENCE
    first, second = _line(ref="a"), _line(ref="b")
    crlf = first.replace(b"\n", b"\r\n")
    seed = {"schema": 1, "run": 7, "repo_id": "dd2433c0-7277-4a63-8640-c73089700480",
            "offset": len(crlf), "digest": hashlib.sha256(crlf).hexdigest()}
    parent = f"---\nstatus: active\n---\n{BLACKBOARD_FENCE}\nperiod_state: {json.dumps(seed)}\n".encode()
    assert set(cursor_state(parent, first + second)["seen_movements"]) == movements(first)
    with pytest.raises(MovementError, match="prefix is invalid"):
        cursor_state(parent, second + first)


def test_all_existing_history_readers_and_service_order_are_unchanged(tmp_path):
    import io
    from rich.console import Console
    from coga import logfile
    from coga.recurring import _pause_origins, read_serviced_ledger
    from coga.config import Config
    from coga.service_order import service_order
    from coga.tasks import list_tasks
    from coga.views import render_show
    cfg = Config(repo_root=tmp_path, current_user="a", default_status="draft", agents={}, slack_webhook=None, slack_enabled=False)
    (tmp_path / "tasks").mkdir()
    for ref, status in [("a", "canceled"), ("b", "draft")]:
        (tmp_path / "tasks" / f"{ref}.md").write_text(f"---\ntitle: {ref}\nstatus: {status}\nowner: a\nworkflow: null\n---\n\n<!-- coga:blackboard -->\n")
    raw = (_line(ref="a", version="") + b"legacy\n" + _line(ref="retired")
           + _line("2026-10-27 00:00", ref="a", message="task canceled — no longer needed")
           + _line(ref="b") + _line(ref="recurring/gone", message="paused (in_progress → paused)"))
    path = tmp_path / "log.md"
    path.write_bytes(raw)
    def readers():
        console = Console(file=io.StringIO(), width=120)
        render_show(cfg, "a", console=console)
        return (logfile.task_log_lines(cfg, "a"), logfile.first_activity_map(cfg)["a"],
                logfile.last_activity_map(cfg)["a"],
                [v for v in logfile.iter_log_messages(cfg) if v[0] == "a"],
                [v for v in logfile.iter_log_messages_reverse(cfg) if v[0] == "a"],
                _pause_origins(cfg, {"recurring/gone"}), read_serviced_ledger(cfg),
                service_order(list_tasks(cfg), logfile.first_activity_map(cfg)), console.file.getvalue())
    before = readers()
    path.write_bytes(select(raw, RetentionSnapshot(frozenset({"a", "b"})), datetime(2026, 9, 27)).mutation.postimage)
    assert readers() == before


@pytest.mark.parametrize("value", ["true", "-1", "1.0", '"30"', "[]"])
def test_config_retention_rejects_non_integer_policy(tmp_path, value):
    (tmp_path / "coga.toml").write_text(f"version = 1\n[log]\nretention_days = {value}\n")
    with pytest.raises(ConfigError, match="non-negative int"):
        load_config(tmp_path, require_user=False)


@pytest.mark.parametrize("text,local", [("log = 1", False), ("[log]\nother = 30", False), ("[log]\nretention_days = 0", True)])
def test_config_retention_rejects_shape_keys_and_local_override(tmp_path, text, local):
    (tmp_path / "coga.toml").write_text("version = 1\n" + ("" if local else text))
    if local:
        (tmp_path / "coga.local.toml").write_text(text)
    with pytest.raises(ConfigError):
        load_config(tmp_path, require_user=False)


def test_config_retention_default_zero_and_huge(tmp_path):
    for text, value in [("", 30), ("[log]\nretention_days = 0", 0), ("[log]\nretention_days = " + str(10**100), 10**100)]:
        (tmp_path / "coga.toml").write_text("version = 1\n" + text)
        assert load_config(tmp_path, require_user=False).log_retention_days == value
