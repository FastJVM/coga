#!/usr/bin/env python3
"""Flush the daily-digest spool — the script body of recurring/digest.

Runs as a Coga script step (see `coga.commands.launch_script`): the
working directory is the host repo, and `coga` is importable. We call
`run_digest` directly rather than shelling out to `coga digest`, so the flush
does not depend on `coga` being on `PATH` inside the script environment.

`coga digest` is idempotent — when there are no Done records, recurring
errors, or post-filter new commits, it posts nothing — so this exits 0 on a
quiet day. A genuine notification failure crashes loud (per `notification.post`), which the
script launcher reports as a non-zero exit and posts live.
"""

from __future__ import annotations

import sys

from coga.commands.digest import run_digest
from coga.config import ConfigError, load_config


def main() -> int:
    try:
        cfg = load_config()
    except ConfigError as exc:
        sys.stderr.write(f"[digest] {exc}\n")
        return 2
    run_digest(cfg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
