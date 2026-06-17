---
title: First run works without Slack configured
status: draft
mode: interactive
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
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
step: 1 (design)
---

## Description

A stranger who just ran `pipx install relay-os` and `relay init` must be able to
run real commands **without configuring a Slack webhook**. Today Slack is
effectively required: commands crash if `$SLACK_WEBHOOK_URL` is unset and the
user hasn't explicitly opted out via `[slack].enabled = false`. That's a
first-run wall for a brand-new user who has never heard of our Slack setup.

Goal: out-of-the-box, no-Slack is the frictionless default.

- A fresh `relay init` repo runs `relay draft` / `mark` / `launch` / `bump`
  with no Slack config and no crash.
- Decide the default posture: ship `[slack].enabled = false` by default, OR
  treat a missing webhook as "Slack off" with a one-time hint, rather than a
  hard error. (Design step picks; keep it fail-loud only when the user has
  *opted in* to Slack but mis-configured it.)
- Don't regress the fail-loud contract for users who *did* enable Slack: an
  enabled-but-broken webhook must still surface loudly (principle 6).
- README/onboarding reflects that Slack is optional and how to turn it on.

## Context

RC release-gate blocker (see `relay/roadmap`). Pairs with
`improve-readme-and-doc` and `relay-cli-shipping` — all three are about a
stranger getting from install to first task without hitting a wall. Relates to
`rename-slack-to-a-notification-system-with-pluggab` (the bigger notification
refactor); this ticket is the narrow "don't block first run" slice, not that
refactor.
