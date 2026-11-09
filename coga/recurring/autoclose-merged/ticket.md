---
{}
---
<!-- coga:recurring-state -->

<!-- coga:blackboard -->

This blackboard persists across every run of this recurring task. The
`autoclose` sweep keeps no durable state here - every run's output
is the tickets it marks done and the live Done posts they produce.

A run that disposed of or preserved a feature checkout appends a
`## Autoclose Sweep: retire follow-ups` section to the *period task's*
blackboard for that firing (`autoclose._report_retire_followups` writes
`COGA_TASK_BLACKBOARD`), not here. That section is a per-run report the
scheduler deletes with the period task. The durable worklist is the sibling
file `retires.md` next to this `ticket.md`: the same run records each
preserved closure there keyed by slug, every run re-judges the open entries
and drops those whose branch is gone and whose worktree is gone or is the
primary checkout, and
`coga retire <slug>` drops its own once it has disposed of the checkout. A
sweep that touched no checkout and discharged nothing writes nothing.

A run that closes a PR with an unanswered review thread also appends a
`## Autoclose Sweep: unanswered review threads` section to the period task
blackboard (stdout for hand runs) and posts a Slack summary. The closure
audit line names the thread locations durably.
