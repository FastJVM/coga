---
title: External users can't install managed skills (relay-skills access)
status: draft
mode: interactive
owner: zach
human: zach
agent: claude
assignee: zach
contexts: []
skills: []
workflow: null
secrets: null
---

## Description

On `relay init --update`, the ~12 optional managed skills all failed to install
for Greg because he has no access to the `relay-skills` repo — which is the
default state for any outside / onboarding user. The managed-skill install path
should either not require private-repo access, degrade cleanly to a working
install without them, or clearly state that these skills are optional and how to
obtain access.

## Context

Reported by Greg (external user). The *noise* of these failures (12 full `gh`
usage dumps burying the success lines) is already owned by
`marketing/quiet-relay-init-managed-skill-failures` (draft); this ticket is the
orthogonal *access/availability* problem for non-team users. Skill install
delegates to `gh skill` (see the `relay/cli` context, `relay skill`) and
`src/relay/skill_manager.py`.
