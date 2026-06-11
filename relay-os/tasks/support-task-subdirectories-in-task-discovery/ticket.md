---
title: Support task subdirectories in task discovery
status: in_progress
mode: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts:
- relay/codebase
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
step: 4 (review)
---

## Description

Allow tasks to live in subdirectories of `relay-os/tasks/` (e.g.
`tasks/auto/<slug>/`) so related tickets can be grouped by area. Task
discovery currently only sees direct children, so a nested ticket is
invisible to every CLI command. Extend discovery (and anything that
depends on it — slug resolution, validate, scaffolding paths) to find
tickets one level deeper, keeping the bare slug as the universal
reference. As the first real use, move the existing
`stream-agent-progress-in-auto-mode-and-recurring-l` ticket into
`relay-os/tasks/auto/`.

## Context

- Discovery is `list_tasks()` in `src/relay/tasks.py` (~line 50): it
  iterates `tasks_root.iterdir()`, keeps direct child dirs containing a
  `ticket.md`, skips `_`-prefixed names (`_template`). The dir name is
  the slug.
- Keep the slug as the leaf directory name; tickets stay referenced by
  bare slug (and unique prefix — see `resolve_task()` in the same file),
  not by path. Duplicate leaf names across subdirs: `list_tasks()`
  raises a typed error, and `relay validate` catches that error and
  reports the colliding paths legibly instead of crashing.
- A subdir that itself contains a `ticket.md` is a task, not a group —
  don't recurse into task dirs. `_`-prefix skipping applies at both
  levels.
- `relay draft` / `relay ticket` scaffolding writes to
  `tasks/<slug>/`; decide whether they accept a `group/slug` form or
  whether grouping stays a manual `git mv`. Manual move is acceptable
  for now if scaffold support balloons the scope.
- Known slug→path reconstruction sites to fix or confirm safe:
  `_authored_task_refs` in `src/relay/commands/ticket.py` (~line 270)
  takes `rel.parts[0]` as the slug — wrong for nested tasks;
  `task_dir()` in `src/relay/paths.py` (~line 92) builds `tasks/<slug>`
  directly (appears uncalled, but is exported API — make nesting-aware
  or remove); the debug-run orphan sweep in
  `src/relay/commands/recurring.py` (~line 280) does its own
  `iterdir()` — confirm debug runs are always top-level; scaffold dedup
  in `src/relay/scaffold.py` (~line 113) — new tasks are always created
  top-level, confirm that's intentional.
- Do the `git mv` of the stream-agent ticket in the same PR as the code
  change so they merge atomically — if the move merges before the code,
  every CLI command on main goes blind to that ticket.
- Mirror any behavior change in the seeded fixture `example/relay-os/`
  and tests (`tests/test_*.py`); note `example/relay-os/` has no
  `tasks/` dir today, so the nested-task fixture has to be added, not
  edited. Per CLAUDE.md, keep
  `src/relay/resources/templates/relay-os/` in sync if templates are
  affected.
- Explicitly out of scope: slug-prefix naming conventions (rejected),
  and the auto-mode output-streaming work itself (separate ticket:
  `stream-agent-progress-in-auto-mode-and-recurring-l`).
