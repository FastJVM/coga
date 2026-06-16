---
title: Replace relay setup with relay build
status: in_progress
mode: interactive
owner: nick
human: zach
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

Replace the `relay setup` command with `relay build`. The user-facing change is
just the name and what it launches: after `relay init`, the user runs `relay
build` instead of `relay setup`. Mechanically it is a rename — `relay setup`
already does init-if-needed + capture-name + launch-the-onboarding-ticket, and
all of that carries over. What changes is the target: `relay build` launches the
new `relay-build` onboarding ticket (single question → agent-led chat → scan →
spec → ticket batch) instead of the old `relay-setup` interview. "relay setup"
should disappear from the command, the source file, and the next-steps text.

## Context

- Files: `src/relay/commands/setup.py` → `build.py`; the command registration +
  `_BUILTIN_COMMANDS` entry in `src/relay/cli.py`; `relay init`'s next-steps
  text (`init.py:264–270`) repointed at `relay build`. The packaged
  `relay-setup` ticket template → `relay-build`, and the `init/setup` workflow →
  `build` (keep the live and packaged copies in sync).
- Name capture stays in the command. The launch gate at
  `src/relay/config.py:216` fails loud if `user` is unset, so capture must run
  before launch — which is exactly why `relay init` does NOT need a prompt.
- The onboarding flow this command launches is designed in
  `marketing/relay-build-onboarding-flow`; this ticket is just the command +
  rename. Sequence it after that design lands so the target names are fixed.
- This ticket's own slug is still `remove-relay-setup-command` — rename to
  `relay-build-command` when convenient (deferred: it is mid-launch).
