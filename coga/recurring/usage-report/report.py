#!/usr/bin/env python3
"""Weekly agent-token report: the renderer behind the usage-report period task.

Single-consumer deterministic work lives beside its ticket, not in `src/coga/`
(the microkernel rule). This module imports only shared core infra:
`coga.config` for the repo and `coga.usage` for the records and the rollup.

Run ad hoc to print exactly what the Monday post says, without posting or
writing anything:

    python coga/recurring/usage-report/report.py --since 2026-08-31 --until 2026-09-07

The window is half-open calendar `[since, until)` in UTC and defaults to the
last completed ISO week, so the same `coga/log.md` and the same dates always
render the same text — a missed week is recovered by re-running with explicit
dates, and there is no cursor to keep.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta, timezone

from coga.config import load_config
from coga.usage import UsageRecord, load_records, rollup

TOKEN_FIELDS = (
    ("input", "input_tokens"),
    ("cache write", "cache_creation_input_tokens"),
    ("cache read", "cache_read_input_tokens"),
    ("output", "output_tokens"),
)


@dataclass(frozen=True)
class Report:
    since: date
    until: date
    sessions: int
    unknown_sessions: int
    input_tokens: int
    cache_creation_input_tokens: int
    cache_read_input_tokens: int
    output_tokens: int
    # `(key, total_tokens)` per model, largest first. Every rollup bucket is
    # kept, including `(unknown)` for a null model and `<synthetic>`.
    models: tuple[tuple[str, int], ...]

    @property
    def total_tokens(self) -> int:
        return (
            self.input_tokens
            + self.cache_creation_input_tokens
            + self.cache_read_input_tokens
            + self.output_tokens
        )

    def to_dict(self) -> dict:
        data = asdict(self)
        data["since"] = self.since.isoformat()
        data["until"] = self.until.isoformat()
        data["total_tokens"] = self.total_tokens
        data["models"] = [{"model": key, "total_tokens": n} for key, n in self.models]
        return data


def default_window(today: date) -> tuple[date, date]:
    """The last completed ISO week: previous Monday to this Monday, half-open."""
    this_monday = today - timedelta(days=today.weekday())
    return this_monday - timedelta(days=7), this_monday


def build_report(records: list[UsageRecord], since: date, until: date) -> Report:
    """Roll `records` up over the half-open UTC window `[since, until)`."""
    if until <= since:
        raise ValueError(f"empty window: until {until} is not after since {since}")
    # `rollup`'s `until` is inclusive (`_record_matches` keeps `ts == until`,
    # and a date-only `until` expands to the end of that day), so the half-open
    # window is built from datetimes: the last instant before `until` 00:00.
    start = datetime.combine(since, time.min, tzinfo=timezone.utc)
    end = datetime.combine(until, time.min, tzinfo=timezone.utc) - timedelta(
        microseconds=1
    )
    result = rollup(records, by="model", since=start, until=end)
    overall = result.overall
    models = sorted(
        ((row.key, row.total_tokens) for row in result.groups),
        key=lambda item: (-item[1], item[0]),
    )
    return Report(
        since=since,
        until=until,
        sessions=overall.sessions,
        unknown_sessions=overall.unknown_sessions,
        input_tokens=overall.input_tokens,
        cache_creation_input_tokens=overall.cache_creation_input_tokens,
        cache_read_input_tokens=overall.cache_read_input_tokens,
        output_tokens=overall.output_tokens,
        models=tuple(models),
    )


def render(report: Report) -> str:
    """The Slack/stdout text. One header line, then the breakdown."""
    lines = [f"Agent usage — {_window_label(report)}"]
    if report.sessions == 0:
        lines.append("No Coga-launched sessions recorded in this window.")
        return "\n".join(lines)
    summary = (
        f"{format_tokens(report.total_tokens)} tokens across "
        f"{_plural(report.sessions, 'session')}"
    )
    if report.unknown_sessions:
        summary += (
            f" ({_plural(report.unknown_sessions, 'session')} "
            f"{'has' if report.unknown_sessions == 1 else 'have'} unknown "
            "counts, so this is a floor)"
        )
    lines.append(summary)
    lines.append(
        "  "
        + " · ".join(
            f"{label} {format_tokens(getattr(report, field))}"
            for label, field in TOKEN_FIELDS
        )
    )
    key_width = max(len(key) for key, _ in report.models)
    cells = [(key, format_tokens(n)) for key, n in report.models]
    count_width = max(len(cell) for _, cell in cells)
    for key, cell in cells:
        lines.append(f"  {key:<{key_width}}  {cell:>{count_width}}")
    return "\n".join(lines)


def format_tokens(n: int) -> str:
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.2f}B"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


def _window_label(report: Report) -> str:
    if report.since.weekday() == 0 and report.until - report.since == timedelta(days=7):
        return f"week of {report.since.isoformat()} (Mon–Sun)"
    return f"{report.since.isoformat()} to {report.until.isoformat()} (UTC, end exclusive)"


def _plural(n: int, noun: str) -> str:
    return f"{n} {noun}" if n == 1 else f"{n} {noun}s"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Print last week's agent token usage as the Monday post renders it."
    )
    parser.add_argument("--since", type=date.fromisoformat, help="YYYY-MM-DD, inclusive (UTC)")
    parser.add_argument("--until", type=date.fromisoformat, help="YYYY-MM-DD, exclusive (UTC)")
    parser.add_argument("--json", action="store_true", help="emit the report as JSON")
    args = parser.parse_args(argv)
    since, until = default_window(datetime.now(timezone.utc).date())
    since = args.since or since
    until = args.until or until
    if until <= since:
        parser.error(f"--until {until} must be after --since {since}")
    # Read-only, like `coga usage`: a fresh clone without the gitignored
    # `coga.local.toml` user setting can still render the report.
    report = build_report(load_records(load_config(require_user=False)), since, until)
    print(json.dumps(report.to_dict(), indent=2) if args.json else render(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
