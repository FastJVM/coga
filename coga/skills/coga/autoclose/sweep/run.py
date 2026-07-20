#!/usr/bin/env python3
"""Run the merged-ticket autoclose sweep for recurring/autoclose-merged.

The deterministic recipe lives beside this entry point in `recipe.py`, imported
as a sibling module (it re-exports `GhError` from `coga.autoclose` so the whole
sweep surface comes from one place). Coga runs a skill script as
`python <skill-dir>/run.py`, so `sys.path[0]` is already the skill dir; the
explicit insert below makes the sibling import resolve the same way when a test
loads this file via `spec_from_file_location` (where `sys.path[0]` is not the
skill dir).
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from coga.config import ConfigError, load_config  # noqa: E402
from coga.validate import TaskValidationError  # noqa: E402

from recipe import GhError, sweep_merged  # noqa: E402


def main() -> int:
    try:
        cfg = load_config()
    except ConfigError as exc:
        sys.stderr.write(f"[autoclose] {exc}\n")
        return 2

    try:
        count = sweep_merged(cfg, quiet=False)
    except GhError as exc:
        sys.stderr.write(f"[autoclose] {exc}\n")
        return 2
    except TaskValidationError as exc:
        sys.stderr.write(f"[autoclose] {exc}\n")
        return 2

    if count == 0:
        sys.stdout.write("[autoclose] no tickets bumped.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
