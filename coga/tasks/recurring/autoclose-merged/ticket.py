#!/usr/bin/env python3
"""Deterministic half of the autoclose-merged period task."""

from __future__ import annotations

import os
import subprocess
import sys

from coga.config import load_config
from coga.runner import run_recipe

# Through the registry, not a direct import of the recipe function: `run_recipe`
# is the layer that records a failing recipe's stderr on the period blackboard.
code = run_recipe(load_config(), "autoclose", [])
if code:
    sys.exit(code)
# Catch landed branches without a live ticket, even when autoclose closed none.
# Keep both the branch report and any failure on this period's blackboard.
code = run_recipe(load_config(), "branch-sweep", [])
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
