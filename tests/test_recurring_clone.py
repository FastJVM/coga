"""`scope: clone` recurring templates: serviced per clone, with no period task."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import tracemalloc
from datetime import datetime
from pathlib import Path
from textwrap import dedent
from unittest.mock import Mock

import pytest

from conftest import windows_skip
from typer.testing import CliRunner

from coga import recurring_runner as recurring_cmd
from coga import recurring_clone, oscompat
from coga.cli import app
from coga.config import load_config
from coga.recurring import (
    RecurringError,
    Template,
    list_templates,
    scan_clone_due,
    scan_due,
)
from coga.recurring_autofix import RunRecord
from coga.recurring_clone import clone_state_dir, read_clone_ledger, run_clone_template
from coga.tasks import list_tasks


NOW = datetime(2026, 4, 22, 10, 0, 0)  # a Wednesday; the daily 7am firing is due

CLONE_TEMPLATE = """
---
schedule: "0 7 * * *"
title: "Local sweep"
scope: clone
---

## Description

Sweep this clone's local state.

<!-- coga:blackboard -->
"""

# Records what the runner handed the script, then exits with `EXIT_CODE`.
CLONE_SCRIPT = """
import json, os, sys
from pathlib import Path
out = Path(os.environ["COGA_COGA_OS_ROOT"]) / "runs.jsonl"
keys = ("COGA_RECURRING_SCOPE", "COGA_RECURRING_TEMPLATE", "COGA_RECURRING_PERIOD",
        "COGA_TASK_SLUG", "COGA_TASK_BLACKBOARD")
with out.open("a") as fh:
    fh.write(json.dumps({key: os.environ.get(key) for key in keys}) + "\\n")
print("swept local state")
sys.exit(EXIT_CODE)
"""


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


def _clone_template(company: Path, name: str = "local-sweep", *, exit_code: int = 0) -> None:
    _write(company / "recurring" / name / "ticket.md", CLONE_TEMPLATE)
    _write(
        company / "recurring" / name / "ticket.py",
        CLONE_SCRIPT.replace("EXIT_CODE", str(exit_code)),
    )


def _runs(company: Path) -> list[dict[str, str | None]]:
    path = company / "runs.jsonl"
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text().splitlines()]


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    company = tmp_path / "coga"
    _write(company / "coga.toml", "version = 1\n")
    _write(company / "coga.local.toml", 'user = "marc"\n')
    monkeypatch.chdir(company)
    return company


@pytest.mark.parametrize(
    ("extra", "script", "message"),
    [
        ("", False, "requires a reserved `ticket.py`"),
        ("delegate: bootstrap/orient\n", True, "`delegate` needs a period task"),
        ("state_keys: [cursor]\n", True, "`state_keys` needs a period task"),
        ("workflow: direct/body\n", True, "`workflow` needs a period task"),
    ],
)
def test_clone_scope_rejects_what_needs_a_period_task(
    repo: Path, extra: str, script: bool, message: str
) -> None:
    text = CLONE_TEMPLATE.replace("scope: clone\n", f"scope: clone\n{extra}")
    _write(repo / "recurring" / "local-sweep" / "ticket.md", text)
    if script:
        _write(repo / "recurring" / "local-sweep" / "ticket.py", "raise SystemExit(0)\n")
    with pytest.raises(RecurringError, match=message):
        Template.load(repo / "recurring" / "local-sweep", now=NOW)


def test_unknown_scope_is_a_template_error(repo: Path) -> None:
    _clone_template(repo)
    path = repo / "recurring" / "local-sweep" / "ticket.md"
    path.write_text(path.read_text().replace("scope: clone", "scope: machine"))
    with pytest.raises(RecurringError, match="`scope` must be one of repo, clone"):
        Template.load(path.parent, now=NOW)


def test_shared_scan_creates_no_period_task_for_a_clone_template(repo: Path) -> None:
    _clone_template(repo)
    cfg = load_config(repo)

    scan = scan_due(cfg, now=NOW)

    assert scan.tasks == [] and scan.errors == []
    assert list_tasks(cfg) == []
    assert not (repo / "log.md").exists()
    assert [due.template.name for due in scan_clone_due(cfg, now=NOW).due] == [
        "local-sweep"
    ]


def test_clone_run_records_the_period_locally_and_runs_once(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _clone_template(repo)
    cfg = load_config(repo)
    monkeypatch.setattr("coga.recurring.datetime", _frozen_datetime())
    monkeypatch.setenv("COGA_TASK_SLUG", "recurring/leaked")

    record = RunRecord(started=NOW)
    assert recurring_cmd._run_clone_scoped(cfg, record) is False

    assert _runs(repo) == [
        {
            "COGA_RECURRING_SCOPE": "clone",
            "COGA_RECURRING_TEMPLATE": "local-sweep",
            "COGA_RECURRING_PERIOD": "2026-04-22",
            # No period task: nothing for the script to bump or report onto.
            "COGA_TASK_SLUG": None,
            "COGA_TASK_BLACKBOARD": None,
        }
    ]
    entry = read_clone_ledger(cfg, "local-sweep")
    assert entry is not None and entry.period == "2026-04-22"
    log = (clone_state_dir(cfg) / "local-sweep.log").read_text()
    assert "swept local state" in log
    [outcome] = record.outcomes
    assert (outcome.slug, outcome.result) == ("recurring/local-sweep", "completed")
    assert list_tasks(cfg) == []

    # Serviced here this period: the next sweep of this clone skips it.
    again = RunRecord(started=NOW)
    assert recurring_cmd._run_clone_scoped(cfg, again) is False
    assert len(_runs(repo)) == 1
    assert again.outcomes == []
    [status] = list_templates(cfg, NOW)
    assert (status.scope, status.serviced, status.due) == ("clone", True, False)


def test_failed_clone_run_is_a_problem_and_retries_next_sweep(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _clone_template(repo, exit_code=3)
    cfg = load_config(repo)
    monkeypatch.setattr("coga.recurring.datetime", _frozen_datetime())

    record = RunRecord(started=NOW)
    assert recurring_cmd._run_clone_scoped(cfg, record) is True

    assert read_clone_ledger(cfg, "local-sweep") is None
    [outcome] = record.outcomes
    assert (outcome.result, outcome.exit_code) == ("failed", 3)
    assert "swept local state" in outcome.blackboard
    assert recurring_cmd._run_clone_scoped(cfg, RunRecord(started=NOW)) is True
    assert len(_runs(repo)) == 2


def test_clone_chatty_script_has_bounded_log_and_retains_final_output(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(recurring_clone, "_OUTPUT_LOG_CHARS", 8000)
    script = repo / "chatty.py"
    script.write_text(
        "import os\n"
        "for _ in range(256): os.write(1, b'x' * 65536)\n"
        "os.write(1, b'\\xffFINAL OUTPUT\\n')\n"
    )
    cfg = load_config(repo)
    tracemalloc.start()
    try:
        result = run_clone_template(cfg, "chatty", script, "today", timeout=10)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert peak < 8_000_000, f"retained too much of the 16 MiB output: {peak}"
    assert result.exit_code == 0
    assert len(result.output) == 4000
    assert result.output.endswith("\ufffdFINAL OUTPUT\n")
    log = result.log_path.read_text()
    assert "output truncated" in log
    assert log.endswith("\ufffdFINAL OUTPUT\n")
    assert len(log) < 12500
    assert len(capsys.readouterr().out) < 8500


def test_clone_timeout_keeps_diagnostics_and_does_not_advance_ledger(repo: Path) -> None:
    script = repo / "hung.py"
    script.write_text("import time\nprint('started work', flush=True)\ntime.sleep(30)\n")
    cfg = load_config(repo)
    started = time.monotonic()
    result = run_clone_template(cfg, "hung", script, "today", timeout=0.3)
    assert time.monotonic() - started < 6
    assert result.exit_code == 124
    assert "started work" in result.output
    assert "timed out" in result.output
    assert "exit 124" in result.log_path.read_text()
    assert read_clone_ledger(cfg, "hung") is None


@windows_skip("POSIX process-group cleanup")
@pytest.mark.parametrize("parent_waits", [True, False])
def test_clone_timeout_kills_descendant_holding_stdout(repo: Path, parent_waits: bool) -> None:
    script = repo / "descendant.py"
    child_pid = repo / "child.pid"
    script.write_text(
        "import subprocess, sys\nfrom pathlib import Path\n"
        "child = subprocess.Popen([sys.executable, '-c', "
        "'import signal, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(30)'])\n"
        f"Path({str(child_pid)!r}).write_text(str(child.pid))\n"
        + ("child.wait()\n" if parent_waits else "")
    )
    result = run_clone_template(load_config(repo), "descendant", script, "today", timeout=0.5)
    assert result.exit_code == 124
    pid = int(child_pid.read_text())
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            break
        # An orphan may await init's reap, but must no longer be executing.
        stat = Path(f"/proc/{pid}/stat")
        if stat.exists() and stat.read_text().split()[2] == "Z":
            break
        time.sleep(0.01)
    else:
        pytest.fail("descendant survived timeout")


def test_clone_sweep_continues_after_timeout_and_retries_it(
    repo: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clone_template(repo, "a-hung")
    (repo / "recurring" / "a-hung" / "ticket.py").write_text("import time\ntime.sleep(30)\n")
    _clone_template(repo, "z-success")
    monkeypatch.setattr("coga.recurring.datetime", _frozen_datetime())
    def short_run(*args, **kwargs):
        return run_clone_template(*args, **kwargs, timeout=0.3)
    monkeypatch.setattr(recurring_cmd, "run_clone_template", short_run)
    cfg = load_config(repo)
    record = RunRecord(started=NOW)
    assert recurring_cmd._run_clone_scoped(cfg, record) is True
    assert [(o.template, o.exit_code) for o in record.outcomes] == [
        ("a-hung", 124), ("z-success", 0),
    ]
    assert read_clone_ledger(cfg, "a-hung") is None
    assert read_clone_ledger(cfg, "z-success") is not None
    assert [due.template.name for due in scan_clone_due(cfg, now=NOW).due] == ["a-hung"]


@pytest.mark.parametrize("timeout", [0, -1, float("inf"), float("nan")])
def test_clone_script_rejects_unbounded_deadlines(repo: Path, timeout: float) -> None:
    with pytest.raises(ValueError, match="finite and positive"):
        run_clone_template(load_config(repo), "bad", repo / "unused.py", "today", timeout=timeout)


@pytest.fixture
def windows_kernel(monkeypatch: pytest.MonkeyPatch) -> Mock:
    import ctypes

    kernel = Mock()
    for name in ("SetInformationJobObject", "TerminateJobObject", "CloseHandle",
                 "AssignProcessToJobObject"):
        getattr(kernel, name).return_value = 1
    kernel.CreateJobObjectW.return_value = 123
    kernel.OpenJobObjectW.return_value = 456
    kernel.GetCurrentProcess.return_value = -1
    monkeypatch.setattr(ctypes, "WinDLL", lambda *a, **kw: kernel, raising=False)
    monkeypatch.setattr(ctypes, "get_last_error", lambda: 5, raising=False)
    monkeypatch.setattr(ctypes, "WinError", lambda code: OSError(code, "Windows error"), raising=False)
    return kernel


def test_windows_job_owns_descendants_after_direct_child_exits(windows_kernel: Mock) -> None:
    child = Mock()
    child.poll.return_value = 0
    with oscompat._WindowsJob() as job:
        info = windows_kernel.SetInformationJobObject.call_args.args
        assert info[1] == 9  # JobObjectExtendedLimitInformation
        assert info[2]._obj.BasicLimitInformation.LimitFlags == 0x2000
        job.terminate()
        child.wait()
        windows_kernel.TerminateJobObject.assert_called_once_with(123, 124)
        child.wait.assert_called_once()
    windows_kernel.CloseHandle.assert_called_once_with(123)


def test_windows_job_closes_when_process_start_fails(windows_kernel: Mock) -> None:
    with pytest.raises(OSError, match="spawn failed"):
        with oscompat._WindowsJob():
            raise OSError("spawn failed")
    windows_kernel.CloseHandle.assert_called_once_with(123)


def test_windows_job_configuration_failure_releases_handle(windows_kernel: Mock) -> None:
    windows_kernel.SetInformationJobObject.return_value = 0
    with pytest.raises(OSError, match="Windows error"):
        oscompat._WindowsJob()
    windows_kernel.CloseHandle.assert_called_once_with(123)


def test_windows_job_termination_error_is_reported_and_closes_handle(windows_kernel: Mock) -> None:
    windows_kernel.TerminateJobObject.return_value = 0
    with pytest.raises(OSError, match="Windows error"):
        with oscompat._WindowsJob() as job:
            job.terminate()
    windows_kernel.CloseHandle.assert_called_once_with(123)


@pytest.mark.parametrize("failure", [
    None, "OpenJobObjectW", "AssignProcessToJobObject", "CloseHandle",
])
def test_windows_wrapper_joins_job_before_starting_script(
    monkeypatch: pytest.MonkeyPatch, windows_kernel: Mock, failure: str | None,
) -> None:
    argv = [sys.executable, "script with spaces.py", "argument with spaces"]
    monkeypatch.setattr(sys, "argv", ["-c", "job-name", *argv])

    def run(command: list[str]) -> int:
        windows_kernel.AssignProcessToJobObject.assert_called_once_with(456, -1)
        windows_kernel.CloseHandle.assert_called_once_with(456)
        assert command == argv
        return 17

    spawn = Mock(side_effect=run)
    monkeypatch.setattr(subprocess, "call", spawn)
    if failure:
        getattr(windows_kernel, failure).return_value = 0
        with pytest.raises(OSError, match="Windows error"):
            exec(oscompat._WINDOWS_JOB_WRAPPER, {})
        spawn.assert_not_called()
    else:
        with pytest.raises(SystemExit) as caught:
            exec(oscompat._WINDOWS_JOB_WRAPPER, {})
        assert caught.value.code == 17
        spawn.assert_called_once()
    if failure != "OpenJobObjectW":
        windows_kernel.CloseHandle.assert_called_once_with(456)


@pytest.mark.skipif(os.name != "nt", reason="Windows job-object integration")
@pytest.mark.parametrize("parent_waits", [True, False])
def test_windows_timeout_kills_descendant_after_parent_exit(
    tmp_path: Path, parent_waits: bool,
) -> None:
    import ctypes

    child_pid = tmp_path / "child.pid"
    script = tmp_path / "descendant.py"
    script.write_text(
        "import subprocess, sys\nfrom pathlib import Path\n"
        "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])\n"
        f"Path({str(child_pid)!r}).write_text(str(child.pid))\n"
        + ("child.wait()\n" if parent_waits else "")
    )
    code, _, _ = recurring_clone._run_clone_script(
        [sys.executable, str(script)], cwd=tmp_path, env=dict(os.environ), timeout=2,
    )
    assert code == 124
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    kernel.WaitForSingleObject.restype = ctypes.c_uint32
    kernel.TerminateProcess.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    handle = kernel.OpenProcess(0x100001, False, int(child_pid.read_text()))
    if not handle:
        assert ctypes.get_last_error() == 87  # PID no longer exists.
        return
    try:
        assert kernel.WaitForSingleObject(handle, 2000) == 0
    finally:
        kernel.TerminateProcess(handle, 1)  # Cleanup if the regression fails.
        kernel.CloseHandle(handle)


def test_inactive_repo_skips_non_exempt_clone_templates(repo: Path) -> None:
    _clone_template(repo)
    cfg = load_config(repo)

    scan = scan_clone_due(cfg, now=NOW, inactive_since="2026-01-01")

    assert scan.due == [] and scan.inactivity_skips == ["local-sweep"]


def test_named_launch_runs_a_clone_template_now(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _clone_template(repo)
    monkeypatch.setattr(recurring_cmd, "_relay_off_control_single_repo_run", lambda *a: None)
    monkeypatch.setattr(recurring_cmd, "run_autofix", lambda *a, **k: None)

    first = CliRunner().invoke(app, ["recurring", "launch", "local-sweep"])
    second = CliRunner().invoke(app, ["recurring", "launch", "local-sweep"])

    assert first.exit_code == 0, first.output
    assert second.exit_code == 0, second.output
    # A named launch ignores the clone ledger, as it ignores the shared one.
    assert len(_runs(repo)) == 2
    assert list_tasks(load_config(repo)) == []


def test_clone_only_sweep_skips_shared_templates(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _clone_template(repo)
    _write(
        repo / "recurring" / "shared" / "ticket.md",
        CLONE_TEMPLATE.replace("scope: clone\n", ""),
    )
    _write(repo / "recurring" / "shared" / "ticket.py", "raise SystemExit(0)\n")
    monkeypatch.setattr(recurring_cmd, "run_autofix", lambda *a, **k: None)

    assert recurring_cmd.run_recurring_scan(load_config(repo), clone_only=True) == 0

    assert len(_runs(repo)) == 1
    assert list_tasks(load_config(repo)) == []


def test_ledger_lives_in_the_primary_checkout_for_a_linked_worktree(git_repo) -> None:
    """A run from a temporary control worktree counts for the clone that owns it."""
    linked = git_repo.root.parent / "linked"
    git_repo.git("worktree", "add", "--detach", str(linked))

    cfg = load_config(linked / "coga", require_user=False)

    assert clone_state_dir(cfg) == git_repo.coga_os / ".coga" / "recurring-clone"


def _frozen_datetime() -> type[datetime]:
    class Frozen(datetime):
        @classmethod
        def now(cls, tz=None):  # type: ignore[no-untyped-def,override]
            return NOW

    return Frozen
