#!/usr/bin/env python3
"""Deterministic half of the blackboard-size period task.

Reports the `large-blackboard` findings of `coga validate --json`: each
flagged ticket's ref, its measured blackboard size and the threshold. The
alert is informational; nothing is filed, blocked or edited.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass

from coga.blackboard import (
    BLACKBOARD_WARN_BYTES,
    append_blackboard_report,
    format_bytes,
)
from coga.config import Config
from coga.notification import post
from coga.runner import run_entry
from coga.task_env import blackboard_from_env

NAME = "blackboard-size"
FINDING_KIND = "large-blackboard"
REPORT_HEADING = "## Oversized blackboards"
# `coga.blackboard.blackboard_size_warning` renders the measured size and the
# threshold only into the finding's message; this reads them back from it.
_SIZES = re.compile(
    r"blackboard region is (?P<size>[^()]+?) \(warning threshold (?P<threshold>[^()]+?)\)"
)


@dataclass(frozen=True)
class Oversized:
    task: str
    size: str
    threshold: str


def oversized_blackboards(validate_payload: dict) -> list[Oversized]:
    """The `large-blackboard` findings in a `coga validate --json` payload."""
    found: list[Oversized] = []
    for issue in validate_payload.get("issues", []):
        if issue.get("kind") != FINDING_KIND:
            continue
        match = _SIZES.search(issue.get("message", ""))
        if match is None:
            raise ValueError(
                f"{NAME}: cannot read the size from the {FINDING_KIND} "
                f"finding for {issue.get('task')!r}: {issue.get('message')!r}"
            )
        found.append(Oversized(issue["task"], match["size"], match["threshold"]))
    return sorted(found, key=lambda item: item.task)


def render_report(found: list[Oversized]) -> str:
    threshold = found[0].threshold if found else format_bytes(BLACKBOARD_WARN_BYTES)
    lines = [REPORT_HEADING, ""]
    if not found:
        lines.append(f"No ticket blackboard exceeds the {threshold} threshold.")
        return "\n".join(lines) + "\n"
    lines += [
        f"Threshold: {threshold} of live notes (`coga validate` "
        f"`{FINDING_KIND}`). Informational: no review or block follows; "
        "`coga/blackboard` owns the optional remedy.",
        "",
    ]
    lines += [f"- `{item.task}` — {item.size}" for item in found]
    return "\n".join(lines) + "\n"


def render_alert(found: list[Oversized]) -> str:
    listed = ", ".join(f"{item.task} ({item.size})" for item in found)
    return (
        f"{len(found)} ticket blackboard(s) over the {found[0].threshold} "
        f"threshold, FYI only: {listed}"
    )


def run(cfg: Config, argv: list[str]) -> int:
    if argv:
        print(f"{NAME}: unexpected arguments: {' '.join(argv)}", file=sys.stderr)
        return 2
    result = subprocess.run(
        [sys.executable, "-m", "coga.cli", "validate", "--json"],
        cwd=cfg.repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    # Exit 1 only means validation found errors elsewhere; the payload stands.
    if result.returncode not in (0, 1):
        sys.stderr.write(result.stderr)
        print(f"{NAME}: coga validate exited {result.returncode}", file=sys.stderr)
        return result.returncode or 1
    found = oversized_blackboards(json.loads(result.stdout))
    report = render_report(found)
    print(report, end="")
    blackboard = blackboard_from_env(cfg.repo_root)
    if blackboard is not None:
        append_blackboard_report(cfg, blackboard, report)
    if found:
        # An FYI, never an important alert: an oversized blackboard needs no action.
        post(cfg, f"📏 {render_alert(found)}", fatal=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(run_entry(NAME, run, sys.argv[1:], scheduled=True))
