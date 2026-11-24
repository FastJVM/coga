---
name: coga-dev/internals
description: Index of the concurrency and publication guarantees behind coga launch, megalaunch, the recurring runner, and open-pr, with one line and a link per internals page; attaching it loads only this index, not the child pages.
---

# Internals

The kernel operates on local ticket and audit files. Read the
[code map](../codebase/SKILL.md) for module owners.

- [Agent spawn](agent-spawn/SKILL.md) covers prompt and agent execution.
- [Assist attribution](assist-publication/SKILL.md) covers owner-held sessions.
- [Blackboard I/O](blackboard-io/SKILL.md) covers ticket-body boundaries.
- [Audit log](spool-merge/SKILL.md) covers append and retention.
- [Recurring admission](recurring-admission/SKILL.md) covers scheduled dispatch.
