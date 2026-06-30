#!/usr/bin/env python3
"""Run the blocker-reminder sweep for recurring/blocker-reminders."""

from __future__ import annotations

import sys

from coga.blocker_reminders import remind_blocked_tasks
from coga.config import ConfigError, load_config


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
