"""Shared recurring-reminder / sweep engine.

Every recurring reminder and sweep repeats the same shape::

    fire = in_window(today) AND NOT satisfied()

Admin and patents each hand-rolled this periodic-sweep logic in every script.
This module owns the shared ~80%: reading ticket frontmatter, resolving the
tasks directory, the date-window arithmetic and the in-window check, the ack
helper (coga's sanctioned cross-run state home), the ``coga slack`` notify
plumbing, and the ``--today`` / ``--tasks-dir`` / ``--notify`` CLI harness. Each
reminder supplies the unique 20% — which records to load, its window spec, a
``satisfied()`` rule, and how to format its report.

Downstream repos import it from the installed package (``from coga import
reminders``); nothing is materialized into a repo. Stdlib-only and
dependency-free, matching the existing coga sweep scripts (Python >= 3.11).

See the ``coga/reminders`` bootstrap skill for the adoption/migration note.
"""

from __future__ import annotations

import argparse
import calendar
import os
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from coga.taskfile import read_blackboard, replace_blackboard

# --------------------------------------------------------------------------
# Date arithmetic
# --------------------------------------------------------------------------


def add_years(d: date, years: int) -> date:
    """``d`` plus ``years``, clamping Feb 29 to Feb 28 in a non-leap target year."""
    try:
        return d.replace(year=d.year + years)
    except ValueError:  # Feb 29 -> a year with no Feb 29
        return d.replace(year=d.year + years, day=28)


def add_months(d: date, months: int) -> date:
    """``d`` plus ``months``, clamping the day to the target month's last day
    (e.g. Jan 31 + 1 month -> Feb 28/29)."""
    total = d.month - 1 + months
    year = d.year + total // 12
    month = total % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def parse_date(raw: str) -> date | None:
    """``raw`` as an ISO date; blank or unparseable -> ``None``."""
    raw = raw.strip()
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


# --------------------------------------------------------------------------
# Window evaluation — the kernel: fire = in_window(today) AND NOT satisfied()
# --------------------------------------------------------------------------


def in_window(
    today: date, opens: date, closes: date, *, past_deadline_fires: bool = False
) -> bool:
    """Whether ``today`` falls in the reminder's window ``[opens, closes)``.

    The default window is open-inclusive, close-exclusive: a monthly period, or
    an annual window that ages out at ``closes``. With ``past_deadline_fires``,
    the window has no upper bound — once ``today`` reaches ``opens`` it keeps
    firing, so a money obligation that must not lapse silently keeps firing after
    its deadline until ``satisfied()`` becomes true.
    """
    if today < opens:
        return False
    if past_deadline_fires:
        return True
    return today < closes


# --------------------------------------------------------------------------
# Frontmatter reading
# --------------------------------------------------------------------------


def read_frontmatter(path: Path) -> dict[str, str]:
    """Top-level scalar frontmatter fields of a ticket, as strings.

    Deliberately dependency-free: reads the block between the first two ``---``
    fences and keeps only column-0 ``key: value`` lines, so nested/indented keys
    (lists, the workflow block) are ignored. Returns ``{}`` when there is no
    frontmatter.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return {}
    if not text.startswith("---"):
        return {}
    _, _, after = text.partition("---")
    block, sep, _ = after.partition("\n---")
    if not sep:
        return {}
    fields: dict[str, str] = {}
    for line in block.splitlines():
        if not line or line[0].isspace() or line.lstrip().startswith("#"):
            continue
        key, colon, value = line.partition(":")
        if not colon:
            continue
        fields[key.strip()] = value.strip().strip("'\"")
    return fields


# --------------------------------------------------------------------------
# Tasks directory
# --------------------------------------------------------------------------


def default_tasks_dir() -> Path | None:
    """The coga tasks directory from ``$COGA_COGA_OS_ROOT``.

    Every coga launch sets ``COGA_COGA_OS_ROOT`` (the ``coga/`` root), so a
    launched sweep needs no ``--tasks-dir``. Returns ``None`` when the variable
    is unset — a standalone run must then pass ``--tasks-dir`` explicitly (the
    harness reports the missing directory).
    """
    env_root = os.environ.get("COGA_COGA_OS_ROOT")
    return Path(env_root) / "tasks" if env_root else None


# --------------------------------------------------------------------------
# Ack helper — coga's sanctioned cross-run state home
# --------------------------------------------------------------------------

_ACK_PREFIX = "Acked:"


def read_ack(ticket: Path) -> str | None:
    """The recorded ``Acked: <period>`` marker in a reminder's blackboard, or ``None``.

    The ack is the universal ``satisfied()`` fallback: a reminder is satisfied for
    a period once a human — or a ``coga recurring ack`` wrapper — has recorded that
    period in ``ticket`` below its ``<!-- coga:blackboard -->`` fence. State lives
    in the reminder's own blackboard, coga's sanctioned cross-run state home, not
    in a period task that is reaped each run.
    """
    try:
        text = read_blackboard(ticket)
    except (OSError, UnicodeDecodeError):
        return None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(_ACK_PREFIX):
            return stripped[len(_ACK_PREFIX):].strip() or None
    return None


def record_ack(ticket: Path, period: str) -> None:
    """Record ``Acked: <period>`` in ``ticket``'s blackboard region.

    Rewrites the single ``Acked:`` line in place when present, else appends one.
    The ticket body and frontmatter remain byte-for-byte unchanged.
    """
    line = f"{_ACK_PREFIX} {period}"
    text = read_blackboard(ticket)
    lines = text.splitlines()
    for i, existing in enumerate(lines):
        if existing.strip().startswith(_ACK_PREFIX):
            lines[i] = line
            break
    else:
        if lines and lines[-1].strip():
            lines.append("")
        lines.append(line)
    replace_blackboard(ticket, "\n".join(lines) + "\n")


# --------------------------------------------------------------------------
# Notify — a firing reminder is unfinished work a human must act on
# --------------------------------------------------------------------------


def notify(task: str, message: str, *, important: bool = False) -> int:
    """Post ``message`` to coga's Slack, returning the ``coga slack`` exit code.

    Shells out to ``coga slack`` (no coga import — a downstream sweep script may
    run where only the CLI is on PATH). Posts to the normal coga channel by
    default; pass ``important=True`` to route to the coga-important channel
    (``coga slack --important``). Reserve important for the rare hard-deadline or
    money obligation that must not lapse silently — a routine reminder does not
    belong there. coga reads the webhook from the environment and fails loud if
    it is unset, so a missing webhook surfaces as a non-zero return here.
    """
    cmd = ["coga", "slack", "--task", task, "--message", message]
    if important:
        cmd.append("--important")
    return subprocess.run(cmd).returncode


# --------------------------------------------------------------------------
# CLI harness
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class SweepResult:
    """What a sweep returns to the harness.

    ``report`` is printed to stdout verbatim (the parity surface). ``alerts`` is
    one ready-to-post message per obligation that fired; the harness posts them
    only under ``--notify`` and is otherwise print-only.
    """

    report: str
    alerts: list[str] = field(default_factory=list)


def run(
    sweep,
    *,
    task_slug: str,
    description: str = "",
    important: bool = False,
    argv: list[str] | None = None,
) -> int:
    """The shared ``--today`` / ``--tasks-dir`` / ``--notify`` CLI harness.

    ``sweep`` is ``sweep(today: date, tasks_dir: Path) -> SweepResult`` — it owns
    record loading, the window spec, the ``satisfied()`` rule, and formatting.
    The harness resolves ``today`` / ``tasks_dir``, prints the report, and under
    ``--notify`` posts each alert (a bare run is print-only). Alerts go to the
    normal coga Slack channel; pass ``important=True`` to route them to
    coga-important — reserve that for a hard-deadline or money obligation.
    ``task_slug`` is the
    ``coga slack --task`` fallback when ``$COGA_TASK_SLUG`` is unset (a standalone
    run). Returns 0 when handled, non-zero on failure so a script-mode launch
    posts 💥 and leaves the task inspectable.
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
        help="Override the tasks directory (defaults to the coga tasks dir).",
    )
    parser.add_argument(
        "--notify",
        action="store_true",
        help="Post an alert per fired obligation to coga Slack (bare run is print-only).",
    )
    args = parser.parse_args(argv)

    today = args.today or date.today()
    tasks_dir = args.tasks_dir or default_tasks_dir()
    if tasks_dir is None or not tasks_dir.is_dir():
        print(f"tasks directory not found: {tasks_dir}", file=sys.stderr)
        return 1

    result = sweep(today, tasks_dir)
    print(result.report)

    if args.notify and result.alerts:
        channel = "coga-important" if important else "coga"
        print(
            f"\nPosting {len(result.alerts)} alert(s) to the {channel} channel …",
            file=sys.stderr,
        )
        task = os.environ.get("COGA_TASK_SLUG") or task_slug
        failures = 0
        for message in result.alerts:
            if notify(task, message, important=important) != 0:
                failures += 1
                print("  ! failed to post an alert", file=sys.stderr)
        if failures:
            return 1
    return 0
