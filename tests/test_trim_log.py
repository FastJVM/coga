from __future__ import annotations

import hashlib
import json
import shutil
from datetime import date
from uuid import UUID

import pytest

from coga.config import load_config
from coga.log_retention import RetentionError
from coga.paths import packaged_template_path
from coga.taskfile import read_blackboard, replace_blackboard
from coga_edge import phone_home, trim_log

TODAY = date(2026, 10, 27)
REPO_ID = "dd2433c0-7277-4a63-8640-c73089700480"


def _line(ref="retired", stamp="2020-01-01 00:00", message="task done"):
    return f"{stamp} v1 [{ref}] [human:a] {message}\n".encode()



def _seed(git_repo, raw=None):
    path = git_repo.coga_os / "log.md"
    path.write_bytes(raw if raw is not None else _line() + _line("recent", "2026-10-26 12:00"))
    git_repo.git("add", "coga/log.md")
    git_repo.git("commit", "-m", "seed archived history")
    git_repo.git("push", "origin", "main")
    return load_config(git_repo.coga_os), path



def _phone(git_repo, raw, *, carrier=False):
    parent = git_repo.coga_os / "recurring/phone-home/ticket.md"
    parent.parent.mkdir(parents=True)
    for name in ("ticket.md", "ticket.py"):
        shutil.copyfile(packaged_template_path("recurring", "phone-home", name), parent.with_name(name))
    state = {"schema": 1, "run": 7, "repo_id": REPO_ID, "offset": len(raw), "digest": hashlib.sha256(raw).hexdigest()}
    region = read_blackboard(parent)
    _, match = phone_home._state(region)
    replace_blackboard(parent, region[:match.start()] + "period_state: " + json.dumps(state) + region[match.end():])
    if carrier:
        from coga.recurring_state import render_carrier
        parent.write_text(render_carrier(read_blackboard(parent) + "\nother: keep\n"), encoding="utf-8", newline="\n")
        parent.with_name("ticket.py").unlink()
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



def test_install_preserves_other_selections_and_refuses_disabled(git_repo):
    cfg = load_config(git_repo.coga_os)
    jobs = cfg.repo_root / "recurring" / "jobs.toml"
    jobs.parent.mkdir(parents=True, exist_ok=True)
    jobs.write_text("# mine\n[jobs]\ndream = false\n", encoding="utf-8", newline="\n")
    trim_log.install(cfg)
    text = jobs.read_text(encoding="utf-8")
    assert text.startswith("# mine\n") and "dream = false" in text and "trim-log = true" in text
    jobs.write_text("[jobs]\ntrim-log = false\n", encoding="utf-8", newline="\n")
    before = jobs.read_bytes()
    with pytest.raises(RetentionError, match="disabled"):
        trim_log.install(cfg)
    assert jobs.read_bytes() == before



@pytest.mark.parametrize("carrier", [False, True])
def test_trim_and_phone_home_alternate_preserving_delayed_unread_movement(git_repo, monkeypatch, carrier):
    cfg, path = _seed(git_repo, _line("consumed"))
    parent = _phone(git_repo, path.read_bytes(), carrier=carrier)
    delayed = _line("unread")
    path.write_bytes(path.read_bytes() + delayed)
    assert "Removed 1 events" in trim_log.trim(cfg, clock=lambda: TODAY)
    assert path.read_bytes() == delayed
    assert _report(cfg, monkeypatch) == 1
    for index in range(3):
        assert "Removed 1 events" in trim_log.trim(cfg, clock=lambda: TODAY)
        assert _report(cfg, monkeypatch) == 0
        path.write_bytes(path.read_bytes() + _line(f"unread-{index}"))
        assert "unchanged" in trim_log.trim(cfg, clock=lambda: TODAY)
        assert _report(cfg, monkeypatch) == 1
    assert phone_home._state(read_blackboard(parent))[0]["run"] == 14
    if carrier:
        assert "other: keep" in read_blackboard(parent)



@pytest.mark.parametrize("carrier", [False, True])
def test_parked_phone_home_preserves_unread_movement_and_cursor_identity(git_repo, carrier):
    cfg, path = _seed(git_repo, _line("consumed"))
    parent = _phone(git_repo, path.read_bytes(), carrier=carrier)
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
        parent.with_name("ticket.py").write_text("# local fork\n", encoding="utf-8", newline="\n")
    git_repo.git("add", "coga/recurring")
    git_repo.git("commit", "-m", "seed incompatible reporting state")
    git_repo.git("push", "origin", "main")
    before = path.read_bytes()
    parents = {p: p.read_bytes() for p in (cfg.repo_root / "recurring").rglob("ticket.md")}
    with pytest.raises(ValueError, match="phone-home"):
        trim_log.trim(cfg, clock=lambda: TODAY)
    assert path.read_bytes() == before
    assert all(p.read_bytes() == raw for p, raw in parents.items())



def test_retention_refuses_bad_ledger_before_any_delete(git_repo):
    raw = _line("recurring/absent", message="reused recurring/absent for nonsense") + _line()
    cfg, path = _seed(git_repo, raw)
    with pytest.raises(RetentionError, match="invalid serviced period"):
        trim_log.trim(cfg, clock=lambda: TODAY)
    assert path.read_bytes() == raw



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



def test_trim_preserves_an_append_after_planning(git_repo, monkeypatch):
    cfg, path = _seed(git_repo)
    recent = path.read_bytes().splitlines(keepends=True)[-1]
    appended = _line("concurrent", "2026-10-27 13:00")
    original_replace = trim_log.replace_log

    def append_before_replace(cfg, mutation):
        with path.open("ab") as stream:
            stream.write(appended)
        original_replace(cfg, mutation)

    monkeypatch.setattr(trim_log, "replace_log", append_before_replace)
    assert "Removed 1 events" in trim_log.trim(cfg, clock=lambda: TODAY)
    assert path.read_bytes() == recent + appended
