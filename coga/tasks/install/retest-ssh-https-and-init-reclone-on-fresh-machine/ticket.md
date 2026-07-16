---
slug: install/retest-ssh-https-and-init-reclone-on-fresh-machine
title: Retest SSH/HTTPS clone + init re-clone on a fresh work machine
status: in_progress
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
step: 1 (implement)
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

**Retest 2026-07-08 (fresh-container, HTTPS path):** `COGA_REPO_URL` override
verified working (including a local-path value — Greg's workaround is a
sanctioned path now); code prefers an SSH coga remote when one exists; failed
clone rolls back atomically. Still open here: (a) the real SSH-default-machine
run this ticket asks for, and (b) the re-clone surprise itself, which
escalated — the clone vendors *main HEAD*, not the installed version, and is
slated for removal in `install/vendor-cli-from-installed-package-not-git-clone`.
If that ticket lands first, only the SSH-machine verification remains.

**Added 2026-07-15 (nick, launch prep):** while on the fresh machine, also
time the full path from `pip install` to first felt success (init → build →
first ticket → something visibly works). If it exceeds ~10 minutes or ends
at "installed, now what?", that's a launch blocker — file it against the
launch gates, not here. One measurement, no new scope.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
