from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

import pytest

from coga import telemetry as t
from coga.config import load_config
from coga.taskfile import read_blackboard, replace_blackboard

PACKAGED = Path(__file__).resolve().parents[1] / "src/coga/resources/templates/coga"
REPO_ID = "dd2433c0-7277-4a63-8640-c73089700480"
NOW = datetime(2026, 9, 22, tzinfo=timezone.utc)
PRIVATE = "PRIVATE-SENTINEL-titles-paths-actors-bodies"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def _seed(root: Path) -> Path:
    parent = root / "recurring/phone-home/ticket.md"
    _write(parent, (PACKAGED / "recurring/phone-home/ticket.md").read_text())
    return parent


@pytest.fixture
def repo(tmp_path, monkeypatch):
    root = tmp_path / "coga"
    _write(root / "coga.toml", 'version = 1\n[git]\nenabled = false\n[agents.claude]\ncli = "claude"\nfile = "CLAUDE.md"\n')
    _write(root / "coga.local.toml", 'user = "'+PRIVATE+'"\n')
    _seed(root)
    monkeypatch.chdir(root)
    return root


def _state(root):
    return t._state(read_blackboard(root / "recurring/phone-home/ticket.md"))[0]


def _line(message="task done", ref="work", stamp="2026-09-22 07:00"):
    return f"{stamp} [{ref}] [human:{PRIVATE}] {message}\n".encode()


def _run(repo, monkeypatch, *, enabled=True, outcome="accepted"):
    monkeypatch.setattr(t, "_admitted", lambda cfg: cfg.telemetry_enabled)
    sent = []
    def sender(cfg, kind, data):
        assert _state(repo)["run"] > 0
        if kind == "capture":
            assert _state(repo)["repo_id"] == data["distinct_id"]
        sent.append((kind, data))
        return outcome
    cfg = replace(load_config(repo), telemetry_enabled=enabled)
    assert t.run_phone_home_recipe(cfg, [], sender=sender, clock=lambda: NOW, identity=lambda: UUID(REPO_ID)) == 0
    return sent


def test_first_next_quiet_and_lost_delivery(repo, monkeypatch):
    (repo / "log.md").write_bytes(_line())
    first = _run(repo, monkeypatch)
    assert first[0][1]["properties"]["movement_count"] == 0
    (repo / "log.md").write_bytes(_line() + _line("advanced to step 2 (review)"))
    failed = _run(repo, monkeypatch, outcome="network-error")
    assert failed[0][1]["properties"]["movement_count"] == 1
    quiet = _run(repo, monkeypatch)
    assert quiet[0][1]["properties"]["movement_count"] == 0
    assert first[0][1]["distinct_id"] == quiet[0][1]["distinct_id"] == REPO_ID
    assert _state(repo)["run"] == 3


def test_disabled_has_no_identity_worker_or_receipt_and_reenable_counts_gap(repo, monkeypatch):
    monkeypatch.setattr(t, "_bounded_worker", lambda *a: pytest.fail("worker created"))
    monkeypatch.setattr(t, "_admitted", lambda cfg: cfg.telemetry_enabled)
    cfg = replace(load_config(repo), telemetry_enabled=False)
    t.run_phone_home_recipe(cfg, [], identity=lambda: pytest.fail("minted identity"))
    assert _state(repo)["repo_id"] is None
    _run(repo, monkeypatch)
    (repo / "log.md").write_bytes(_line())
    assert _run(repo, monkeypatch, enabled=False) == []
    (repo / "log.md").write_bytes(_line() + _line("task done — gap"))
    resumed = _run(repo, monkeypatch)
    assert resumed[0][1]["properties"]["movement_count"] == 1
    assert _state(repo)["run"] == 4


def test_inventory_scope_and_exact_zero_statuses(repo, monkeypatch):
    for index, status in enumerate(sorted(t.VALID_STATUSES)):
        name = f"tasks/v2/{status}.md" if index % 2 else f"tasks/{status}/ticket.md"
        _write(repo/name, f"---\nstatus: {status}\ntitle: {PRIVATE}\n---\n{PRIVATE}\n")
    for name in ("tasks/recurring/a.md", "tasks/_template/ticket.md", "tasks/README.md", "tasks/active/attachment.md"):
        _write(repo/name, "not a ticket")
    props = _run(repo, monkeypatch)[0][1]["properties"]
    assert all(props[f"tickets_{s}"] == 1 for s in t.VALID_STATUSES)
    assert PRIVATE not in json.dumps(props)
    for path in (repo/"tasks").rglob("*.md"):
        path.unlink()
    props = _run(repo, monkeypatch)[0][1]["properties"]
    assert all(props[f"tickets_{s}"] == 0 for s in t.VALID_STATUSES)


@pytest.mark.parametrize("bad", ["bad-status", "duplicate", "malformed"])
def test_invalid_inventory_preserves_cursor_identity_but_advances_run(repo, monkeypatch, bad, capsys):
    _run(repo, monkeypatch)
    before = _state(repo)
    (repo / "log.md").write_bytes(_line())
    _write(repo/"tasks/work.md", "---\nstatus: draft\n---\n")
    if bad == "duplicate":
        _write(repo/"tasks/work/ticket.md", "---\nstatus: draft\n---\n")
    else:
        _write(repo/"tasks/work.md", "---\nstatus: bogus\n---\n" if bad == "bad-status" else "---\nbad: [\n---\n")
    assert _run(repo, monkeypatch) == []
    after = _state(repo)
    assert after == {**before, "run": before["run"] + 1}
    assert "snapshot skipped" in capsys.readouterr().out


@pytest.mark.parametrize("message,expected", [
    ("advanced to step 2 (review)", True),
    ("advanced to step 2 (review) → claude — ready", True),
    ("task done", True), ("task done — ready", True),
    ("auto-bumped on merge of PR #42 → done", True),
    ("auto-bumped on merge of the linked PR → done", True),
    ("advanced to step 0 (review)", False),
    ("advanced to step 2 ()", False),
    ("advanced to step 2 (review)garbage", False),
    ("advanced to step 2 (review) → ", False),
    ("advanced to step 2 (review) →  ", False),
    ("advanced to step 2 (review\nowner)", False),
    ("task donegarbage", False), ("task done-ish", False),
    ("auto-bumped on merge of PR #42 → donegarbage", False),
    ("rewound to step 1 (code)", False), ("created", False),
    ("launched", False), ("task paused", False), ("blocked", False),
    ("unblocked", False), ("prose task done", False),
])
def test_movement_grammar(message, expected):
    assert t._movement(_line(message).rstrip(b"\n")) is expected


def test_movement_counts_real_bumps_with_spaced_names_and_parentheses(repo, monkeypatch):
    from typer.testing import CliRunner

    from coga.cli import app
    from coga.create import create_task
    from coga.logfile import append_log, iter_log_messages

    _write(repo / "coga.local.toml", 'user = "Jane Doe"\n')
    _write(repo / "workflows/review.md", """---
name: review
steps:
  - name: implement
    assignee: agent
    skills: []
  - name: review (owner)
    assignee: owner
    skills: []
---
## implement
Implement.
## review (owner)
Review.
""")
    cfg = load_config(repo)
    created = create_task(
        cfg=cfg, title="Work", workflow_name="review", contexts=[],
        owner="Jane Doe", status="in_progress", agent="claude",
    )
    _run(repo, monkeypatch)
    for _ in range(2):
        result = CliRunner().invoke(app, ["bump", created["slug"]])
        assert result.exit_code == 0, result.output
    messages = [message for _, message in iter_log_messages(cfg)]
    assert "advanced to step 2 (review (owner)) → Jane Doe" in messages
    assert "task done" in messages
    assert "[human:Jane Doe] task done" in (repo / "log.md").read_text()
    append_log(cfg, "recurring/phone-home", "human:Jane Doe", "task done")
    event = _run(repo, monkeypatch)[0][1]
    assert event["properties"]["movement_count"] == 2


@pytest.mark.parametrize("line", [b"prose task done", _line(ref="recurring"), _line(ref="recurring/phone-home"), _line(stamp="2026-99-22 07:00"), b"2026-09-22 07:00 [] [] task done", b"2026-09-22 07:00 [work] [ ] task done", b"2026-09-22 07:00 [ ] [human:Jane Doe] task done", b"2026-09-22 07:00 [work] [human:Jane\nDoe] task done", b"\xff"])
def test_movement_rejects_housekeeping_and_malformed_envelopes(line):
    assert not t._movement(line.rstrip(b"\n"))


def test_cursor_complete_lines_dedup_equal_and_unsorted_times_rewrites():
    seed = {"offset": 0, "digest": hashlib.sha256(b"").hexdigest()}
    raw = _line(ref="deleted") + _line(ref="deleted") + _line(ref="other", stamp="2020-01-01 01:00") + b"partial"
    offset, digest, count, reset = t._cursor(raw, seed, baseline=False)
    assert count == 2 and not reset
    assert raw[offset:] == b"partial"
    state = {"offset": offset, "digest": digest}
    assert t._cursor(raw, state, baseline=False)[2:] == (0, False)
    for rewrite in (b"", _line("task done — rewritten") + raw):
        assert t._cursor(rewrite, state, baseline=False)[2:] == (0, True)
    prefix = _line()[:-1]
    offset, digest, _, _ = t._cursor(prefix, seed, baseline=False)
    assert offset == 0
    assert t._cursor(prefix+b"\n", {"offset":offset,"digest":digest}, baseline=False)[2] == 1


def test_exact_http_envelope_and_provenance(repo, monkeypatch):
    _write(repo/"tasks/private.md", f"---\nstatus: draft\ntitle: {PRIVATE}\n---\n{PRIVATE}\n")
    (repo/"log.md").write_bytes(_line("task done — "+PRIVATE))
    monkeypatch.setattr(t, "version", lambda name: "0.3.2+test" if name == "coga" else pytest.fail("metadata source"))
    monkeypatch.setattr(t.platform, "release", lambda: "6.8.0-"+PRIVATE)
    monkeypatch.setattr(t.platform, "system", lambda: "Linux")
    event = _run(repo, monkeypatch)[0][1]
    bodies = []
    monkeypatch.setattr(t, "_post_http", lambda body: bodies.append(body) or "accepted")
    assert t._capture(load_config(repo), event) == "accepted"
    wire = json.loads(bodies[0])
    assert set(wire) == {"api_key", "event", "distinct_id", "timestamp", "properties"}
    assert wire["api_key"] == "test-capture-key"
    assert wire["event"] == "coga_weekly_snapshot"
    assert wire["distinct_id"] == REPO_ID and wire["timestamp"] == "2026-09-22T00:00:00Z"
    assert wire["properties"] == {
        "coga_version":"0.3.2+test", "os_name":"linux", "os_version":"6.8.0",
        "python_version":".".join(map(str, sys.version_info[:3])),
        **{f"tickets_{s}":int(s == "draft") for s in t.VALID_STATUSES}, "movement_count":0,
    }
    assert PRIVATE.encode() not in bodies[0]
    assert all(type(wire["properties"][k]) is int for k in t._COUNT_KEYS)


@pytest.mark.parametrize("value", ["SECRET invalid", "a"*65, "1.2/secret", "1.2é"])
def test_invalid_package_version_fails_before_identity_reservation(repo, monkeypatch, value):
    monkeypatch.setattr(t, "version", lambda _: value)
    with pytest.raises(t.TelemetryError, match="invalid phone-home event"):
        _run(repo, monkeypatch)
    assert _state(repo)["run"] == 0


@pytest.mark.parametrize("mutation", [lambda e: e.update(extra="private"), lambda e: e["properties"].update(movement_count=True), lambda e: e["properties"].update(owner="private"), lambda e: e.update(distinct_id="private"), lambda e: e.update(timestamp="private")])
def test_worker_schema_rejects_extra_or_wrong_types(repo, monkeypatch, mutation):
    event = _run(repo, monkeypatch)[0][1]
    mutation(event)
    with pytest.raises(t.TelemetryError):
        t._capture(load_config(repo), event)


def test_admission_all_gates_and_symlinks(repo, monkeypatch, tmp_path):
    cfg = load_config(repo)
    monkeypatch.delenv("PYTEST_CURRENT_TEST")
    monkeypatch.delenv("CI", raising=False)
    assert not t._admitted(cfg)  # source import
    monkeypatch.setattr(t, "__file__", str(tmp_path/"site-packages/coga/telemetry.py"))
    assert t._admitted(cfg)
    assert not t._admitted(replace(cfg, telemetry_enabled=False))
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "")
    assert not t._admitted(cfg)
    monkeypatch.delenv("PYTEST_CURRENT_TEST")
    monkeypatch.setenv("CI", "true")
    assert not t._admitted(cfg)
    monkeypatch.delenv("CI")
    dev = tmp_path/"dev"
    _write(dev/"pyproject.toml", '[project]\nname = "coga"\n')
    _write(dev/"src/coga/runner.py", "")
    (dev/"tests").mkdir()
    (dev/"example").mkdir()
    link = tmp_path/"linked"
    link.symlink_to(dev, target_is_directory=True)
    assert not t._admitted(replace(cfg, repo_root=link/"example"))
    monkeypatch.chdir(link/"example")
    assert not t._admitted(cfg)


def test_suppressed_updates_marker_without_identity(repo):
    t.run_phone_home_recipe(load_config(repo), [], identity=lambda: pytest.fail("identity"), sender=lambda *a: pytest.fail("sender"))
    assert _state(repo)["run"] == 1 and _state(repo)["repo_id"] is None


def test_real_worker_inherits_test_gate(repo):
    result = subprocess.run([sys.executable, "-c", "from coga.telemetry import _worker_main; _worker_main()", "capture", str(repo)], input="{}", text=True, capture_output=True, timeout=5)
    assert result.stdout.strip() == "suppressed"


def test_parent_deadline_kills_and_reaps_sleeping_worker(repo, monkeypatch):
    monkeypatch.setattr(t, "_admitted", lambda cfg: True)
    monkeypatch.setattr(t, "_DEADLINE", 0.05)
    popen = subprocess.Popen
    children = []
    def sleeping(*args, **kwargs):
        child = popen([sys.executable,"-c","import time; time.sleep(60)"], **kwargs)
        children.append(child)
        return child
    monkeypatch.setattr(t.subprocess, "Popen", sleeping)
    assert t._bounded_worker(load_config(repo), "capture", {}) == "timed-out"
    assert children[0].poll() is not None


def test_slack_receipt_keyless_and_nonfatal(repo, monkeypatch):
    event = _run(repo, monkeypatch)[0][1]
    cfg = replace(load_config(repo), notification_channels=["slack"], slack_enabled=True)
    calls = []
    monkeypatch.setattr(t.notification, "post", lambda *a, **kw: calls.append((a, kw)))
    assert t._receipt(cfg, event, "accepted") == "accepted"
    args, kwargs = calls[0]
    assert kwargs == {"fatal":False,"record_failure":False}
    assert args[1].startswith("phone-home attempted / HTTP accepted: ")
    assert json.loads(args[1].split(": ",1)[1]) == event
    assert "api_key" not in args[1]


def test_period_report_aggregates_delivery_failure_without_failing(repo, monkeypatch):
    period = repo/"tasks/recurring/phone-home/ticket.md"
    _write(period, "---\nstatus: in_progress\n---\n\n<!-- coga:blackboard -->\n")
    monkeypatch.setenv("COGA_TASK_BLACKBOARD", str(period))
    monkeypatch.setattr(t, "_admitted", lambda cfg: True)
    cfg = replace(load_config(repo), notification_channels=["slack"], slack_enabled=True)
    calls = []
    def sender(cfg, kind, data):
        calls.append(kind)
        return "rejected" if kind == "capture" else "timed-out"
    assert t.run_phone_home_recipe(cfg, [], sender=sender) == 0
    assert calls == ["capture", "receipt"]
    report = read_blackboard(period)
    assert report.count("Warning:") == 1
    assert "capture rejected" in report and "receipt timed-out" in report
    assert _state(repo)["run"] == 1


@pytest.mark.parametrize("state", ["{}", "not json", '{"schema":true,"run":0,"repo_id":null,"offset":0,"digest":"x"}'])
def test_corrupt_state_and_argv_fail_visibly_without_sending(repo, state):
    parent = repo/"recurring/phone-home/ticket.md"
    replace_blackboard(parent, "\nperiod_state: "+state+"\n")
    for argv in ([], ["--help"]):
        with pytest.raises(t.TelemetryError):
            t.run_phone_home_recipe(load_config(repo), argv, sender=lambda *a: pytest.fail("sent"))


def test_parent_publication_reaches_second_checkout_without_dirty_files(git_repo, monkeypatch, tmp_path):
    root = git_repo.coga_os
    parent = _seed(root)
    _write(git_repo.root/"tracked.txt", "committed")
    git_repo.git("add", "coga/recurring/phone-home/ticket.md", "tracked.txt")
    git_repo.git("commit", "-m", "seed phone home")
    git_repo.git("push", "origin", "main")
    header = parent.read_bytes().split(b"<!-- coga:blackboard -->")[0]
    _write(git_repo.root/"unrelated.txt", "leave dirty")
    _write(git_repo.root/"tracked.txt", "tracked dirty")
    _run(root, monkeypatch)
    assert parent.read_bytes().split(b"<!-- coga:blackboard -->")[0] == header
    assert not git_repo.origin_tracks("unrelated.txt")
    assert (git_repo.root/"tracked.txt").read_text() == "tracked dirty"
    assert git_repo.git("show", "main:tracked.txt", cwd=git_repo.origin) == "committed"
    clone = tmp_path/"second"
    git_repo.git("clone", "-b", "main", str(git_repo.origin), str(clone))
    assert (clone/"coga/recurring/phone-home/ticket.md").read_bytes() == parent.read_bytes()
    _write(clone/"coga/coga.local.toml", 'user = "marc"\n')
    assert _state(clone/"coga")["repo_id"] == REPO_ID


def test_http_one_post_no_redirect_or_response_body(repo, monkeypatch):
    # Bypass only the suite's rejection wrapper, intercept the actual HTTP API.
    import importlib
    original = t._post_http
    fresh = importlib.util.spec_from_file_location("telemetry_transport_test", t.__file__)
    module = importlib.util.module_from_spec(fresh)
    fresh.loader.exec_module(module)
    calls = []
    class Connection:
        def __init__(self, host, timeout):
            calls.append((host, timeout))
        def request(self, *args, **kwargs):
            calls.append((args, kwargs))
        def getresponse(self):
            return type("Response", (), {"status":302})()
        def close(self):
            calls.append("closed")
    monkeypatch.setattr(module.http.client, "HTTPSConnection", Connection)
    assert module._post_http(b"{}") == "rejected"
    assert len(calls) == 3 and calls[-1] == "closed"
    assert calls[1][0] == ("POST", "/i/v0/e/")
    assert t._post_http is original


def test_false_gates_parent_and_worker_before_http_or_process(repo, monkeypatch):
    cfg = replace(load_config(repo), telemetry_enabled=False)
    monkeypatch.setattr(t.subprocess, "Popen", lambda *a, **kw: pytest.fail("worker created"))
    assert t._bounded_worker(cfg, "capture", {}) == "suppressed"
    assert t._capture(cfg, {}) == "suppressed"
    assert t._receipt(cfg, {}, "accepted") == "suppressed"


def test_cas_detects_parent_edit_and_preserves_prose(repo, monkeypatch):
    parent = repo/"recurring/phone-home/ticket.md"
    original = parent.read_bytes()
    actual_replace = t.replace_blackboard
    def race(path, region, *, expected_bytes):
        assert expected_bytes == original
        path.write_bytes(original + b"\nConcurrent prose\n")
        return actual_replace(path, region, expected_bytes=expected_bytes)
    monkeypatch.setattr(t, "replace_blackboard", race)
    from coga.taskfile import TaskFileError
    with pytest.raises(TaskFileError, match="changed"):
        t.run_phone_home_recipe(load_config(repo), [])
    assert parent.read_bytes() == original + b"\nConcurrent prose\n"


def test_suppressed_cursor_baselines_complete_eof(repo):
    (repo/"log.md").write_bytes(_line()+b"partial")
    t.run_phone_home_recipe(load_config(repo), [])
    assert _state(repo)["offset"] == len(_line())
    assert _state(repo)["repo_id"] is None


def test_publication_failure_keeps_reservation_and_local_evidence(repo, monkeypatch, capsys):
    def fail(*a, **kw):
        raise t.git.GitError("simulated failure")
    monkeypatch.setattr(t.git, "publish", fail)
    sent = _run(repo, monkeypatch)
    assert len(sent) == 1 and _state(repo)["run"] == 1
    assert "sync failed" in (repo/"log.md").read_text()
    assert "local state retained" in capsys.readouterr().out


def test_slack_failure_cannot_change_successful_capture(repo, monkeypatch):
    monkeypatch.setattr(t, "_admitted", lambda cfg: True)
    cfg = replace(load_config(repo), slack_enabled=True, notification_channels=["slack"])
    calls = []
    def send(cfg, kind, data):
        calls.append((kind, data))
        return "accepted" if kind == "capture" else "network-error"
    assert t.run_phone_home_recipe(cfg, [], sender=send) == 0
    assert [k for k,_ in calls] == ["capture","receipt"]
    assert calls[1][1]["outcome"] == "accepted"
    assert _state(repo)["run"] == 1


def test_crlf_parent_preserves_header_and_unrelated_prose(repo):
    parent = repo/"recurring/phone-home/ticket.md"
    raw = parent.read_bytes().replace(b"\n", b"\r\n") + b"\r\nExtra prose\r\n"
    parent.write_bytes(raw)
    t.run_phone_home_recipe(load_config(repo), [])
    after = parent.read_bytes()
    assert after.split(b"period_state:")[0] == raw.split(b"period_state:")[0]
    assert after.endswith(b"\r\n\r\nExtra prose\r\n")
    assert _state(repo)["run"] == 1
