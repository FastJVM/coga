---
title: Match concurrent Codex sessions to their launch so usage stops undercounting
status: in_progress
owner: nicktoper
contexts:
- dev/code
- dev/checkouts
- coga/usage
- coga/internals/activity-capture
- coga/prompt-composition
- coga/packaging
- coga/testing
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 2 (peer-review)
agent: claude
---

## Description

coga usage reports 20 of 55 Codex sessions last week (Sep 28 - Oct 4) as unknown; their real tokens are about 43% of Codex usage. Give every agent launch a unique marker in the composed prompt and use it to pick the right transcript when several match.

## Context

Usage capture (`src/coga/usage.py`) matches a Codex session to its rollout by
"one new `rollout-*.jsonl` whose `session_meta.cwd` equals the launch cwd and
whose start is in the window". Two launches in one checkout at once, or a
resume, break that and the record becomes `usage_status: unknown` with zero
tokens. Claude is pinned by `--session-id` and is effectively complete; its
resume fallback (`_claude_fallback_transcripts`) has the same ambiguity on a
smaller scale. Diagnosis and numbers are under `## Evidence`.

## Scope

1. **Launch marker.** `spawn_agent_session` (`commands/launch.py`, near the
   `usage_session_id` mint) always mints a uuid, not only when the agent has a
   `session_id_flag`, and the composed prompt carries one line
   `coga-launch: <uuid>` at its **end** (a unique line near the top would break
   cross-session prompt-cache prefixes, e.g. repeated `bootstrap/orient`).
2. **Tie-break by marker.** In `_parse_codex_session`, keep the existing
   filters; when more than one candidate survives, keep those whose first user
   message contains the marker, and accept exactly one. Apply the same
   tie-break to the Claude resume fallback. Exact match only; no heuristic
   (never guess, `coga/principles` #6).
3. **`usage_reason`.** New nullable record field carrying the parser's reason
   for `unknown` (it is already printed to stderr). Old records stay readable.
4. **Provably empty sessions are zero, not unknown.** Only when the pinned
   Claude transcript exists but has no assistant usage: record `ok` with zero
   tokens. A missing Codex rollout stays `unknown` (absence is not proof).

Update the owning contracts in the same PR: `coga/internals/activity-capture`
(matching, `usage_reason`, empty-session rule), `coga/prompt-composition`
(marker line), `coga/usage` if the unknown/floor wording changes, plus the
packaged twins under `src/coga/resources/templates/coga/bootstrap/contexts/`.

## Evidence

### Diagnosis (2026-10-05, from a `bootstrap/orient` session)

All 103 unknown records in `coga/log.md` (of 1002) were matched against this
machine's transcripts: Claude by pinned `session_id` file, else transcripts
with a line `timestamp` inside `started_at..ended_at`; Codex by top-level
rollouts whose `session_meta` start falls in that window, grouped by cwd.

| Cause | n |
|---|---|
| Claude transcript pruned (oldest local 2026-09-05; ~30-day retention) | 37 |
| Codex: >1 new top-level rollouts, same cwd, in window (concurrency) | 36 |
| Codex: candidate exists but not where expected (likely resume of a pre-existing rollout) | 11 |
| Codex: no rollout at all (mostly 6-30 s `orient` quits) | 10 |
| Claude: pinned transcript exists, no assistant usage (3-5 s sessions) | 5 |
| Claude: >1 transcripts in window (resume + concurrency) | 3 |
| schema 1, no window | 1 |

Since 2026-09-05 Claude has only 8 unknowns (5 empty). The gap is Codex.

### Last week (2026-09-28 .. 2026-10-04)

- Reported: 131 sessions, 21 unknown (Claude 1/76, trivial; Codex 20/55).
- Recovered by finding the ticket slug in each candidate rollout's composed
  prompt and taking the last `token_count.info.total_token_usage`:
  13 sessions exact = 52.6M tokens; 5 still ambiguous (2-3 rollouts name the
  same ticket: relaunch/resume), est. ~20M; 2 trivial ~0.
- Codex reported 95.2M vs real ~168M (~43% missing); overall 305M vs ~377M
  (~19% low).
- Slug matching alone resolved 13/18, which is why a per-launch marker should
  close nearly all of it.

### Decisions

- Marker at end of prompt (prompt-cache prefix), exact match only.
- Step 4 kept narrow: only a pinned, existing, empty Claude transcript is zero.
- No backfill of past records.

## Out of scope

- Resumed Codex sessions whose new turns never resend the prompt: may stay
  unknown. Note it in the contract.
- Backfilling past records: the log is append-only; no correction records.
- Claude transcript retention (`cleanupPeriodDays`): Claude Code setting, not
  Coga.

## Acceptance

- Tests in the usage test module cover: two concurrent Codex rollouts in one
  cwd resolve to the marked one; marker absent from all candidates stays
  unknown; a resumed Claude session with two in-window transcripts resolves by
  marker; empty pinned Claude transcript yields `ok`/zero; `usage_reason` is
  set on unknown and round-trips through `load_records`.
- `python -m pytest` and `coga validate --json` pass; packaging twin test
  passes.
- After merge, re-running the diagnosis on a week of new records shows Codex
  unknowns mostly limited to sub-minute or resumed sessions.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: launch-marker-usage-match

## Plan (agreed with owner 2026-10-05)

- Spawn always mints a launch uuid; prompt (and oversized-prompt pointer) ends with `coga-launch: <uuid>`.
- Tie-break only when >1 candidate: Codex = marker in any user/developer `response_item` message (prompt is a user msg after AGENTS.md in normal mode, a developer msg in discussion mode — "first user message" would miss both); Claude fallback = marker in an in-window user line. Tool output never searched (`ps` could leak a sibling's argv).
- `usage_reason` nullable, unknown only, schema stays 2.
- Pinned, existing, empty Claude transcript -> ok/zero.
- Known gaps: Claude discussion mode (marker in system prompt), resumed Codex rollouts.

## Implement handoff (2026-10-05)

Branch `launch-marker-usage-match` pushed, one commit, rebased on `origin/main` (80463f62b).

- `commands/launch.py` `spawn_agent_session`: always mints `launch_marker = uuid4()`, appends `\n\ncoga-launch: <uuid>\n` after `prompt_suffix` (so it's in `excluded_user_texts` too); `_argv_prompt` pointer repeats the line; passes `launch_marker` to `capture_session`. Claude `--session-id` minting unchanged.
- `usage.py`: `LAUNCH_MARKER_PREFIX`/`launch_marker_line`; `_codex_rollout_has_marker` (user/developer `response_item` messages only), `_claude_transcript_has_marker` (in-window `user` lines, text blocks only); tie-break runs only when >1 candidate, exactly one marked wins. `UsageRecord.usage_reason` (unknown only, schema stays 2). Pinned-existing-empty Claude transcript -> ok/zero; empty fallback stays unknown.
- Docs + packaged twins: activity-capture (marker, tie-breaks, usage_reason, empty rule, known gaps), prompt-composition (`### Launch marker`), usage (usage_reason / provably-empty sentence).
- Tests: 7 new in `tests/test_usage.py` (codex user+developer marker resolve, marker only in tool output stays unknown, marker absent stays unknown, claude resumed resolve, empty pinned = zero, empty fallback unknown, usage_reason round-trip); `tests/test_launch.py` pins `uuid4` for exact-argv tests + pointer marker test.

Verification:
- `PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q -p no:cacheprovider` -> 3270 passed, 1 failed. The failure, `tests/test_edge_distribution.py::test_documented_legacy_adoption_preserves_state_and_reconciles_callers`, also fails on untouched base (expects `_custom-phone-home` first in live `coga/recurring/` ordering) — pre-existing, unrelated; needs its own ticket.
- `coga validate --json` (repo): 1 error, pre-existing on base (`marketing/readme-top` unsynthesized-draft-blackboard). `example/`: no issues.

Known gaps (documented): Claude discussion launches (marker goes to system prompt), resumed Codex rollouts (excluded by the pre-spawn snapshot).
