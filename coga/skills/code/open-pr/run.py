#!/usr/bin/env python3
"""Push the branch and open (or ready) the PR — the script body of code/open-pr.

Thin wrapper over the sibling `recipe.open_pr` (the recipe lives beside this
script in the skill dir, so the skill is self-contained). Runs as a Coga script step
(see `coga.commands.launch_script`): the launch supervisor executes it in place
of an agent and, on exit 0, advances the workflow; on any non-zero exit it posts
a failure and leaves the step put. That is the point — the open-pr step cannot
complete without producing a real PR, so no one can bump past it with nothing
built. The exit code, not an agent's judgment, gates the bump.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from coga.config import ConfigError, load_config
from recipe import OpenPrError, open_pr


def main() -> int:
    slug = os.environ.get("COGA_TASK_SLUG", "<unknown>")
    blackboard = os.environ.get("COGA_TASK_BLACKBOARD")
    if not blackboard:
        sys.stderr.write(
            "[open-pr] COGA_TASK_BLACKBOARD is not set — run this as a Coga script step.\n"
        )
        return 2

    try:
        cfg = load_config()
        url = open_pr(cfg, slug=slug, blackboard_path=Path(blackboard))
    except (ConfigError, OpenPrError) as exc:
        sys.stderr.write(f"[open-pr] {exc}\n")
        return 2

    sys.stdout.write(f"[open-pr] PR ready: {url}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
