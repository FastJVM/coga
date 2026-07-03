#!/usr/bin/env python3
"""The recurring sweep, as a stateless bootstrap script target.

`coga recurring` launches this via `coga launch bootstrap/recurring-scan` after
writing the runtime flags into a narrow env contract:

- `COGA_RECURRING_FORCE=1`       → the `--all` forced full run
- `COGA_RECURRING_INTERACTIVE=1` → the `--interactive` human-stepped run

Both default to off when unset, so a bare `coga launch bootstrap/recurring-scan`
runs the ordinary scheduled scan. The deterministic work lives in
`coga.recurring_runner.run_recurring_scan`; this file only wires the env
contract to it and propagates the exit code.
"""

from __future__ import annotations

import os
import sys

from coga.config import load_config
from coga.recurring_runner import run_recurring_scan


def main() -> int:
    cfg = load_config()
    force = os.environ.get("COGA_RECURRING_FORCE") == "1"
    interactive = os.environ.get("COGA_RECURRING_INTERACTIVE") == "1"
    return run_recurring_scan(cfg, force=force, interactive=interactive)


if __name__ == "__main__":
    sys.exit(main())
