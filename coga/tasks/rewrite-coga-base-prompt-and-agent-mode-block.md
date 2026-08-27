---
slug: rewrite-coga-base-prompt-and-agent-mode-block
title: Rewrite coga base prompt and agent-mode block
status: in_progress
owner: nicktoper
human: nicktoper
agent: codex
assignee: codex
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
step: 3 (open-pr)
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

## Peer-review notes

Ran `/code-review` (default effort) against the branch diff vs `main`, plus an
independent read. Six findings applied as `ad38f018`; verified each against the
source before acting rather than taking the report at face value.

**Must-fix — escalation guard (would have regressed PR #622).** The trim
rewrote "Only an execution directive appended after the task layers ...
overrides it" to "A later execution directive ... overrides this default."
Confirmed in `compose.py`: agent mode is layer 2 and step skills are layer 6,
so step skills genuinely *are* later. An attended launch composing
`code/implement` ("ask the attending human, or `coga block` in a queue run")
could resolve the conflict by recency and terminate the session with a block
instead of asking. The base prompt's companion sentence ("read every other
instruction to block ... through that mode rule") had been deleted in the same
commit, so both halves of the two-sided guard were gone at once. Both restored.

**Must-fix — microkernel summary contradicted `coga/codebase`.** The new
section enumerated the edge as "skills, `ticket.py`, and aliases" and omitted
the `runner.RECIPES` carve-out that keeps registered `coga run` recipes
(`open_pr.py`, `delete_task.py`) inside core under exception 2. Because the
base prompt composes into *every* launch while `coga/codebase` attaches
per-ticket, the abridged version would often be the only one an agent sees.
Restored the carve-out and the `[aliases]`-vs-`runner.RECIPES` distinction.

**Also fixed:** the no-skip-ahead guard (`coga bump` really does expose `--to`
and `--backward`, documented human-only in `commands/bump.py`); the supervisor
teardown enumeration (`mark done` / `mark canceled` / `block` also end the
session — mattered for the workflow-less `coga mark done` path the prompt still
recommends); two dangling references in the bundled `bootstrap/ticket` skill to
the deleted "YAML discipline" heading; and curly quotes, which no other file
under `src/coga/resources/` uses.

Added `test_compose.py` assertions pinning the restored guards — the existing
test only covered the surviving first half of the attended sentence, which is
why the regression passed CI.

Net size after restorations: 1,091 words vs 1,580 on `main` (31% smaller;
was 38% before the guards came back — a trade worth making).

**Design note for nick, not blocking:** the "Keep Coga small and legible"
section is Coga-repo-specific guidance carried on every launch in every user
repo. It is gated by "When changing Coga itself", and the ticket explicitly
asked for the microkernel framing, so I kept it — but if per-launch token cost
matters more than reach, this section is the first candidate to cut back to a
pointer to `coga/codebase`.

## PR

Rewrite the two package resources composed into every launch — the Coga base
prompt (`src/coga/resources/prompt.md`) and the agent-mode block
(`prompt-agent.md`) — for legibility, and align them with the settled
microkernel/minimal-core direction.

- Consolidates repeated lifecycle, blocking, and escalation prose; merges the
  former "Your task file", "Finishing a step", "Blocking", "FYIs", and "YAML
  discipline" sections into four tighter ones.
- Adds a "Keep Coga small and legible" section stating the microkernel
  boundary: core holds only >=2-consumer shared infrastructure and genuine
  command implementations (including registered `runner.RECIPES` entries);
  skills, a ticket's exact sibling `ticket.py`, and aliases stay at the edge.
- Preserves every behavioral contract: ticket/blackboard fence, bump/step
  transitions, supervisor teardown, human-only `--to`/`--backward`, blocking
  precedence, FYI commands, frontmatter discipline, the attended ask-and-wait
  default, and the always-answer-the-human rule.
- Retargets two references in the bundled `bootstrap/ticket` skill to a
  heading this rewrite removed.

Net effect: 1,580 -> 1,091 words on every composed prompt, with the escalation
and core-boundary contracts stated more precisely than before.

No CLI or composition-order behavior changes.

Test plan: `python -m pytest` (2,112 passed), including new
`tests/test_compose.py` assertions pinning the escalation guard, the
`runner.RECIPES` carve-out, and the human-only bump selectors.
