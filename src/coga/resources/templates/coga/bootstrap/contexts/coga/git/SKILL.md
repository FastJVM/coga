---
name: coga/git
description: Work with tickets on ordinary Git branches; ticket state lives on the base.
---

# Working with Git

Coga writes the ticket and the audit log in the current checkout. You can run
Coga in a directory without Git. A workflow can declare `enter:` / `exit:`
step scripts ([coga/workflows](../workflows/SKILL.md#step-scripts)); the
packaged branch workflows declare `git/ticket-enter` and `git/ticket-exit`,
which put code on a ticket branch and ticket state on the base
([branch step scripts](#branch-step-scripts)). Use ordinary `git pull`,
`git push`, and `gh` to share work, and `git branch -d` or GitHub to clean up
merged branches.

## Checkout policy

Use ordinary Git branches in the checkout where the work started. If a
branch switch would disrupt work in progress, coordinate with the person using
the checkout before switching. A [recurring run](../recurring/SKILL.md#checkout-policy)
is the only Coga workflow that can use a disposable clone or linked Git worktree.
The branch step scripts switch between the base and the ticket branch, so
Git's own refusal to switch over conflicting local changes applies.

## Ticket Git record

Use one line per field in the blackboard's `## Dev` section. Each workflow step
updates its own fields and preserves other lines.

```text
branch: <name>
base: <branch>
remote: <name>
reviewed: <full commit OID>
pr: <full /pull/ URL>
```

`git/ticket-enter` records branch, base and remote. `code/peer-review` records
the final reviewed head. `git/push-and-open-pr` records the PR URL. Workflow
gates read branch and PR from this record. If a needed field is missing or
disagrees with Git or GitHub, stop and resolve the discrepancy.

## Branch to merge

Code lives on the ticket branch; the ticket and its `coga/log.md` lines live
on the base. Commit implementation and review changes without
`coga/tasks/**` or `coga/log.md`, so a PR carries no ticket state and another
ticket's edits never block it. The `exit` script publishes the ticket at every
step change, so `coga status` on a fresh clone of the base shows it current.

The PR script pushes the branch, opens or updates the PR, records the URL and
bumps as its last action. The owner reviews and merges the PR; the final bump
publishes `status: done` to the base, before or after the merge. The
agent-merge workflow merges and then bumps in its merge script.

Before handing off code, reconcile with the base: run the local or packaged
`git/ticket-enter/run.py rebase` with the ticket environment, which rebases
the branch onto `<remote>/<base>` and keeps the live ticket and log across it.
Inspect staged, unstaged and committed work separately. Preserve unique
changes on both sides. If Git reports a conflict, a failed push, or
unexpected dirt, keep local state, report the failure, and resolve it before
retrying.

## Branch step scripts

`git/ticket-enter` runs before each step starts. It switches to the recorded
branch, carrying the live ticket and log bytes across the switch: the copy in
the checkout is the newest one.

- With no `branch:` under `## Dev`, it creates `coga/<slug-part>` from `HEAD`
  (a suffixed name when taken) and records `branch:`, `base:` (the starting
  branch) and `remote:` (the base's upstream remote or `origin`).
- Already on the recorded branch (a session ended without a step change), it
  does nothing.
- It refuses a detached `HEAD`, a `branch:` without `base:` or `remote:`, a
  recorded branch that exists neither locally nor as `<remote>/<branch>`, and
  local and remote-tracking tips that have diverged. A refusal fails the step
  before any agent starts.

`git/ticket-exit` runs once after `coga bump`, `coga mark done|canceled` and
`coga block` have written the ticket:

1. On the ticket branch, it commits everything except `coga/tasks/**` and
   `coga/log.md` as `<slug>: handoff at <step>`, pushes the branch when the
   remote lacks its tip, and switches back to the base with the live ticket
   and log. Other tickets' staged changes stay staged. A staged change to
   the carried ticket or log stops the switch so you can resolve it. On the
   base, or with no branch recorded, it only publishes. On any other branch
   it refuses.
2. It publishes one commit on `<remote>/<base>`, built in a temporary index
   from that ref: this ticket's files and its own new `coga/log.md` lines.
   For a directory-form task it includes tracked and non-ignored attachments
   and leaves nested tickets alone. Other tickets' edits and unpushed local
   base commits are never published.
3. It fast-forwards the local base when it can, and otherwise says so.

`run.py rebase` rebases the ticket branch onto `<remote>/<base>`. It saves the
live ticket and log under the ticket's data directory, restores the tracked
copies so Git sees a clean tree, rebases, and writes them back. On a conflict
it leaves the rebase and names the saved copies.

Both scripts stop at the first Git failure, a rejected push included, with
Git's message and local state intact; nothing retries. A failed `exit` keeps
the step change written locally and makes the command exit non-zero; launch
and megalaunch stop before the next step until a later `exit` succeeds.
Recovery is manual: finish the push or switch with Git, then bump, block or
mark again, or rerun the script with the ticket environment.

Tickets frozen before these scripts existed (an `open-branch` step or
`git: ticket-branch`) are rewritten by
`python -m coga_edge.migrate_step_scripts`: it reports by default and
publishes the rewrites to the base with `--apply`; `--path <ticket>` rewrites
one live copy in place.

## Shared audit log

Lifecycle commands append to `coga/log.md`. The scaffold sets `merge=union`
so both sides of an append conflict survive; the `exit` script adds only its
ticket's new lines to the base's log. Log compaction snapshots the log and
preserves bytes appended before its final read. An append between that read
and the atomic replacement can still be lost. Keep compaction and routine
writes apart when possible.
