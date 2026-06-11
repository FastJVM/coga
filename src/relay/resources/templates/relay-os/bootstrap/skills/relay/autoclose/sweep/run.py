#!/usr/bin/env python3
"""Run the merged-ticket autoclose sweep for recurring/autoclose-merged."""

from __future__ import annotations

import sys

from relay.automerge import GhError, auto_bump_merged
from relay.config import ConfigError, load_config
from relay.validate import TaskValidationError


def main() -> int:
    try:
        cfg = load_config()
    except ConfigError as exc:
        sys.stderr.write(f"[autoclose] {exc}\n")
        return 2

    try:
        count = auto_bump_merged(cfg, quiet=False)
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
