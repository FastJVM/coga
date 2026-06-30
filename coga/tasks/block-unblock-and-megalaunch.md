---
slug: block-unblock-and-megalaunch
title: Block, unblock, and megalaunch
status: in_progress
autonomy: interactive
owner: nick
human: nick
agent: codex
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

Replace the current "panic parks a recurring task" design with first-class
blocking and megalaunch semantics.

The product decision is that a blocked ticket is normal workflow state, not a
panic. Remove the `coga panic` command and replace it with `coga block` /
`coga unblock`, make `blocked` a real ticket status, teach status to show why a
ticket is blocked and where it is blocked, and build a budget-aware "work all
launchable tickets" path that can attempt active work until tasks finish, hand
off, run out of budget, or block.

Desired model:

1. **Block** — an agent that needs human input calls
   `coga block --task <slug> --reason "<specific ask>"`. The command appends a
   blocker entry to the task blackboard, logs/notifies/syncs through the normal
   surfaces, preserves `step:`, transitions the ticket to `status: blocked`, and
   ends the launched session. This replaces `coga panic`; do not keep `panic` as
   the product surface.
2. **See why/where** — `coga status` must make blocked work legible without
   opening each ticket. It should show the blocked status, current step, owner,
   every open blocker cause (not just the latest one), blocker age/reason, and
   the next command. A focused blocked view such as `coga status --blocked` or
   `coga blockers` is acceptable if the main status table stays readable; the
   focused view should expand multi-blocker tickets so a human can see all
   outstanding asks in one place.
3. **Unblock** — `coga unblock <slug>` is the human answer path. With
   `--answer "<text>"` it records the answer non-interactively; without an
   answer it should run an attended prompt, similar in spirit to `coga ticket`,
   showing the blocker and asking for the answer/resolution. It appends the
   answer to the blackboard, marks the blocker resolved, and transitions
   `blocked -> active` while preserving `step:` so any later `coga launch` can
   resume the same workflow step from files.
4. **Megalaunch** — add one `megalaunch` engine that attempts launchable work
   sequentially. A `coga megalaunch` command/alias should let a human run it on
   demand, and a daily recurring task script should run the same engine for
   overnight/background work. Both surfaces should share the same eligibility,
   budget, and result accounting code. Despite the name, this is not parallel
   fire-and-forget: it is sequential, budget-gated, and conservative.
5. **Attempt all launchable active work** — the megalaunch path should
   not depend on a durable ticket-level `autonomy:` category. Eligible work is
   determined by the live ticket state: `status: active`, current step is
   agent-owned, assignee resolves to a configured agent, no open blocker, no
   owner/review gate, launch/auth/worktree checks pass, and the assigned agent
   has enough remaining budget.
6. **Manage token consumption** — before each launch, check the assigned
   agent's remaining usable budget against a guard. Do not start a launch that
   is unlikely to complete. The run record should distinguish launched,
   completed, blocked, skipped-human-gate, skipped-unresolved-blocker,
   skipped-budget, and failed.
7. **Daily recurring runner** — add or update a daily recurring task that runs
   the same megalaunch engine. It should be safe to invoke manually and on
   schedule, use the shared budget guard, and leave a compact run summary with
   counts and per-ticket outcomes.
8. **Trim run blackboards** — keep recurring/megalaunch blackboards bounded.
   Preserve unresolved blocker asks, the latest run summary, and any durable
   decisions, but trim or compact old per-run noise so the next launch prompt
   does not grow forever. The trimming rule should be deterministic and tested.
9. **Invocation decides attended vs unattended** — manual `coga launch` stays
   attended by default; megalaunch/recurring runs use unattended launch policy.
   If this removes the durable `autonomy:` field from tickets, update the
   canonical ticket schema, create/ticket/validate/launch docs, templates, and
   seeded examples in the same PR.

Non-goals:

- No live waiting terminal.
- No nested agent sessions.
- No Slack app/buttons/server; markdown remains the source of truth.
- Do not land the superseded PR #468 implementation as-is.

## Context

This is now a broader Coga workflow-model change, not a narrow recurring patch.
Read `coga/architecture`, `coga/cli`, `coga/sync`, and the current direction
contexts before implementing. Behavior changes must update both live Coga
contexts under `coga/contexts/coga/` and packaged copies under
`src/coga/resources/templates/coga/bootstrap/contexts/coga/` where those copies
exist.

Important constraints:

- `blocked` should be command-owned, just like `active`, `in_progress`,
  `paused`, and `done`; agents and humans should not hand-edit status.
- The blackboard remains the durable explanation layer. Status tells the queue
  that the task is blocked; the blackboard carries the blocker reason and
  answer.
- `paused` still means intentionally shelved. `blocked` means waiting on a
  concrete answer.
- The existing PR #468 branch is closed/superseded. Start implementation from
  this revised spec rather than trying to incrementally patch that diff.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

Current direction:
- [2026-06-29] Ticket renamed from `async-park-and-continue-on-block` to `block-unblock-and-megalaunch` because the scope is no longer the narrow async-park PR. Historical log and usage entries may still name the old slug.
- [2026-06-29] Owner rejected landing the narrow async-park PR as-is. PR #468 was closed and the task body was rewritten around first-class `coga block` / `coga unblock`, real `status: blocked`, blocked-status visibility, and a shared budget-aware `megalaunch` engine for CLI + recurring use. The `async-park-continue` branch/worktree below are historical/superseded implementation evidence, not the implementation path to continue from.
- [2026-06-29] Manual queue-state repair: this ticket had been marked `done` during owner review even though the revised implementation never existed. Reopened to `in_progress`, restored `step: 1 (implement)`, and assigned implementation to `codex` so the revised spec can actually execute.

branch: block-unblock-megalaunch
worktree: /tmp/coga-block-unblock
commit: 9d274705 peer-review: fix megalaunch budget/eligibility bugs and doc sync (rebased onto origin/main)
pr: https://github.com/FastJVM/coga/pull/483
superseded-pr: https://github.com/FastJVM/coga/pull/468

Notes:
- Historical `async-park-continue` / PR #468 implementation is closed and superseded.
- Revised implementation was originally committed on `block-unblock-megalaunch` at `1b455351`; peer-review fixes were first applied at `f01d94f7`, then rebased to `9d274705` during open-pr.
- [2026-06-30] Opened PR #483 from `block-unblock-megalaunch` to `main`. GitHub initially reported conflicts, so the branch was rebased onto `origin/main`, conflicts in `src/coga/blackboard.py` and `src/coga/cli.py` were resolved by keeping `main`'s production-note/state-sweep behavior plus this branch's blocker/megalaunch behavior, and the rebased branch was force-pushed with lease. GitHub now reports the PR as `MERGEABLE`; `gh pr checks 483` reports no checks on the branch.
- [2026-06-30] Rebase verification: `PYTHONPATH=src python3.12 -m pytest -q` — 944 passed, 1 skipped; `git diff --check` — passed; `PYTHONPATH=src python -m coga.cli validate --task block-unblock-and-megalaunch --json` — passed (`ok_count: 1`); CLI smoke `PYTHONPATH=src python -m coga.cli --help`, `block --help`, and `megalaunch --help` — passed.

Revised implementation:
- Added first-class `coga block` and `coga unblock`; removed `coga panic` from the CLI surface.
- Added real `status: blocked`, blocker parsing/resolution in task blackboards, blocked-task status expansion via `coga status --blocked`, and launch refusal for blocked tickets until answered.
- Added shared `coga.megalaunch` engine plus `coga megalaunch` command and daily `recurring/megalaunch` script task using the same budget guard and result accounting.
- Updated live Coga OS contexts/skills/workflows and packaged templates to describe block/unblock/megalaunch semantics.

Verification (revised implementation):
- `PYTHONPATH=src python -m pytest -q` — 907 passed, 1 skipped.
- `git diff --cached --check` — passed before commit.
- `PYTHONPATH=src python -m coga.cli validate --task block-unblock-and-megalaunch --json` — passed (`ok_count: 1`).
- CLI smoke: `PYTHONPATH=src python -m coga.cli --help`, `block --help`, and `megalaunch --help` all show the new commands.

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
- [2026-06-29] [agent:claude] Peer review of the revised `block-unblock-megalaunch` branch @ `1b455351` (`/code-review --base main`, 8 finder angles + verify). The block/unblock/status/validate surfaces are solid (blocked threaded through VALID_STATUSES, launch refusal, workflow-required check; `--blocked` expands every open ask; attended+non-interactive unblock; panic cleanly removed; deterministic+tested blackboard trim). Found two must-fix correctness bugs in the megalaunch engine plus one doc-sync miss; applied fixes in commit `f01d94f7`:
  - **Budget guard broken across tasks** (`megalaunch.py`): the `records` usage snapshot was loaded once and never refreshed, so task 2..N's budget check saw zero of the tokens earlier tasks in the same run spent. Fixed by reloading usage per task. Regression test `test_megalaunch_budget_refreshes_across_tasks`.
  - **Non-active tickets treated as launch candidates** (`megalaunch.py`): `_candidate_result` returned None (=launch) for any non-active/non-blocked status, so done/draft/paused tickets fell through to `_launch_until_stop`, failed preflight, and landed as `failed` — making every run report failures and exit 1 (nightly recurring returned failed every fire). Fixed by skipping non-{active,blocked} tickets in the run loop (also closes the in_progress script/blocker-gate bypass). Regression test `test_megalaunch_ignores_non_active_tickets`.
  - **Live `coga/contexts/dev/code` left stale**: still said `coga panic` while its packaged twin was updated. Synced to `coga block`. Also updated README (block/unblock/megalaunch/`--blocked` + lifecycle) per owner's chosen scope.
  - Skipped as nits (noted for later, not blocking): reuse cleanups (`usage.rollup`/`_parse_ts`/`_harness_stop_reason` duplication), per-step double-compose/git-auth efficiency, unconditional blocker-parse in plain `coga status`, and `mark_blocked` write-before-validate ordering (consistent with existing `mark_*`).
  - Verification: `PYTHONPATH=src python3.12 -m pytest -q` — 909 passed, 1 skipped; `git diff --check` — clean. No live context still references `coga panic`. The live/packaged `architecture` drift is pre-existing (secrets-model/terminology, live is ahead) and out of scope.

Owner review assist:
- [2026-06-27 22:13] [agent:codex] Inspected PR #468 at head ed76ced8. GitHub reports the PR open, non-draft, MERGEABLE, with no status checks configured/reported and no PR comments. Local checks in `/tmp/coga-async-park`: `PYTHONPATH=src python -m pytest tests/test_recurring.py -q` — 85 passed; `PYTHONPATH=src python -m pytest -q` — 900 passed, 1 skipped; `PYTHONPATH=src python -m coga.cli validate --task async-park-and-continue-on-block --json` — ok_count 1, no issues. No owner-review blocker found; local `git merge-tree main HEAD` was not rerun after sandbox read-only git metadata because GitHub reports the PR mergeable.
- [2026-06-29 22:20] [agent:codex] Rechecked the renamed/re-scoped ticket at `step: 4 (review)`. PR #468 is closed unmerged with owner comment saying the ticket is being rewritten around removing `coga panic` in favor of block/unblock plus broader drain/status design. Only open GitHub PR is unrelated docs cleanup #470. Local source search still finds `coga panic` registered in `src/coga/cli.py` and no `block`, `unblock`, `megalaunch`, or `status: blocked` implementation in `src/`/tests. `PYTHONPATH=src python -m coga.cli validate --task block-unblock-and-megalaunch --json` passed (`ok_count: 1`). Review recommendation: there is no current implementation PR to approve for the revised scope; return this ticket to implementation or open a new implementation branch/PR before owner review.

---

## Blockers

- [2026-06-26 21:59] [agent:claude] Implementation is committed on branch async-park-continue at d92bd679, but coga bump cannot advance because the live ticket frontmatter is status: draft. Launch/activate the task into in_progress, then rerun coga bump to hand off to peer-review.

- [2026-06-26 22:03] [agent:claude] Implementation is committed on branch async-park-continue at d92bd679, but coga bump cannot advance because the live ticket frontmatter is status: draft. Launch/activate the task into in_progress, then rerun coga bump to hand off to peer-review.

## Usage

{"agent":"codex","cache_creation_input_tokens":null,"cache_read_input_tokens":2934400,"cli":"codex","input_tokens":154521,"model":"gpt-5.5","output_tokens":7115,"provider":"openai","schema":1,"session_id":"019f077c-30e3-7d92-82f1-ccb41abd64e2","slug":"async-park-and-continue-on-block","step":"peer-review","title":"Async park-and-continue on block","ts":"2026-06-27T05:24:44.583580Z","usage_status":"ok"}

{"agent":"claude","cache_creation_input_tokens":291708,"cache_read_input_tokens":1575817,"cli":"claude","input_tokens":19315,"model":"claude-opus-4-8","output_tokens":16395,"provider":"anthropic","schema":1,"session_id":"4bd8aa99-3833-4809-a2bb-042dbb0cce43","slug":"async-park-and-continue-on-block","step":"open-pr","title":"Async park-and-continue on block","ts":"2026-06-27T22:05:12.337734Z","usage_status":"ok"}

{"agent":"codex","cache_creation_input_tokens":null,"cache_read_input_tokens":1997696,"cli":"codex","input_tokens":239243,"model":"gpt-5.5","output_tokens":11470,"provider":"openai","schema":1,"session_id":"019f0b21-3288-72a1-9c69-5f50041dca88","slug":"async-park-and-continue-on-block","step":"review","title":"Async park-and-continue on block","ts":"2026-06-28T21:25:25.031685Z","usage_status":"ok"}

{"agent":"codex","cache_creation_input_tokens":null,"cache_read_input_tokens":501120,"cli":"codex","input_tokens":169078,"model":"gpt-5.5","output_tokens":5135,"provider":"openai","schema":1,"session_id":"019f1576-32f3-7bd3-80a1-7ac32fddb9cc","slug":"block-unblock-and-megalaunch","step":"review","title":"Block, unblock, and megalaunch","ts":"2026-06-29T22:21:58.534443Z","usage_status":"ok"}

{"agent":"codex","cache_creation_input_tokens":null,"cache_read_input_tokens":3428224,"cli":"codex","input_tokens":119900,"model":"gpt-5.5","output_tokens":15047,"provider":"openai","schema":1,"session_id":"019f1a85-6be6-71c1-8ced-fbde4f702dab","slug":"block-unblock-and-megalaunch","step":"open-pr","title":"Block, unblock, and megalaunch","ts":"2026-06-30T22:07:20.813901Z","usage_status":"ok"}
