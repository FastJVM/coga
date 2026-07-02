---
title: Retest SSH/HTTPS clone + init re-clone on a fresh work machine
status: draft
mode: llm
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

The SSH-vs-HTTPS fix (`relay-forces-https`) and configurable remote name
(`remote-default-origin`) both merged as done, yet Greg — an external user whose
machine clones GitHub over SSH — still hit HTTPS friction and was surprised that
`relay init` attempts to clone again (he set `RELAY_REPO_URL` to his local
checkout to get past it). Retest the full SSH-default onboarding path on a clean
work machine to confirm the merged fixes actually cover his case, and file
follow-ups for whatever still breaks — notably the init re-clone surprise.

## Context

Reported by Greg (#4). This is a verification ticket, not a re-implementation:
the relevant behavior already shipped via `relay-forces-https` (done) and
`remote-default-origin` (done), so the open question is whether those fixes hold
on a real SSH-default machine. Touchpoints to exercise: `RELAY_REPO_URL` /
`clone_upstream` in `src/relay/commands/update.py`, and source normalization in
`src/relay/skill_manager.py`. Sibling onboarding issues live in this `install/`
group.
