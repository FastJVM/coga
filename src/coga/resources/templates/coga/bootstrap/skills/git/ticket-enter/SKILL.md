---
name: git/ticket-enter
description: Step-start script for branch workflows; switch to (or create) the ticket branch, carrying the live ticket and log. `run.py rebase` rebases the branch onto its base.
---

A workflow that declares `enter: git/ticket-enter` makes Coga run this
skill's `run.py` (no argument) before each step it starts: the first step of
a launch, each step the supervisor chains, and each megalaunch step. Do not
list it as a workflow step. `coga/git` ("Ticket branches") owns the contract.

- With a `branch:` recorded under `## Dev`, it switches there (tracking
  `<remote>/<branch>` when only the remote ref exists). Already on it, it
  does nothing. It refuses a detached `HEAD`, an incomplete record, a
  missing branch and diverged local and remote tips.
- Without one, it creates `coga/<slug-part>` (a suffixed name when taken)
  from the current `HEAD` and records `branch`, `base` (the current branch)
  and `remote` (its upstream remote, or `origin`).
- The live ticket and `coga/log.md` cross the switch: their bytes are saved,
  restored to `HEAD`, and written back after `git switch`. Any other
  modified file that blocks the switch fails it with Git's message.

## Rebase onto the base

On the ticket branch the live ticket is always modified, so a plain rebase
refuses. Run the local or packaged `git/ticket-enter/run.py rebase` with
the ticket environment, from the repository root. It saves the live ticket and log to `$COGA_TASK_DATA_DIR/rebase-saved/`,
restores them to `HEAD`, fetches, runs `git rebase <remote>/<base>`, and
copies the saved files back. There is no `--autostash` and no merge of the
ticket. On a conflict it stops with the saved copies kept and named; finish
or abort the rebase, then copy them back by hand.
