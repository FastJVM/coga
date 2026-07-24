#!/usr/bin/env python3
"""Run the branch sweep for recurring/branch-sweep.

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

from coga import git  # noqa: E402
from coga.config import ConfigError, load_config  # noqa: E402

from recipe import sweep_branches  # noqa: E402


def main() -> int:
    try:
        cfg = load_config()
    except ConfigError as exc:
        sys.stderr.write(f"[branch-sweep] {exc}\n")
        return 2

    root = git._toplevel(cfg.repo_root)
    if root is None:
        sys.stderr.write(f"[branch-sweep] {cfg.repo_root} is not inside a git repo\n")
        return 2

    result = sweep_branches(cfg, root, echo=print)

    if result.remote_unavailable:
        sys.stderr.write(f"[branch-sweep] {result.remote_unavailable}\n")
        return 2

    if result.gh_unavailable:
        sys.stderr.write(f"[branch-sweep] {result.gh_unavailable}\n")
        return 2

    if not result.local_deleted and not result.remote_deleted:
        sys.stdout.write("[branch-sweep] no branches deleted.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
