---
title: Dedup duplicate draft tickets
status: active
mode: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
- relay/roadmap
skills: []
workflow:
  name: direct/body
  steps:
  - name: execute
    skills:
    - direct/body
    assignee: agent
step: 1 (execute)
---

## Description

The draft backlog (60+ tickets) has accumulated duplicate concept-capture
stubs. Consolidate them so the board is legible before planning later roadmap
waves. This is the Wave 0 "dedup pass" from `relay/roadmap`.

**Destructive + propose-then-confirm.** Deletion is `relay delete` (recoverable
via `git restore`, no Slack broadcast). Before deleting any ticket: read the
target, confirm it is genuinely covered by the canonical ticket, and **get
explicit human approval for the delete set** — do not delete on your own
judgment. If a stub's title hints at intent the canonical ticket misses, fold
that intent into the canonical ticket's body first, then delete the stub.

Discovery is already done (2026-06-15 orient session). Re-verify each target is
still an empty stub / still overlaps before acting — the board may have moved.

### Confirmed safe (empty stubs fully covered by a canonical ticket)

| Delete (empty stub) | Covered by |
|---|---|
| `rename-workfflow` | `rename-workflow-primitive-to-playbook` |
| `change-workflow-dname` | `rename-workflow-primitive-to-playbook` |
| `uncommitted-stuff-not-handled` | `clean-uncommitted-work` |
| `autocleanup-worktree-branche` | `use-worktree-when-starting-a-dev-task` (its scope half 2 is cleanup) |

Caveat to check: `change-workflow-dname` ("dname") is cryptic — could mean
display-name vs directory-name vs the primitive rename. Confirm with the owner
it is not a distinct idea before deleting.

### Needs an owner decision (both have real content)

1. **Automerge-trigger pair — same work.** `drift-status-still-calls-auto-bump-
   merged-after-mo` (decision framing: "which automerge triggers does Relay
   ship?") and `retire-standalone-relay-automerge-triggers-recurri` (the action:
   "make the recurring sweep the sole trigger"). Recommend: keep
   `retire-standalone…`, fold the open decision from `drift-status…` into it,
   delete `drift-status…`. NOTE: `automerge-ticket` [active] is a *different*
   feature (`code/optimistic-merge`) — not a dupe, leave it.
2. **`sync-dirty-files`** (empty stub, ambiguous) — could mean "commit stranded
   dirty work" (→ fold into `clean-uncommitted-work`) or "sync dirty files
   across checkouts" (→ overlaps `sync-support-files-and-bare-ticket-shim`).
   Owner decides: fold or leave.

### Not duplicates (leave alone)

`improve-prompt-for-relay-launch` vs `improve-prompt-for-relay-ticket` —
different targets; both empty but distinct.

### Steps

1. Re-verify each candidate is still an empty stub / still overlaps.
2. Present the final delete + merge set to the owner; get explicit approval.
3. For any merge, fold unique intent into the canonical ticket first.
4. `relay delete` the approved set.
5. Record what was deleted/merged on the blackboard.

## Context

See `relay/roadmap` for where this sits (Wave 0). Deletion of a task directory
runs through `bootstrap/delete-task`; the git history is the audit trail and the
only recovery path, so confirm before removing. Per the global rules and base
prompt, anything destructive is confirm-first — the human is present in this
interactive ticket.
