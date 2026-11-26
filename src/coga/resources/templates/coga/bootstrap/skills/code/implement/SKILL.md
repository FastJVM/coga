---
name: code/implement
description: Implement and verify the change on the ticket branch.
---

1. Read the ticket, its contexts and the recorded Git fields under `## Dev`.
   Follow `coga/git`. On an older frozen snapshot without `branch:`, run the
   local or packaged `git/open-branch/run.py --no-bump` with the ticket
   environment. Keep the current `implement` step open. If a branch is
   already recorded, switch to it if needed and stop if Git refuses.
   When adding codebase facts to `## Context`, cite the module and symbol
   and describe how it affects the ticket.
2. Implement the requested behavior and update its canonical documentation.
   Use repo-native tests and supporting fixtures. Run the repo's required
   checks and retain their actual commands and results.
3. Commit the implementation, without `coga/tasks/**` or `coga/log.md`:
   ticket state lives on the base, and the workflow's `exit` script
   publishes it there. Reconcile with the base: on a workflow with
   `enter: git/ticket-enter`, run the local or packaged
   `git/ticket-enter/run.py rebase` with the ticket environment, which keeps
   the live ticket across the rebase; otherwise fetch the recorded remote
   and rebase. Preserve unique changes and repeat checks after rebasing.
4. Record the actual implementing agent, tested head, diff base, check
   receipts and review-depth rationale in the live ticket's `## PR`.
   Follow `coga/pr-publication/preparation` for the schema. Name any
   limitations, deviations and remaining work in the handoff.
5. Bump when the work and handoff are ready.

If every requirement has already landed, record evidence for each under
`## Already satisfied` and close with `coga mark done`. File any remaining
obligations first. Resolve ambiguous findings through session conduct.
