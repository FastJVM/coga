---
slug: resolve-blocker-inline-via-chat-on-interactive-lau
title: Resolve blocker inline via chat on interactive launch
status: in_progress
autonomy: interactive
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
- coga/architecture
- coga/cli
- coga/codebase
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

Today `coga launch <slug>` **hard-refuses** a `blocked` ticket
(`src/coga/commands/launch.py:211`), printing a message that tells the human to
run `coga status --blocked` then `coga unblock <slug> --answer "..."` and launch
again. So resolving a blocker is three commands and two of them are outside the
session where the thinking actually happens: `coga unblock` with no `--answer`
gives a rigid terminal prompt, not a discussion.

This ticket makes an **interactive** `coga launch` of a blocked ticket instead
open the normal agent chat, whose **first job is to work through the open
blocker asks with the human**, land on a resolution, record it, and then roll
straight into the current workflow step — one command, one continuous session.
The open ask is often something the human needs to *reason about* (the
motivating case: `drain-pending-auto-tickets-with-leftover-session-b`, blocked on
a rescope decision the owner couldn't answer cold). A chat is the right surface
for that; a one-line `--answer` prompt is not.

Scope is deliberately narrow: this changes **only** the interactive,
human-at-a-TTY launch path. `coga megalaunch` and any unattended/auto launch
keep today's behavior — they skip blocked tickets and report
`skipped-unresolved-blocker` (`src/coga/megalaunch.py:139`), because an
unattended run has no human to discuss with. The discriminator is
"explicit interactive human act" vs. "batch".

## Context

### Current behavior (verified)

- `src/coga/commands/launch.py:211` — the blocked guard that hard-bails. This is
  the only thing to change; draft/paused already activate inline just above/below
  it, and `done` stays refused.
- `src/coga/megalaunch.py:139` — megalaunch already classifies a blocked ticket
  as `skipped-unresolved-blocker` and never launches it. **Leave this as is.**
- `coga unblock <slug> --answer "..."` is the existing command that appends the
  resolution to the blackboard and moves `blocked → active` **preserving
  `step:`**. Reuse it verbatim as the recording mechanism — do not invent a new
  write path. Open asks are read from the blackboard `## Blockers` section (see
  `coga.blackboard.open_blockers`, already imported by megalaunch).

### The status-flow decision (locked with Nick — option A)

`coga bump` requires `status: in_progress`. For the session to flow from
"resolve the blocker" into "do the step and bump" without a second launch, we
chose **option A**: an interactive launch of a blocked ticket reactivates it
inline the same way launch already inline-activates a draft/paused ticket —
`blocked → active → in_progress` up front — then spawns the agent with a
blocker-resolution preamble. The preamble makes **resolve-or-re-block** the
agent's mandated first action.

- Accepted cost of A: the ticket is briefly `in_progress` while an open ask is
  still unresolved. If the session dies mid-discussion you get an `in_progress`
  ticket with an open blocker — visible drift that `coga status` /
  `coga validate` already surface. This is acceptable because resolving or
  re-blocking is the first thing the composed session is told to do.
- Rejected (option B): leave it `blocked`, have the agent run `coga unblock`
  mid-session (→ `active`) — but then nothing flips it to `in_progress`, `bump`
  refuses, and you need a second launch. Defeats the one-session goal.

### Preamble content

When launch reactivates a previously-blocked ticket in this path, the composed
prompt gains a leading section (a new compose layer or a launch-injected
preamble — implementer's call, but it must be part of the composed prompt, not a
runtime side channel) that:

1. States the ticket was blocked and is being resumed to resolve the blocker.
2. Lists the open asks **verbatim** from the blackboard `## Blockers` section
   (including stale/junk ones, so the human can clear them — e.g. the literal
   `"test"` blocker currently on the drain ticket).
3. Instructs: discuss with the human, reach a resolution, then run
   `coga unblock <slug> --answer "<synthesized resolution>"` to record it, and
   only then proceed to the current workflow step's real work.
4. Instructs: if the human decides it **cannot** be resolved, run `coga block`
   again with the refined reason instead of proceeding.

## Acceptance Criteria

- [ ] Interactive `coga launch <blocked-slug>` (stdin+stdout are TTYs) no longer
      hard-refuses. It reactivates the ticket inline (`blocked → active →
      in_progress`, preserving `step:`) and spawns the agent, exactly like the
      existing draft/paused inline-activation path.
- [ ] The composed prompt for that launch includes a blocker-resolution preamble
      carrying the verbatim open asks from the blackboard `## Blockers` section
      and the resolve-record-or-reblock instructions above.
- [ ] Recording a resolution goes through the existing
      `coga unblock <slug> --answer "..."` path — no new blackboard write path.
- [ ] **Non-interactive / unattended launches of a blocked ticket are
      unchanged**: they still fail loud / refuse. `coga megalaunch` still reports
      `skipped-unresolved-blocker` and never launches a blocked ticket. Add/keep
      a test proving the batch path is untouched.
- [ ] `done` tickets are still refused; draft/paused inline-activation is
      unchanged.
- [ ] The `coga/architecture` and `coga/cli` contexts are updated in the **same
      PR** to describe the new interactive-launch-of-blocked behavior (both the
      live `coga/bootstrap/contexts/...` copy and the packaged
      `src/coga/resources/templates/...` copy stay in sync — see
      `coga/codebase`). Today both say launch flatly "refuses" a blocked ticket;
      that's now conditional on interactive vs. batch.
- [ ] `python -m pytest` passes with new coverage for: interactive blocked →
      inline reactivation + preamble present; non-interactive blocked → still
      refused; megalaunch blocked → still skipped. `coga validate --json` is
      clean.

## Open questions for implement/design

- Exactly how "interactive" is detected at the blocked branch — reuse the same
  TTY check launch already uses to gate interactive launches, so the two agree.
- Whether the preamble is a new named compose layer or a launch-time injected
  block; either is fine if it lands in the composed prompt and is covered by a
  test.

<!-- coga:blackboard -->
## Production notes

This blackboard is for active-work handoff notes. Authoring scratch was cleared at activation; durable requirements belong in the ticket body.
