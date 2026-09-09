#!/usr/bin/env python3
"""Deterministic half of the digest period task."""

from __future__ import annotations

import os
import subprocess
import sys

from coga.commands.digest import run_digest_recipe
from coga.config import load_config

code = run_digest_recipe(load_config(), [])
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
