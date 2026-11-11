"""Native Windows backend for ``repl_supervisor.run_with_done_marker``.

The agent inherits the supervisor's console (no PTY, no proxy): its TUI
renders over a local console or an SSH ConPTY and reads keys directly. A
kill-on-close Job Object (``oscompat.ProcessTree``) owns the whole tree; a
named event holds the wrapper until spawn admission commits; CTRL_BREAK is
the graceful stop and ``TerminateJobObject`` the forced one. Because the
supervisor never sees the agent's output, idle-timeout cannot be measured
here: callers that arm it get one warning and run with ``max_session`` only.

The command planner below is also pure, importable on POSIX for tests and
used by ``coga.launch`` at preflight. It budgets the final serialized
command lines (CreateProcess's 32,767 UTF-16 units including NUL; cmd.exe's
8,191) and carries batch-file (``.cmd``/``.bat``) argv losslessly through a
one-expansion environment variable rather than interpolating values into
shell source.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import tempfile
import time
from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import PureWindowsPath
from typing import Callable, Iterable, Mapping
from uuid import uuid4

from coga import oscompat
from coga.repl_supervisor import (
    SENTINEL_ENV,
    _KILL_GRACE_SECONDS,
    _SENTINEL_POLL_INTERVAL,
    _TIMEOUT_EXIT_CODE,
    _TTY_SANITIZE,
    AgentCliNotFound,
    ReplOutcome,
    _admit_held_child,
    _sentinel_signals_done,
    completion_pending,
    remove_sentinel_dir,
)

# CreateProcess's lpCommandLine limit, in UTF-16 units including the NUL.
COMMAND_LINE_LIMIT = 32_767
# cmd.exe's documented command-line limit; applied to both the literal shell
# invocation and the line after its one variable expansion, including NUL.
SHELL_LINE_LIMIT = 8_191
# Maximum length of one environment variable's value.
ENV_VALUE_LIMIT = 32_767

STATUS_CONTROL_C_EXIT = 0xC000013A
_NTSTATUS_ERROR = 0xC0000000
# ``oscompat._WindowsJob.terminate`` uses this as every member's exit code.
_JOB_TERMINATE_CODE = 124

_BATCH_SUFFIXES = (".cmd", ".bat")
_BATCH_VAR_PREFIX = "COGA_BATCH_"
_BATCH_VAR_PLACEHOLDER = _BATCH_VAR_PREFIX + "0" * 32
_DEFAULT_PATHEXT = ".COM;.EXE;.BAT;.CMD"

IDLE_TIMEOUT_WARNING = (
    "idle-timeout is unavailable on Windows; running with max-session only"
)


# --- command planning (pure) --------------------------------------------------


class CommandRefused(ValueError):
    """The agent command cannot be represented on Windows; refuse pre-spawn."""


@dataclass(frozen=True)
class CommandPlan:
    """The complete agent argv chosen for one Windows spawn.

    ``argv[0]`` is the resolved absolute executable. ``prompt_in_file`` says
    whether the prompt rides as its file pointer; ``batch`` whether the
    executable is a ``.cmd``/``.bat`` file using the shell transport.
    """

    argv: tuple[str, ...]
    prompt_arg: str
    prompt_in_file: bool
    batch: bool


def command_line_units(command_line: str) -> int:
    """UTF-16 code units of a command line, including its terminating NUL."""
    return len(command_line.encode("utf-16-le")) // 2 + 1


def _env_get(env: Mapping[str, str], key: str) -> str | None:
    """Windows environment names are case-insensitive."""
    if key in env:
        return env[key]
    folded = key.upper()
    for name, value in env.items():
        if name.upper() == folded:
            return value
    return None


def resolve_executable(name: str, env: Mapping[str, str]) -> str | None:
    """Resolve ``name`` against the *child's* PATH and PATHEXT, not ours.

    A name with a directory component is checked where it is. A bare name is
    searched only in the child PATH's directories (never the current
    directory). A name whose suffix is already in PATHEXT is tried as given
    before PATHEXT extensions are appended.
    """
    extensions = [
        ext for ext in (_env_get(env, "PATHEXT") or _DEFAULT_PATHEXT).split(";") if ext
    ]
    suffix = PureWindowsPath(name).suffix.lower()
    candidates_for = (
        (lambda base: [base])
        if suffix and suffix in {ext.lower() for ext in extensions}
        else (lambda base: [base + ext for ext in extensions])
    )
    if any(sep in name for sep in ("\\", "/")) or PureWindowsPath(name).drive:
        directories: Iterable[str] = [""]
    else:
        directories = [d for d in (_env_get(env, "PATH") or "").split(";") if d]
    for directory in directories:
        directory = directory.strip('"')
        base = os.path.join(directory, name) if directory else name
        for candidate in candidates_for(base):
            if os.path.isfile(candidate):
                return os.path.abspath(candidate)
    return None


def is_batch_file(path: str) -> bool:
    return PureWindowsPath(path).suffix.lower() in _BATCH_SUFFIXES


def batch_quote(token: str) -> str:
    """Always-quote one token for a batch file's ``%*``/``%1`` forwarding.

    Embedded double quotes are doubled; a run of backslashes immediately
    before an embedded quote or the closing quote is doubled; every other
    character, including ``%``, ``!``, ``^`` and other backslashes, stays
    literal. Unlike ``subprocess.list2cmdline``, nothing is ever left bare,
    so cmd.exe metacharacters remain inside quotes.
    """
    out: list[str] = ['"']
    backslashes = 0
    for char in token:
        if char == "\\":
            backslashes += 1
            continue
        if char == '"':
            out.append("\\" * (backslashes * 2))
            out.append('""')
        else:
            out.append("\\" * backslashes)
            out.append(char)
        backslashes = 0
    out.append("\\" * (backslashes * 2))
    out.append('"')
    return "".join(out)


def batch_command_value(argv: list[str] | tuple[str, ...]) -> str:
    """The transport variable's value: every final token, each quoted."""
    return " ".join(batch_quote(token) for token in argv)


def shell_command_line(variable: str) -> str:
    """The raw cmd.exe command line expanding ``variable`` exactly once.

    ``/d`` skips AutoRun, ``/v:off`` disables delayed expansion, and ``/s``
    strips only the outer quotes. Percent sequences introduced by the
    variable's value are not expanded again.
    """
    return f'cmd.exe /d /e:on /v:off /s /c "%{variable}%"'


def system_cmd() -> str:
    """Absolute path of Windows' own cmd.exe, never a PATH lookup."""
    if os.name == "nt":
        import ctypes

        buffer = ctypes.create_unicode_buffer(260)
        length = ctypes.windll.kernel32.GetSystemDirectoryW(buffer, len(buffer))
        if 0 < length < len(buffer):
            return os.path.join(buffer.value, "cmd.exe")
    root = os.environ.get("SystemRoot") or os.environ.get("SYSTEMROOT") or r"C:\Windows"
    return str(PureWindowsPath(root, "System32", "cmd.exe"))


def fresh_batch_variable(env: Mapping[str, str]) -> str:
    """A ``COGA_BATCH_<uuid>`` name that no child variable already uses."""
    taken = {name.upper() for name in env}
    while True:
        name = f"{_BATCH_VAR_PREFIX}{uuid4().hex}"
        if name.upper() not in taken:
            return name


def _check(units: int, limit: int, what: str, remedy: str) -> None:
    if units > limit:
        raise CommandRefused(
            f"the Windows {what} would be {units} UTF-16 units including its "
            f"terminator, over the {limit}-unit limit, even with the prompt "
            f"passed as a file pointer. {remedy}"
        )


_NATIVE_REMEDY = (
    "Shorten the agent's configured launch_args, discussion template, title "
    "or other arguments."
)
_BATCH_REMEDY = (
    "Shorten the agent's configured arguments, or point the agent's `cli` at "
    "a native executable instead of a .cmd/.bat shim."
)


def check_budgets(
    argv: list[str] | tuple[str, ...],
    *,
    batch: bool,
    job_name: str = oscompat.JOB_NAME_PLACEHOLDER,
    gate_name: str | None = oscompat.GATE_NAME_PLACEHOLDER,
    variable: str = _BATCH_VAR_PLACEHOLDER,
    comspec: str | None = None,
) -> tuple[str, str] | None:
    """Raise ``CommandRefused`` unless every serialized line fits.

    Returns the ``(cmd.exe, raw line)`` shell plan for a batch file, else
    None. Placeholders have the real identifiers' fixed width, so a preflight
    measurement equals the spawn's; the spawn re-checks with real names.
    """
    argv = list(argv)
    shell: tuple[str, str] | None = None
    if batch:
        value = batch_command_value(argv)
        literal = shell_command_line(variable)
        expanded = literal.replace(f"%{variable}%", value)
        _check(len(value), ENV_VALUE_LIMIT, "batch transport variable", _BATCH_REMEDY)
        _check(command_line_units(literal), SHELL_LINE_LIMIT, "cmd.exe command line", _BATCH_REMEDY)
        _check(command_line_units(expanded), SHELL_LINE_LIMIT, "expanded cmd.exe command line", _BATCH_REMEDY)
        shell = (comspec or system_cmd(), literal)
    else:
        _check(
            command_line_units(subprocess.list2cmdline(argv)),
            COMMAND_LINE_LIMIT,
            "agent command line",
            _NATIVE_REMEDY,
        )
    wrapper = oscompat.interactive_wrapper_argv(job_name, gate_name, argv, shell)
    _check(
        command_line_units(subprocess.list2cmdline(wrapper)),
        COMMAND_LINE_LIMIT,
        "supervisor wrapper command line",
        _BATCH_REMEDY if batch else _NATIVE_REMEDY,
    )
    return shell


def _refuse_batch_line_breaks(parts: list[tuple[str, str]]) -> None:
    for token, role in parts[1:]:
        if "\r" in token or "\n" in token:
            raise CommandRefused(
                f"the agent's {role} argument contains a raw line break, which "
                "a Windows .cmd/.bat agent cannot receive intact. Remove those "
                "line breaks, or point the agent's `cli` at a native "
                "executable."
            )


def plan_agent_command(
    parts_for: Callable[[str], list[tuple[str, str]]],
    *,
    prompt: str | None,
    pointer_for: Callable[[bool], str],
    env: Mapping[str, str],
    comspec: str | None = None,
) -> CommandPlan:
    """Choose the complete prompt or its file pointer by serialized size.

    ``parts_for(prompt_arg)`` returns the final ``(token, role)`` list with
    the unresolved CLI first. ``pointer_for(batch)`` returns the pointer text
    for that transport. ``prompt=None`` plans only the pointer form (the
    callers' preflight, before a prompt exists). A ``.cmd``/``.bat`` agent
    always gets the pointer. Raises ``AgentCliNotFound`` or
    ``CommandRefused``.
    """
    first = parts_for(prompt if prompt is not None else pointer_for(False))
    cli = first[0][0]
    executable = resolve_executable(cli, env)
    if executable is None:
        raise AgentCliNotFound(cli)
    batch = is_batch_file(executable)

    def build(prompt_arg: str) -> tuple[list[tuple[str, str]], list[str]]:
        parts = parts_for(prompt_arg)
        return parts, [executable, *(token for token, _ in parts[1:])]

    if prompt is not None and not batch:
        parts, argv = build(prompt)
        try:
            check_budgets(argv, batch=False, comspec=comspec)
        except CommandRefused:
            pass
        else:
            return CommandPlan(tuple(argv), prompt, False, False)
    pointer = pointer_for(batch)
    parts, argv = build(pointer)
    if batch:
        _refuse_batch_line_breaks(parts)
    check_budgets(argv, batch=batch, comspec=comspec)
    return CommandPlan(tuple(argv), pointer, True, batch)


@dataclass(frozen=True)
class _Spawn:
    argv: list[str]
    shell: tuple[str, str] | None
    env: dict[str, str]
    variable: str | None


def _prepare_spawn(cmd: list[str], env: Mapping[str, str]) -> _Spawn:
    executable = resolve_executable(cmd[0], env)
    if executable is None:
        raise AgentCliNotFound(cmd[0])
    argv = [executable, *cmd[1:]]
    child_env = dict(env)
    if not is_batch_file(executable):
        return _Spawn(argv, None, child_env, None)
    for index, token in enumerate(argv[1:], start=1):
        if "\r" in token or "\n" in token:
            raise CommandRefused(
                f"argument {index} for the .cmd/.bat agent contains a raw "
                "line break that cmd.exe cannot carry intact."
            )
    variable = fresh_batch_variable(child_env)
    child_env[variable] = batch_command_value(argv)
    return _Spawn(argv, (system_cmd(), shell_command_line(variable)), child_env, variable)


# --- console and signals --------------------------------------------------------


class ConsoleModes:
    """Saved stdin/stdout console modes, restored on every exit path."""

    def __init__(self, saved: list[tuple[int, int]]) -> None:
        self._saved = saved

    @classmethod
    def save(cls) -> ConsoleModes:
        if os.name != "nt":
            return cls([])
        import ctypes
        from ctypes import wintypes

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.GetStdHandle.argtypes = [wintypes.DWORD]
        kernel.GetStdHandle.restype = ctypes.c_void_p
        kernel.GetConsoleMode.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.DWORD)]
        kernel.GetConsoleMode.restype = ctypes.c_int
        saved: list[tuple[int, int]] = []
        for std in (-10 & 0xFFFFFFFF, -11 & 0xFFFFFFFF):  # STD_INPUT/OUTPUT_HANDLE
            handle = kernel.GetStdHandle(std)
            mode = wintypes.DWORD()
            if handle and kernel.GetConsoleMode(handle, ctypes.byref(mode)):
                saved.append((handle, mode.value))
        return cls(saved)

    def restore(self) -> None:
        if not self._saved:
            return
        import ctypes

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.SetConsoleMode.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        kernel.SetConsoleMode.restype = ctypes.c_int
        for handle, mode in self._saved:
            kernel.SetConsoleMode(handle, mode)


def _interrupt_signals() -> list[int]:
    return [
        sig
        for sig in (signal.SIGINT, getattr(signal, "SIGBREAK", None))
        if sig is not None
    ]


def _ignore_interrupts() -> list[tuple[int, object]]:
    """Ignore Ctrl+C/Ctrl+Break in the parent while the agent owns the console.

    Mirrors POSIX raw mode, where Ctrl+C becomes a byte for the child.
    Returns the previous handlers for ``_restore_handlers``.
    """
    previous: list[tuple[int, object]] = []
    for sig in _interrupt_signals():
        try:
            previous.append((sig, signal.signal(sig, signal.SIG_IGN)))
        except (ValueError, OSError):  # not the main thread
            pass
    return previous


def _restore_handlers(previous: list[tuple[int, object]]) -> None:
    for sig, handler in reversed(previous):
        try:
            signal.signal(sig, handler)  # type: ignore[arg-type]
        except (ValueError, OSError, TypeError):
            pass


# --- exit classification ----------------------------------------------------------


def classify_exit(code: int, term_kind: str | None) -> tuple[int, str, list[str]]:
    """Windows twin of ``repl_supervisor._classify_exit``, from a DWORD code.

    ``code`` is the wrapper's unsigned exit code, which the wrapper keeps
    equal to the agent's. An NTSTATUS error other than STATUS_CONTROL_C_EXIT
    (the CTRL_BREAK outcome) and the Job terminate code is a real crash,
    whether or not Coga was stopping the child, and keeps its raw code.
    Otherwise an untouched child is ``natural`` with its raw code, and a
    child Coga stopped reports 0 for ``done`` or 124 for ``timeout``.
    """
    code &= 0xFFFFFFFF
    crashed = code >= _NTSTATUS_ERROR and code not in (
        STATUS_CONTROL_C_EXIT,
        _JOB_TERMINATE_CODE,
    )
    if term_kind is None:
        return code, ("crash" if crashed else "natural"), []
    if crashed:
        return code, "crash", [
            f"child exited with NTSTATUS 0x{code:08X}",
            f"NOT our stop - real crash, reporting exit 0x{code:08X}",
        ]
    if term_kind == "timeout":
        teardown_code = _TIMEOUT_EXIT_CODE
        teardown_label = "timeout - liveness limit, agent never signalled done"
    else:
        teardown_code = 0
        teardown_label = "completion observed"
    return teardown_code, term_kind, [
        f"child exited with code 0x{code:08X} after our stop",
        f"reporting exit {teardown_code} ({teardown_label})",
    ]


# --- the supervisor -----------------------------------------------------------------


def _console_attached() -> bool:
    """The POSIX branch's ``sys.stdout.isatty()`` test, as a seam for tests."""
    return sys.stdout.isatty()



def run(
    cmd: list[str],
    env: Mapping[str, str],
    *,
    session_id: str | None = None,
    terminal_status: Callable[[], str | None] | None = None,
    idle_timeout: float | None = None,
    max_session: float | None = None,
    output_fd: int | None = None,
    input_fd: int | None = None,
    after_spawn: Callable[[], None] | None = None,
    spawn_release_guard: (
        Callable[[], AbstractContextManager[None]] | None
    ) = None,
    after_spawn_release: Callable[[], None] | None = None,
    on_spawn_admission_failure: Callable[[], None] | None = None,
) -> ReplOutcome:
    """Supervise one agent on native Windows; see ``run_with_done_marker``.

    ``input_fd`` is unused: the agent reads the inherited console directly.
    ``output_fd`` only redirects the watcher's notices (stderr by default).
    """
    del input_fd

    def notify(line: str) -> None:
        text = f"\n[coga watcher] {line}\n"
        try:
            if output_fd is not None:
                os.write(output_fd, text.encode("utf-8"))
            else:
                sys.stderr.write(text)
                sys.stderr.flush()
        except (OSError, ValueError):
            pass

    if idle_timeout is not None:
        notify(IDLE_TIMEOUT_WARNING)

    console = _console_attached()
    child_env = dict(env)
    sentinel_dir: str | None = None
    sentinel_path = ""
    if console:
        sentinel_dir = tempfile.mkdtemp(prefix="coga-done-")
        sentinel_path = os.path.join(sentinel_dir, "sentinel")
        child_env[SENTINEL_ENV] = sentinel_path
    else:
        # No loop polls a sentinel here; the explicit empty channel tells
        # lifecycle writers its absence is by design, not a lost signal.
        child_env[SENTINEL_ENV] = ""

    modes = ConsoleModes.save() if console else None
    previous_handlers: list[tuple[int, object]] = []
    tree: oscompat.ProcessTree | None = None
    sent_term = False
    term_kind: str | None = None
    term_reason: str | None = None
    done_signalled = False
    try:
        spawn = _prepare_spawn(cmd, child_env)
        check_budgets(
            spawn.argv,
            batch=spawn.shell is not None,
            variable=spawn.variable or _BATCH_VAR_PLACEHOLDER,
            comspec=spawn.shell[0] if spawn.shell else None,
        )
        tree = ProcessTree(
            spawn.argv,
            interactive=True,
            gate=after_spawn is not None,
            new_process_group=True,
            shell=spawn.shell,
            env=spawn.env,
        )
        if after_spawn is not None:
            # Any raise leaves through the `finally`, whose Job close kills
            # the held (or, after release, running) wrapper.
            _admit_held_child(
                tree.release,
                after_spawn=after_spawn,
                spawn_release_guard=spawn_release_guard,
                after_spawn_release=after_spawn_release,
                on_spawn_admission_failure=on_spawn_admission_failure,
            )
        if not console:
            return ReplOutcome(tree.process.wait() & 0xFFFFFFFF, "natural")

        previous_handlers = _ignore_interrupts()
        sent_kill = False
        term_deadline = 0.0
        session_start = time.monotonic()

        def trigger_term(reason: str, *, kind: str) -> None:
            nonlocal sent_term, term_kind, term_reason, term_deadline
            sent_term = True
            term_kind = kind
            term_reason = reason
            term_deadline = time.monotonic() + _KILL_GRACE_SECONDS
            notify(f"stopping REPL - trigger={reason}")
            notify("CTRL_BREAK sent to the agent's process group")
            assert tree is not None
            try:
                tree.interrupt()
            except OSError as exc:
                notify(f"CTRL_BREAK failed ({exc}); waiting for the Job kill")

        while True:
            timeout = (
                max(0.0, term_deadline - time.monotonic())
                if sent_term and not sent_kill
                else _SENTINEL_POLL_INTERVAL
            )
            try:
                code = tree.process.wait(timeout=min(timeout, _SENTINEL_POLL_INTERVAL))
                break
            except subprocess.TimeoutExpired:
                pass

            if sent_term and not sent_kill and time.monotonic() >= term_deadline:
                sent_kill = True
                notify(
                    f"child still alive after {_KILL_GRACE_SECONDS}s - "
                    "terminating its Job Object"
                )
                tree.kill()

            # Latch even mid-teardown: a liveness stop can race the agent's
            # own done signal, and that evidence is kept apart from the cause.
            if not done_signalled and _sentinel_signals_done(sentinel_path, session_id):
                done_signalled = True
                if not sent_term:
                    trigger_term(
                        "sentinel-file (COGA_DONE_SENTINEL touched)", kind="done"
                    )

            if (
                not sent_term
                and terminal_status is not None
                and not completion_pending(sentinel_path)
            ):
                status = terminal_status()
                if status is not None:
                    trigger_term(
                        f"ticket-terminal ({status}; done signal not observed)",
                        kind="done",
                    )

            if (
                max_session is not None
                and not sent_term
                and time.monotonic() - session_start >= max_session
            ):
                trigger_term(
                    f"max-session (wall-clock exceeded {max_session:g}s)",
                    kind="timeout",
                )

        # One last look once the child is gone. Observation only.
        if not done_signalled and _sentinel_signals_done(sentinel_path, session_id):
            done_signalled = True
    finally:
        try:
            if tree is not None:
                # Kill-on-close: no descendant outlives the session.
                tree.close()
        finally:
            _restore_handlers(previous_handlers)
            if modes is not None:
                modes.restore()
            if sent_term:
                try:
                    os.write(
                        output_fd if output_fd is not None else sys.stdout.fileno(),
                        _TTY_SANITIZE,
                    )
                except (OSError, ValueError):
                    pass
            if sentinel_dir is not None:
                remove_sentinel_dir(sentinel_dir)

    exit_code, kind, notes = classify_exit(code, term_kind)
    for note in notes:
        notify(note)
    reason = term_reason if kind == term_kind else None
    return ReplOutcome(exit_code, kind, reason, done_signalled)


# Indirection so Linux tests can substitute a fake tree.
ProcessTree = oscompat.ProcessTree

__all__ = [
    "COMMAND_LINE_LIMIT",
    "ENV_VALUE_LIMIT",
    "IDLE_TIMEOUT_WARNING",
    "SHELL_LINE_LIMIT",
    "STATUS_CONTROL_C_EXIT",
    "CommandPlan",
    "CommandRefused",
    "ConsoleModes",
    "batch_command_value",
    "batch_quote",
    "check_budgets",
    "classify_exit",
    "command_line_units",
    "plan_agent_command",
    "resolve_executable",
    "run",
]
