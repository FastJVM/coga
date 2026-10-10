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
step: 3 (review-design)
agent: claude
---

## Description

Investigate identical session usage records appearing multiple times, distinguish duplicate writes from merge=union duplication, and make usage accounting count each logical record once without collapsing distinct launches or legitimate session segments.

Done when regressions cover repeated capture, duplicate lines after union merges, distinct sessions with equal token counts, records without session_id, and the supported legacy record schemas (v1 and v2, both accepted by `usage` record parsing). Pin the safe record identity before choosing writer idempotency, reader deduplication, or both. Verify coga usage totals and identify any other affected consumers. A consumer that reads records through the fixed `usage` path is covered and verified here. A consumer with its own reader gets a follow-up ticket, named on the blackboard, unless its fix is trivial. Preserve the append-only audit history; do not rewrite old logs as a shortcut.

**Design finding (2026-10-08).** The duplicates are real and reproduced, and they come from the union landing path in `git.publish`. They are not double writes by launch capture. The report's "12 sessions, 2–4 copies, 2026-08-31 → 2026-10-01" matches **this repo's** `coga/log.md` exactly. Thinkpick, magicator, and multiply carry the same defect at smaller counts (evidence is on the blackboard). In every one of the 24 duplicated records across four repos, each extra copy was added by a *later* commit (a `Log: …`, `Sync coga state`, or `Ticket: …` publish, or a squash-merged PR), never by the commit that wrote the original. That rules out `capture_session` writing twice, and none of the copies came from a git merge commit. Writer idempotency in `append_record` would therefore fix nothing. This ticket fixes the reader. The publish-path root cause gets its own follow-up ticket (see Out of scope).

### Pinned record identity

A logical usage record is **the exact JSON message text of its log line**: the bytes after the `YYYY-MM-DD HH:MM [<ref>] [<actor>] ` prefix, which is what `_LOG_LINE_RE` group 1 captures. Two lines whose message text is byte-identical are one record. Lines whose message text differs in any byte stay separate records.

Why this is safe:
- Union copies are byte-identical. `git merge-file --union` copies whole lines.
- `capture_session` builds every record once, with microsecond `ts`/`started_at`/`ended_at` taken from that launch's own window, and `UsageRecord.to_json` serializes canonically (`sort_keys`, fixed separators). So in practice two distinct launches do not produce identical text, even with equal token counts, no `session_id`, or a shared provider session. This is a conservative, practical identity backed by every observed record, not a mathematical guarantee: nothing enforces globally unique timestamps, and the launch UUID is not stored in the record. No schema or writer change is in scope. Schema-1 records also carry microsecond `ts` (verified in the logs of the local sibling repos).
- `session_id` is **not** the identity. It is null on 66 of this repo's records, and distinct records legitimately share one. This repo has a real case: session `0b93746c…` produced both a `bootstrap/resolve-conflicts` and a `recurring/resolve-conflicts` record, with different `ts` and tokens. Resumed or chained segments can share one too.
- The parsed `UsageRecord` value is not the identity either. Text equality is the more conservative rule, because it never merges two lines that differ in any byte.

### Acceptance criteria

- [ ] `usage.load_records` returns each logical record (identity above) once, keeping first-occurrence order, however many times its line appears in `coga/log.md`.
- [ ] Regression tests in `tests/test_usage.py` cover all of the following (optional but recommended extras: two messages that parse to the same `UsageRecord` but differ in whitespace or key order both stay counted; first-occurrence order is asserted; identical messages under differing prefixes collapse):
  - [ ] **Union duplicate**: a log built by actually running `git merge-file --union` through `git._merge_union_bytes`. The base lacks record X; control has X followed by Y; the working copy has a local-only line Z followed by X. This yields X twice, which `load_records` returns once, and `rollup` totals equal the single-copy totals. Also check the hand-written variants seen in the wild: non-adjacent copies, and x3/x4 copies.
  - [ ] **Repeated capture**: two `capture_session` calls for two launches with identical `ParsedUsage` (same tokens and the same `session_id`, as when a provider session is resumed) but different windows produce two records, and both count. Appending one identical `UsageRecord` twice via `append_record` loads as one.
  - [ ] **Distinct sessions with equal token counts**: two records that differ only in `session_id` and `ts` both count.
  - [ ] **No `session_id`**: two `session_id: null` records with different `ts` both count. An identical duplicate of one of them collapses. This also covers an `unknown` record: `unknown_sessions` is counted once per logical record.
  - [ ] **Legacy schemas**: an identical duplicated schema-1 line collapses, and so does an identical duplicated schema-2 line. A schema-1 and a schema-2 record that agree on every field they share both stay counted, because their text differs.
- [ ] `coga usage --json` over a duplicated fixture reports the deduplicated `sessions`, `unknown_sessions`, and token totals. Add this test where `commands/usage.py` is already exercised.
- [ ] The usage-report recurring job, which calls `load_records` → `rollup`, reports deduplicated totals over a fixture with duplicate lines. Add this test to `tests/test_usage_report.py`.
- [ ] `scripts/human_minutes.py` `parse_log` uses the same pinned identity (exact JSON message text) for usage records, replacing its `session_id` collapse. Whole-line dedupe stays for audit events. New tests in `tests/test_human_minutes_script.py` show that (a) two distinct records sharing a `session_id` both reach `usage_records`, and (b) one identical record JSON appended under two different prefixes (e.g. `12:00` and `12:01`, since `logfile.append_log` stamps a fresh minute prefix per append) reaches `usage_records` once. The existing `test_union_log_duplicates_and_free_form_text_do_not_change_ledger` still passes. Owner accepted (2026-10-09) that re-running a published human-minutes ledger covering 2026-08-18 may shift slightly, because of the one real shared-`session_id` pair there.
- [ ] No existing `coga/log.md` is rewritten. `coga show` and the raw log still display every line.
- [ ] The docs record the identity and the union-duplication fact. `docs/contexts/coga/usage/SKILL.md` (and its packaged twin) gets the identity, and `docs/contexts/coga/internals/spool-merge/SKILL.md` (and its twin) gets the union-duplication fact. `python -m pytest` passes, including `tests/test_packaging.py`.
- [ ] Verification: run `coga usage --json --by task` in this repo before and after the change and put both numbers in the PR. At the 2026-10-08 evaluation: before 1,108 sessions, 115 unknown, 6,488,526,008 total tokens; after 1,091 sessions, 114 unknown, 6,428,167,938 total tokens (a drop of 17 sessions, 1 unknown, 60,358,070 tokens). Lines appended since will move these numbers, so recompute rather than assert them.

### Proposed shape

1. **`src/coga/usage.py` `load_records()`**: keep a `seen: set[str]` of `match.group(1)` texts. Skip a line whose message text is already in `seen`. Add a text to `seen` only after `UsageRecord.from_json` succeeds, so non-record lines are unaffected. Update the docstring to name the identity and why union can duplicate. `rollup()`, `capture_session()`, and `append_record()` stay unchanged. Every consumer goes through `load_records`, so deduping at the loader, not in `rollup`, covers `coga usage` and usage-report together.
2. **`scripts/human_minutes.py` `parse_log()`**: replace the `seen_usage_sessions` (by `session_id`) set with a set of accepted usage-record message texts, and keep the `seen_lines` whole-line dedupe for audit events. Whole-line dedupe alone is not enough: an identical record appended twice across a minute boundary gets two different prefixes. Reword the adjacent comment so it names the message-text identity instead of `session_id`.
3. **Tests** as listed in the acceptance criteria. Build the union fixture with `coga.git._merge_union_bytes` and plain byte strings; no git repo is needed.
4. **Docs**:
   - `coga/usage`, section "The read API": `load_records` returns each logical record once; the identity is the exact JSON message text; say why `session_id` is not the identity; duplicate lines stay in the log (append-only) and are only collapsed at read time.
   - `coga/internals/spool-merge`, section "`merge=union` files": correct the claim that union "never loses or revives anything meaningful" for `log.md`. Union can *duplicate* an appended line when `publish` merges against a merge base that predates a line already on control. Any reader that counts log lines must collapse byte-identical copies, as `usage.load_records` does.
   - Edit the canonical `docs/contexts/...` files and the packaged twins under `src/coga/resources/templates/coga/bootstrap/contexts/coga/{usage,internals/spool-merge}/SKILL.md` identically.
   - `coga/internals/activity-capture` keeps "exactly one record" per launch, which stays true. Change it only if a sentence there contradicts the new read rule.

### Out of scope

- **Fixing the publish-path root cause.** `git._build_tree` union-merges with `ancestor = merge-base HEAD <control>`. When the checkout's HEAD lags a line that is already on control, `git merge-file --union` re-adds that line. Fixing this changes the state-publication contract, and it affects every `log.md` line, audit lines included. Owner confirmed (2026-10-09) that this goes to a separate follow-up ticket, filed as a draft: `stop-publish-union-merges-from-re-adding-log-lines` (see blackboard).
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
- **Follow-up ticket (filed 2026-10-09 as draft `stop-publish-union-merges-from-re-adding-log-lines`):** "Stop `publish` union merges from re-adding log lines already on control". Scope: `git._build_tree` / `_merge_union_bytes` base selection for `merge=union` paths when HEAD lags control. It also affects duplicated audit lines (e.g., `launched`). Owner: `coga/internals/spool-merge` and `coga/internals/state-publication`. The related ticket `tell-agents-never-to-git-commit-coga-task-and-log` covers the squash-PR variant (#732).

## Owner decisions (review-design, 2026-10-09)

1. Publish-path root cause stays out of this ticket. Filed as the draft `stop-publish-union-merges-from-re-adding-log-lines`.
2. A small shift in re-run human-minutes ledgers covering 2026-08-18 is accepted.
3. Evaluator must-fix accepted: `human_minutes.parse_log` uses exact-message identity for usage records. Folded into the Description's acceptance criteria and proposed shape, along with both optional recommendations and the refreshed baselines.

## Evaluator review

Cold review, 2026-10-08. **One must-fix before implementation; the shared-reader approach is otherwise ready for owner review.** The ticket body independently supplies the identity, scope, implementation shape, and testable acceptance criteria. Its headings compose correctly. The frozen workflow matches the packaged `code/design-then-implement` workflow and correctly hands this review to the owner next.

### Must fix

1. **P2 — Apply the pinned message identity to the independent human-minutes reader too.** Proposed shape item 2 removes `seen_usage_sessions` but leaves only `seen_lines` in `scripts/human_minutes.py::parse_log`. That handles union copies but not the ticket's other explicit case: appending an identical `UsageRecord` twice. `src/coga/logfile.py::append_log` generates a fresh minute-level prefix on each append. Two appends across a minute boundary therefore have identical JSON messages but different whole lines. The proposed `usage.load_records` counts one; the proposed human-minutes reader counts two. With a non-null session ID this also regresses the current script, which counts one. A temporary fixture with identical valid record JSON at `12:00` and `12:01` confirmed the current script returns one record, whole-line identity yields two, and message identity yields one. No such differing-prefix duplicate exists in the current repo log; this is a contract/regression gap, not a claim about the observed union copies. Replace session-ID deduplication with exact-message deduplication for accepted usage records while preserving whole-line deduplication for audit events. Add a regression covering this case alongside the distinct-records/shared-session case. Alternatively, explicitly scope this consumer exception out and name its follow-up; leaving the two identities implicit is not sufficient.

### Optional recommendations

- Add a loader regression where two messages parse to the same `UsageRecord` but differ in JSON whitespace or key order, and both remain counted. The proposed schema-1/schema-2 case does not catch accidental deduplication by parsed value, since `UsageRecord.schema` itself differs. Also assert first-occurrence ordering and identical messages under differing prefixes.
- Qualify “two distinct launches never produce identical text” in the identity rationale. `usage._format_ts` preserves datetime precision, but neither it nor `capture_session` enforces globally unique timestamps, and the launch UUID is not stored in the record. Exact text is a conservative, practical legacy identity supported by the observed records, not a mathematical uniqueness guarantee. This does not require a schema or writer change in this PR.

### Verified evidence and scope

- `commands/launch.py::spawn_agent_session` has one capture call in `finally`; `usage.capture_session` constructs one record and calls `append_record` once. `git._build_tree` union-merges the control, merge-base, and working bytes. Running the real `_merge_union_bytes(current=b'A\nX\nY\n', base=b'A\n', other=b'A\nZ\nX\n')` returned `A X Y Z X` as separate lines. Commit `c8a3cdfda` adds the cited prior orient record during a later resolve-conflicts log publication. These checks support reader deduplication and the separate publication follow-up; I did not repeat the full four-repository blame survey.
- `commands/usage.py` and `coga/recurring/usage-report/{report.py,ticket.py}` use `load_records` and `rollup`; the report is live-only. The shared loader has two real consumers and satisfies the microkernel rule. `phone_home._movement` accepts movement messages rather than usage JSON; `docs/evidence/velocity.md` counts task sets. The three named topic twins exist and currently match byte-for-byte.
- Current `coga usage --json --by task`: **1,108 sessions, 115 unknown, 6,488,526,008 tokens**. Applying exact-message deduplication in memory to the same log: **1,091 sessions, 114 unknown, 6,428,167,938 tokens**. The difference is still 17 sessions, one unknown, and 60,358,070 tokens. The additional launch since design explains the changed baselines; no log was rewritten.
- Baseline verification: `.venv/bin/python -m pytest -q tests/test_usage.py tests/test_usage_report.py tests/test_human_minutes_script.py tests/test_packaging.py` — **83 passed**. The CLI regression belongs in `tests/test_usage.py::test_usage_command_outputs_json`; existing loader, report, and ledger fixtures support the proposed additions. This is baseline evidence, not implementation validation or a full-suite run.

### Owner handoff

Resolve the must-fix and the existing Open Questions at `review-design`: retain the separate publish-path follow-up and arrange its filing, and confirm the intended correction to historical human-minutes totals. The body already chooses the separate publication scope and includes the script fix; align the remaining questions with the accepted disposition. No ticket-body edits, implementation, branch, or PR were produced in this step.
