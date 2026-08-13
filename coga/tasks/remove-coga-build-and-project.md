---
slug: remove-coga-build-and-project
title: remove-coga-build-and-project
status: draft
owner: nick
human: nick
agent: claude
assignee: claude
contexts: []
skills: []
workflow: code/with-review
secrets: null
script: null
---

## Description

Remove the `coga build` and `coga project` entry points — neither has ever
been used — and make `coga chat` (→ `launch bootstrap/orient`) the single
conversational door into a repo. This is a pure-removal ticket: delete both
surfaces and everything only they consume, and repoint every reference
(`coga init` closing message, docs, contexts, alias tables) at `coga chat`
so a fresh repo is never left pointing at a dead command. Do not build a
replacement onboarding flow here — that is deliberately deferred to
`v2/onboarding-v2-first-run-experience-after-removing`.

Done looks like: no `build` or `project` spelling anywhere in live code,
packaged templates, or docs; `pytest` green with `test_project.py` removed
and alias/init/packaging tests updated; `coga validate --json` clean.

## Context

What each entry point is:

- `coga build` is an alias (`build = "launch coga-build"` in
  `src/coga/aliases.py` and the packaged `coga.toml` template) that launches
  the packaged first-run onboarding ticket
  `src/coga/resources/templates/coga/tasks/coga-build.md`, backed by the
  `build` workflow (live copy `coga/workflows/build/`, packaged copy under
  `src/coga/resources/templates/coga/workflows/build/`).
- `coga project` is a real Typer command (`src/coga/commands/project.py`,
  registered in `src/coga/cli.py`) that runs the `bootstrap/project` skill
  (`src/coga/resources/templates/coga/bootstrap/skills/bootstrap/project/SKILL.md`)
  against the packaged `bootstrap/project/ticket.md`.

Known reference inventory (grep for `build`/`project`/`coga-build` to
confirm; this list was accurate at authoring time): `src/coga/aliases.py`,
`src/coga/cli.py`, `src/coga/commands/project.py`, `src/coga/commands/init.py`
(points fresh repos at the removed path), `src/coga/dependencies.py`,
packaged templates under `src/coga/resources/templates/coga/` (`coga.toml`,
`log.md`, `tasks/coga-build.md`, `bootstrap/project/`, `bootstrap/skills/
bootstrap/project/`, `bootstrap/contexts/coga/cli/SKILL.md`,
`workflows/build/`), live repo copies (`coga/coga.toml`,
`coga/workflows/build/`, `coga/contexts/coga/codebase/SKILL.md`), tests
(`tests/test_project.py`, `tests/test_aliases.py`, `tests/test_init.py`,
`tests/test_packaging.py`), and docs (`README.md`, `docs/getting-started.md`,
`docs/reference.md`, `docs/cli-extension-audit.md`).

Watch out for:

- Live `coga/` vs packaged `src/coga/resources/templates/coga/` copies must
  stay in sync — remove both sides of each pair (CLAUDE.md rule).
- Repos initialized before this change may still carry `build` alias lines
  in their own `coga.toml`; the alias table change only affects the packaged
  template and built-in fallbacks, which is fine — don't try to migrate
  existing repos.
- Overlap: `coga/tasks/v2/cleanup-core-commands/work-orchestration-commands-to-tickets.md`
  lists `coga project` in its migration scope. This ticket supersedes that
  part by deleting the command outright; leave a note there rather than
  migrating.
- Out of scope: any new onboarding flow (see the v2 ticket above), and any
  change to `coga chat` / `bootstrap/orient` behavior beyond doc pointers.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
