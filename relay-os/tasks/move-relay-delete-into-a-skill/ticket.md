---
title: Move relay delete into a skill
status: active
mode: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
- relay/architecture
- relay/principles
- relay/cli
- relay/codebase
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
  - name: open-pr
    skills:
    - code/open-pr
  - name: review
    assignee: owner
step: 1 (implement)
---

## Description

Refactor `relay delete` so the deletion logic lives in a skill, not in
`src/relay/commands/delete.py`. The public CLI surface (`relay delete <slug>`,
`--force`) stays — only the implementation moves.

Why: per the dream-5 architectural correction, executable behavior in Relay
belongs in `SKILL.md` directories. Anything Dream (or any other orchestrator)
needs to call should be reachable as a skill attached to a Relay task — not a
private Python helper imported across the codebase. Today `relay delete` is a
direct Typer command; that means Dream's cleanup-orphan-markers worker either
has to shell out to the CLI or duplicate the deletion logic. Lifting deletion
into a skill closes that gap and makes the surface uniform.

## Proposed Shape

- New skill `bootstrap/delete-task` (name TBD during implement) under
  `relay-os/skills/bootstrap/delete-task/SKILL.md`, with a `script:` entry
  point that performs the actual filesystem delete + lock check.
- `relay delete <slug>` becomes a thin Typer entrypoint that scaffolds an
  ephemeral `mode: script` task whose one workflow step references the
  skill, then `relay launch`es it. Or — equivalent — calls the skill
  script directly with the same env vars `mode: script` would inject.
  Pick whichever keeps the orient/dream architecture story consistent;
  document the choice in the blackboard before merging.
- `task.lock` semantics, `--force`, "refuse if held", "bootstrap shims
  aren't user-deletable" — all preserved. This is a refactor, not a
  redesign.

## Acceptance Criteria

- `src/relay/commands/delete.py` (or wherever the body lives) is reduced
  to argument parsing + dispatch into the skill.
- The skill is independently invocable from a `mode: script` task. A test
  proves this — scaffold a script task whose step references the skill,
  run `relay launch`, see the target task directory removed.
- Existing CLI behavior is preserved: prefix matching, `--force`, lock
  refusal, bootstrap-shim refusal, no Slack broadcast on delete.
- Existing tests for `relay delete` still pass; new tests cover the skill
  path.
- `relay/cli` context updated so the "relay delete" entry mentions that
  the implementation is a skill (one sentence — don't bloat the doc).

## Out Of Scope

- Changing user-visible flags or behavior of `relay delete`.
- Touching `relay delete --exact` semantics — keep that surface stable
  (Dream's cleanup-orphan-markers worker depends on it; see sibling
  ticket `make-dream-workers-skills-only`).
- Building the Dream orchestration around this skill — that's the third
  sibling ticket `compose-dream-as-recurring-plus-alias`.

## Context

Sibling tickets in this split:

- `make-dream-workers-skills-only` — validate-drift and
  cleanup-orphan-markers become skills with `SKILL.md` shape, no direct
  Python imports from Dream.
- `compose-dream-as-recurring-plus-alias` — `relay dream` Python command
  is replaced by a recurring task definition plus a `dream` alias that
  composes the skill-based workers (including this delete skill).

Background: `relay-os/tasks/dream-5/ticket.md` is the original combined
ticket; this one carries the "deletion lives in a skill" piece of it.
