#!/usr/bin/env python3
"""Deterministic half of the usage-report period task: post last week's tokens."""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from coga.config import load_config
from coga.notification import post

# `coga launch` copies only this file into the period task, so the renderer is
# reached through the template directory under the active checkout's Coga OS
# root, never as a sibling import.
sys.path.insert(
    0, str(Path(os.environ["COGA_COGA_OS_ROOT"]) / "recurring" / "usage-report")
)
import report  # noqa: E402

cfg = load_config()
since, until = report.default_window(datetime.now(timezone.utc).date())
text = report.render(report.build_report(report.load_records(cfg), since, until))
# One post attempt per run, on the important route the owner chose for it.
# `fatal=False`: a delivery miss is already loud on stderr and in `log.md`, and
# must not leave the period task `in_progress`; repost by hand with
# `coga slack --task <slug> --message "$(python coga/recurring/usage-report/report.py --since … --until …)"`.
post(cfg, text, important=True, fatal=False)
# Complete the step through the CLI: calling a Typer command function
# in-process would pass `OptionInfo` sentinels instead of real defaults.
sys.exit(
    subprocess.run(
        [sys.executable, "-m", "coga.cli", "bump", os.environ["COGA_TASK_SLUG"]],
        check=False,
    ).returncode
)
