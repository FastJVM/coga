"""Isolated CLI/agent processes for the synchronized authoring teardown test."""

from __future__ import annotations

import importlib
import json
from pathlib import Path
import signal
import subprocess
import sys

from coga import cli, git, launch, repl_supervisor
from coga.ticket import Ticket


role, state_dir = sys.argv[1:3]
state = Path(state_dir)
settings = json.loads((state / "settings.json").read_text(encoding="utf-8"))


def record(name: str, value: object = True) -> None:
    (state / name).write_text(json.dumps(value), encoding="utf-8", newline="\n")


def remote(path: str) -> str:
    return subprocess.check_output(
        ["git", "--git-dir", settings["origin"], "show", f"main:{path}"],
        text=True, encoding="utf-8",
    )


if role == "agent":
    sibling = Path("tasks/sibling.md")
    ticket = Ticket.read(sibling)
    ticket.body += "\nSibling handoff.\n"
    if settings["failure"] == "validation":
        ticket.frontmatter["contexts"] = ["missing/context"]
    ticket.write(sibling)
    support = Path("contexts/team/SKILL.md")
    support.parent.mkdir(parents=True)
    support.write_text(
        "---\nname: team\ndescription: Team knowledge.\n---\nHandoff context.\n",
        encoding="utf-8", newline="\n",
    )
    child = subprocess.Popen([sys.executable, __file__, "cancel", state_dir])

    def terminate_agent(signum, frame):
        # The real supervisor signals the entire group. Reap our CLI child so
        # its interrupted/completed sweep is proven before the outer finalizer.
        record("cancel-exit.json", child.wait(timeout=5))
        sys.exit(0)

    signal.signal(signal.SIGTERM, terminate_agent)
    record("agent-ready")
    if settings["child_sweep"] == "completed":
        record("child-reaped", child.wait(timeout=10))
    while True:
        signal.pause()

elif role == "cancel":
    def terminate_cancel(signum, frame):
        record("cancel-terminated")
        sys.exit(143)

    signal.signal(signal.SIGTERM, terminate_cancel)
    sweep = cli._sweep_coga_state

    def child_sweep(cfg):
        # mark canceled has published its own transition and emitted the done
        # marker before cli.main reaches this boundary. No timing sleeps.
        record("child-sweep-entered")
        if settings["child_sweep"] == "interrupted":
            while True:
                signal.pause()
        sweep(cfg)
        record("child-sweep-completed")

    cli._sweep_coga_state = child_sweep
    sys.argv = ["coga", "mark", "canceled", "duplicate", "--message", "Use sibling"]
    try:
        cli.main()
    except SystemExit as exc:
        if exc.code not in (None, 0):
            raise
    record("cancel-completed")

elif role == "outer":
    command = importlib.import_module("coga.commands.ticket")
    # Match test_repl_supervisor's forced-PTY harness: proxy to captured stdout
    # and /dev/null stdin, but exercise the real pty.fork and process-group stop.
    command._interactive_stdio_has_tty = lambda: True
    sys.stdout.isatty = lambda: True
    signals_done = repl_supervisor._sentinel_signals_done

    def gated_done(path, session_id):
        gate = (
            "child-sweep-entered" if settings["child_sweep"] == "interrupted"
            else "child-reaped"
        )
        return (
            (state / "agent-ready").exists() and (state / gate).exists()
            and signals_done(path, session_id)
        )

    repl_supervisor._sentinel_signals_done = gated_done
    run_agent = launch.run_with_done_marker

    def run_with_watchdog(*args, **kwargs):
        kwargs["max_session"] = 15  # failure backstop, never the synchronization
        outcome = run_agent(*args, **kwargs)
        record("outcome.json", {
            "kind": outcome.kind, "exit_code": outcome.exit_code,
            "done_signalled": outcome.done_signalled,
        })
        return outcome

    launch.run_with_done_marker = run_with_watchdog
    finalize = command.finalize_authored

    def observed_finalize(*args, **kwargs):
        record("before-finalize.json", {
            "target": remote("coga/tasks/duplicate.md"),
            "sibling": remote("coga/tasks/sibling.md"),
        })
        publish = git.publish

        def observed_publish(cfg, paths, *args, **kwargs):
            record("finalizer-publish.json", [str(path) for path in paths])
            return publish(cfg, paths, *args, **kwargs)

        git.publish = observed_publish
        try:
            return finalize(*args, **kwargs)
        finally:
            git.publish = publish

    command.finalize_authored = observed_finalize
    sweep = cli._sweep_coga_state

    def outer_sweep(cfg):
        record("outer-sweep.json", {"withheld": git.state_sweep_withheld.get()})
        return sweep(cfg)

    cli._sweep_coga_state = outer_sweep
    sys.argv = ["coga", "ticket", "duplicate", "--agent", "claude"]
    cli.main()

else:
    raise AssertionError(role)
