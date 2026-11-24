"""Isolated CLI and agent processes for the PTY authoring cancellation test."""

from __future__ import annotations

import importlib
import json
from pathlib import Path
import signal
import subprocess
import sys

from coga import cli, launch, repl_supervisor
from coga.ticket import Ticket


role, state_dir = sys.argv[1:3]
state = Path(state_dir)
settings = json.loads((state / "settings.json").read_text(encoding="utf-8"))


def record(name: str, value: object = True) -> None:
    (state / name).write_text(json.dumps(value), encoding="utf-8", newline="\n")


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
    child = subprocess.run([sys.executable, __file__, "cancel", state_dir], check=False)
    record("cancel-exit.json", child.returncode)
    while True:
        signal.pause()

elif role == "cancel":
    sys.argv = ["coga", "mark", "canceled", "duplicate", "--message", "Use sibling"]
    cli.main()

elif role == "outer":
    command = importlib.import_module("coga.commands.ticket")
    command.interactive_stdio_has_tty = lambda: True
    sys.stdout.isatty = lambda: True
    signals_done = repl_supervisor._sentinel_signals_done

    def gated_done(path, session_id):
        return (state / "cancel-exit.json").exists() and signals_done(path, session_id)

    repl_supervisor._sentinel_signals_done = gated_done
    run_agent = launch.run_with_done_marker

    def run_with_watchdog(*args, **kwargs):
        kwargs["max_session"] = 15
        outcome = run_agent(*args, **kwargs)
        record("outcome.json", {
            "kind": outcome.kind, "exit_code": outcome.exit_code,
            "done_signalled": outcome.done_signalled,
        })
        return outcome

    launch.run_with_done_marker = run_with_watchdog
    sys.argv = ["coga", "ticket", "duplicate", "--agent", "claude"]
    cli.main()

else:
    raise AssertionError(role)
