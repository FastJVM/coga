"""`enter` step script for branch workflows, plus `run.py rebase`.

With no argument, coga runs this before each step of a ticket whose workflow
declares `enter: git/ticket-enter`. It switches to the ticket's recorded
branch, or creates `coga/<slug-part>` from the current HEAD and records
`branch`/`base`/`remote` under `## Dev`. The live ticket and `coga/log.md`
bytes cross the switch: the base's copy is the newest one.

`run.py rebase` rebases the ticket branch onto `<remote>/<base>` without
merging or stashing the ticket. Both stop at the first Git failure and leave
local state for a person to fix.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from coga.blackboard import read_dev_fields, set_dev_fields
from coga.taskfile import TaskFileError, read_blackboard, replace_blackboard
from coga_edge.git_workflow import branch_slug_part, fresh_branch_name
from coga_edge.ticket_git import (
    TicketGitError,
    current_branch,
    dev_record,
    is_ancestor,
    out,
    ref_tip,
    run_op,
    switch_carrying,
    ticket_paths,
    tracked_in_head,
)

PREFIX = "ticket-enter"


def recorded_branch(fields: dict[str, str]) -> tuple[str, str, str] | None:
    branch = fields.get("branch")
    if not branch:
        return None
    missing = [key for key in ("base", "remote") if not fields.get(key)]
    if missing:
        raise TicketGitError(
            f"`## Dev` records branch: {branch} without "
            f"{' or '.join(f'{key}:' for key in missing)}; complete the record "
            "by hand, then launch again"
        )
    return branch, fields["base"], fields["remote"]


def refuse_diverged(branch: str, remote: str) -> None:
    local = ref_tip(f"refs/heads/{branch}")
    tracking = ref_tip(f"refs/remotes/{remote}/{branch}")
    if local and tracking and local != tracking and not (
        is_ancestor(local, tracking) or is_ancestor(tracking, local)
    ):
        raise TicketGitError(
            f"local `{branch}` and `{remote}/{branch}` have diverged; reconcile "
            "them by hand, then launch again"
        )


def enter() -> int:
    paths = ticket_paths()
    slug = os.environ["COGA_TASK_SLUG"]
    start = current_branch()
    if not start:
        raise TicketGitError("HEAD is detached; switch to a branch, then launch again")

    record = recorded_branch(dev_record(paths.ticket))
    if record is not None:
        branch, _base, remote = record
        if start == branch:
            return 0  # resumed on the branch (a session ended without exit)
        local = ref_tip(f"refs/heads/{branch}")
        tracking = ref_tip(f"refs/remotes/{remote}/{branch}")
        if not local and not tracking:
            raise TicketGitError(
                f"the recorded branch `{branch}` exists neither locally nor as "
                f"`{remote}/{branch}`; fetch it or fix `## Dev`, then launch again"
            )
        refuse_diverged(branch, remote)
        if local:
            switch_carrying(paths, branch, "--", branch)
        else:
            switch_carrying(paths, branch, "-c", branch, "--track", f"{remote}/{branch}")
        print(f"{PREFIX}: switched to `{branch}`", file=sys.stderr)
        return 0

    remote = out(
        "for-each-ref", "--format=%(upstream:remotename)", f"refs/heads/{start}"
    ) or "origin"
    name = f"coga/{branch_slug_part(slug)}"
    taken = ref_tip(f"refs/heads/{name}") or ref_tip(f"refs/remotes/{remote}/{name}")
    branch = fresh_branch_name(slug, remote, str(paths.top)) if taken else name
    # Same commit, so no carried file can block the switch.
    run_op(f"git switch -c {branch}", "switch", "-c", branch)
    region = read_blackboard(paths.ticket)
    replace_blackboard(
        paths.ticket,
        set_dev_fields(region, branch=branch, base=start, remote=remote),
    )
    print(f"{PREFIX}: created `{branch}` from `{start}`", file=sys.stderr)
    return 0


def rebase() -> int:
    """Rebase the ticket branch onto its base, keeping the live ticket."""
    paths = ticket_paths()
    record = recorded_branch(dev_record(paths.ticket))
    if record is None:
        raise TicketGitError("`## Dev` records no branch; nothing to rebase")
    branch, base, remote = record
    if current_branch() != branch:
        raise TicketGitError(f"HEAD is not on the ticket branch `{branch}`")
    keep = Path(os.environ.get("COGA_TASK_DATA_DIR") or os.environ["TMPDIR"]) / "rebase-saved"
    keep.mkdir(parents=True, exist_ok=True)
    saved: list[tuple[str, Path]] = []
    for rel in paths.carried:
        file = paths.top / rel
        if not file.is_file():
            continue
        copy = keep / rel.replace("/", "__")
        shutil.copy2(file, copy)
        saved.append((rel, copy))
    run_op(f"git fetch {remote} {base}", "fetch", "--quiet", remote, base)
    for rel, _ in saved:
        if tracked_in_head(rel):
            out("checkout", "HEAD", "--", rel)
    try:
        run_op(f"git rebase {remote}/{base}", "rebase", f"{remote}/{base}")
    except TicketGitError as exc:
        kept = ", ".join(f"{rel} -> {copy}" for rel, copy in saved)
        raise TicketGitError(
            f"{exc}; the live copies are kept ({kept}). Finish or abort the "
            "rebase, then copy them back over the files."
        ) from exc
    for rel, copy in saved:
        shutil.copy2(copy, paths.top / rel)
        copy.unlink()
    print(f"{PREFIX}: rebased `{branch}` onto `{remote}/{base}`", file=sys.stderr)
    return 0


def main(argv: list[str]) -> int:
    if argv not in ([], ["rebase"]):
        print("usage: run.py [rebase]", file=sys.stderr)
        return 2
    try:
        return rebase() if argv else enter()
    except TicketGitError as exc:
        print(f"{PREFIX}: {exc}", file=sys.stderr)
        return 1
    except (OSError, KeyError, ValueError, TaskFileError) as exc:
        print(f"{PREFIX}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
