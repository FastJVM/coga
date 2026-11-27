---
name: git/ticket-enter
description: Enter the ticket branch with the ticket files and audit log. Run `run.py rebase` to rebase the branch onto its base.
---

A workflow that declares `enter: git/ticket-enter` makes Coga run this
skill's `run.py` (no argument) before each step it starts: the first step of
a launch, each step the supervisor chains, and each megalaunch step. Do not
list it as a workflow step. See `coga/git` ("Branch step scripts").

- With a `branch:` recorded under `## Dev`, it switches there (tracking
  `<remote>/<branch>` when only the remote ref exists). Already on it, it
  does nothing. It refuses a detached `HEAD`, an incomplete record, a
  missing branch and diverged local and remote tips.
- Without one, it creates `coga/<slug-part>` (a suffixed name when taken)
  from the current `HEAD` and records `branch`, `base` (the current branch)
  and `remote` (its upstream remote, or `origin`).
- The live ticket files and `coga/log.md` accompany the switch. Git names
  any other modified file that blocks the switch.

## Rebase onto the base

On the ticket branch the live ticket is always modified, so a plain rebase
refuses. Run the local or packaged `git/ticket-enter/run.py rebase` with
the ticket environment, from the repository root. The script fetches, saves
the live ticket files and log under `$COGA_TASK_DATA_DIR/rebase-saved/`, and
restores the tracked copies before rebasing onto `<remote>/<base>`. It
restores the live files after a successful rebase. On a conflict, finish or
abort the rebase and restore the files from the path in the error message.
