---
slug: put-build-back
title: put-build-back
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

Restore `coga build`, the first-run onboarding flow, which was removed in PR
#691 (`remove-coga-build-and-project`, commit `8394d3b3`, 2026-08-17). Zach
used build on his weather app and it turned a half-baked idea into something
real — it adds value and we want it back. Restore **build only**: `coga
project` and the `bootstrap/project` skill stay removed (explicit owner
decision).

## Context

`coga build` is not a Python command — it is the alias `build = "launch
coga-build"` plus a packaged `coga-build` ticket and the `build/onboarding`
workflow (two agent steps: `gather-and-spec` asks "What do you want to
build?", writes a signed-off vision to `coga/contexts/product/vision/SKILL.md`;
`generate-batch` scaffolds a flat batch of draft tickets from it). The
workflow steps carry no skills; their instructions live inline in the
workflow file. Keep it an alias — per the microkernel rule, a launch-target
command is an argv rewrite in `[aliases]`, not a Typer command.

To restore, revert the build-scoped parts of commit `8394d3b3` (a full
`git revert` would also resurrect `coga project` — don't). That means bringing
back:

- `build` alias in `src/coga/aliases.py` `DEFAULT_ALIASES`, `coga/coga.toml`,
  and `src/coga/resources/templates/coga/coga.toml`
- `coga/workflows/build/onboarding.md` **and** its packaged twin
  `src/coga/resources/templates/coga/workflows/build/onboarding.md` (live and
  packaged copies stay in sync)
- `src/coga/resources/templates/coga/tasks/coga-build.md` (packaged ticket)
- the reverted `src/coga/commands/init.py` seeding and the associated test
  coverage removed from `tests/test_aliases.py`, `tests/test_init.py`,
  `tests/test_packaging.py`
- doc/context mentions trimmed by the PR (README, `docs/getting-started.md`,
  `docs/reference.md`, `docs/cli-extension-audit.md`,
  `coga/contexts/coga/architecture`, `coga/contexts/coga/codebase`,
  `coga/contexts/coga/usage`, packaged `bootstrap/contexts/coga/cli` and
  `bootstrap/contexts/coga/architecture`) — restore only the build mentions,
  leave `project` mentions out, and resolve any drift from commits landed
  since the removal.

Leave removed: `src/coga/commands/project.py`, the `bootstrap/project` skill,
`tests/test_project.py`, and the packaged `bootstrap/project/ticket.md`.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
