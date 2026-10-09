"""`coga run publish-state` — publish Coga state now and confirm it landed.

The end-of-command sweep (`git.sync_coga_state`) publishes the same files but
is best-effort: it reports a failed push on stderr and exits 0, so a caller
cannot tell whether a file it just wrote is on the control branch. A handoff
that tells someone else to use those files from a fresh clone needs that
answer first — `build/onboarding` must not offer `coga launch <slug>` for its
starter tickets until the agreed `product/vision` is published.

This recipe is that strict check. It runs the shared `git.publish` over
`git.coga_root_paths` (the sweep's membership: the Coga root and the contexts
root) and requires every named path to be on control afterwards, either landed
by this publication or already matching. It adds no publication policy of its
own; `coga/internals/state-publication` owns that.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from coga import git
from coga.config import Config

DEFAULT_MESSAGE = "Publish coga state"


def recipe_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="coga run publish-state",
        description=(
            "Publish eligible files under the Coga roots to the control branch "
            "and confirm the named files are there. Exits 0 only on confirmation."
        ),
    )
    parser.add_argument(
        "--message",
        default=DEFAULT_MESSAGE,
        help="Commit message for the publication commit.",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Files that must be on the control branch afterwards (relative to the current directory).",
    )
    return parser


def _refuse(text: str) -> int:
    sys.stderr.write(f"publish-state: {text}\n")
    return 1


def run_publish_state_recipe(cfg: Config, argv: list[str]) -> int:
    """`coga run publish-state [--message M] [PATH...]`.

    Exit 0: every named path is on the control branch (stdout lists them), or
    `[git].enabled = false` so there is no control branch to publish to
    (stdout says so). Exit 1: publication was refused, failed, or could not be
    confirmed; the files stay on disk as written and stderr names the cause.
    Exit 2: argv or a named path is invalid; nothing was published.
    """
    args = recipe_parser().parse_args(argv)
    roots = git.coga_root_paths(cfg)
    required: list[Path] = []
    for raw in args.paths:
        path = Path(os.path.abspath(raw))
        if not any(path == root or root in path.parents for root in roots):
            sys.stderr.write(
                f"publish-state: {raw} is outside the Coga roots; source there "
                "reaches control through a reviewed PR, not state publication\n"
            )
            return 2
        if path.is_symlink() or not path.is_file():
            sys.stderr.write(f"publish-state: {raw} is not a regular file\n")
            return 2
        required.append(path)

    if not cfg.git_enabled:
        sys.stdout.write(
            "publish-state: [git].enabled = false — no control branch to publish "
            "to; the files stay local\n"
        )
        return 0
    try:
        root = git.toplevel(cfg.repo_root)
    except git.GitError as exc:
        return _refuse(f"not published: {exc}")
    if root is None:
        return _refuse(f"not published: {cfg.repo_root} is not in a git repository")

    try:
        landed = git.publish(cfg, roots, args.message, require_paths=required)
    except git.UncertainPublishError as exc:
        return _refuse(f"publication unconfirmed: {exc}")
    except git.StateRegressionError as exc:
        return _refuse(f"publication refused: {exc}")
    except git.GitError as exc:
        return _refuse(f"publication failed: {exc}")
    if landed is None:
        # Past the enabled and repository checks, the remaining soft-skip is
        # a missing control branch; `publish` already wrote its remedy line.
        return _refuse("not published: control branch unavailable")

    remote, control = cfg.git_remote, cfg.git_control_branch
    target = f"{remote}/{control}" if git.remote_configured(root, remote) else f"local {control}"
    outcome = "published to" if landed else "already on"
    sys.stdout.write(f"publish-state: {outcome} {target}\n")
    for path in required:
        sys.stdout.write(f"  {git.relative_to_root(root, path)}\n")
    return 0


__all__ = ["recipe_parser", "run_publish_state_recipe"]
