---
slug: rewrite-coga-base-prompt-and-agent-mode-block
title: Rewrite coga base prompt and agent-mode block
status: in_progress
owner: nicktoper
human: nicktoper
agent: codex
assignee: claude
contexts:
- coga/principles
- coga/codebase
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
step: 2 (peer-review)
---

## Description

Rewrite the coga **base prompt** and the **agent-mode block** (the package
resources composed into every launch — see `compose.py` and
`src/coga/resources/`) so they read cleanly and reflect coga's current framing,
in particular the **microkernel / minimal-core** direction settled in
`decide-what-belongs-in-core-vs-skills-and-move-ski` (core holds only
command-backing and ≥2-consumer shared code; everything else is a skill recipe).

This is a prose/quality pass on the two prompts, not a behavior change to the
CLI. Goal: tighter, more legible instructions to the launched agent, aligned
with the principles and the core-vs-skills line.

## Context

- The base prompt and agent-mode block are **package resources**, not files
  under `coga/`. They live in `src/coga/resources/` and are assembled by
  `compose.py` (layers 1 in the prompt-composition order). Confirm exact paths
  before editing.
- They are composed into every launch, so length is a token cost on every
  agent run — favor tightening over adding.
- The microkernel policy has **landed** — the rule is written into `CLAUDE.md`
  and `coga/codebase` (`agree-the-core-vs-skills-move-list-then-execute`, done).
  This ticket is unblocked; make the base prompt speak that same language.
- Out of scope: changing `compose.py` composition order or any CLI behavior;
  rewriting the `coga/` contexts (a separate concern).

**Absorbed: the editorial pass (2026-07-27).** This ticket now also carries the
human-owned editorial pass formerly tracked as
`launch-prompt/review-and-edit-the-relay-launch-prompt-editorial`, which was
deleted rather than parked: it scoped `src/relay/resources/` (gone since the
coga rebrand) and sequenced behind a sibling trim ticket that no longer exists.
Running two tickets over the same prose was churn. What travels here:

- The pass is **wording, tone, and clarity**, not just structural trim — the
  parts that are taste and judgment on the behavioral contract.
- Working shape: the agent drafts support material (a marked-up read of the
  prompt — remaining redundancy, awkward phrasings, instructions that could be
  sharper, anything ambiguous to a launched agent); nick reviews, edits to the
  bar he wants, and owns the result.
- Surface is the whole launch-prompt set, not the base prompt alone: the base
  prompt plus the mode overlays that `compose.py` layers on top of it. Confirm
  the current filenames under `src/coga/resources/` before editing — the old
  ticket's `prompt-interactive.md` / `prompt-auto.md` names predate the current
  agent-mode and queue-guidance split.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: codex/rewrite-launch-prompts
worktree: /tmp/coga-rewrite-launch-prompts

## Implement notes

- Confirmed composition paths: `src/coga/resources/prompt.md` is the base
  layer and `src/coga/resources/prompt-agent.md` is the unconditional agent
  mode layer. Queue guidance is appended separately by
  `prompt-queue.md`/`prompt-megalaunch.md`.
- Editorial direction: consolidate repeated lifecycle/escalation prose, keep
  the every-launch contract operational, and state the minimal-core boundary
  without pulling the longer rationale out of `coga/codebase`.
- Rewrote both package resources and committed them as `befa28a7` (`Rewrite
  launch prompt guidance`). The base/mode layers are 979 words, down from
  1,580 (about 38%), while preserving the ticket/blackboard, transition,
  blocking, FYI, YAML, attended-session, and human-response contracts.
- Added the microkernel boundary directly to the base prompt: core is limited
  to >=2-consumer shared infrastructure and genuine Python command
  implementations; skills, exact sibling `ticket.py` work, and aliases stay
  at the edge. Added composition assertions for that contract.
- Reviewed `prompt-queue.md` and `prompt-megalaunch.md` for interaction with
  the shorter Agent mode. They remain the later, explicit override of the
  attended default and need no edits. Remaining repetition there is
  intentional because each overlay must stand alone in its launch mode.
- Verification: `PYTHONPATH=/tmp/coga-rewrite-test-deps:/tmp/coga-rewrite-launch-prompts/src
  python3.12 -m pytest` -> 2,112 passed. (`hatchling`, a declared test
  dependency absent from ambient Python, was installed only under `/tmp`.)
  `git diff --check` passed. Final fetch/rebase found the branch current with
  `origin/main` and one commit ahead.
