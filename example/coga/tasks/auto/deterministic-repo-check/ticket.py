"""Deterministic half of the seeded example ticket."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ticket_path = Path(os.environ["COGA_TASK_BLACKBOARD"])
with ticket_path.open("a") as handle:
    handle.write(
        f"ticket.py ran headlessly at {os.environ['COGA_TASK_STEP']}\n"
    )

raise SystemExit(
    subprocess.run(
        [
            sys.executable,
            "-m",
            "coga.cli",
            "mark",
            "done",
            os.environ["COGA_TASK_SLUG"],
            "--message",
            "deterministic fixture check passed",
        ],
        check=False,
    ).returncode
)
