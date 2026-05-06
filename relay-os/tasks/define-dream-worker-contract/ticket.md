---
title: Design Dream known-skill dispatch contract
status: done
mode: interactive
owner: nick
human: nick
agent: claude1
assignee: nick
contexts:
- relay/architecture
- relay/principles
- relay/codebase
- relay/current-direction
- relay/project-stage
workflow:
  name: code/with-review
  steps:
  - name: implement
    skill: code/implement-and-pr
  - name: review
---

## Description

Design how Dream runs independent background maintenance skills.

Dream should stay a bootstrap maintenance feature: `bootstrap/dream` executes a
small, explicit set of known shipped skills. It should not become a project
extension framework, a recursive worker registry, or a single large cleanup
script.

Each known Dream skill needs a small, legible contract: what it consumes, what
it may change, how it reports results, and how it avoids repeating work.

## Context

Parent ticket: `relay-os/tasks/add-bootstrap-retro-skill-for-knowledge-extraction/`.

This ticket should settle the bootstrap contract before individual Dream skills
grow their own incompatible conventions.

## Design

### Dream location

Dream remains:

`relay-os/skills/bootstrap/dream/SKILL.md`

This is deliberate. Dream is a shipped bootstrap feature for maintaining Relay
itself. Relay's bootstrap Dream does not need to provide a plugin API.

User space can still define a separate Dream-like maintenance loop directly,
for example `rem`, `ops/dream`, or another normal skill/workflow/recurring
task. That user-space loop owns its own dispatch rules, state, naming, and
conventions. It is not plugged into bootstrap Dream.

### Dispatch model

`bootstrap/dream/SKILL.md` owns the dispatch list. Dream runs only the known
skills named there, in the order named there.

Adding a file under `relay-os/skills/bootstrap/dream/tasks/` does not enable it.
There is no recursive discovery rule, no hidden registry, no daemon, no
database, and no local cache.

Initial known skills:

- `bootstrap/dream/tasks/validate-drift` - always run first.
- `bootstrap/dream/tasks/dev/stale-branches` - run when the repo is a git code
  repo and branch cleanup evidence is useful.

Adding another Dream skill is a normal Relay code/docs change: edit
`bootstrap/dream/SKILL.md` to add it to the known-skill list, add its contract,
and update tests/docs. That keeps the control point legible.

### Known skill contract

Each known skill is an ordinary SKILL.md. The frontmatter stays standard:
`name`, `description`, and optional `script`.

The body should include a `## Known Skill Contract` section:

- `Purpose` - what maintenance question this skill answers.
- `Runs` - exact command, manual instructions, or script entry point.
- `Inputs` - files, commands, APIs, or task state the skill may read.
- `May change` - exact files/refs/state the skill may edit, or `none`.
- `Action` - one of `report-only`, `proposal-only`, `pr-required`,
  `direct-fix`.
- `Idempotency` - how reruns avoid duplicate work.
- `Stop and ask` - conditions that require human review before continuing.
- `Output` - blackboard section, PR link, created ticket, or no-op result.

Action meanings:

- `report-only` - read state and write a result to the Dream run blackboard.
- `proposal-only` - write evidence and proposed commands/edits, but do not
  mutate the repo or external systems.
- `pr-required` - make durable file changes only on a branch and open a PR.
- `direct-fix` - make only the narrow deterministic change named in
  `May change`.

### Output

Each known skill writes its own section to the Dream run blackboard:

`## Dream Skill: <name>`

The orchestrator appends one run-level summary:

`## Dream Run Summary`

That summary lists each known skill, result status, output pointer, and human
review gates. Result statuses should stay small and consistent:

- `no-op`
- `reported`
- `proposed`
- `direct-fixed`
- `pr-opened`
- `human-needed`

### Safety

Destructive behavior is never implicit. Deleting task directories, deleting git
refs, removing locks, changing lifecycle state, or touching secrets requires
exact evidence and human review by default.

A known skill may declare direct destructive behavior only when the rule is
deterministic, narrow, and named in `May change`. Otherwise it must use
`proposal-only` or `pr-required`.

## Acceptance criteria

- [x] `bootstrap/dream` has an explicit known-skill list and dispatch order.
- [x] Known Dream skill SKILL.md files have a documented body convention.
- [x] Dream can summarize known skill results in one run-level blackboard
      section.
- [x] Destructive skill behavior requires evidence and review by default.
- [x] The contract is documented as shipped bootstrap behavior, while making
      clear that users can define separate user-space maintenance loops.
