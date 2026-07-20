#!/usr/bin/env python3
"""Run the blocker-reminder sweep for recurring/blocker-reminders.

The deterministic recipe lives beside this entry point in `recipe.py`, imported
as a sibling module. Coga runs a skill script as `python <skill-dir>/run.py`, so
`sys.path[0]` is already the skill dir; the explicit insert below makes the
sibling import resolve the same way when a test loads this file via
`spec_from_file_location` (where `sys.path[0]` is not the skill dir).
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from coga.config import ConfigError, load_config  # noqa: E402

from recipe import remind_blocked_tasks  # noqa: E402


def main() -> int:
    try:
        cfg = load_config()
    except ConfigError as exc:
        sys.stderr.write(f"[blockers] {exc}\n")
        return 2

    count = remind_blocked_tasks(cfg)
    if count == 0:
        sys.stdout.write("[blockers] no unresolved blockers to remind.\n")
    else:
        sys.stdout.write(f"[blockers] reminded {count} blocker(s).\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
