---
slug: bumppy-requires-exactly-two-agents
title: bumppy-requires-exactly-two-agents
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
workflow: code/with-review
secrets: null
---

## Description

`resolve_other_agent` in `src/coga/bump.py` resolves the `other-agent` role
token by taking the single `[agents.*]` entry that is not the ticket's own
`agent:`. It raises `AssigneeResolutionError` unless exactly one candidate
remains — so the token only works in a repo with exactly two configured agent
types. Adding a third (Zach hit this adding a local-llm agent during testing)
makes every `other-agent` resolution fail loud.

Give `other-agent` an explicit way to name the peer: a per-agent `peer` key in
`coga.toml`, e.g. `[agents.claude] peer = "codex"`. When the ticket's agent
declares a `peer`, resolution returns it. When it doesn't, fall back to today's
exactly-one inference, so two-agent repos keep working with no config change
and no migration.

## Context

### The bug is live, not hypothetical

The original report said nothing uses `other-agent` today. That is true only of
repo-local `coga/workflows/`. The bundled batteries do use it:

- `src/coga/resources/templates/coga/bootstrap/workflows/code/with-review.md` —
  `peer-review` step, `assignee: other-agent`. This is the default workflow for
  code changes in this repo.
- `src/coga/resources/templates/coga/bootstrap/workflows/docs/with-review.md` —
  same shape.

Roughly 25 live tickets under `coga/tasks/` carry `assignee: other-agent`
frozen into their workflow snapshot. Role tokens resolve at bump time against
current config, not at freeze time, so the day a third `[agents.*]` lands in
`coga/coga.toml`, those tickets fail on the bump into `peer-review` —
mid-workflow, after the implement step's work is already done.

`coga/coga.toml` currently declares exactly two agents: `[agents.claude]` and
`[agents.codex]`. That is the only reason this is not already broken.

### Call sites

Four places resolve the token; all four must keep working:

- `coga.bump.resolve_other_agent` — the resolver itself.
- `coga.bump.resolve_step_assignee` — dispatches `other-agent` to it.
- `coga.commands.bump.bump` — resolves the incoming step's role on a forward
  bump.
- `coga.create.create_task` — resolves step 1's role at activation when
  `--workflow` is passed.

`VALID_ASSIGNEE_ROLES` lives in `src/coga/workflow.py` and is the shared
vocabulary (`owner` | `human` | `agent` | `other-agent`); the token set itself
does not change.

### Design constraints

- **No silent guessing.** The current code fails loud on ambiguity, and that is
  correct behavior worth preserving. A three-agent repo with no `peer` declared
  must still raise `AssigneeResolutionError` with an actionable message naming
  the fix (`add peer = "<type>" to [agents.<agent>]`), not pick arbitrarily.
- **Two-agent repos need zero config.** The existing inference stays as the
  fallback when `peer` is unset. This is what makes the ~25 frozen snapshots a
  non-issue.
- **A declared `peer` must name a configured agent type.** Validate it and fail
  loud on a typo rather than resolving to a nickname no agent answers to.
- Config parsing lives in `src/coga/config.py`; the new key rides the existing
  `[agents.*]` table alongside `cli`, `file`, `mode`, and `discussion`.

### Scope

In scope:

1. The `peer` config key, parsed and validated in `coga.config`.
2. `resolve_other_agent` prefers a declared `peer`, falls back to inference,
   fails loud otherwise. All four call sites above keep working.
3. A `coga validate` check that flags a workflow (repo-local or frozen on a
   ticket) declaring `other-agent` that cannot resolve against current config —
   so the failure surfaces before a bump hits it mid-workflow. The existing
   role-token check sits in `coga.validate` next to its `VALID_ASSIGNEE_ROLES`
   use; extend around there.
4. Docs and contexts updated in the same PR, per CLAUDE.md. Touch points:
   `docs/concepts.md` (the assignee-role and `[agents.*]` sections),
   `coga/contexts/coga/architecture/SKILL.md` (its `other-agent` resolution
   paragraph), and `coga/workflows/_template.md`. Every one of these has a
   packaged twin under `src/coga/resources/templates/coga/` — update both
   copies.

Out of scope:

- **Do not rewrite the frozen `other-agent` snapshots on existing tickets.**
  They are correct as-is and must keep resolving under the new rule. That they
  need no migration is an acceptance criterion, not work to do.
- **Do not edit `coga/coga.toml` or `coga.local.toml`** to seed `peer` keys.
  The fallback covers this repo's two-agent config; the owner adds `peer` when
  a third agent lands.
- Changing the `VALID_ASSIGNEE_ROLES` vocabulary or adding new role tokens.

### Testing

Tests live in `tests/`, named after the module under test — `tests/test_bump.py`
for the resolver, plus the config and validate suites. Cover: two agents with no
`peer` (inference, unchanged); three agents with `peer` declared; three agents
without `peer` (raises, message names the fix); `peer` pointing at an
unconfigured type; and `peer` set on a two-agent repo (explicit beats
inference). Run `python -m pytest` and `coga validate --json`.

### Related

`coga/tasks/activation-does-not-resolve-step-1-s-assignee-role.md` touches the
same `create.py` resolution path — read it before editing `create_task` so the
two changes don't collide.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
