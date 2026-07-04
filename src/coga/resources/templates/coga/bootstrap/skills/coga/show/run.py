#!/usr/bin/env python3
"""Render a task's ticket + log — the script-shaped home for `coga show`."""

from __future__ import annotations

import sys

from coga.config import ConfigError
from coga.tasks import TaskNotFoundError
from coga.views import ViewError, render_show_from_env


def main() -> int:
    try:
        render_show_from_env()
    except ConfigError as exc:
        sys.stderr.write(f"[show] {exc}\n")
        return 2
    except (ViewError, TaskNotFoundError) as exc:
        sys.stderr.write(f"[show] {exc}\n")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
