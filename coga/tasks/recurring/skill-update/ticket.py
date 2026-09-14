#!/usr/bin/env python3
"""Deterministic half of the skill-update period task."""

from __future__ import annotations

import os
import subprocess
import sys

from coga.skill_update import run_skill_update_recipe
from coga.config import load_config

code = run_skill_update_recipe(load_config(), [])
if code:
    sys.exit(code)
# Complete the step through the CLI: calling a Typer command function
# in-process would pass `OptionInfo` sentinels instead of real defaults.
sys.exit(
    subprocess.run(
        [sys.executable, "-m", "coga.cli", "bump", os.environ["COGA_TASK_SLUG"]],
        check=False,
    ).returncode
)
