---
slug: cleanup-core-commands/README
title: Cleanup core commands task directory
status: draft
owner: nicktoper
human: nicktoper
agent: codex
assignee: nicktoper
contexts: []
skills: []
workflow: null
secrets: null
script: null
---

## Description

Directory index for the core-command cleanup tickets. Do not launch this README
as the implementation task; launch one of the child tickets below.

Owner direction for the whole directory: the only command presumed irreducibly
core is `create`; every other command, including lifecycle verbs such as `mark`
and `bump`, should be treated as a candidate to become a
ticket/workflow/script-shaped operation unless the design proves a specific
bootstrapping exception.

## Context

The product rule for this ticket set is: Coga commands should operate on durable
tickets, not perform substantive work as untracked side effects. Keep CLI
entrypoints thin; put reusable behavior in `src/coga/` modules, and put
workflow/process shape in `coga/workflows/`, `coga/skills/`, and packaged
bootstrap resources as appropriate.

If behavior moves or the command boundary changes, update the matching durable
context/source doc in the same PR, especially
`coga/contexts/coga/extension-model/SKILL.md`, `docs/cli-extension-audit.md`,
`src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md`,
`coga/contexts/coga/principles/SKILL.md`,
`coga/contexts/coga/architecture/SKILL.md`, and packaged template copies when
applicable.

## Child Tickets

- `cleanup-core-commands/lifecycle-verbs-to-ticket-operations` — `mark`, `bump`,
  `block`, and `unblock`.
- `cleanup-core-commands/launch-decomposition` — launch executor substrate versus
  movable launch policy/orchestration.
- `cleanup-core-commands/read-report-commands-as-ticket-workflows` — `show`,
  `status`, `validate`, `usage`, and `recurring list`.
- `cleanup-core-commands/work-orchestration-commands-to-tickets` — `project`,
  `retire`, `megalaunch`, `slack`, and digest/recurring maintenance surfaces.
- `cleanup-core-commands/support-commands-boundary` — `secret get`, `uninstall`,
  package upgrade/refresh docs, and bootstrap-adjacent support commands,
  excluding `create`, `launch` substrate, and `skill *`.
- `cleanup-core-commands/residual-command-surfaces` — `init`, `ticket`, `delete`,
  `skill *`, bare `recurring`, `recurring launch <name>`, and default aliases.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
