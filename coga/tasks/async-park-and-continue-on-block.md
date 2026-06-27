---
slug: async-park-and-continue-on-block
title: Async park-and-continue on block
status: in_progress
autonomy: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts:
- coga/architecture
- coga/cli
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
step: 4 (review)
---

## Description

When an unattended (overnight/auto) ticket hits a blocker, it should **park the
question and let the sweep keep going** — not stall the whole run waiting on a
human who is asleep. The motivation is token utilization: one blocked ticket
must not idle the rest of the night.

The chosen model is **clean async park**, not a live waiting terminal (owner
decision). It leans on Relay's existing stateless-session property: the prompt
is a pure function of the files on disk, so a parked ticket can be reconstructed
and resumed later with no live process held open.

Behavior:

1. **Park** — on a blocker, the agent writes the specific question/blocker to
   the blackboard (working section) and calls `relay panic` so it posts to
   Slack naming the owner with the blocker reason and the action needed. (Today
   panic already leaves the ticket `in_progress` and writes a `PANIC` marker —
   build on that, don't reinvent it.)
2. **Keep sweeping** — the recurring/drain sweep advances to the next ready
   ticket instead of aborting the remaining queue when a ticket parks. Confirm
   and, if needed, fix that a panic/non-zero exit from one task does not bail
   the rest of the sweep.
3. **Resume on answer** — define the handshake: once the human answers (edits
   the blackboard / clears the block), the next `relay launch` / sweep resumes
   the parked ticket from its current step, reading the answer out of the
   blackboard. No live terminal, no nested session.

Pairs with `issue-inbox-slack` (panics carrying the blocker reason + required
action + a link to the next command) — the park message should be readable and
actionable straight from Slack.

## Context

This refines the panic/escalation model, so respect its current invariants
(see the base prompt + `relay/cli`): panic is the blocker channel (not routine
handoff), and agents do not launch nested sessions. The change is "park cleanly
and let the sweep continue + resume statelessly," **not** "keep trying after a
panic." Read `relay/architecture` on stateless sessions and the recurring
sweep's sequential, one-live-task-per-template behavior before changing the
sweep loop (`src/relay/commands/recurring.py`).

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: async-park-continue
worktree: /tmp/coga-async-park
pr: https://github.com/FastJVM/coga/pull/468

Notes:
- Implementation launched from prompt step `implement`, but the live ticket frontmatter still says `status: draft`; verify before final `coga bump`.

Implementation:
- Commit: d92bd679 Let recurring sweeps park panicked tasks.
- `coga recurring` now snapshots the task blackboard before launch and treats a new `## Blockers` entry plus `status: in_progress` as an async panic park.
- The sweep continues to the next due task for both observed panic forms: a non-zero launch exit and a done-marker return after the blocker was written.
- Arbitrary launch failures and unfinished non-interactive tasks without a new blocker still fail/stop as before.
- Updated recurring/sync/CLI contexts to document the blocker-based resume handshake.

Verification:
- `python -m pytest tests/test_recurring.py -q` — 84 passed.
- `python -m pytest` — 899 passed, 1 skipped.
- `git diff --check` — passed.
- `PYTHONPATH=/tmp/coga-async-park/src python -m coga.cli validate --json` — failed on existing unrelated repo task drift (bad install/README frontmatter, install/* missing blackboard fences/autonomy, several missing-step/unknown-assignee warnings); no new validation issue tied to this change identified.

Peer review:
- [2026-06-26 22:32] [agent:codex] `codex review --base main` found one must-fix: if a launch returns `"timeout"` after writing a blocker, the new blocker-detection path classifies it as an async park before the watchdog timeout path can pause/log it. Fixing by preserving timeout handling ahead of async-park classification.
- [2026-06-26 22:39] [agent:codex] Applied peer-review fix in commit ed76ced8 (`peer-review: preserve recurring timeout handling`): post-launch async-park classification now skips watchdog timeouts, and `tests/test_recurring.py` covers timeout-after-blocker as a pause/logged timeout rather than an in-progress park.
- [2026-06-26 22:39] [agent:codex] Verification after review fix: `python -m pytest tests/test_recurring.py -q` — 85 passed; `python -m pytest` — 900 passed, 1 skipped; `git diff --check` — passed.

---

## Blockers

- [2026-06-26 21:59] [agent:claude] Implementation is committed on branch async-park-continue at d92bd679, but coga bump cannot advance because the live ticket frontmatter is status: draft. Launch/activate the task into in_progress, then rerun coga bump to hand off to peer-review.

- [2026-06-26 22:03] [agent:claude] Implementation is committed on branch async-park-continue at d92bd679, but coga bump cannot advance because the live ticket frontmatter is status: draft. Launch/activate the task into in_progress, then rerun coga bump to hand off to peer-review.

## Usage

{"agent":"codex","cache_creation_input_tokens":null,"cache_read_input_tokens":2934400,"cli":"codex","input_tokens":154521,"model":"gpt-5.5","output_tokens":7115,"provider":"openai","schema":1,"session_id":"019f077c-30e3-7d92-82f1-ccb41abd64e2","slug":"async-park-and-continue-on-block","step":"peer-review","title":"Async park-and-continue on block","ts":"2026-06-27T05:24:44.583580Z","usage_status":"ok"}
