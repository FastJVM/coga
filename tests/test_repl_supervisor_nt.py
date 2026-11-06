"""The native Windows supervisor backend and its command planner.

The planner, batch quoting, exit classification and the supervision loop
(over a fake process tree) run on every platform. Cases marked
``windows_only`` drive the real Job Object, named-event gate, CTRL_BREAK,
cmd.exe transport and Python 3.11 exit boundaries on native Windows.
"""

from __future__ import annotations

import hashlib
import json
import os
import signal
import subprocess
import sys
import textwrap
import time
from contextlib import contextmanager
from pathlib import Path

import pytest

from coga import repl_supervisor_nt as nt
from coga._nt_session_wrapper import _signed_exit_status
from coga.oscompat import process_exit_status
from coga.repl_supervisor import (
    SENTINEL_ENV,
    _TIMEOUT_EXIT_CODE,
    _TTY_SANITIZE,
    AgentCliNotFound,
    run_with_done_marker,
)
from coga.usage import _has_marker_line, _without_excluded_texts

windows_only = pytest.mark.skipif(os.name != "nt", reason="native Windows only")


# --- exit codes ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("dword", "signed"),
    [(0, 0), (7, 7), (0x7FFFFFFF, 0x7FFFFFFF), (0x80000000, -0x80000000),
     (0xC000013A, 0xC000013A - 0x100000000), (0xFFFFFFFF, -1)],
)
def test_wrapper_and_cli_pass_a_signed_equivalent_dword(dword: int, signed: int) -> None:
    assert _signed_exit_status(dword) == signed
    assert process_exit_status(dword, windows=True) == signed
    assert signed & 0xFFFFFFFF == dword
    assert process_exit_status(dword, windows=False) == dword


def test_classify_untouched_child_is_natural_with_raw_code() -> None:
    assert nt.classify_exit(0, None) == (0, "natural", [])
    assert nt.classify_exit(7, None) == (7, "natural", [])
    assert nt.classify_exit(0x80000001, None) == (0x80000001, "natural", [])
    assert nt.classify_exit(nt.STATUS_CONTROL_C_EXIT, None)[:2] == (
        nt.STATUS_CONTROL_C_EXIT, "natural",
    )


def test_classify_untouched_ntstatus_error_is_a_crash() -> None:
    assert nt.classify_exit(0xC0000005, None)[:2] == (0xC0000005, "crash")


def test_classify_our_stop_reports_the_teardown_code() -> None:
    for code in (0, 1, nt.STATUS_CONTROL_C_EXIT, 124):
        assert nt.classify_exit(code, "done")[:2] == (0, "done")
        assert nt.classify_exit(code, "timeout")[:2] == (_TIMEOUT_EXIT_CODE, "timeout")


def test_classify_crash_racing_our_stop_surfaces_the_crash() -> None:
    code, kind, notes = nt.classify_exit(0xC0000005, "done")
    assert (code, kind) == (0xC0000005, "crash")
    assert any("real crash" in note for note in notes)
    assert nt.classify_exit(0xC0000409, "timeout")[:2] == (0xC0000409, "crash")


# --- planner ------------------------------------------------------------------------


def test_command_line_units_count_utf16_and_the_terminator() -> None:
    assert nt.command_line_units("") == 1
    assert nt.command_line_units("abc") == 4
    assert nt.command_line_units("é") == 2
    assert nt.command_line_units("\U0001F600") == 3  # one surrogate pair


@pytest.mark.parametrize(
    ("token", "quoted"),
    [
        ("", '""'),
        ("plain", '"plain"'),
        ("two words", '"two words"'),
        ('say "hi"', '"say ""hi"""'),
        ("C:\\dir\\", '"C:\\dir\\\\"'),
        ('a\\"b', '"a\\\\""b"'),
        ("a\\\\b", '"a\\\\b"'),
        ("%PATH% !x! ^ & | < > ( )", '"%PATH% !x! ^ & | < > ( )"'),
        ("\u2028東京\U0001F600", '"\u2028東京\U0001F600"'),
    ],
)
def test_batch_quote_always_quotes_and_doubles_only_before_quotes(
    token: str, quoted: str
) -> None:
    assert nt.batch_quote(token) == quoted


def test_batch_command_value_and_single_expansion_shell_line() -> None:
    assert nt.batch_command_value(["C:\\a b\\agent.cmd", "x", ""]) == (
        '"C:\\a b\\agent.cmd" "x" ""'
    )
    line = nt.shell_command_line("COGA_BATCH_abc")
    assert line == 'cmd.exe /d /e:on /v:off /s /c "%COGA_BATCH_abc%"'


def test_fresh_batch_variable_never_reuses_a_child_variable(monkeypatch) -> None:
    names = iter(["a" * 32, "b" * 32])

    class FakeUuid:
        def __init__(self, hexa: str) -> None:
            self.hex = hexa

    monkeypatch.setattr(nt, "uuid4", lambda: FakeUuid(next(names)))
    taken = {f"coga_batch_{'a' * 32}": "existing"}
    assert nt.fresh_batch_variable(taken) == f"COGA_BATCH_{'b' * 32}"


def _touch(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")
    return path


def test_resolve_executable_uses_the_child_path_and_pathext(tmp_path: Path) -> None:
    child_bin = tmp_path / "child bin"
    parent_bin = tmp_path / "parent"
    agent = _touch(child_bin / "agent.CMD")
    _touch(parent_bin / "agent.exe")
    env = {"Path": f"{parent_bin}x;{child_bin}", "PathExt": ".EXE;.CMD"}
    assert nt.resolve_executable("agent", env) == os.path.abspath(agent)
    # An explicit extension in PATHEXT is tried as given.
    assert nt.resolve_executable("agent.CMD", env) == os.path.abspath(agent)
    # A name outside the child PATH is not found from the current directory.
    assert nt.resolve_executable("agent", {"PATH": str(tmp_path)}) is None
    # A path with a directory is checked where it is.
    assert nt.resolve_executable(str(child_bin / "agent"), env) == os.path.abspath(agent)


def _exe_env(directory: Path) -> dict[str, str]:
    # Lower-case PATHEXT so the case-sensitive Linux run finds `.exe` stubs.
    return {"PATH": str(directory), "PATHEXT": ".exe"}


def _parts_for(cli: str, *, title: str = "Title", kickoff: str | None = None):
    def parts(prompt_arg: str) -> list[tuple[str, str]]:
        result = [(cli, "agent CLI"), ("--flag", "launch option"), ("-n", "title"),
                  (title, "title"), (prompt_arg, "prompt")]
        if kickoff is not None:
            result.append((kickoff, "kickoff"))
        return result

    return parts


def _pointer(batch: bool) -> str:
    sep = "\u2028" if batch else "\n"
    return f"Read the file C:\\Temp\\p.md{sep}{sep}coga-launch: m{sep}"


def test_plan_keeps_a_fitting_prompt_for_a_native_executable(tmp_path: Path) -> None:
    exe = _touch(tmp_path / "claude.exe")
    plan = nt.plan_agent_command(
        _parts_for("claude"), prompt="hi \"there\"\n", pointer_for=_pointer,
        env=_exe_env(tmp_path), comspec="C:\\Windows\\System32\\cmd.exe",
    )
    assert plan.argv == (os.path.abspath(exe), "--flag", "-n", "Title", 'hi "there"\n')
    assert (plan.prompt_in_file, plan.batch) == (False, False)


def test_plan_measures_the_serialized_line_not_the_raw_prompt(tmp_path: Path) -> None:
    _touch(tmp_path / "claude.exe")
    env = _exe_env(tmp_path)
    # 23,000 quotes serialize to ~46,000 units: the raw length would fit.
    quotes = '"' * 23_000
    plan = nt.plan_agent_command(
        _parts_for("claude"), prompt=quotes, pointer_for=_pointer, env=env,
    )
    assert plan.prompt_in_file and plan.prompt_arg == _pointer(False)


def _largest_fitting(fits, low: int, high: int) -> int:
    while low < high:
        mid = (low + high + 1) // 2
        if fits(mid):
            low = mid
        else:
            high = mid - 1
    return low


@pytest.mark.parametrize("char", ["x", "\\", "東", "\U0001F600"])
def test_plan_switches_to_the_pointer_exactly_past_the_budget(
    tmp_path: Path, char: str
) -> None:
    _touch(tmp_path / "claude.exe")
    env = _exe_env(tmp_path)

    def plan(n: int):
        return nt.plan_agent_command(
            _parts_for("claude"), prompt=char * n, pointer_for=_pointer, env=env,
        )

    largest = _largest_fitting(lambda n: not plan(n).prompt_in_file, 0, 40_000)
    fitting = plan(largest)
    over = plan(largest + 1)
    assert not fitting.prompt_in_file and over.prompt_in_file
    import coga.oscompat as oscompat

    wrapper = oscompat.interactive_wrapper_argv(
        oscompat.JOB_NAME_PLACEHOLDER, oscompat.GATE_NAME_PLACEHOLDER, list(fitting.argv)
    )
    assert nt.command_line_units(subprocess.list2cmdline(wrapper)) <= nt.COMMAND_LINE_LIMIT
    over_argv = [*fitting.argv[:-1], char * (largest + 1)]
    over_wrapper = oscompat.interactive_wrapper_argv(
        oscompat.JOB_NAME_PLACEHOLDER, oscompat.GATE_NAME_PLACEHOLDER, over_argv
    )
    assert nt.command_line_units(subprocess.list2cmdline(over_wrapper)) > nt.COMMAND_LINE_LIMIT


def test_plan_refuses_an_oversized_pointer_form_without_printing_values(
    tmp_path: Path,
) -> None:
    _touch(tmp_path / "claude.exe")
    secret_title = "T" * 40_000
    with pytest.raises(nt.CommandRefused) as excinfo:
        nt.plan_agent_command(
            _parts_for("claude", title=secret_title), prompt="hi",
            pointer_for=_pointer, env=_exe_env(tmp_path),
        )
    message = str(excinfo.value)
    assert "32767" in message and "UTF-16" in message and "launch_args" in message
    assert secret_title not in message


def test_plan_gives_a_batch_agent_the_unicode_separated_pointer(tmp_path: Path) -> None:
    shim = _touch(tmp_path / "codex.cmd")
    plan = nt.plan_agent_command(
        _parts_for("codex", kickoff="Begin"), prompt="short", pointer_for=_pointer,
        env={"PATH": str(tmp_path), "PATHEXT": ".exe;.cmd"},
        comspec="C:\\Windows\\System32\\cmd.exe",
    )
    assert plan.batch and plan.prompt_in_file
    assert plan.argv[0] == os.path.abspath(shim)
    assert plan.prompt_arg == _pointer(True)
    assert "\n" not in plan.prompt_arg and "\r" not in plan.prompt_arg


@pytest.mark.parametrize(
    ("parts_kwargs", "role"),
    [({"title": "two\nlines"}, "title"), ({"kickoff": "a\rb"}, "kickoff")],
)
def test_plan_refuses_raw_line_breaks_in_batch_arguments_by_role(
    tmp_path: Path, parts_kwargs, role: str
) -> None:
    _touch(tmp_path / "codex.bat")
    with pytest.raises(nt.CommandRefused) as excinfo:
        nt.plan_agent_command(
            _parts_for("codex", **parts_kwargs), prompt="p", pointer_for=_pointer,
            env={"PATH": str(tmp_path), "PATHEXT": ".bat"},
        )
    message = str(excinfo.value)
    assert f"agent's {role} argument" in message and "native executable" in message
    assert "two" not in message and "a\rb" not in message


def test_plan_keeps_native_line_breaks_in_non_prompt_arguments(tmp_path: Path) -> None:
    _touch(tmp_path / "claude.exe")
    plan = nt.plan_agent_command(
        _parts_for("claude", title="two\nlines"), prompt="p",
        pointer_for=_pointer, env=_exe_env(tmp_path),
    )
    assert "two\nlines" in plan.argv


def test_batch_budgets_cover_both_shell_lines_and_the_wrapper() -> None:
    def fits(n: int) -> bool:
        try:
            nt.check_budgets(["C:\\a.cmd", "y" * n], batch=True, comspec="C:\\cmd.exe")
        except nt.CommandRefused:
            return False
        return True

    largest = _largest_fitting(fits, 0, 9_000)
    expanded = nt.shell_command_line("COGA_BATCH_" + "0" * 32).replace(
        "%COGA_BATCH_" + "0" * 32 + "%",
        nt.batch_command_value(["C:\\a.cmd", "y" * largest]),
    )
    assert nt.command_line_units(expanded) == nt.SHELL_LINE_LIMIT
    with pytest.raises(nt.CommandRefused, match="expanded cmd.exe command line"):
        nt.check_budgets(["C:\\a.cmd", "y" * (largest + 1)], batch=True, comspec="C:\\cmd.exe")


def test_plan_reports_a_missing_cli(tmp_path: Path) -> None:
    with pytest.raises(AgentCliNotFound):
        nt.plan_agent_command(
            _parts_for("absent"), prompt="p", pointer_for=_pointer,
            env={"PATH": str(tmp_path)},
        )


def test_batch_pointer_marker_is_an_exact_line_and_excluded_from_human_text() -> None:
    from coga.launch import _BATCH_POINTER_SEPARATOR, _prompt_pointer
    from coga.usage import launch_marker_line

    marker = "00000000-0000-4000-8000-000000000000"
    pointer = _prompt_pointer(
        Path("C:/Temp/p.md"), launch_marker_line(marker),
        separator=_BATCH_POINTER_SEPARATOR,
    )
    assert "\n" not in pointer and pointer.endswith("\u2028")
    assert _has_marker_line([pointer], marker)
    assert not _has_marker_line([pointer.replace("\u2028coga", "\u2028see coga")], marker)
    assert not _has_marker_line([pointer], marker[:-1] + "1")
    assert _without_excluded_texts([pointer, "human ask"], [pointer]) == ["human ask"]


# --- supervision loop over a fake tree ------------------------------------------


class _FakeProcess:
    def __init__(self, tree: _FakeTree) -> None:
        self._tree = tree
        self.pid = 4242

    def wait(self, timeout: float | None = None) -> int:
        result = self._tree.behavior(self._tree)
        if result is not None:
            return result
        time.sleep(min(timeout or 0.01, 0.01))
        raise subprocess.TimeoutExpired("agent", timeout)


class _FakeTree:
    """Records the supervisor's calls; ``behavior(tree)`` decides each wait."""

    instances: list[_FakeTree] = []
    behavior = staticmethod(lambda tree: 0)
    fail_release: BaseException | None = None

    def __init__(self, argv, *, interactive, gate, new_process_group, shell, env) -> None:
        self.argv = argv
        self.kwargs = dict(
            interactive=interactive, gate=gate, new_process_group=new_process_group,
            shell=shell,
        )
        self.env = env
        self.events: list[str] = []
        self.started = time.monotonic()
        self.process = _FakeProcess(self)
        type(self).instances.append(self)

    def release(self) -> None:
        self.events.append("release")
        if self.fail_release is not None:
            raise self.fail_release

    def interrupt(self) -> None:
        self.events.append("interrupt")

    def kill(self) -> None:
        self.events.append("kill")

    def close(self) -> None:
        self.events.append("close")


@pytest.fixture
def fake_tree(monkeypatch, tmp_path: Path):
    _FakeTree.instances = []
    _FakeTree.behavior = staticmethod(lambda tree: 0)
    _FakeTree.fail_release = None
    restored: list[str] = []

    class Modes:
        @classmethod
        def save(cls):
            restored.append("saved")
            return cls()

        def restore(self) -> None:
            restored.append("restored")

    monkeypatch.setattr(nt, "ProcessTree", _FakeTree)
    monkeypatch.setattr(nt, "ConsoleModes", Modes)
    monkeypatch.setattr(nt, "_console_attached", lambda: True)
    monkeypatch.setattr(nt, "_KILL_GRACE_SECONDS", 0.2)
    _touch(tmp_path / "agent.exe")
    out = tmp_path / "watcher.out"
    fd = os.open(out, os.O_RDWR | os.O_CREAT)
    yield {
        "env": {"PATH": str(tmp_path), "PATHEXT": ".exe"},
        "fd": fd,
        "output": lambda: out.read_bytes(),
        "modes": restored,
    }
    os.close(fd)


def _write_sentinel(tree: _FakeTree, content: str) -> None:
    path = tree.env[SENTINEL_ENV]
    if path and not os.path.exists(path):
        Path(path).write_text(content + "\n", encoding="utf-8")


def _run(fake, **kwargs):
    return nt.run(["agent", "--x"], fake["env"], output_fd=fake["fd"], **kwargs)


def test_fake_sentinel_interrupts_then_reports_done(fake_tree) -> None:
    def behavior(tree):
        _write_sentinel(tree, "slug")
        return nt.STATUS_CONTROL_C_EXIT if "interrupt" in tree.events else None

    _FakeTree.behavior = staticmethod(behavior)
    previous = signal.getsignal(signal.SIGINT)
    outcome = _run(fake_tree, session_id="slug")
    tree = _FakeTree.instances[0]
    assert (outcome.exit_code, outcome.kind, outcome.done_signalled) == (0, "done", True)
    assert "sentinel-file" in outcome.reason
    assert tree.events == ["interrupt", "close"]
    assert tree.kwargs == dict(interactive=True, gate=False, new_process_group=True, shell=None)
    assert tree.argv == [os.path.abspath(Path(fake_tree["env"]["PATH"]) / "agent.exe"), "--x"]
    assert signal.getsignal(signal.SIGINT) is previous
    assert fake_tree["modes"] == ["saved", "restored"]
    output = fake_tree["output"]()
    assert b"CTRL_BREAK sent" in output
    assert _TTY_SANITIZE in output


def test_fake_child_ignoring_break_is_job_killed_after_grace(fake_tree) -> None:
    def behavior(tree):
        _write_sentinel(tree, "slug")
        return 124 if "kill" in tree.events else None

    _FakeTree.behavior = staticmethod(behavior)
    outcome = _run(fake_tree, session_id="slug")
    assert (outcome.exit_code, outcome.kind) == (0, "done")
    assert _FakeTree.instances[0].events == ["interrupt", "kill", "close"]
    assert b"terminating its Job Object" in fake_tree["output"]()


def test_fake_max_session_is_a_timeout(fake_tree) -> None:
    _FakeTree.behavior = staticmethod(
        lambda tree: nt.STATUS_CONTROL_C_EXIT if "interrupt" in tree.events else None
    )
    outcome = _run(fake_tree, max_session=0.1, session_id="slug")
    assert (outcome.exit_code, outcome.kind, outcome.done_signalled) == (
        _TIMEOUT_EXIT_CODE, "timeout", False,
    )
    assert "max-session" in outcome.reason


def test_fake_idle_timeout_warns_once_and_is_not_armed(fake_tree) -> None:
    calls = {"n": 0}

    def behavior(tree):
        calls["n"] += 1
        return 0 if calls["n"] > 30 else None

    _FakeTree.behavior = staticmethod(behavior)
    outcome = _run(fake_tree, idle_timeout=0.01)
    assert (outcome.exit_code, outcome.kind) == (0, "natural")
    assert fake_tree["output"]().count(nt.IDLE_TIMEOUT_WARNING.encode()) == 1


@pytest.mark.parametrize("code", [7, 0x80000001])
def test_fake_natural_exit_passes_the_dword_through(fake_tree, code: int) -> None:
    _FakeTree.behavior = staticmethod(lambda tree: code)
    outcome = _run(fake_tree)
    assert (outcome.exit_code, outcome.kind, outcome.reason) == (code, "natural", None)
    assert _TTY_SANITIZE not in fake_tree["output"]()


def test_fake_crash_racing_done_keeps_crash_and_observation(fake_tree) -> None:
    def behavior(tree):
        _write_sentinel(tree, "slug")
        return 0xC0000005 if "interrupt" in tree.events else None

    _FakeTree.behavior = staticmethod(behavior)
    outcome = _run(fake_tree, session_id="slug")
    assert (outcome.exit_code, outcome.kind, outcome.done_signalled) == (
        0xC0000005, "crash", True,
    )
    assert outcome.reason is None


def test_fake_done_signal_is_latched_after_exit(fake_tree) -> None:
    def behavior(tree):
        _write_sentinel(tree, "slug")
        return 0

    _FakeTree.behavior = staticmethod(behavior)
    outcome = _run(fake_tree, session_id="slug")
    assert (outcome.kind, outcome.done_signalled) == ("natural", True)


def test_fake_terminal_ticket_stops_without_claiming_a_sentinel(fake_tree) -> None:
    _FakeTree.behavior = staticmethod(
        lambda tree: 0 if "interrupt" in tree.events else None
    )
    outcome = _run(fake_tree, terminal_status=lambda: "done", session_id="slug")
    assert (outcome.kind, outcome.done_signalled) == ("done", False)
    assert "ticket-terminal" in outcome.reason


def test_fake_non_console_runs_natural_with_empty_channel(fake_tree, monkeypatch) -> None:
    monkeypatch.setattr(nt, "_console_attached", lambda: False)
    _FakeTree.behavior = staticmethod(lambda tree: 0xC0000005)
    outcome = _run(fake_tree, session_id="slug")
    tree = _FakeTree.instances[0]
    assert (outcome.exit_code, outcome.kind, outcome.done_signalled) == (
        0xC0000005, "natural", False,
    )
    assert tree.env[SENTINEL_ENV] == ""
    assert tree.events == ["close"]
    assert fake_tree["modes"] == []


def test_fake_supplied_environment_reaches_the_child(fake_tree) -> None:
    fake_tree["env"]["ONLY_IN_CHILD"] = "1"
    _run(fake_tree)
    tree = _FakeTree.instances[0]
    assert tree.env["ONLY_IN_CHILD"] == "1"
    assert "ONLY_IN_CHILD" not in os.environ


def test_fake_missing_binary_raises_before_spawn(fake_tree) -> None:
    with pytest.raises(AgentCliNotFound):
        nt.run(["absent"], fake_tree["env"], output_fd=fake_tree["fd"])
    assert _FakeTree.instances == []


def test_fake_batch_agent_runs_through_one_expansion_transport(fake_tree, tmp_path) -> None:
    shim = _touch(tmp_path / "shim dir %PATH%" / "codex.cmd")
    fake_tree["env"]["PATH"] += f";{shim.parent}"
    fake_tree["env"]["PATHEXT"] = ".cmd"
    nt.run(["codex", 'a "b" %PATH%'], fake_tree["env"], output_fd=fake_tree["fd"])
    tree = _FakeTree.instances[0]
    comspec, line = tree.kwargs["shell"]
    (variable,) = [name for name in tree.env if name.startswith("COGA_BATCH_")]
    assert line == f'cmd.exe /d /e:on /v:off /s /c "%{variable}%"'
    assert tree.env[variable] == nt.batch_command_value(
        [os.path.abspath(shim), 'a "b" %PATH%']
    )
    assert comspec.lower().endswith("cmd.exe")


# Admission: the four failure boundaries, mirroring the POSIX pipe gate.


@contextmanager
def _recording_guard(events: list[str]):
    events.append("guard-enter")
    try:
        yield
    finally:
        events.append("guard-exit")


def _admission(events: list[str], **overrides):
    callbacks = dict(
        after_spawn=lambda: events.append("after_spawn"),
        spawn_release_guard=lambda: _recording_guard(events),
        after_spawn_release=lambda: events.append("after_release"),
        on_spawn_admission_failure=lambda: events.append("compensate"),
    )
    callbacks.update(overrides)
    return callbacks


def test_fake_gate_releases_after_admission_inside_the_guard(fake_tree) -> None:
    events: list[str] = []
    _FakeTree.behavior = staticmethod(lambda tree: 0)
    outcome = _run(fake_tree, **_admission(events))
    tree = _FakeTree.instances[0]
    assert outcome.kind == "natural"
    assert tree.kwargs["gate"] is True
    assert tree.events == ["release", "close"]
    assert events == ["guard-enter", "after_spawn", "after_release", "guard-exit"]


def _boom():
    raise RuntimeError("refused")


def test_fake_failure_before_release_compensates_and_kills(fake_tree) -> None:
    events: list[str] = []
    with pytest.raises(RuntimeError, match="refused"):
        _run(fake_tree, **_admission(events, after_spawn=_boom))
    assert _FakeTree.instances[0].events == ["close"]
    assert events == ["guard-enter", "compensate", "guard-exit"]
    assert fake_tree["modes"] == ["saved", "restored"]


def test_fake_failed_set_event_compensates_and_kills(fake_tree) -> None:
    events: list[str] = []
    _FakeTree.fail_release = OSError("SetEvent failed")
    with pytest.raises(OSError, match="SetEvent"):
        _run(fake_tree, **_admission(events))
    assert _FakeTree.instances[0].events == ["release", "close"]
    assert events == ["guard-enter", "after_spawn", "compensate", "guard-exit"]


def test_fake_failure_after_release_retains_admission(fake_tree) -> None:
    events: list[str] = []
    with pytest.raises(RuntimeError, match="refused"):
        _run(fake_tree, **_admission(events, after_spawn_release=_boom))
    assert _FakeTree.instances[0].events == ["release", "close"]
    assert events == ["guard-enter", "after_spawn", "guard-exit"]


def test_fake_failed_compensation_is_reported_while_the_guard_is_held(fake_tree) -> None:
    events: list[str] = []

    def failing_compensation():
        events.append("compensate")
        raise OSError("cannot retract")

    with pytest.raises(RuntimeError, match="could not be retracted") as excinfo:
        _run(fake_tree, **_admission(
            events, after_spawn=_boom, on_spawn_admission_failure=failing_compensation,
        ))
    assert "admission=refused" in str(excinfo.value)
    assert events == ["guard-enter", "compensate", "guard-exit"]
    assert _FakeTree.instances[0].events == ["close"]


def test_dispatch_from_shared_entry_on_windows(monkeypatch) -> None:
    seen = {}

    def fake_run(cmd, env, **kwargs):
        seen.update(cmd=cmd, env=env, **kwargs)
        return "outcome"

    monkeypatch.setattr("coga.repl_supervisor.os.name", "nt", raising=False)
    monkeypatch.setattr(nt, "run", fake_run)
    try:
        result = run_with_done_marker(["agent"], {"A": "1"}, session_id="s", max_session=5)
    finally:
        monkeypatch.undo()
    assert result == "outcome"
    assert seen["cmd"] == ["agent"] and seen["max_session"] == 5
    assert seen["session_id"] == "s" and seen["idle_timeout"] is None


# --- native Windows ---------------------------------------------------------------


def _python_child(body: str) -> list[str]:
    return [sys.executable, "-c", textwrap.dedent(body)]


def _native_env(**extra: str) -> dict[str, str]:
    return {**os.environ, **extra}


@pytest.fixture
def console(monkeypatch):
    monkeypatch.setattr(nt, "_console_attached", lambda: True)


@windows_only
def test_native_sentinel_tears_down_child_and_grandchildren(console, tmp_path) -> None:
    from coga.oscompat import process_is_running

    pids = tmp_path / "pids.json"
    outcome = run_with_done_marker(
        _python_child(f"""
            import json, os, subprocess, time
            a = subprocess.Popen(["ping", "-n", "60", "127.0.0.1"], stdout=subprocess.DEVNULL)
            b = subprocess.Popen(["cmd", "/c", "ping -n 60 127.0.0.1 >NUL"])
            open({str(pids)!r}, "w").write(json.dumps([a.pid, b.pid]))
            open(os.environ["{SENTINEL_ENV}"], "w").write("slug\\n")
            time.sleep(60)
        """),
        _native_env(),
        session_id="slug",
    )
    assert (outcome.exit_code, outcome.kind, outcome.done_signalled) == (0, "done", True)
    for pid in json.loads(pids.read_text()):
        assert not process_is_running(pid)


@windows_only
def test_native_child_ignoring_ctrl_break_is_killed_after_grace(console, capfd) -> None:
    outcome = run_with_done_marker(
        _python_child(f"""
            import os, signal, time
            signal.signal(signal.SIGBREAK, signal.SIG_IGN)
            open(os.environ["{SENTINEL_ENV}"], "w").write("slug\\n")
            time.sleep(60)
        """),
        _native_env(),
        session_id="slug",
    )
    assert (outcome.exit_code, outcome.kind) == (0, "done")
    assert "terminating its Job Object" in capfd.readouterr().err


@windows_only
def test_native_max_session_is_a_timeout(console) -> None:
    started = time.monotonic()
    outcome = run_with_done_marker(
        _python_child("import time; time.sleep(60)"), _native_env(), max_session=1,
    )
    assert (outcome.exit_code, outcome.kind) == (_TIMEOUT_EXIT_CODE, "timeout")
    assert time.monotonic() - started < 10


@windows_only
@pytest.mark.parametrize(
    ("code", "kind"),
    [(7, "natural"), (0x80000001, "natural"), (0xC0000005, "crash")],
)
def test_native_exit_codes_cross_the_wrapper(console, code: int, kind: str) -> None:
    outcome = run_with_done_marker(
        _python_child(f"import ctypes; ctypes.windll.kernel32.ExitProcess({code})"),
        _native_env(),
    )
    assert (outcome.exit_code, outcome.kind) == (code, kind)


@windows_only
def test_native_late_done_signal_is_latched(console) -> None:
    outcome = run_with_done_marker(
        _python_child(f"""
            import os
            open(os.environ["{SENTINEL_ENV}"], "w").write("slug\\n")
        """),
        _native_env(),
        session_id="slug",
    )
    assert outcome.done_signalled


@windows_only
def test_native_idle_timeout_warns(console, capfd) -> None:
    outcome = run_with_done_marker(
        _python_child("pass"), _native_env(), idle_timeout=0.01,
    )
    assert outcome.kind == "natural"
    assert capfd.readouterr().err.count(nt.IDLE_TIMEOUT_WARNING) == 1


@windows_only
def test_native_gate_holds_the_child_until_release(console, tmp_path) -> None:
    started = tmp_path / "started"
    observed: list[bool] = []

    def admit() -> None:
        time.sleep(0.5)
        observed.append(started.exists())

    outcome = run_with_done_marker(
        _python_child(f"open({str(started)!r}, 'w').close()"),
        _native_env(),
        after_spawn=admit,
    )
    assert outcome.exit_code == 0
    assert observed == [False] and started.exists()


@windows_only
@pytest.mark.parametrize("boundary", ["before-release", "set-event"])
def test_native_refused_admission_never_starts_the_child(
    console, tmp_path, monkeypatch, boundary: str
) -> None:
    from coga import oscompat

    started = tmp_path / "started"
    compensated: list[bool] = []
    after_spawn = _boom if boundary == "before-release" else (lambda: None)
    if boundary == "set-event":
        def failing_release(self):
            raise OSError("SetEvent failed")

        monkeypatch.setattr(oscompat.ProcessTree, "release", failing_release)
    with pytest.raises((RuntimeError, OSError)):
        run_with_done_marker(
            _python_child(f"open({str(started)!r}, 'w').close()"),
            _native_env(),
            after_spawn=after_spawn,
            on_spawn_admission_failure=lambda: compensated.append(True),
        )
    time.sleep(0.5)
    assert compensated == [True] and not started.exists()


@windows_only
def test_native_child_environment_and_path_resolution(console, tmp_path) -> None:
    child_bin = tmp_path / "child bin"
    child_bin.mkdir()
    out = tmp_path / "env.txt"
    (child_bin / "only-child.CMD").write_text(
        f'@"{sys.executable}" -c "import os; open(r\'{out}\', \'w\').write(os.environ[\'ONLY_CHILD\'])"\r\n',
        encoding="utf-8",
    )
    env = {k: v for k, v in os.environ.items() if k.upper() not in {"PATH", "PATHEXT"}}
    env.update(PATH=f"{child_bin};{os.environ['SystemRoot']}\\System32", PATHEXT=".CMD", ONLY_CHILD="yes")
    outcome = run_with_done_marker(["only-child"], env)
    assert outcome.exit_code == 0
    assert out.read_text() == "yes"
    assert "ONLY_CHILD" not in os.environ


def _console_modes() -> list[int]:
    return [mode for _, mode in nt.ConsoleModes.save()._saved]


@windows_only
def test_native_console_modes_are_restored(console) -> None:
    before = _console_modes()
    if not before:
        pytest.skip("no console attached")
    run_with_done_marker(
        _python_child("""
            import ctypes
            k = ctypes.windll.kernel32
            k.SetConsoleMode(k.GetStdHandle(-10), 7)
        """),
        _native_env(),
    )
    assert _console_modes() == before


_RECORDER = """
import hashlib, json, sys
pointer = sys.argv[-1]
path = pointer.split("Read the file ", 1)[1].split(" in full", 1)[0]
data = open(path, "rb").read()
json.dump({"argv": sys.argv[1:], "sha": hashlib.sha256(data).hexdigest()},
          open(sys.argv[1], "w", encoding="utf-8"))
"""

_NPM_SHIM = """@ECHO off
GOTO start
:find_dp0
SET dp0=%~dp0
EXIT /b
:start
SETLOCAL
CALL :find_dp0
"{python}" "%dp0%\\recorder.py" %*
"""


@windows_only
@pytest.mark.parametrize("suffix", [".cmd", ".bat"])
@pytest.mark.parametrize("form", ["direct", "npm"])
def test_native_batch_transport_round_trips_shell_sensitive_argv(
    tmp_path, suffix: str, form: str
) -> None:
    from coga.launch import _BATCH_POINTER_SEPARATOR, _prompt_pointer

    shim_dir = tmp_path / "a b %PATH% !x! ^ & (y) 東"
    shim_dir.mkdir()
    (shim_dir / "recorder.py").write_text(_RECORDER, encoding="utf-8")
    shim = shim_dir / f"agent{suffix}"
    if form == "direct":
        shim.write_text(
            f'@"{sys.executable}" "{shim_dir / "recorder.py"}" %*\r\n', encoding="utf-8"
        )
    else:
        shim.write_text(_NPM_SHIM.format(python=sys.executable).replace("\n", "\r\n"), encoding="utf-8")
    prompt_file = shim_dir / "prompt %TEMP% ! ^.md"
    prompt = "multi\nline\r\nprompt \"quoted\" %PATH% ! \u2028 \U0001F600\n"
    prompt_file.write_bytes(prompt.encode("utf-8"))
    receipt = tmp_path / "receipt.json"
    pointer = _prompt_pointer(prompt_file, "coga-launch: m", separator=_BATCH_POINTER_SEPARATOR)
    tokens = [str(receipt), "", 'q"uo\\"te\\', "%USERNAME%", "!x!", "^&|<>()", "a\\\\b\\", pointer]
    env = _native_env(PATHEXT=".CMD;.BAT")
    env["PATH"] = f"{shim_dir};{env['PATH']}"
    outcome = run_with_done_marker([str(shim), *tokens], env)
    assert outcome.exit_code == 0
    recorded = json.loads(receipt.read_text(encoding="utf-8"))
    assert recorded["argv"] == tokens
    assert recorded["sha"] == hashlib.sha256(prompt.encode("utf-8")).hexdigest()


_OUTER_CLI = """
import json, sys
from coga import launch as service
from coga.cli import app
from coga.repl_supervisor import run_with_done_marker
from coga import repl_supervisor_nt

repl_supervisor_nt._console_attached = lambda: True
cmd = json.loads(sys.argv[1])
receipt = sys.argv[2]

def launch(task, **kwargs):
    outcome = run_with_done_marker(cmd, dict(__import__("os").environ), session_id="slug")
    json.dump(outcome._asdict() if hasattr(outcome, "_asdict") else outcome.__dict__,
              open(receipt, "w"))
    raise service.LaunchBail(outcome.exit_code)

service.launch = launch
sys.argv = ["coga", "launch", "x"]
app()
"""


@windows_only
@pytest.mark.parametrize(
    ("child", "dword", "kind", "done"),
    [
        ("raise SystemExit(7)", 7, "natural", False),
        ("import ctypes; ctypes.windll.kernel32.ExitProcess(0xC0000005)",
         0xC0000005, "crash", False),
        (f"import os, time; open(os.environ['{SENTINEL_ENV}'], 'w').write('slug\\n'); time.sleep(60)",
         0, "done", True),
        (f"import ctypes, os, signal, time; signal.signal(signal.SIGBREAK, signal.SIG_IGN); "
         f"open(os.environ['{SENTINEL_ENV}'], 'w').write('slug\\n'); "
         "time.sleep(0.8); ctypes.windll.kernel32.ExitProcess(0xC0000005)",
         0xC0000005, "crash", True),
    ],
)
def test_native_exit_codes_cross_wrapper_and_outer_cli(
    tmp_path, child: str, dword: int, kind: str, done: bool
) -> None:
    receipt = tmp_path / "outcome.json"
    result = subprocess.run(
        [sys.executable, "-c", _OUTER_CLI, json.dumps([sys.executable, "-c", child]), str(receipt)],
        timeout=60,
    )
    outcome = json.loads(receipt.read_text())
    assert result.returncode & 0xFFFFFFFF == dword
    assert (outcome["exit_code"], outcome["kind"], outcome["done_signalled"]) == (dword, kind, done)
