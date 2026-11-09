---
{}
---
<!-- coga:recurring-state -->

<!-- coga:blackboard -->

This blackboard persists across every run of this recurring task. The
`branch-sweep` sweep keeps no durable state here. It is `scope: clone`, so a
run creates no period task and has no period blackboard: its output is the
branches it deletes or reports as skipped, written as a `## Branch Sweep`
report to this clone's `.coga/recurring-clone/branch-sweep.log` and the run
record. `coga recurring` records the serviced daily period in the clone-local
ledger under the primary checkout's `.coga/`, not in `coga/log.md`.
