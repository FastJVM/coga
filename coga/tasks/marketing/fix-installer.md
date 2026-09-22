---
title: Fix installation and one-task onboarding for V1
status: draft
owner: nicktoper
workflow: code/with-review
---

## Description

Fix the supported installation and first-run onboarding path so a new user
can go from a clean environment to one useful completed Coga task, with the
human directing and reviewing the work. Reproduce the current path first,
fix the concrete friction found, and align the onboarding instructions with
the README. Done means the fixes are merged and a clean installed-package
run reaches that first completed task with exact version, prerequisites,
commands and result recorded.

## Context

This is the V1 prerequisite owned by `marketing/build-the-launch-plan`.
Read `README.md`, `coga/install`, `coga/init`, `coga/first-task` and
`coga/releasing` (`docs/contexts/coga/{install,init,first-task,releasing}/SKILL.md`,
which replace the deleted `docs/getting-started.md` and `docs/releasing.md`)
and the current init/build onboarding implementation before selecting changes. Use the
existing supported install path and agent prerequisites; do not create a new
installer tier or broad onboarding framework. Test the minimum supported
Python version and the actual installed artifact, not only an editable tree.

These topics are cited, not attached: read `coga/codebase` (source layout),
`coga/extension-model` (microkernel rule), `coga/packaging` and `coga/testing`
before implementation, and `coga/workflows`, `coga/launch` and
`coga/knowledge` (fact ownership) before changing first-run behavior. Each
lives at `docs/contexts/<ref>/SKILL.md`; they replace the old
`coga/codebase` and `coga/architecture` sections of those names. Keep runtime
fixes at the existing shared/package contract boundary, update the owning
contexts/docs and any packaged twins with behavior changes, and verify the
relevant tests plus a first-task smoke run.

Coordinate commands and explanation with `marketing/readme-top`. Reuse or
link already-completed cleanup fixes rather than assuming old audit findings
remain live. The parked `v2/onboarding-v2-first-run-experience-after-removing`
ticket starts from the obsolete assumption that coga build was removed;
it does not govern this V1 path or need to be completed first. PostHog stays
in `marketing/add-telemetry`. No product release or personal-account action
is authorized by authoring this brief.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
