#!/usr/bin/env python3
"""Run the branch sweep for recurring/branch-sweep."""

from __future__ import annotations

import sys

from coga import git
from coga.branchsweep import sweep_branches
from coga.config import ConfigError, load_config


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
