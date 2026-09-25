"""Baseline measurement for this ticket (run 2026-09-25 during authoring).

Counts human activity days on origin/main first-parent history, excluding
Coga machine commits and merges of machine-generated PRs (Dream, skill-update).
Usage: python measure-activity.py <repo> [<repo> ...]  (defaults: coga xpllm magicator under ~/Code)
"""
from __future__ import annotations

import datetime as dt
import re
import subprocess
import sys
from pathlib import Path

MACHINE = re.compile(
    r"^(Log:|Sync coga state|Dream|Ticket: recurring/|Autofix:|Ticket: autofix/|Recurring"
    r"|Update Coga-managed skills"
    r"|Merge pull request #\d+ from \S+/(claude/dream-|coga/skill-update|coga/dream|dream/))"
)


def human_days(repo: Path, since: str = "2026-05-01") -> list[dt.date]:
    out = subprocess.run(
        ["git", "-C", str(repo), "log", "origin/main", "--first-parent", f"--since={since}", "--format=%cs %s"],
        capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    return sorted({dt.date.fromisoformat(l[:10]) for l in out if not MACHINE.match(l[11:])})


def main(argv: list[str]) -> None:
    repos = argv or [str(Path.home() / "Code" / r) for r in ("coga", "xpllm", "magicator")]
    today = dt.date.today()
    for r in repos:
        ds = human_days(Path(r))
        gaps = [(str(a), (b - a).days) for a, b in zip(ds, ds[1:]) if (b - a).days >= 5]
        print(f"== {r}: last human {ds[-1]} ({(today - ds[-1]).days}d ago); active days {len(ds)}; gaps>=5d {gaps}")


if __name__ == "__main__":
    main(sys.argv[1:])
