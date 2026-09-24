---
name: coga/task-grouping
description: Related Coga tickets are grouped by plain directories; directory documentation has no ticket lifecycle and is not a parent task.
---

# Group related tickets with directories

Owner clarification, 2026-09-09: Coga groups related work in plain directories.
There is no parent-ticket concept for a group. Each actual ticket has its own
scope, workflow, assignee, and lifecycle; the containing directory has none.

```text
coga/tasks/v1/updater/3-auto-update/
  README.md
  1-download-and-verify.md
  2-startup-upgrade-probe.md
  3-manual-hook-updates.md
```

`README.md` can explain the group, shared design, and how its tickets fit
together. Coga excludes that filename from ticket discovery. A reusable domain
decision may instead live in a named context. A README does not compose into a
ticket launch automatically; each ticket must identify the parts it needs.

Distinguish a grouping directory from a directory-form task:

- `tasks/group/one.md` is one task in a group of related tasks.
- `tasks/one/ticket.md` is one task with room for attachments or `ticket.py`.
  Discovery stops at that task directory; nested tickets are not discovered.

Do not retain or invent an umbrella ticket just to give a directory an owner,
status, completion checkbox, or approval gate. Do not put `ticket.md` in a
grouping directory or add parent/child frontmatter fields. Dependencies and
launch gates name exact actual tickets or a checkable decision section; a
directory cannot become `done`.

When splitting work, allocate every remaining decision and deliverable to a
real ticket, preserve shared material in the README or a context, and update
live references and launch gates before retiring the superseded ticket. The
owner's approval to split work does not imply that the resulting tickets'
product designs have been approved for implementation.

This clarification came from the updater review: the assistant proposed
keeping `3-auto-update` as a parent ticket, and the owner corrected the model
to a directory containing actual tasks. The owner reduced the updater to two
tickets on 2026-09-10 and added a third (`2-startup-upgrade-probe`) on
2026-09-11; the grouping rule is unchanged. The Coga follow-up is
tracked in
`coga/prevent-parent-ticket-assumptions-during-task-spli`.
