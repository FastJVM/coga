---
title: Prevent duplicate session usage records from inflating totals
status: in_progress
owner: nicktoper
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
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
step: 2 (evaluate-design)
agent: claude
launch_generation: 7e5efbc2-ae30-417d-bf15-8af89bc9ac84
---

## Description

Investigate identical session usage records appearing multiple times, distinguish duplicate writes from merge=union duplication, and make usage accounting count each logical record once without collapsing distinct launches or legitimate session segments.

Done when regressions cover repeated capture, duplicate lines after union merges, distinct sessions with equal token counts, records without session_id, and the supported legacy record schemas (v1 and v2, both accepted by `usage` record parsing). Pin the safe record identity before choosing writer idempotency, reader deduplication, or both. Verify coga usage totals and identify any other affected consumers. A consumer that reads records through the fixed `usage` path is covered and verified here. A consumer with its own reader gets a follow-up ticket, named on the blackboard, unless its fix is trivial. Preserve the append-only audit history; do not rewrite old logs as a shortcut.

**Design finding (2026-10-08).** The duplicates are real and reproduced, and they come from the union landing path in `git.publish`. They are not double writes by launch capture. The report's "12 sessions, 2–4 copies, 2026-08-31 → 2026-10-01" matches **this repo's** `coga/log.md` exactly. Thinkpick, magicator, and multiply carry the same defect at smaller counts (evidence is on the blackboard). In every one of the 24 duplicated records across four repos, each extra copy was added by a *later* commit (a `Log: …`, `Sync coga state`, or `Ticket: …` publish, or a squash-merged PR), never by the commit that wrote the original. That rules out `capture_session` writing twice, and none of the copies came from a git merge commit. Writer idempotency in `append_record` would therefore fix nothing. This ticket fixes the reader. The publish-path root cause gets its own follow-up ticket (see Out of scope).

### Pinned record identity

A logical usage record is **the exact JSON message text of its log line**: the bytes after the `YYYY-MM-DD HH:MM [<ref>] [<actor>] ` prefix, which is what `_LOG_LINE_RE` group 1 captures. Two lines whose message text is byte-identical are one record. Lines whose message text differs in any byte stay separate records.

Why this is safe:
- Union copies are byte-identical. `git merge-file --union` copies whole lines.
- `capture_session` builds every record once, with microsecond `ts`/`started_at`/`ended_at` taken from that launch's own window, and `UsageRecord.to_json` serializes canonically (`sort_keys`, fixed separators). So two distinct launches never produce identical text, even with equal token counts, no `session_id`, or a shared provider session. Schema-1 records also carry microsecond `ts` (verified in the logs of the local sibling repos).
- `session_id` is **not** the identity. It is null on 66 of this repo's records, and distinct records legitimately share one. This repo has a real case: session `0b93746c…` produced both a `bootstrap/resolve-conflicts` and a `recurring/resolve-conflicts` record, with different `ts` and tokens. Resumed or chained segments can share one too.
- The parsed `UsageRecord` value is not the identity either. Text equality is the more conservative rule, because it never merges two lines that differ in any byte.

### Acceptance criteria

- [ ] `usage.load_records` returns each logical record (identity above) once, keeping first-occurrence order, however many times its line appears in `coga/log.md`.
- [ ] Regression tests in `tests/test_usage.py` cover all of the following:
  - [ ] **Union duplicate**: a log built by actually running `git merge-file --union` through `git._merge_union_bytes`. The base lacks record X; control has X followed by Y; the working copy has a local-only line Z followed by X. This yields X twice, which `load_records` returns once, and `rollup` totals equal the single-copy totals. Also check the hand-written variants seen in the wild: non-adjacent copies, and x3/x4 copies.
  - [ ] **Repeated capture**: two `capture_session` calls for two launches with identical `ParsedUsage` (same tokens and the same `session_id`, as when a provider session is resumed) but different windows produce two records, and both count. Appending one identical `UsageRecord` twice via `append_record` loads as one.
  - [ ] **Distinct sessions with equal token counts**: two records that differ only in `session_id` and `ts` both count.
  - [ ] **No `session_id`**: two `session_id: null` records with different `ts` both count. An identical duplicate of one of them collapses. This also covers an `unknown` record: `unknown_sessions` is counted once per logical record.
  - [ ] **Legacy schemas**: an identical duplicated schema-1 line collapses, and so does an identical duplicated schema-2 line. A schema-1 and a schema-2 record that agree on every field they share both stay counted, because their text differs.
- [ ] `coga usage --json` over a duplicated fixture reports the deduplicated `sessions`, `unknown_sessions`, and token totals. Add this test where `commands/usage.py` is already exercised.
- [ ] The usage-report recurring job, which calls `load_records` → `rollup`, reports deduplicated totals over a fixture with duplicate lines. Add this test to `tests/test_usage_report.py`.
- [ ] `scripts/human_minutes.py` `parse_log` no longer collapses distinct usage records that share a `session_id`. Its existing whole-line dedupe already removes union copies. A new test in `tests/test_human_minutes_script.py` shows that two distinct records sharing a `session_id` both reach `usage_records`. The existing `test_union_log_duplicates_and_free_form_text_do_not_change_ledger` still passes.
- [ ] No existing `coga/log.md` is rewritten. `coga show` and the raw log still display every line.
- [ ] The docs record the identity and the union-duplication fact. `docs/contexts/coga/usage/SKILL.md` (and its packaged twin) gets the identity, and `docs/contexts/coga/internals/spool-merge/SKILL.md` (and its twin) gets the union-duplication fact. `python -m pytest` passes, including `tests/test_packaging.py`.
- [ ] Verification: run `coga usage --json --by task` in this repo before and after the change and put both numbers in the PR. Expected before: 1107 sessions, 115 unknown, 6,485,226,704 total tokens, as of 2026-10-08. Expected after: 1090 sessions, 114 unknown, 6,424,868,634 total tokens. Lines appended after 2026-10-08 will move these numbers, so recompute rather than assert them.

### Proposed shape

1. **`src/coga/usage.py` `load_records()`**: keep a `seen: set[str]` of `match.group(1)` texts. Skip a line whose message text is already in `seen`. Add a text to `seen` only after `UsageRecord.from_json` succeeds, so non-record lines are unaffected. Update the docstring to name the identity and why union can duplicate. `rollup()`, `capture_session()`, and `append_record()` stay unchanged. Every consumer goes through `load_records`, so deduping at the loader, not in `rollup`, covers `coga usage` and usage-report together.
2. **`scripts/human_minutes.py` `parse_log()`**: delete the `seen_usage_sessions` collapse and keep the `seen_lines` dedupe. Reword the adjacent comment so it no longer claims that collapsing by `session_id` is what prevents double counting.
3. **Tests** as listed in the acceptance criteria. Build the union fixture with `coga.git._merge_union_bytes` and plain byte strings; no git repo is needed.
4. **Docs**:
   - `coga/usage`, section "The read API": `load_records` returns each logical record once; the identity is the exact JSON message text; say why `session_id` is not the identity; duplicate lines stay in the log (append-only) and are only collapsed at read time.
   - `coga/internals/spool-merge`, section "`merge=union` files": correct the claim that union "never loses or revives anything meaningful" for `log.md`. Union can *duplicate* an appended line when `publish` merges against a merge base that predates a line already on control. Any reader that counts log lines must collapse byte-identical copies, as `usage.load_records` does.
   - Edit the canonical `docs/contexts/...` files and the packaged twins under `src/coga/resources/templates/coga/bootstrap/contexts/coga/{usage,internals/spool-merge}/SKILL.md` identically.
   - `coga/internals/activity-capture` keeps "exactly one record" per launch, which stays true. Change it only if a sentence there contradicts the new read rule.

### Out of scope

- **Fixing the publish-path root cause.** `git._build_tree` union-merges with `ancestor = merge-base HEAD <control>`. When the checkout's HEAD lags a line that is already on control, `git merge-file --union` re-adds that line. Fixing this changes the state-publication contract, and it affects every `log.md` line, audit lines included. It goes to a follow-up ticket, proposed on the blackboard.
- Writer idempotency in `append_record` or `capture_session`. No double write was found.
- Rewriting or compacting any existing `coga/log.md`, or deduping `coga show` output.
- `src/coga_edge/phone_home.py` telemetry. It counts only movement lines, never usage records, and already applies `set()` to the new lines it scans. Session and token records are verifiably excluded from the snapshot, so it is not affected.
- `docs/evidence/velocity.md`'s inline script. It counts the set of distinct tasks per week, so it is not affected by duplicate lines.

## Context

### Report relayed by the owner — 2026-10-07

Another AI reports 12 sessions with identical usage records repeated two to four times between 2026-08-17 and 2026-10-01, plus duplicate lines introduced by merge=union in thinkpick's log. The underlying excerpts were not supplied; reproduce counts and identify the repository before claiming a cause.

The owner has no excerpts to add; reproducing is part of the work. A local checkout of thinkpick exists at `~/Code/thinkpick`. Its `coga/.gitattributes` sets `**/log.md merge=union` and `**/retires.md merge=union`, so the union path is live there. As of 2026-10-08, though, its current `coga/log.md` is only 40 lines with 3 usage records, and that file's 20-commit history shows only about 6 `"schema"` lines. So the reported duplicates probably sit on other branches, in other repos, or in history before compaction. Find where they actually are before treating thinkpick's current log as the reproduction.

The only record key that looks like an identity is `session_id`, and it is optional. Resumed segments can also share one provider session, so the design must name the record identity explicitly. `load_records` reads only the current `coga/log.md` and has no dedup today. If the design finds real double writes in launch capture rather than union duplication, consider splitting the writer fix from the reader dedup at the design gate.

This differs from the done dedupe-claude-transcript-usage-by-message-id ticket: that work deduplicates message events within a provider transcript, not whole session records stored in log.md. Start with `src/coga/usage.py::append_record`, `load_records`, and their launch callers, then the log union-merge path. Distinguish the same logical record repeated from different launches or resumed segments sharing a provider session.

The reported inflation of coga usage needs a fixture and corrected before/after totals. Telemetry inflation is unverified: coga/usage explicitly says session activity/token records are excluded from aggregate telemetry. Inspect actual consumers rather than copying that claim as fact. One concrete consumer to check is the phone-home recurring job (`coga/recurring/phone-home/ticket.md` and its `ticket.py`, packaged under `src/coga/resources/templates/coga/recurring/phone-home/`), which mentions usage.

Read coga/usage (`docs/contexts/coga/usage/SKILL.md`), coga/internals/activity-capture (`docs/contexts/coga/internals/activity-capture/SKILL.md`), and coga/internals/spool-merge (`docs/contexts/coga/internals/spool-merge/SKILL.md`), cited rather than attached as investigation and possible editing targets. Update the owning topic and twins for any changed identity or accounting contract.

### Investigation map (2026-10-08 design step)

- Write path: `commands/launch.py` `spawn_agent_session()`, in its `finally`, calls `usage.capture_session()` once per spawned launch. That calls `usage.append_record()` → `logfile.append_log()`. The `finally` then calls `git.sync_log()` → `git.publish()` with only the log path.
- Landing path: `git.publish()` → `_build_tree()`. For a `merge=union` path, it sets `data = _merge_union_bytes(current=<control copy>, base=<copy at merge-base(HEAD, control)>, other=<working copy>)`. With base `A`, control `A X Y`, and working `A Z X`, `git merge-file --union` yields `A X Y Z X`. This was reproduced with the real git binary during design. It matches the observed commits; for example, `c8a3cdfda` "Log: bootstrap/resolve-conflicts" re-adds a 16:49 record that its parent `276448100` had already added.
- Read path: `usage.load_records()` reads `log_path(cfg)` and keeps lines whose `_LOG_LINE_RE` group 1 parses through `UsageRecord.from_json()` (schema 1 or 2). `usage.rollup()` → `_build_row()` counts `len(records)` as sessions and sums tokens. Today neither function dedupes anything.
- Consumers via `load_records`: `commands/usage.py` (`coga usage`), plus `coga/recurring/usage-report/report.py`, which is live-only (no packaged twin) and is called from its `ticket.py`.
- Consumer with its own reader: `scripts/human_minutes.py` `parse_log()`. It already dedupes whole lines, but it also collapses records by `session_id`, which undercounts. The fix is trivial and in scope.
- Not a usage consumer: `src/coga_edge/phone_home.py` `_cursor()` / `_movement()`, which count movement lines only.
- Existing tests to extend: `tests/test_usage.py` (`test_append_and_load_records_from_log`, `test_load_schema_one_record_with_activity_fields_absent`), `tests/test_usage_report.py`, and `tests/test_human_minutes_script.py` (`test_union_log_duplicates_and_free_form_text_do_not_change_ledger`).
- `example/coga/log.md` has no usage records. No fixture change is needed there.

### Owning topics

`coga/usage` (`docs/contexts/coga/usage/SKILL.md`) owns the read contract and record identity. `coga/internals/spool-merge` (`docs/contexts/coga/internals/spool-merge/SKILL.md`) owns `merge=union` semantics. `coga/internals/activity-capture` (`docs/contexts/coga/internals/activity-capture/SKILL.md`) owns capture and the schema. All three have packaged bootstrap twins.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

coga-launch: bd0d85c9-93f3-4b3c-aeee-592a75ad2d2d

## Design notes (2026-10-08)

### Reproduction: where the duplicates are

I counted schema-1/2 record lines in each local repo's current `coga/log.md`, comparing duplicate message texts:

| repo | records | distinct | dup records (extra copies) | total tokens before → after | inflation |
|---|---|---|---|---|---|
| coga (this repo) | 1107 | 1090 | 13 (17) | 6,485,226,704 → 6,424,868,634 | 0.94% |
| magicator | 210 | 205 | 5 (5) | 1,479,597,915 → 1,434,645,026 | 3.13% |
| multiply | 620 | 615 | 5 (5) | 3,286,661,117 → 3,275,450,169 | 0.34% |
| thinkpick | 5 | 4 | 1 (1) | 13,643,545 → 8,610,443 | 58% |
| admin, demo-hackathon, patents, tablet, xpllm | — | — | 0 | — | — |

The reported "12 sessions repeated 2–4 times, 2026-08-31 → 2026-10-01" is this repo: 12 records with x2/x3/x4 copies fall in that range. A 13th, a `bootstrap/orient` record at 2026-10-08 23:49, was duplicated today by `c8a3cdfda`. Thinkpick's single duplicate (2026-09-23 orient) is its whole "merge=union" story.

### Cause: union landing, not a double write

`git blame --line-porcelain` over every copy found:
- 0 of 24 duplicated records had two copies in the same commit, so `capture_session` never double-wrote.
- 0 extra copies came in through a merge commit.
- Each extra copy was added by a later single-parent publish commit (`Log: …`, `Sync coga state`, `Ticket: … — created`), or by a squash-merged PR that carried `coga/log.md` lines (#732, `81cefcb7f`).

The mechanism is `git._build_tree`'s union merge with `ancestor = merge-base HEAD control`. When the publishing checkout's HEAD is behind a line already on control (a feature or detached checkout, or one that was not fast-forwarded), and that line sits at a different position in the working copy than on control, `git merge-file --union` emits it twice. I reproduced this with base `A`, control `A X Y`, working `A Z X` → `A X Y Z X`. When the line sits at the same position, union keeps a single copy (base `A`, control `A X Y`, working `A X Z` → `A X Y Z`), which is why this only happens sometimes.

### Decision

- Identity is the exact record JSON message text. Dedupe happens in the reader, in `load_records`. No writer change. Reasons are in the Description.
- Consumers: `coga usage` and usage-report are covered through `load_records`. `scripts/human_minutes.py` has its own reader and the fix is trivial (drop the `session_id` collapse), so it is in scope. phone-home and the velocity evidence script are unaffected.
- **Proposed follow-up ticket (not yet filed):** "Stop `publish` union merges from re-adding log lines already on control". Scope: `git._build_tree` / `_merge_union_bytes` base selection for `merge=union` paths when HEAD lags control. It also affects duplicated audit lines (e.g., `launched`). Owner: `coga/internals/spool-merge` and `coga/internals/state-publication`. The related ticket `tell-agents-never-to-git-commit-coga-task-and-log` covers the squash-PR variant (#732).

## Open Questions

1. Should I file the publish-path follow-up ticket above now, with the owner choosing priority? Or does the owner want the root-cause fix folded into this ticket? I recommend a separate ticket: it changes the state-publication contract and touches every log line, not just usage.
2. The `scripts/human_minutes.py` fix changes `usage_sessions` and token totals only for windows that contain distinct records sharing a `session_id`. Only one such pair (2026-08-18) exists in this repo. Is it acceptable that a re-run of a published ledger covering 2026-08-18 could shift slightly? If not, I'll move that fix to its own ticket.
