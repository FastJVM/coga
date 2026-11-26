---
name: git/ticket-exit
description: Step-change script for branch workflows; commit and push the code branch without ticket state, return to the base, and publish only the current ticket to it.
---

A workflow that declares `exit: git/ticket-exit` makes Coga run this skill's
`run.py` after every step change: `coga bump` (including the final bump to
`done` and a human rewind), `coga mark done`, `coga mark canceled` and
`coga block`. Do not list it as a workflow step. `coga/git`
("Ticket branches") owns the contract.

1. On the recorded ticket branch, it stages everything except
   `<coga root>/tasks/**` and `<coga root>/log.md`, commits
   `<slug>: handoff at <step>` when anything is staged, and pushes the
   branch with upstream set. Ticket state never lands on the code branch.
2. It switches back to the recorded base, carrying the live ticket and log
   bytes across the switch.
3. It fetches the base and builds one commit on `<remote>/<base>` in a
   temporary index holding this task's files and `log.md` as the base's log
   plus this ticket's local lines it lacks, then runs
   `git push <remote> <oid>:<base>`. It fast-forwards the local base when it
   is an ancestor and warns otherwise. Other tickets' files and unpushed
   local base commits are never published.

On the base with no branch recorded (an owner step before any launch), it
only publishes. On any other branch it refuses. It stops at the first Git
failure, a rejected push included, with Git's message and local state
intact; the lifecycle write has already landed locally. The next `exit`
republishes the whole task file.
