#!/usr/bin/env python3
"""Run megalaunch from the recurring/megalaunch script task."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from coga.config import ConfigError, load_config
from coga.megalaunch import render_run_summary, run_megalaunch, write_run_summary


def main() -> int:
    try:
        cfg = load_config()
    except ConfigError as exc:
        sys.stderr.write(f"[megalaunch] {exc}\n")
        return 2

    run = run_megalaunch(cfg)
    summary = render_run_summary(run)
    sys.stdout.write(summary)

    blackboard = os.environ.get("COGA_TASK_BLACKBOARD")
    if blackboard:
        write_run_summary(Path(blackboard), run)

    return 1 if run.counts["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
