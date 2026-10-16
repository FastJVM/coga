#!/usr/bin/env python3
"""Clone-scoped branch sweep: runs in every clone, with no period task."""

from __future__ import annotations

import sys

from coga.config import load_config
from coga.runner import run_recipe

# Through the registry, not a direct import of the recipe function: `run_recipe`
# is the recipe layer's reporting surface. A `scope: clone` run has no period
# task to bump; its exit code is the outcome the sweep records.
sys.exit(run_recipe(load_config(), "branch-sweep", []))
