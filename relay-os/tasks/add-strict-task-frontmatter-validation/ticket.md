---
title: Add strict task frontmatter validation
status: done
mode: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts:
- relay/architecture
- relay/principles
- relay/codebase
- relay/current-direction
- relay/project-stage
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement-and-pr
  - name: review
    skills: []
---

## Description

Relay tasks are edited by agents, humans, and CLI commands. Today
`relay validate` catches some repo drift, but the task frontmatter schema is
still too loose: required keys are implicit, `skill` vs `skills` is not
settled in the validator, and commands that mutate a task do not all perform a
task-scoped validation pass before reporting success.

Implement strict task validation and wire it into every Relay-owned task edit.
The goal is to fail at the edge of the edit, while the bad task is still in
front of the human or agent, instead of letting malformed frontmatter drift
until launch or Dream.

Canonical normal task frontmatter after this change:

```yaml
title: Add strict task frontmatter validation
status: draft
mode: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts: []
skills: []
workflow: null
```

`contexts:`, `skills:`, and `workflow:` are mandatory keys. `contexts` and
`skills` are lists and may be empty. `workflow` is either `null` or a frozen
workflow mapping. Use `skills:` plural for ticket-level process instructions;
do not introduce new singular `skill:` usage. Workflow steps may also carry
step-local `skills:` when the step needs extra process instructions beyond the
ticket-level skills.

The task directory itself is also part of the contract:

```text
relay-os/tasks/<slug>/
  ticket.md
  blackboard.md
  log.md
```

`ticket.md` must start with YAML frontmatter, the frontmatter must parse to a
mapping, and the markdown body should keep the normal human-facing sections
(`## Description`, `## Context`) intact.

## Validation rules

- Required task keys: `title`, `status`, `mode`, `owner`, `human`, `agent`,
  `assignee`, `contexts`, `skills`, `workflow`.
- `title`, `owner`, `human`, `agent`, and `assignee` must be non-empty
  strings.
- `status` must be one of the Relay lifecycle states supported by the code
  (`draft`, `active`, `in_progress`, `paused`, `done`).
- `mode` must be one of `interactive`, `auto`, or `script`.
- `contexts` must be a list of refs; every ref must resolve to an existing
  context.
- `skills` must be a list of refs; every ref must resolve to an existing
  skill.
- `workflow` must be `null` or a frozen workflow mapping with a `name` and
  `steps`.
- If `workflow` is non-null and `status` is not `done`, `step` is required and
  must point at an existing step.
- If `workflow` is null, `step` must be absent.
- If `status` is `done`, `step` must be absent.
- Workflow step skills use `skills:` plural; each step's `skills` value is a
  list and may be empty.
- Unknown frontmatter fields should fail unless they are declared through an
  explicit ticket-format extension mechanism. If that mechanism is not ready,
  land the canonical allowlist first and document the extension follow-up.

## Implementation plan

1. Add a task-scoped validation primitive in `src/relay/validate.py`, e.g.
   `validate_task_dir(cfg, ref)` and `validate_ticket_frontmatter(cfg, ref,
   ticket)`, so commands can validate one edited task without scanning the
   whole repo.
2. Extend `relay validate` with `--task <slug>` so humans and agents can run
   the same check manually after direct edits.
3. Update `relay validate --json` to report strict schema issues with stable
   `kind` values and exact file/task references.
4. Wire post-edit validation into all Relay-owned task mutators:
   `relay draft` / `relay create`, `relay ticket` after the authoring session
   returns, `relay mark`, `relay bump`, launch-time status transitions,
   recurring/Dream task scaffolding, retire scaffolding, and any helper that
   rewrites `ticket.md`.
5. Keep validation after the write but before success/Slack reporting where
   possible. If a write succeeded but validation fails, print the exact schema
   errors and exit non-zero instead of broadcasting a clean handoff.
6. Update fixtures/templates so new tasks include mandatory `contexts: []`,
   `skills: []`, and `workflow: null` when empty.
7. Migrate existing shipped tasks, bootstrap shims, workflow fixtures, and
   tests from singular `skill:` to plural `skills:` where this ticket makes
   that canonical.

## Acceptance criteria

- [ ] `relay validate --task <slug>` validates exactly one task directory and
      emits both text and JSON output.
- [ ] Missing `ticket.md`, `blackboard.md`, or `log.md` is an error.
- [ ] Missing required frontmatter keys are errors naming the exact key and
      task.
- [ ] Wrong frontmatter shapes are errors (`contexts: foo`, `skills: foo`,
      malformed workflow mapping, bad `step:`).
- [ ] Broken context and skill refs are errors naming the missing ref and
      expected path.
- [ ] Relay-owned commands that edit task files call the task-scoped validator
      before reporting success.
- [ ] `relay ticket <slug>` validates after the authoring agent exits, so a
      bad hand-edit is surfaced immediately.
- [ ] Existing validation tests cover the new task-scoped API, the CLI
      `--task` flag, and at least one post-edit command hook.
- [ ] Seeded templates and example fixtures use the canonical
      `contexts: []`, `skills: []`, `workflow: null` shape.
- [ ] Documentation/context mentions the canonical schema and the manual
      command agents should run after direct task edits.

## Context

- This was designed from `relay launch bootstrap/orient`; the human explicitly
  selected `skills:` plural as the task-level process field.
- This ticket's own workflow frontmatter still uses the current legacy
  singular `skill:` field so it remains launchable before this migration is
  implemented.
- Related but not owned here:
  - `fail-loud-on-missing-context-or-skill-at-launch` handles launch-time
    missing refs.
  - `implement-validate-drift-dream-worker` handles periodic validation drift.
  - `add-extend-ticket-format-skill` covers future repo-specific custom
    fields.
- Keep the enforcement in `relay validate` / CLI write paths. A skill can
  document the habit, but it cannot reliably intercept every Relay-owned edit.
