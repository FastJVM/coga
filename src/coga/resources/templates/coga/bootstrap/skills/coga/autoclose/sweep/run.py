#!/usr/bin/env python3
"""Run the merged-ticket autoclose sweep for recurring/autoclose-merged."""

from __future__ import annotations

import sys

from coga.autoclose import GhError, sweep_merged
from coga.config import ConfigError, load_config
from coga.validate import TaskValidationError


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
