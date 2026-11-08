---
{}
---
<!-- coga:recurring-state -->

<!-- coga:blackboard -->

This blackboard persists across every run of this recurring task. A run reads
it at the start to pick up where the last run left off, and updates it at the
end with whatever the next run needs.

Dream's per-period task is disposable after it is marked done, but Dream does
not delete itself mid-run. Dream keeps no durable state here — every finding
ends in a PR, a draft ticket, or a recorded marker instead. `coga recurring`
keeps Dream's serviced-period record in the repo-global `coga/log.md`;
`log.md` keeps retained human history; [trim-log](https://github.com/FastJVM/coga/blob/main/coga/recurring/trim-log/ticket.md) preserves histories of tickets still on disk.
