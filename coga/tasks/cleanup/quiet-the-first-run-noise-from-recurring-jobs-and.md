---
slug: cleanup/quiet-the-first-run-noise-from-recurring-jobs-and
title: Quiet the first-run noise from recurring jobs and managed skills
status: draft
owner: nick
human: nick
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
secrets: null
step: 1 (design)
---

## Description

Decide and then fix what a stranger sees in the first minute. Two findings:
`coga status` in a one-minute-old repo lists six recurring jobs as "due — not
created", and `coga init` installs seven managed skills including the
`google-agents-cli-*` set, pip-installing gmail and calendar dependencies into
the venv. Both need network time and look odd in a repo that has no work in it
yet.

## Context

**Finding** (audit, 2026-09-02, check 2 rows g and k). A fresh
`coga init` in an existing project installs 7 managed skills and pip-installs
gmail / google-calendar requirements — network-dependent, slow, and surprising
in someone else's repo. Immediately after, `coga status` on a repo containing
one draft ticket renders a six-row Recurring footer of jobs marked
"due — not created".

**The decision comes first** — this is why the ticket carries a design step.
Is the seven-skill install the intended first impression, or should the Google
agent skills be opt-in (`coga skill install ...` when the user wants them)?
Should the Recurring footer be suppressed until at least one period task has
run, or is a repo that ships six recurring jobs by default the wrong default?
Neither answer is obvious and both change what a new user meets on line one.
`src/coga/resources/managed-skills.toml` is the manifest; the footer is in
`src/coga/commands/status.py`.

**Constraint.** Whatever changes, the first run must stay honest — hiding
state to look tidy is the wrong direction (`coga/principles`, fail loud).
Quiet is not the same as concealed.

Source: `marketing/phase-0-audit` step 1 (2026-09-02), triaged by the owner
in step 2 (2026-09-03). This directory holds the work the owner wants done
before the marketing materials ship.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
