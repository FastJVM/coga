---
title: Give the three-kinds-of-work taxonomy an owning doc
status: draft
owner: nicktoper
contexts:
  - coga/principles
  - coga/codebase
workflow:
  name: docs/with-review
  steps:
  - name: implement
    skills: []
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills: []
    assignee: agent
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 1 (implement)
---

## Description

Coga's pitch now rests on a taxonomy that exists nowhere in the repo: humans do three kinds of work — routine (fix merge conflicts, bump dependencies), understood (fully specifiable before doing: support, adding a feature), and unknown (the work you discover by doing, with a 'known cone' of what you have done and blur beyond it). Coga maps to all three (routine: scripts, recurring, recipes; understood: ticket + frozen workflow + megalaunch; unknown: chat, blackboard, rewind that keeps everything learned, superseded designs, Dream) and is built for the third. Under the one-owner rule in coga/architecture, a fact the pitch summarizes must have exactly one owning surface. Give the taxonomy that owner in docs/vision.md — a new section beside 'How we decide what to automate' — and add a one-line pointer from coga/principles so the root principle names what the human is supposed to think about. Also relabel the human rewind (coga bump --to / --backward) where coga/architecture and coga/cli call it 'an exceptional human debug/recovery operation': it is that for understood work, and a normal move for unknown work; say both. Do not restate the taxonomy in a second place; the pitch and docs/market-thesis.md may summarize and link.

## Context

Source of the taxonomy: the owner's pitch draft of 2026-09-16/17 (chat
session, `bootstrap/orient`). It is not yet in any repo file.

Receipts already in code, for the section to cite rather than restate:

- Routine: recurring templates under `coga/recurring/`, the `ticket.py`
  sibling, `coga run` recipes (`runner.RECIPES`).
- Understood: `coga create --workflow`, frozen steps, `coga megalaunch`.
- Unknown: `coga chat` (`bootstrap/orient`), the blackboard region,
  `coga bump --to/--backward` (reposition-only; `src/coga/bump.py:37-60`),
  `## Superseded designs` (`src/coga/blackboard.py:219`), `coga ticket
  <slug>` re-authoring at any status, Dream.

Where the "exceptional debug/recovery" wording lives today:
`coga/contexts/coga/architecture/SKILL.md` (Two state machines per ticket,
data plane) and the packaged twin; `coga/cli` under `coga bump`. Change the
live and packaged copies together (`tests/test_packaging.py`).

Related evaluation record: `docs/pitch-evaluation.md`,
`docs/research-work-comparison.md` (unknown work vs CE/Kortix).

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
