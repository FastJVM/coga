---
title: Collapse recurring period tasks to one dir per template under tasks/recurring/,
  period in blackboard
status: active
mode: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
step: 1 (design)
---

## Description

Change recurring tasks from **one fresh directory per period** to **one
persistent directory per template**, living under a `tasks/recurring/` group,
with the current period tracked in the task's **blackboard** instead of the
slug.

- **Today:** `tasks/recurring-dream-2026-W21/`, `tasks/recurring-dream-2026-W22/`,
  … — a new directory each period; the `recurring-` prefix is the identity
  marker and the `<period>` is the dedup key, both baked into the slug.
- **Target:** `tasks/recurring/dream/` — one directory per template. The
  `recurring/` group dir carries the namespacing the prefix used to; the
  blackboard records which period the run is currently servicing; the
  append-only `log.md` accumulates period history (logs are never composed
  into prompts, so unbounded growth is fine).

### Why

The `recurring-` slug prefix is purely a namespace marker, and the `<period>`
suffix is purely a dedup/identity key — both encode in the slug what now has
better homes: the group directory (namespace) and the blackboard/log (period
state). Wins: recurring runs grouped in `relay status`, a cleaner layout, and
period state where state belongs. Uses the group-qualified-slug machinery from
\#350.

### Scope — slug-encoded identity moves out of the slug

Both the prefix and the period are string-matched as identity/dedup keys in
`src/relay/recurring.py`. All of this moves to group-membership +
blackboard/log:

- `_recurring_slug` (~:689) and the `slug_override` passed at `:608` in
  `scaffold_template` — slug becomes the template-scoped `recurring/<name>`;
  no prefix, no period.
- `_period_already_scaffolded` (~:727) — the get-or-create dedup. Currently
  reads the template `log.md` for `scaffolded <slug>`; the period key now
  comes from blackboard/log state, not the slug.
- `_live_task_for_template` (~:700, prefix at :714) — "one live task per
  template" simplifies to one dir, BUT the prior-period **orphan resume**
  semantics need rethinking: there's no longer a separate prior-period
  directory to find — it's the same dir, advancing to a new period.
- `is_recurring_period_task` (~:361) — `relay status` peeling generated vs
  human tasks; re-derive from the group, not the prefix.
- `_reap_debug_orphans` + `is_debug_slug` — `-dbg-` debug runs intentionally
  omit the `recurring-` prefix today; preserve the debug/real distinction
  under the new shape.
- `relay/period-task` context — already tells a period run that persistent
  state lives in the parent's blackboard; this change overlaps with / may
  simplify that mechanism. Review and reconcile.

### Open design questions (resolve in the design step)

- **Per-period isolation.** Today each period gets its own blackboard + log.
  With one persistent dir, does each new period reset or section the
  blackboard? Confirm Dream/REM don't rely on a clean per-run blackboard.
- **Orphan resume across periods** — define the new "a prior period's run
  never finished" detection now that it's not a distinct directory.
- **Migration** of existing per-period directories, deleted-ticket log
  history, and period ledgers — migrate, or support both shapes during
  transition.

### Done-when / housekeeping

- Sync both the live `relay-os/` copy and the packaged
  `src/relay/resources/templates/relay-os/` copy for any touched
  template/context.
- Update the `relay/architecture` and `relay/cli` contexts in the same PR —
  both currently document the `recurring-<name>-<period>` slug shape and the
  prefix-based "one live task per template" identity (CLAUDE.md: behavior
  change ⇒ update the matching context in the same PR).

## Context

