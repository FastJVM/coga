---
title: Document Quick Start for empty and existing repositories
status: draft
owner: nicktoper
workflow: null
---

## Description

Give the README two complete Quick Start paths: a new empty repository eligible for coga build onboarding, and an existing repository where init says coga build is unavailable. Follow current init behavior instead of routing both users into an empty-repository-only command.

Done when each path states its prerequisites and gives valid commands through a first usable task or conversation, explains when build is available, and is checked against current help and representative empty/nonempty fixtures. Keep this change focused on onboarding instructions; a broader README rewrite is outside scope.

## Context

### Report relayed by the owner — 2026-10-07

Another AI reports that coga init in an existing repository says “coga build is unavailable here,” while the README sends readers to build. Intake confirms the corresponding init message and empty-repo-only packaged onboarding contract. README currently has empty Existing repo and New repo subsections; complete those paths rather than adding another competing Quick Start.

Read coga/init (`docs/contexts/coga/init/SKILL.md`), cited rather than attached; inspect empty/filled repository detection and handoff messages. Start with `src/coga/commands/init.py`, its tests, README.md, and `src/coga/resources/templates/coga/workflows/build/onboarding.md`. Coordinate the missing vision publication fix in publish-build-vision-before-handing-off-starter-ti; do not promise clone-ready generated contexts until that path is verified.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
