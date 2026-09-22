"""The recurring-reminder sweep harness: ``run()`` and ``SweepResult``.

Every recurring reminder or sweep repeats one shape::

    fire = in_window(today) AND NOT satisfied()

and then does the same three things with whatever fired: resolve ``today`` and
the tasks directory, print a report, and post one alert per firing through
``coga slack``. That tail is the whole of what this module owns. Which records
to load, the window arithmetic, the ``satisfied()`` rule (a ticket field, a
recorded ack, or a live query), and the report and alert wording all belong to
the individual sweep — they differ per obligation and were the part a wider
engine got wrong the first time.

Four sweep shapes are known to need nothing more than this harness; the
fixtures under ``tests/fixtures/reminders/`` are the worked example of each:

- **date window** — a grant- or filing-anchored ``[opens, closes)`` window with
  a ticket field as ``satisfied()`` (``golden/`` and ``retrofit/`` patents
  sweeps);
- **period ack** — a monthly nudge satisfied once a human records
  ``Acked: YYYY-MM`` on the reminder's blackboard (``admin/xero_reconcile_sweep``);
- **date high-water ack** — a running pile acknowledged through a date,
  ``Acked: YYYY-MM-DD``, with only newer items surfaced
  (``admin/brex_missing_receipts_sweep``);
- **live query, no window** — ``fire`` is simply "the query returned work"
  (``admin/brex_missing_gl_sweep``).

An ack is an ordinary ``key: value`` blackboard line, read with
``coga.period_state.parse_keys`` over ``coga.taskfile.read_blackboard`` and
written by the human who acknowledges it; no writer lives here.

Posting is the default. A sweep run as a recurring template's ``ticket.py``
receives no operands, so an opt-in flag could never reach it there and a
retrofit went silent on Slack while its stdout stayed byte-identical. Pass
``--dry-run`` to print without posting. Completion is the script's own job, as
for every ``ticket.py``: end with ``coga bump`` / ``coga mark done`` after
``run()`` returns 0.

Downstream repos import this from the installed package (``from coga import
reminders``); nothing is materialized into a repo.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class SweepResult:
    """What a sweep returns to the harness.

    ``report`` is printed to stdout verbatim (the parity surface). ``alerts`` is
    one ready-to-post message per obligation that fired.
    """

    report: str
    alerts: list[str] = field(default_factory=list)


Sweep = Callable[[date, Path], SweepResult]


def _post(task: str, message: str, *, important: bool) -> int:
    # Through the CLI, not `coga.notification` in-process: the sweep is a plain
    # script and `coga slack` already owns config, task resolution, and the log.
    cmd = [sys.executable, "-m", "coga.cli", "slack", "--task", task, "--message", message]
    if important:
        cmd.append("--important")
    return subprocess.run(cmd, check=False).returncode


def run(
    sweep: Sweep,
    *,
    task_slug: str,
    description: str = "",
    important: bool = False,
    argv: list[str] | None = None,
) -> int:
    """Run ``sweep(today, tasks_dir)`` under the shared ``--today`` / ``--tasks-dir``
    / ``--dry-run`` command line and post its alerts.

    ``tasks_dir`` defaults to ``$COGA_COGA_OS_ROOT/tasks``, which every launch
    sets; a standalone run passes ``--tasks-dir``. Alerts go to the normal coga
    channel, or to coga-important with ``important=True`` — reserve that for a
    hard-deadline or money obligation. ``task_slug`` is the ``coga slack --task``
    fallback when ``$COGA_TASK_SLUG`` is unset. Returns 0 when handled and
    non-zero on a missing tasks directory or a failed post, so a script-mode
    launch leaves the period task inspectable.
    """
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--today",
        type=date.fromisoformat,
        default=None,
        help="Override today's date (YYYY-MM-DD) — for testing.",
    )
    parser.add_argument(
        "--tasks-dir",
        type=Path,
        default=None,
        help="Override the tasks directory (defaults to $COGA_COGA_OS_ROOT/tasks).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the report but post no alerts.",
    )
    args = parser.parse_args(argv)

    today = args.today or date.today()
    env_root = os.environ.get("COGA_COGA_OS_ROOT")
    tasks_dir = args.tasks_dir or (Path(env_root) / "tasks" if env_root else None)
    if tasks_dir is None or not tasks_dir.is_dir():
        print(f"tasks directory not found: {tasks_dir}", file=sys.stderr)
        return 1

    result = sweep(today, tasks_dir)
    print(result.report)
    if not result.alerts:
        return 0

    channel = "coga-important" if important else "coga"
    if args.dry_run:
        print(
            f"\nDry run: {len(result.alerts)} alert(s) not posted to the {channel} channel.",
            file=sys.stderr,
        )
        return 0
    print(
        f"\nPosting {len(result.alerts)} alert(s) to the {channel} channel …",
        file=sys.stderr,
    )
    task = os.environ.get("COGA_TASK_SLUG") or task_slug
    failures = 0
    for message in result.alerts:
        if _post(task, message, important=important) != 0:
            failures += 1
            print("  ! failed to post an alert", file=sys.stderr)
    return 1 if failures else 0
