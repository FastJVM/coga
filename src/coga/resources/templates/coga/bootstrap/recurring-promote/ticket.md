---
title: Promote a task to a recurring template
---

## Description

`coga promote-recurring` runs this stateless script ticket without an agent.
The default alias expands to `coga launch bootstrap/recurring-promote --`.
The trailing `--` passes command options to the script.

`coga promote-recurring <task> --schedule "<cron>" [--name <name>]` moves a task to `coga/recurring/<name>/ticket.md` —
also the "recurring from creation" path (`coga create`, write the body,
promote). The body above the fence travels verbatim; the blackboard resets to
cross-run state. `status`, `step`, `period_generation` and `launch_generation` drop; a frozen workflow
collapses to its name (none stays none); `title`, `owner`, `agent`, `contexts`
(minus `coga/period-task`), `secrets` and extension fields pass through;
ticket `skills:` drop with a warning. Directory-form attachments are copied
except `.state-snapshot.json`. It refuses: an existing destination, a bad cron
or name (checked before anything moves), an unresolvable workflow, and an
`in_progress` or `blocked` task. The template is reloaded before the source is
deleted.

The command refuses a name already used by an effective local or bundled
definition. It records a promotion audit after removing the source and
publishes the source deletion, template and audit together. With Git sync
disabled, the move and audit are local.

With Git sync enabled, a directory-form task with a symlink anywhere in it is
refused with exit 2 before anything moves, because guarded publication refuses
symlinks. Gitignored attachments are copied but are not required to publish.

Exit 75 means local changes need reconciliation. A cleanup or deletion
failure names the affected paths. A publication refusal keeps the local move
for recovery.
Inspect the named paths and audit log before retrying publication. See
[state publication](context:coga/state-publication).

To customize the procedure, copy this directory with `ticket.md`, `ticket.py`
and `promotion.py` into your workspace's `bootstrap/recurring-promote/`.
The complete local directory takes precedence over the installed definition.
