#!/usr/bin/env python3
"""Clone-scoped branch sweep: runs in every clone, with no period task."""

from __future__ import annotations

import os
import subprocess
import sys

from coga.config import load_config
from coga.runner import run_recipe

# Through the registry, not a direct import of the recipe function: `run_recipe`
# is the recipe layer's reporting surface.
code = run_recipe(load_config(), "branch-sweep", [])
# A `scope: clone` run has no period task; its exit code is the outcome. A Coga
# that predates clone scope still runs this as a shared period task, which the
# script must close itself, so bump exactly when there is a task to bump.
slug = os.environ.get("COGA_TASK_SLUG")
if code or not slug:
    sys.exit(code)
# Complete the step through the CLI: calling a Typer command function
# in-process would pass `OptionInfo` sentinels instead of real defaults.
sys.exit(
    subprocess.run(
        [sys.executable, "-m", "coga.cli", "bump", slug], check=False
    ).returncode
)
