---
slug: install/gh-auth-hint-on-managed-skill-rate-limit
title: gh auth hint on managed skill rate limit
status: active
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
- dev/code
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
secrets: null
script: null
step: 1 (implement)
---

## Description

Unauthenticated `gh skill install` runs against GitHub's anonymous API quota
(60 req/hr per IP); repeated inits — or one init behind office NAT — 403 all
managed-skill installs with a raw rate-limit dump. The failures are warn-only
(init proceeds), but the remediation hint suggests re-running
`coga skill install …`, which hits the same limit. When the failure is a
rate-limit 403, the remediation should say `gh auth login` (authenticated
requests get a much higher quota), and the raw GitHub ToS/request-ID blob
should be trimmed to the one actionable line.

## Context

Found in the 2026-07-08 fresh-container retest (third init from one IP,
gh 2.96 unauthenticated). Touchpoints: `src/coga/managed_skills.py` /
`src/coga/skill_manager.py` (failure classification + remediation text).

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
