---
slug: select-session-conduct-instead-of-appending-a-cont
title: Select session conduct instead of appending a contradiction
status: active
owner: nicktoper
human: nicktoper
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

Session conduct is currently authored as a contradiction. The base prompt
always composes `## Working with the human` (attended: ask the human and wait).
For a queue run, `coga megalaunch` / `coga recurring` then append a block
*after the task layers* that negates it. Every queue prompt therefore carries
both the rule and its inverse, and the agent must resolve them by precedence.

Replace that with selection: compose exactly one conduct block — **attended**
or **queue** — chosen by launch context. Never both.

## Context

**Today there are three documents describing conduct, one contradicting the
other two:**

| document | when | size |
|---|---|---|
| `prompt.md` § Working with the human | always | attended default |
| `prompt-megalaunch.md` | appended for megalaunch | 33 lines |
| `prompt-queue.md` | appended for recurring | 29 lines |

The two appended files are ~80% the same content, differently worded — both
say TTY-is-transport, state-your-plan-and-continue, and block-terminally
rather than asking. They genuinely differ in about four lines each:
megalaunch carries the dependency-drain slug hint and the
blocker-resolution exception; recurring carries the stateless-bootstrap
`coga slack` completion signal.

**What the contradiction costs.** The precedence machinery in the base prompt
exists only to manage it:

- "authoritative over any generic instruction elsewhere in this prompt, the
  workflow, or a step skill"
- "Only an execution directive appended *after* the task layers ... overrides it"
- "A workflow or step skill is composed later in this prompt and still does not"
- the companion rule in § Blocking and FYIs

plus six pinned assertions in `tests/test_compose.py`
(`test_compose_agent_prompt_attended_ask_and_wait`). Under selection, most of
that prose has nothing left to disambiguate, and the guards become the simpler
and stronger claim: *exactly one conduct block is composed, and it is the right
one.*

**This is not a revert to `mode_prompt`.** That layer was removed because its
selector was a **ticket field** (`autonomy:`, then `mode:`), and how a session
executes is not a property of the task — see #545. The selector here is
**launch context** (queued vs. attended), which is the honest axis. Same shape,
different and correct reason. It does partially undo the merge in
`475d4645`; that merge was right for the code as it stood, when conduct had one
unconditional value and nothing to select between.

## Design questions for step 1

- Where do the two variants live? Separate package resources selected at
  compose time is the obvious shape, but it reinstates a conditional layer —
  name it for what it actually selects.
- Does the base prompt keep *any* conduct prose, or does the whole section move
  into the selected block? Keeping half in each rebuilds the split.
- Do `prompt-megalaunch.md` and `prompt-queue.md` collapse into one queue
  variant plus a short caller-specific tail, or stay two?
- The blocked-resume preamble (`prompt-blocker-resolution.md`) is a separate
  concern and should stay out of this.
- Migration: `coga/architecture`'s prompt-composition section documents the
  layer list, and both twin copies need updating.

## Risk

This is the highest-consequence prose in the system, and it fails badly in
both directions. An agent that asks-and-waits inside a queue hangs it until a
liveness backstop tears the session down and records the task failed, notifying
nobody. An agent that terminally blocks in an attended session parks a ticket
the human was sitting right there to answer. Step 2 is an owner review gate for
that reason.

## Origin

Found while trimming composed-prompt size in PR #726, which is where the
`mode_prompt` merge landed. Fourth in a run of fossils from two primitive
collapses (`autonomy` removal, and #427's three-files-to-one). Deliberately
kept out of #726 to keep that review scoped.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
