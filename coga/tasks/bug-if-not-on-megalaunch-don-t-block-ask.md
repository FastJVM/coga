---
slug: bug-if-not-on-megalaunch-don-t-block-ask
title: 'bug: if not on megalaunch  don''t block ask'
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
    requires: pr
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 1 (implement)
---

## Description

Fix Coga's launch instructions so an agent running in an ordinary, attended
`coga launch` asks the human for any needed decision, credential, permission,
or other input and waits for the answer in the REPL. It must not call
`coga block` merely to persist that question; during a normal launch it should
block only when the human explicitly asks to park or block the ticket.

Preserve the distinct `coga megalaunch` contract: when missing human input
prevents progress in a queue-run session, the agent must still call
`coga block` as its terminal action so the owner is notified and the queue can
continue. Done means the ordinary-launch and megalaunch instructions state
this boundary unambiguously, focused regression tests cover both prompt paths,
and the matching durable architecture documentation is updated.

## Context

- This is a prompt-contract correction, not a runtime restriction on the
  `coga block` command. A human in an ordinary launch must remain able to ask
  the agent to block the ticket explicitly.
- The ordinary-launch ask-and-wait rule is mode-specific and authoritative
  over generic downstream instructions to block in the base prompt, workflow,
  or step skills. The complete composed prompt must not contradict itself.
  Update directly conflicting agent-facing wording where needed (including
  live/packaged pairs such as `code/implement`), but do not turn this into a
  broad workflow or skill rewrite.
- The ordinary agent guidance is composed from
  `src/coga/resources/prompt.md` and
  `src/coga/resources/prompt-agent.md`. The latter currently says "ask or
  block," while the base prompt's stronger "Never stop silently" rule and
  blocking section can still steer an agent to persist a question instead of
  waiting for the human who is present in the TTY.
- Megalaunch appends `src/coga/resources/prompt-megalaunch.md` through
  `src/coga/megalaunch.py::_megalaunch_prompt_suffix`. Keep that queue-specific
  directive explicit: a TTY is transport for megalaunch, not evidence that a
  human is waiting to answer.
- Add semantic coverage for a full ordinary step prompt in
  `tests/test_compose.py`: it must direct the agent to ask and wait, reserve
  blocking for an explicit human request, and contain no conflicting generic
  direction to block merely because input is needed. In
  `tests/test_megalaunch.py`, assert that the appended queue directive
  overrides that attended default and requires terminal `coga block` when
  unavailable input prevents progress. Update the relevant launch/prompt-composition
  section of `coga/contexts/coga/architecture/SKILL.md` and its packaged copy
  under `src/coga/resources/templates/coga/bootstrap/contexts/coga/` in the
  same change. Run the focused tests, then `python -m pytest` and
  `coga validate --task bug-if-not-on-megalaunch-don-t-block-ask`.
- Prefer consolidating or replacing conflicting base-prompt wording over
  adding another parallel rule; the base prompt is already the largest
  composed layer.
- Do not add a launch mode flag, change blocker lifecycle/state transitions,
  weaken megalaunch's requirement to release the queue with a terminal Coga
  command, or change TTY detection.
- Keep this narrow bug separate from the empty draft
  `rewrite-coga-base-prompt-and-agent-mode-block`; broader prompt rewriting is
  out of scope here.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
