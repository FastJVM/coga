---
name: dev/checkouts/reconciliation
description: Main as the shared source of truth for all agent edits, freshness checkpoints, preserving unique work during reconciliation, and when conflicts need human judgment.
---

# Reconcile work with moving main

The configured remote control branch (`origin/main` by default) is the source of
truth for shared repository state. A local checkout and the launch prompt are
snapshots; expect main to advance during a session. This applies to all agent
edits, including code, documentation, contexts, skills, workflows, tickets,
and bootstrap or ad-hoc work. A fresh launch does not guarantee a fresh handoff.

## Freshness checkpoints

Before editing, fetch current main and inspect changes relevant to the work,
including its governing instructions. Before publishing or handing off edits,
fetch again and reconcile against that tip. Read-only work needs no merge;
qualify conclusions tied to an older revision if relevant files changed.
Git-disabled or remote-less work cannot claim remote freshness; report that
limitation when handing off changes.

## Preserve both sides

Reconciliation preserves main's newer work and the still-needed local intent:

- For committed branch work, merge or rebase current main using the owning
  workflow's procedure ([code branch procedure](../SKILL.md#start-work-end)).
  Resolve straightforward conflicts yourself; a clean Git merge still needs
  inspection for changes in meaning or assumptions.
- For uncommitted edits or a stale publication refusal, inspect the local
  diff and main's intervening changes first. Preserve unique edits in a patch
  or file copy before replacing any working file, including untracked files.
  Take main's version and reapply only the changes still needed. If the work
  already landed, prove that from history and content before dropping the
  duplicate. Keep canonical and packaged copies consistent.
- Refresh the ticket from control before writing a handoff, preserving any
  unpublished notes and respecting CLI-owned lifecycle fields. Never replay
  a transition merely because its publication failed; use the publication
  recovery described in the [handoff procedure](../SKILL.md#in-a-launched-session).

## Verify and escalate

Inspect the combined diff and run checks appropriate to the affected work
after reconciliation. If publication reports that main moved again, repeat
the comparison against the new tip. Normal movement is not itself a blocker.
Escalate per session conduct when intent conflicts, ownership is unclear, or
access prevents reconciliation; identify the conflicting changes and the
decision or capability needed. Never choose main's entire file blindly,
discard unique work to silence sync, or bypass a publication or lifecycle
guard. These rules do not authorize taking over another task's dirty checkout
or crossing a human approval gate.
