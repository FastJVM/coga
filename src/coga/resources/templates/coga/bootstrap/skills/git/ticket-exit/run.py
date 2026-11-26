"""`exit` step script for branch workflows.

Coga runs this after every step change (`coga bump`, `coga mark done|canceled`,
`coga block`) of a ticket whose workflow declares `exit: git/ticket-exit`:

1. On the ticket branch, commit everything except `<coga root>/tasks/**` and
   `<coga root>/log.md`, and push the branch.
2. Switch back to the base, carrying the live ticket and log bytes.
3. Publish only this ticket and its log lines: one commit on
   `<remote>/<base>`, built in a temporary index, pushed as
   `<oid>:<base>`; fast-forward the local base when possible.

It stops at the first Git failure, a rejected push included, with Git's
message and local state intact. Nothing retries.
"""

from __future__ import annotations

import os
import sys

from coga.taskfile import TaskFileError
from coga.ticket import Ticket, TicketError
from coga_edge.ticket_git import (
    TicketGitError,
    TicketPaths,
    current_branch,
    dev_record,
    fast_forward_base,
    git,
    out,
    publish_ticket,
    ref_tip,
    require_unstaged_carried_paths,
    run_op,
    switch_carrying,
    ticket_paths,
)

PREFIX = "ticket-exit"


def handoff_message(slug: str, paths: TicketPaths) -> str:
    try:
        parsed = Ticket.read(paths.ticket)
        step = parsed.current_step()
    except (OSError, UnicodeError, TicketError):
        return f"{slug}: step handoff"
    if step is not None:
        return f"{slug}: handoff at {step['name']}"
    return f"{slug}: handoff ({parsed.status})"


def commit_code(paths: TicketPaths, slug: str) -> None:
    code_paths = (
        "--", ":(top)", f":(top,literal,exclude){paths.tasks_rel}",
        f":(top,literal,exclude){paths.log_rel}",
    )
    run_op(
        "git add -A (without ticket state)", "-C", str(paths.top), "add", "-A",
        *code_paths,
    )
    staged = git("-C", str(paths.top), "diff", "--cached", "--quiet",
                 *code_paths, check=False)
    if staged.returncode == 1:
        run_op("git commit", "-C", str(paths.top), "commit", "--only", "-q", "-m",
               handoff_message(slug, paths), *code_paths)
    elif staged.returncode:
        raise TicketGitError(f"git diff --cached --quiet failed: {staged.stderr.strip()}")


def exit_() -> int:
    paths = ticket_paths()
    slug = os.environ["COGA_TASK_SLUG"]
    if not paths.ticket.is_file():
        raise TicketGitError(f"ticket {paths.ticket_rel} is missing; nothing to publish")
    start = current_branch()
    if not start:
        raise TicketGitError("HEAD is detached; nothing was committed or published")

    fields = dev_record(paths.ticket)
    branch = fields.get("branch")
    if branch:
        base, remote = fields.get("base"), fields.get("remote")
        if not base or not remote:
            raise TicketGitError(
                f"`## Dev` records branch: {branch} without base: or remote:"
            )
        if start == branch:
            require_unstaged_carried_paths(paths)
            commit_code(paths, slug)
            # Push only what the remote lacks: after a merge the host may have
            # deleted the branch, and a no-op push would recreate it.
            if ref_tip(f"refs/heads/{branch}") != ref_tip(f"refs/remotes/{remote}/{branch}"):
                run_op(f"git push {remote} {branch}", "push", "-u", "--", remote,
                       f"refs/heads/{branch}")
            switch_carrying(paths, base, "--", base)
            print(f"{PREFIX}: pushed `{branch}` and returned to `{base}`", file=sys.stderr)
        elif start != base:
            raise TicketGitError(
                f"HEAD is on `{start}`, neither the ticket branch `{branch}` nor "
                f"its base `{base}`; nothing was committed or published"
            )
    else:
        # Not entered yet (an owner step before any launch): the ticket
        # lives on the current branch, which is its base.
        base = start
        remote = out(
            "for-each-ref", "--format=%(upstream:remotename)", f"refs/heads/{start}"
        ) or "origin"

    commit = publish_ticket(paths, slug=slug, remote=remote, base=base)
    if commit is None:
        print(f"{PREFIX}: `{remote}/{base}` already has this ticket's state", file=sys.stderr)
        return 0
    fast_forward_base(paths, base, commit)
    print(f"{PREFIX}: published {paths.task_rel} to `{remote}/{base}`", file=sys.stderr)
    return 0


def main(argv: list[str]) -> int:
    if argv:
        print("usage: run.py", file=sys.stderr)
        return 2
    try:
        return exit_()
    except TicketGitError as exc:
        print(f"{PREFIX}: {exc}", file=sys.stderr)
        return 1
    except (OSError, KeyError, ValueError, TaskFileError) as exc:
        print(f"{PREFIX}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
