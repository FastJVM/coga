---
name: test/relaunch-chain
description: Synthetic probe for the coga launch auto-relaunch chain. Five steps deliberately arranged claude → claude → codex → human → claude so a single run exercises every boundary type — same-agent auto-relaunch, agent rotation, the human gate, and resumption after a human — while each step writes a section of a throwaway doc and logs what the supervisor actually did. Not a real delivery workflow; it exists to test coga itself.
steps:
  - name: draft
    assignee: agent
  - name: expand
    assignee: agent
  - name: peer-pass
    assignee: other-agent
  - name: human-check
    assignee: owner
  - name: finalize
    assignee: agent
---

## How this workflow probes the chain

The `coga launch` supervisor auto-relaunches the next step **only when the
resolved `assignee:` is unchanged** across the bump (see `commands/launch.py`
`_harness_stop_reason`). It stops on any assignee change, on human-owned steps,
on `done`/`paused`/`blocked`, and on non-zero exit. Skill-less agent steps still
chain (absence of skills is no longer a stop condition).

The step order is chosen so one run hits every boundary type exactly once:

| boundary | transition | expected per current code |
| --- | --- | --- |
| draft → expand | claude → claude | **auto-relaunch** (same assignee) |
| expand → peer-pass | claude → codex | **stop** — human must `coga launch` |
| peer-pass → human-check | codex → human | **stop** at the human gate |
| human-check → finalize | human → claude | **stop** — human must `coga launch` |

The "expected" column is the prediction under test, not ground truth. Each step
records what actually happened in the blackboard; a mismatch is the finding.

Every step needs exactly two `[agents.*]` configured (claude + codex) for
`other-agent` on `peer-pass` to resolve unambiguously.

## draft

You are **claude**, the first step. Create `artifact.md` in the task directory
with a top heading `# Coga relaunch chain — test artifact` and a first section
`## 1. draft (claude)` containing one or two sentences of throwaway prose (any
neutral content — this doc is a vehicle, not a deliverable). Then follow the
blackboard logging protocol in the ticket's `## Context` and `coga bump`.

## expand

You are **claude** again, and if the chain works you were **auto-relaunched by
the supervisor** with no human `coga launch` in between — that is the single
most important thing this run is testing, so confirm it explicitly in your log
entry. Append a section `## 2. expand (claude)` to `artifact.md` with another
sentence or two. Log per the protocol, noting whether you were auto-relaunched
or hand-launched and whether the previous REPL torn down cleanly, then
`coga bump`.

## peer-pass

You are **codex**, the other agent. Reaching you required the supervisor to
either relaunch across the claude → codex assignee change (surprise) or stop so
a human relaunched you (expected). State which, in your log entry. Append a
section `## 3. peer-pass (codex)` to `artifact.md`, log per the protocol, then
`coga bump`.

## human-check

Human step. Read `artifact.md` and the blackboard's `## Relaunch test log` so
far. Optionally append a `## 4. human-check (human)` note. Then `coga bump` to
hand to `finalize`. (You may also be the one running `coga launch` for the
agent steps that the supervisor did not auto-chain — note that in the log if
so.)

## finalize

You are **claude**, the last step. You were reached across a human → claude
boundary (expected: stop, so a human launched you — confirm in your log).
Append a closing section `## 5. finalize (claude)` to `artifact.md`, write your
final log entry summarizing the whole chain's boundary-by-boundary behavior,
then — this is the last step — run `coga mark done <slug>` instead of
`coga bump`.
