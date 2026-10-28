---
title: Trim coga/log.md to a configurable age with a weekly recurring job
status: in_progress
owner: nicktoper
contexts:
- coga-dev/principles
- coga/recurring/templates
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
  - name: peer-review
    skills:
    - code/peer-review
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
step: 6 (open-pr)
agent: claude
launch_generation: 88356985-2b2e-4beb-8b78-657bfc4808c0
---

## Description

Bound the growth of `coga/log.md` with an age-based retention setting and a
shipped weekly recurring template that deletes log lines older than the
retention window (git history keeps them; no archive file). Trimming is on by
default in every adopting repo; a repo can change the window or turn trimming
off in `coga.toml`. The design proposes the default window from measured
sizes (see Context) and the owner approves it at the design gate.

Propose **30 calendar days**, with the preservation exceptions below. This
cuts the measured log by about 59%, while keeping complete histories for
tickets still on disk. This is a retention target, not a hard byte ceiling:
live histories, unread movement records, required recurring evidence and
unparseable content can outlive the window. The owner approves this tradeoff
at `review-design`.

### Acceptance criteria

- [ ] Shared-only `[log].retention_days` defaults to `30`; integer `0`
  disables trimming. Reject booleans, negative numbers, non-integers,
  non-table `[log]`, unknown keys and a local `[log]` override. Very large
  positive integers safely mean a cutoff no earlier than `datetime.min`.
  Document the setting and default in `coga/configuration` and its twin.
- [ ] Ship `recurring/trim-log/{ticket.md,ticket.py}` and
  `workflows/trim-log/run.md`, with byte-identical live/package twins. Use
  `schedule: "0 4 * * 1"` (Monday 04:00 in the sweeping process's local
  timezone), `scope: repo`, `run_when_inactive: true`, and one agent-assigned
  `trim` step. Omit owner/agent overrides. The shim invokes the wheel-owned
  edge implementation and completes disabled, empty and no-change periods
  with `python -m coga.cli bump "$COGA_TASK_SLUG"`; no agent fallthrough.
- [ ] Delete only complete, unprotected events strictly before local midnight
  on `today - retention_days`, capturing `today` once per attempt. Keep the
  exact boundary and future timestamps. Preserve surviving bytes, order,
  duplicate multiplicity and v1 escaping. Legacy continuations travel with
  their event; uncertain data follows the conservative policy below.
- [ ] Preserve every discovered on-disk ticket's complete history, including
  drafts and terminal tickets awaiting Retro/retire; preserve recurring
  high-water marks and pause/reset evidence even after period deletion.
  Full and bounded ledger readers, pause eligibility, activity maps for
  existing tasks and service order retain their pre-trim meaning.
- [ ] Malformed serviced-period records remain errors; a trim refuses before
  deleting anything when its full ledger validation finds one. Removal of
  obsolete valid ledger evidence alone must not trigger the runner's
  competitor-admission refusal or re-fire a serviced period.
- [ ] All local append/rewrite/retraction/publication paths coordinate with
  the same reentrant state lock. Concurrent and stale publishers cannot
  silently drop control-only events or reintroduce expired, previously
  trimmed history. Native Git merges fail visibly when they cannot preserve
  both sides. Retraction still removes exactly refused events, including
  legacy continuations, without deleting peer events.
- [ ] Every removed event is already recoverable from reachable Git history.
  A failed or uncertain publish cannot be reported as a completed trim.
  A disabled-Git or non-Git run is a reported non-destructive skip and closes
  its period; a remote-less Git repo may trim after a verified local-control
  commit. Use `Log: recurring/trim-log — ...` for maintenance publication;
  verify `recurring_activity.is_machine_commit` excludes it from activity.
- [ ] Replace phone-home's prefix-dependent cursor as specified below.
  Repeated trim/report alternation preserves unread movement and does not
  zero, replay or double-count it. Preserve the wire payload, delivery policy,
  identity, suppression gates and run counter. No recurring telemetry loss
  caused by ordinary trimming is accepted by this design.
- [ ] The documented feature-specific adoption command installs the new
  template/workflow and log attribute in a pre-feature repo after wheel
  upgrade. Missing config already selects the default; existing overrides,
  explicit `0`, parked templates and local forks survive. Installation is
  idempotent and never becomes a general repo updater.
- [ ] Update the owning contracts and their twins listed under Context,
  including the replacement for the append-only/union claim. The PR and
  release notes explicitly announce default-on retention, its exceptions,
  historical-report limits, native-merge behavior and the adoption command.
- [ ] Verify cutoff boundaries, disabled/no-op/repeated runs, parser edge
  cases, recurring state, cursor migration and alternating writers, real
  local/remote races, stale/native merges and installed-wheel adoption.
  Update representative seeded fixtures; `python -m pytest` passes and
  `coga validate --json` introduces no new findings. Record exact commands
  and results; a filtering-unit-test-only implementation is insufficient.

### Proposed shape — retention policy and parsing

Add `Config.log_retention_days`, a dedicated parser and the shared schema
allowlist entry in `src/coga/config.py`. Do not edit this repo's `coga.toml`
or `coga.local.toml`; the code default enables the job. Days are local calendar
days, matching `src/coga/logfile.py::append_log`'s timezone-free wall-clock
timestamps. Do not reinterpret old timestamps as UTC or promise exact elapsed
24-hour intervals across DST or writers in different zones.

Introduce a byte-preserving event parser in `src/coga/logfile.py`, used by
retention, publication and retraction. Split only at LF. A complete recognized
header starts an event; only an unversioned legacy event can own untagged
continuation lines. A timestamp-looking but malformed header starts an opaque
block instead of inheriting its predecessor's age. Preserve leading orphans,
invalid UTF-8, invalid dates, unknown encodings, unexpected continuations after
v1 events and incomplete EOF data. Preserve the whole event containing a
partial tail. Do not fix, re-encode, sort or deduplicate retained history.
Text indistinguishable from a valid legacy header retains the existing
grammar's interpretation; do not invent a retrospective encoding migration.

Put the shared selector in a focused `src/coga/log_retention.py` (proposed).
Its real consumers are the edge trim planner and log-publication reconciliation;
the core placement is shared infrastructure, not a new recipe. Pass it an
explicit snapshot and cutoff, rather than allowing it to discover arbitrary
repo state or import edge code. Its keep set is the union of:

1. Recent/future complete events and all opaque blocks.
2. Every event tagged with an existing task ref from `tasks.list_tasks`, for
   **all statuses**. This preserves first/minimum activity, physical-last
   activity, cancellation reasons, show/Retro evidence and pause history.
   A malformed/duplicate/unreadable inventory aborts planning; it is not an
   empty task list. Removal of a ticket releases this exemption next time.
3. For every `recurring/<name>` ever represented, all occurrences of the
   greatest valid serviced period using `_LedgerAccumulator`'s
   `(calendar position, period spelling)` ordering. Include absent/parked
   templates. Validate the whole ledger first and refuse on its errors;
   never erase a malformed older record to make the bounded reader succeed.
4. For every recurring ref, the winning `created`/`paused` evidence according
   to `_pause_origins`: timestamp order, then physical order for same-minute
   ties. Preserve a human/unknown pause or a creation that clears an old
   machine pause just as carefully as a resumable pause. Existing periods
   already keep their full histories through item 2.
5. Movement events not yet consumed by an installed phone-home cursor, as
   described below. No cursor exists when the job was never installed;
   an invalid or incompatible installed cursor is a visible planning refusal.

The selector returns original event spans and counts/bytes by reason, not
rendered replacement messages. Retention uses envelope timestamps, while
`usage.load_records` continues filtering reports by the JSON record's `ts`.
Old usage for removed tasks expires; histories retained for on-disk tasks may
leave partial older reports. Document that `coga usage --since` is a query over
retained records, with no completeness guarantee before the window and no
automatic Git-history read. Full historical reporting remains out of scope.

### Proposed shape — publication and concurrency

Remove the audit log's `merge=union` contract. The stock attribute for the
root audit log becomes `/log.md -merge`; preserve `retires.md`'s union rule
and unrelated attributes. `-merge` deliberately makes competing native Git
edits a visible conflict with both index stages available, rather than a
silent union resurrection. Ordinary Coga appends must still reconcile without
manual conflicts through the shared publisher. No custom installed Git merge
driver or repository hook is required.

In `src/coga/git.py`, give the configured `paths.log_path(cfg)` a distinct
event-aware publication path through `_candidates`, `_guard`, `_build_tree`
and the checkout/subsumption proofs. Do not change `_merge_union_bytes`'s
contract for the retire worklist. Proposed log rules:

- Ordinary publication preserves control's entire event sequence and merges
  new complete source events in source order. A missing source event is
  **not** a delete instruction. Use the source's actual merge-base/HEAD
  provenance to distinguish old history from appended events; never use the
  landed published-ref blob as a three-way source base. Preserve the existing
  cap on byte-identical occurrences already on control.
- A stale source may carry events previously published and then trimmed,
  including when its merge base predates those publications. Suppress such
  incoming events only when they are eligible under the current retention
  policy **and** reachable control history proves those exact canonical event
  bytes were already archived. Compare the protected state against the pinned
  control/candidate task tree, not just the stale checkout's inventory. Reuse
  one transient history scan per publication when that proof is necessary;
  do not create a tombstone file or a second archive. A genuinely new event,
  an unproven one, or required state is retained, even if backdated. Fail a
  needed Git inspection visibly instead of treating it as a positive proof.
- Explicit deletions use a proposed `logfile.LogMutation` receipt carried by
  `git.publish(..., log_mutation=...)`: exact preimage plus the selected
  whole-event occurrences to remove. Require the exact control log preimage
  and proof that local bytes still equal the planned postimage; reject an
  ordinary whole-file truncation without
  this receipt. Apply only the named deletion; never overlay a stale short
  file. Trim and rollback are the two real consumers of this shared API.
- `_published_proof` and `_local_control_subsumed` must use the same log
  reconciliation/disposition rules. Retained new events still prevent a
  checkout reset. Archived expired source events may be proved subsumed;
  their absence must not strand a stale feature checkout forever.
  `cli._warn_unpublished_log_lines` uses that same disposition for old trimmed
  events while still naming genuinely unpublished events after a rewrite.
  A weak timestamp-only proof must never authorize discarding an event.

Acquire `git.state_lock(cfg)` **before opening** the append file and hold it
through writing/closing. Apply the same lock to both retraction implementations
and every log replacement, including landed-byte installation. Move
`launch._retract_log_append` onto the shared mutation API; preserve its exact
returned-append identity. `retract_log_lines` callers must hold the transaction
from their before-snapshot through refusal/rollback, or carry explicit event
receipts; a changed prefix cannot silently abandon a required rollback.
Use atomic replacement for local rewrites under the lock. Check other control
worktree paths separately: a publisher must acquire that checkout's lock
before replacing/fast-forwarding its log, or leave it untouched for its own
locked catch-up. Avoid holding two checkout locks in opposite order.
This coordinates upgraded Coga processes; manual Git/file writers remain
subject to Git conflicts and visible local-byte comparison failures.

The edge job's ordered transaction is:

1. Return a successful no-op for a missing/empty log, and a reported skip when
   retention is `0`, or Git is disabled or absent. Otherwise require the
   managed control checkout and publish any
   pending log events first using existing strict publication machinery.
   Verify that every proposed removal is in reachable control history; local
   remote-less control is sufficient. No archival proof means no deletion.
2. Under the state lock, capture the current log, task inventory, shared policy
   and phone-home parent, and compute the keep spans. Pin those decision inputs
   with exact log/parent expectations and a `guard` that compares the relevant
   config/task tree at each attempted control revision. Preserve locally
   authored task state too; a dirty/ambiguous inventory is a retry/refusal,
   not permission to classify its refs as deleted.
3. If needed, migrate the phone cursor first, then atomically replace the log.
   Publish the log and changed parent together, with the explicit deletion
   receipt and subject `Log: recurring/trim-log — retained ...`. The committed
   tree is atomic across both files; the cursor-first local order is also
   safe after a crash because the new cursor works with an untrimmed log.
4. On a definite contention refusal, restore only this attempt's unchanged
   local outputs (log first, then parent), reread current control and recompute;
   do not reuse the old deletion plan. Bound automatic retries. On uncertain
   publication retain recoverable state and report failure; do not bump or
   allow an ordinary sweep to reinterpret pending deletions as appends.
   Rollback callers use the same guarded-delete path and preserve their
   existing retained-state/exit-75 recovery contract.
5. A corrupt ledger/inventory/cursor or incompatible fork needs an actionable
   `coga block` prerequisite report; transient publication failures remain
   nonzero retryable runs. Do not continually retry known input corruption
   without recording the repair ask. Report a compact count/byte summary
   through `runner.run_reported` and the
   fence-aware blackboard API, then release the lock and bump via a subprocess.
   Do not hold the parent lock while invoking the bump subprocess. A successful
   no-op needs no extra maintenance commit; normal lifecycle audit still occurs.

Update `recurring_runner._control_serviced_period_cached`'s post-publication
diff path: deletion-only changes to obsolete valid ledger records are benign
only after proving unchanged semantic high-water/error state at the compared
revisions. Added ledger records, new malformed evidence, changed maxima or
ambiguous evidence keep the competitor refusal. Keep the existing bounded
reverse read's at-least semantics and error reachability; do not replace it
with a last-line heuristic. Add the trim-during-another-sweep race fixture.

### Proposed shape — phone-home cursor

Replace the byte offset/prefix digest with a schema-2 cursor containing the
sorted SHA-256 fingerprints of complete movement events observed at the last
reservation. Preserve `run` and `repo_id` in `period_state`; schema 2 replaces
`offset`/`digest` with `seen_movements`. Hash canonical LF event bytes (including
timestamp/ref/actor, excluding the terminator); CRLF checkout conversion must
not create a new event. Keep exact-event deduplication. Hashes stay local to
the repository and are never payload properties.

Share the existing movement recognition and cursor calculation as focused
core infrastructure used by phone-home and the trim planner, with no core
import of `coga_edge`. In `src/coga_edge/phone_home.py`, `_state` validates both
schemas during migration; `_cursor` on schema 2 counts current movement hashes
absent from `seen_movements`, then reserves the current set before transport.
Disabled/development-suppressed and first-identity runs baseline that set
with movement zero as today. Invalid inventories still preserve the cursor.
Trimming, reordering and removal of consumed records do not reset the cursor.

For a valid schema-1 prefix, migration seeds `seen_movements` from exactly the
consumed prefix, leaving later movement unread. An unused/null-identity cursor
may baseline the whole snapshot because its first enabled run already promises
zero movement. Trim performs this non-sending migration before deletion,
preserving the parent counter, identity, unrelated blackboard content and
above-fence bytes. Use `read_blackboard`/`replace_blackboard(expected_bytes=...)`
and the joint guarded publication above. This narrowly authorizes trim to
migrate cursor fields, not to increment phone-home's run or send a snapshot.
After migration, the trim job only reads the cursor. Test migration and normal
phone-home reservations in both orders and repeatedly alternating.

A non-null schema-1 cursor whose prefix is already invalid cannot be migrated
losslessly from the working file: the trim leaves both files untouched and
reports that prerequisite. Phone-home retains its existing visible reset
behavior for such pre-existing rewrites when it next runs; this ticket does
not silently manufacture consumed history. An incompatible local phone-home
fork likewise needs explicit adaptation, not an overwritten implementation.

The retention selector pins every unconsumed movement event while the installed
cursor has an identity. Thus a report delayed beyond 30 days can still count
its unread movement; long-stopped reporting may retain a small backlog. Once
phone-home reserves the set, the next trim can delete expired consumed events.
The stored fingerprint set is replaced, not accumulated forever; its size is
bounded by the movement events in retained history. With the measured 30-day
selection it is about 33 KB (494 hashes), versus 96 KB for the untrimmed log.
Do not claim distributed exactly-once semantics or replay delivery failures.

### Proposed shape — edge implementation and adoption

Use `src/coga_edge/trim_log.py` (proposed), entered by the reserved shim's
`main()`. Keep selection/publication mechanics in the shared modules above;
job orchestration, reports and installation choices stay at the edge. Wrap
execution in `runner.run_reported`, as phone-home does, without registering a
new `runner.RECIPES` name. Unexpected arguments or missing task environment
fail visibly. The only separate mode is the bounded adoption operation below.

Fresh init receives the template, shim, workflow and attribute from
`commands.update.copy_fresh_templates`. Existing repos adopt by upgrading the
wheel in every participating environment, then explicitly invoking its
`python -m coga_edge.trim_log --install` from that repo using the upgraded
CLI's interpreter. Document the exact interpreter-resolution command already
owned by `coga/edge-code/edge-code-upgrades.md`; test the documented invocation.
A wheel-only upgrade is **not** delivery of the recurring schedule.

`--install` plans/validates the complete feature-specific change before
writing: install only the missing trim template pair and workflow, and narrowly
replace the known stock audit-log union attribute with `/log.md -merge`.
Preserve all unrelated bytes. Identical installed files are no-ops; an existing
custom template/workflow, `_trim-log` parking, symlink, or unfamiliar/conflicting
attribute is left intact and reported for review rather than partially replaced.
The effective configured log attribute must be checked, not inferred from one
textual rule. Do not seed config over an existing value; `0` remains an opt-out.
No other job, schedule, workflow, config, ticket or full local fork is upgraded.
The operator reviews/publishes the named repo edits through normal repo practice.
This command never launches a job or sends telemetry.

Ship a persistent `recurring/trim-log/operations.md` and its twin owning this
adoption/recovery procedure, and link it from installation/release instructions.
Quiesce affected sessions while installing the compatible wheel/repo pair;
do not claim safety with an older writer that neither takes the log lock nor
understands guarded deletion. Rollback requires a compatible pair as well.
In this repository, committed `coga/recurring` changes can publish ahead of a
code PR: stage the live enabling files outside the swept roots until the core
support has landed, or use the repository's documented compatible two-phase
rollout. Do not activate a shim while control lacks its implementation.

### Verification plan

- Parser/config fixtures: just before/at/after the midnight cutoff, DST and
  injected local date, future timestamps, huge day counts, `0`, all rejected
  config shapes, LF/CRLF, escaped v1 messages, legacy continuations, orphan and
  malformed headers, invalid UTF-8, incomplete EOF, empty/missing log, repeated
  no-op byte identity. No test should depend on the wall clock.
- Reader fixtures: compare all six named log APIs, task display and service
  order before/after for existing tasks; terminal histories and cancellation
  reasons; high-water marks out of timestamp/file order, ISO week/year and
  equal-position different period shapes, duplicates, absent/parked templates,
  malformed ledger records both reachable/unreachable to bounded reverse reads;
  human, sweep, watchdog, creation-reset and same-minute pause ties.
- Real-Git fixtures in `tests/test_git.py` and recurring integration tests:
  two clones append versus trim in both publication orders, append during
  local read/replace, stale source missing peer additions, repeated publication
  from an unmoving feature HEAD, empty/distant merge bases, archived expired
  resurrection versus genuinely new backdated input, an inventory/cursor edit
  during a rejected push, definite/uncertain push failure, checkout proof and
  unpublished-line diagnostic, and both rollback writers racing with trim.
  Native trim-versus-append merges must retain both stages on conflict; test
  explicit recovery without deleting the peer event. Keep retire union tests.
- Phone-home tests with fake transport: schema-1 migration with unread suffix,
  first/disabled runs, incompatible prefix, removed consumed events, delayed
  unread movement, duplicate/out-of-order events, CRLF, concurrent cursor CAS,
  crash between parent migration and log replacement, and several alternating
  trim/report cycles with unchanged wire properties and exact counts.
- Installed-wheel tests extend `tests/test_edge_distribution.py`: fresh init,
  pre-feature adoption using the documented command, custom/parked copies,
  config opt-out, unknown attributes, idempotence and no writes outside the
  allowlist. Run the reserved script headlessly on a seeded log and verify
  its completed period, default config, bookkeeping commit and no agent spawn.
  Extend `tests/test_packaging.py`/`tests/test_recurring_shims.py` as needed;
  run the full suite and structure validation after focused checks pass.

### Out of scope

No log-format rewrite, compression, archive file, Git-history pruning, hard
byte quota, shortened usage JSON, full historical reporting, configurable
cron/timezone framework, generic template updater, new CLI recipe, commit
coalescing, unrelated publication-warning changes, telemetry payload changes,
or adoption into other live repositories during implementation. Do not trim
the live log manually to demonstrate the feature. Product approval of the
window and preservation exceptions belongs to the owner gate.

## Context

Split from `fix-the-commit-git-journal` (deleted); siblings
`commit-journal/coalesce-coga-state-commits` and
`commit-journal/publish-log-lines-left-uncommitted`. These are provenance, not
dependencies: publish the trim through existing state-publication machinery;
commit coalescing and unrelated publication-warning changes stay out of scope.

### Owner decisions (2026-10-23)

- Retention is bounded by **age in days**, not size or line count.
- Trimmed lines are **deleted**; git history is the archive.
- The template runs **weekly** and is **on by default** for adopting repos.
  This is a behavior change for adopters: the PR and release notes say so.
- The **default window is the design's call**, with the numbers below.

### Size facts (2026-10-23, this repo)

A 90-day cutoff keeps about 6,886 of 9,255 lines and 1.94 MB of 2.46 MB
(about 79%). Usage `[system]` JSON records are 1,329 lines but about 1.36 MB
(about 55% of bytes). Re-measure during design with the proposed retention
exceptions included; explain the expected steady-state size and whether it
meets the goal. Record size is a possible follow-up, outside this ticket.

### The append-only invariant (most important)

Read `coga-dev/internals/spool-merge` at
`docs/contexts/coga-dev/internals/spool-merge/SKILL.md` (cited, not attached),
sections "`merge=union` files", "One event per log line", "How `publish` lands
a union path", and "Crash-safe replacement is not a lock"; this is an editing
target. `coga/.gitattributes` and its packaged twin mark `log.md` as
`merge=union`; `logfile` describes it as append-only. Trimming breaks that
justification unless a healing reader makes resurrection harmless.

`git._merge_union_bytes` can land a deletion when the base contained the line;
this does not prove safety for git-native merges, stale branches/clones, or
working copies missing peer additions. The design must resolve resurrection
and concurrent-event loss, amend the invariant and attribute as needed, and
update the topic and affected public contracts in the same PR. Locally,
`logfile.append_log` opens the file for append without acquiring
`git.state_lock`; a trim's atomic read/replace or lock alone is insufficient.
Include races with local appends as well as cross-checkout publication.

Legacy events may span untimestamped continuation lines (roughly 500 in the
measurement). Preserve or remove each event with its continuations; specify a
conservative policy for orphan, malformed, and incomplete lines instead of
silently assigning them an age. Preserve the v1 encoding of retained events.

### Lines that must survive

Inventory the `logfile` reader API (`log_lines`, `iter_log_messages`,
`iter_log_messages_reverse`, `task_log_lines`, `last_activity_map`,
`first_activity_map`) and direct readers across `src/coga/`, `src/coga_edge/`,
and live/packaged scripts and templates. Include the CLI's unpublished-line
check and rollback writers such as `logfile.retract_log_lines`, not only
display readers. Known hazards:

- **Recurring serviced-period ledger.** The high-water mark is a
  `created|reused <task-ref> for <period>` line tagged `recurring/<name>`.
  Keep at least the greatest valid calendar period per template regardless of
  age, using the ordering of `recurring._LedgerAccumulator` and
  `recurring.period_key_at_least`, not the last file line or newest event
  timestamp. `recurring.read_serviced_ledger` has forward and bounded reverse
  readers; the design must preserve deduplication and explicitly handle
  malformed-record errors rather than silently repairing them by deletion.
- **Pause provenance.** `recurring._pause_origins` uses creation and pause
  events, timestamp order, and same-minute append order to distinguish machine
  pauses from human pauses. Keep sufficient evidence for existing paused
  periods to retain the same resume eligibility after trimming.
- **Usage records.** `usage` parses `[system]` JSON lines; `coga usage
  --since` is unbounded, so state the tradeoff for reports reaching past the
  window.
- **Task history.** Retro, retire, `coga show`, activity maps and
  `service_order.service_order` consume per-task history. Decide whether full
  histories of still-open tasks survive, and identify the minimum facts
  needed to preserve lifecycle and scheduling behavior if they do not.
- **Phone-home cursor.** `coga_edge.phone_home._cursor` stores an offset and
  prefix digest; rewriting the consumed prefix baselines movement to zero.
  Fix this or seek explicit acceptance at the design gate. Record any accepted
  loss in `coga/recurring/phone-home/ticket.md`, sections "State, publication,
  and loss" and "Scope and approximate movement", and its packaged twin.

Read `coga/recurring/scheduling` at
`docs/contexts/coga/recurring/scheduling/SKILL.md` (cited, not attached),
sections "Periods and the serviced-period ledger" and "Admission and
unfinished runs", for the ledger and pause contracts above. Update affected
contracts and their packaged twins with the implementation.

### Placement and shipping

Read `coga-dev/microkernel` at `docs/contexts/coga-dev/microkernel/SKILL.md`
(cited, not attached), sections "The microkernel rule" and "The `ticket.py`
script phase". Deterministic trim work belongs at the edge, entered through
`coga/recurring/<name>/ticket.py` and using shared core infra, unless the design
proves a `runner.RECIPES` contract is needed. Use the template/workflow pairing
at `coga/recurring/blocker-reminders/` and
`coga/workflows/blocker-reminders/run.md` as a lifecycle example, not a reason
to add a core recipe. The script must complete disabled and no-op periods too;
exit 0 with an open step would fall through to an agent. Choose the template
name, weekly cron, scope and `run_when_inactive` during design.

`recurring.scan_due` discovers local templates;
`commands.update.copy_fresh_templates` seeds fresh repos only. Name the
delivery trigger for existing repos and verify it on a pre-feature fixture,
preserving local customizations and opt-outs. Read `coga/edge-code` at
`docs/contexts/coga/edge-code/SKILL.md` (cited, not attached), sections
"Wheel-owned edge implementations" and "Explicit local forks": a wheel can
update an imported edge implementation, but does not install new repo
templates, schedules or workflows. Do not expand this into a general updater.

### Config

Read `coga/configuration` at `docs/contexts/coga/configuration/SKILL.md`
(cited, not attached), sections "Allowlists" and "Unknown keys fail loud";
update it and its packaged twin with the schema and default in `config.py`.
The design selects the key, day-count validation, disable representation,
cutoff clock/timezone and exact boundary. This repo needs no config edit for
default-on behavior; agents must not edit `coga.toml` or `coga.local.toml`.

The trim commit is bookkeeping: subject it so
`recurring_activity.is_machine_commit` classifies it as non-activity
(`Log: recurring/…` and `Ticket: recurring/…` already are).

### Design measurement (2026-10-27)

Read-only measurement at control commit
`9bff7b617e5aec1c195bee5e79082c6061771094`, with cutoff clock fixed to
`2026-10-27 00:00` local. The log was 2,550,793 bytes, 9,552 LF lines,
8,964 event blocks and 588 legacy continuation lines. Its SHA-256 was
`1122f575a28c8f74ceb568e6dbba361b36c2b5f382a9d7ffb548fe2853ab32e7`.
There were 150 on-disk tasks, 13 serviced-ledger refs, no malformed ledger
errors or opaque blocks, and 1,962 event blocks pinned before applying age.
The phone-home identity was null, so baseline migration adds no unread-history
exception to this measurement. No log bytes were changed.

| Days | Cutoff, local midnight | Retained bytes | Retained LF lines | Old exception bytes |
| --- | --- | ---: | ---: | ---: |
| 14 | 2026-10-13 | 685,595 | 2,701 | 242,893 |
| **30** | **2026-09-27** | **1,053,921** | **3,814** | **145,400** |
| 60 | 2026-08-28 | 1,693,412 | 5,778 | 42,848 |
| 90 | 2026-07-29 | 1,967,684 | 6,617 | 17,260 |

These numbers apply the proposed full-existing-history, greatest-ledger and
pause/reset exceptions, preserving whole legacy events. At 30 days, age alone
accounts for 908,521 bytes; exceptions add 145,400. The saving is 1,496,872
bytes (58.7%). Ninety days saves only 22.9%; 14 saves more but gives a shorter
unconditionally retained reporting window. The 30-day recommendation leaves
roughly a month of recent investigation/reporting history.

The recent rate is about 30 KB/day over 30 days and 36 KB/day over the last
week. With weekly sweeps, ordinary recent history covers approximately 30–37
days. At those rates and today's exception size, expect roughly **1.1–1.5 MB**
of log, plus about 33 KB of schema-2 movement fingerprints in the parent.
This is an extrapolation, not a cap or workload forecast. Long-lived tickets,
stopped phone-home consumption or damaged input increase the exception floor;
successful retirement/consumption releases it. Record-size reduction remains
outside this ticket. Re-measure the implemented selector on the pinned blob
and current main during implementation; explain any difference from this
prototype rather than adjusting acceptance to match an accidental result.

### Investigated reader/writer map

This is the source snapshot behind the proposal; verify the relationships
again after main moves. New module/API names in Proposed shape are proposals,
not claims that those symbols already exist.

| Source and symbols | Relationship relevant to retention |
| --- | --- |
| `src/coga/logfile.py`: `log_lines`, `iter_log_messages`, `iter_log_messages_reverse`, `task_log_lines`, `last_activity_map`, `first_activity_map` | LF splitting, decoded forward/reverse messages and legacy continuation grouping are distinct APIs. First activity takes the minimum timestamp; last activity takes the physical last parseable event, not the maximum timestamp. |
| `src/coga/views.py`: `render_show`, `last_updated_map`, `render_status`; `src/coga/megalaunch.py`: `_tasks_in_service_order`; `src/coga/service_order.py`: `service_order` | Show consumes task history; views consume activity maps, and megalaunch supplies the first-activity map to service ordering. Existing-task history retention preserves these inputs. |
| `src/coga/validate.py`: `_check_one_task` | Idle diagnosis calls `logfile.last_activity`; it must not be reset merely by pruning another ref's history. |
| `src/coga/recurring.py`: `_LedgerAccumulator`, `parse_serviced_period_entries`, `parse_serviced_period_entries_reverse`, `read_serviced_ledger`, `_pause_origins` | The shared accumulator defines valid maxima/errors; target-bounded reverse reads stop per ref. Pause parsing reads the file directly and uses timestamp plus same-minute append order, including creation resets. |
| `src/coga/recurring_runner.py`: `_CONTROL_LOG_ENTRY_RE`, `_read_control_ledger`, `_control_serviced_period_cached` | Control-blob and diff readers bypass ordinary file iterators. The diff reader currently parses both added and removed ledger lines as external competitor changes, which requires the semantic-removal adjustment. |
| `src/coga/usage.py`: `_LOG_LINE_RE`, `load_records`; `src/coga_edge/phone_home.py`: `_ENTRY`, `_movement`, `_cursor`, `run_phone_home` | Usage reads/decodes the raw log before JSON parsing; phone-home reads raw bytes and validates a consumed prefix. Both bypass task-history helpers. |
| `src/coga/cli.py`: `_log_mark`, `_warn_unpublished_log_lines`, `_control_log_lines` | The exit diagnostic falls back to a whole-log comparison after a rewrite. An archived-event disposition must be shared with publication so trimming does not cause a false warning or hide a new event. |
| `src/coga/logfile.py`: `append_log`, `retract_log_lines`; `src/coga/launch.py`: `_retract_log_append`; `src/coga/commands/owner.py`: `owner`; `src/coga/megalaunch.py`: `_restore_ticket_bytes`; `src/coga/recurring_runner.py`: `_restore_period_bytes` | Appending currently opens without the state lock; retractions rewrite bytes, and task/period rollback callers depend on them. The launch path separately retracts a returned provisional append. All must participate in the new transaction. |
| `src/coga/git.py`: `publish`, `_publish_locked`, `_candidates`, `_guard`, `_build_tree`, `_merge_union_bytes`, `_stage_landed`, `fast_forward_control`, `_published_proof`, `_local_control_subsumed` | Candidate selection, retry guards, landed bytes and checkout proofs all encode today's union semantics. Changing only the filter or attribute leaves those assumptions inconsistent. |
| `src/coga/commands/update.py`: `copy_fresh_templates`; `src/coga/commands/init.py`: `_setup_initialized_clone`; `src/coga/recurring.py`: `scan_due` | Fresh init copies resources; existing-init setup does not install recurring templates; the scanner discovers local templates. The implementation must add the named adoption trigger rather than assume wheel replacement discovers repos. |
| `src/coga/runner.py`: `run_reported`; `src/coga/recurring_activity.py`: `is_machine_commit` | The failure-report floor is usable by unregistered edge jobs, and the proposed subject already fits the non-activity classifier. |

Direct prose consumers also matter: the live/package Dream `ticket.md`,
sections on history and the retro pass, and packaged
`bootstrap/skills/retro/done-ticket/SKILL.md` (retro evidence, cancellation
reason and snapshot history) instruct agents to inspect the log. The latter
has no live override in this checkout. Packaged
`bootstrap/retire/ticket.py::retire` routes canceled tickets to that Retro
workflow; `_delete_done_task` publishes task/log changes, rather than parsing
the log itself. The live `recurring/upstream-coga/ticket.py::main` includes
`log_path(cfg)` in publication; its findings cursor reads `upstream-coga.md`,
which is a different file and must not be trimmed. No additional executable
audit parser was found in live or packaged scripts by the `log.md`, `log_path`,
reader-API and v1-envelope searches. Run that inventory again during implementation.

### Owning documentation to change with implementation

- `coga/configuration` owns the setting; `recurring/trim-log/ticket.md` owns
  the job and exceptions; its `operations.md` owns adoption/recovery. Link from
  `coga/install`/`coga/init` and `coga/edge-code` rather than duplicate the runbook.
- `coga-dev/internals/spool-merge` owns the revised log merge/mutation invariant;
  read its cited sections above before replacing the append-only justification.
  Keep the unrelated retire worklist contract intact. Update
  `coga-dev/internals/state-publication/publish` for the shared mutation API.
- `coga/state-publication` and `coga/checkouts` leaves own publication, retained
  state and checkout-proof/recovery behavior; replace obsolete union-log claims.
  `coga/recurring/scheduling` owns unchanged ledger/pause semantics and the
  benign historical-ledger deletion case.
- `coga/usage` owns retained-history reporting; `recurring/phone-home/ticket.md`
  owns the new cursor and its migration, including the two sections named in
  the original task. Update `coga/recurring/templates` if its cross-run-state
  wording needs to identify the narrowly authorized cursor migration writer.
- Fix brief append-only/unbounded summaries in `coga/architecture`,
  `coga/prompt-composition`, Dream and the log module documentation; link to
  the owners instead of restating the retention algorithm. Keep every
  shipped topic/template twin identical, preserving the existing phone-home
  runtime-state exception rather than copying its identity into the package.

Implementation/release handoff must retain the behavioral notice in the
trim runbook and actual release notes. There is no repository changelog to
pretend was updated during this design step.

<!-- Ticket guide — keep this comment when filling in or updating the ticket.
It documents field shapes; these are examples, not values to copy into every
ticket. Omit optional fields and sections until needed. Editing rules come
from the base prompt; body regions from coga/tickets; blackboard conventions
(superseded designs, draft cleanup, oversized notes) from coga/blackboard.
Write requirements under ### subheadings of Description or Context; any other
level-two heading above the fence does not reach the launch prompt.

FRONTMATTER
The real values are in this ticket's YAML header. Required ordinary-ticket
keys are title, status, owner, and workflow. A minimal draft has workflow: null.

    title: Fix retry diagnostics           # What the work is called; identity comes from the file path.
    status: draft                          # CLI state: draft, active, in_progress, paused, blocked, done, canceled.
    owner: human-name                      # Accountable human; receives notifications and owner gates.
    agent: codex                           # Optional configured main agent; activation supplies the default if absent.
    contexts:                              # Optional facts to include in every launch; attach only what is needed.
      - service/retries
    skills:                                # Optional ticket-wide procedures, in addition to workflow step skills.
      - infra/testing-conventions
    workflow: code/with-review             # Draft reference or null; live tickets have the frozen mapping below.
    secrets:                               # Optional environment names mapped to references, never credentials.
      - API_TOKEN: env:LOCAL_API_TOKEN
      - SERVICE_KEY: op://automation-vault/service/api-key

The agent choice is not the current operator or the ticket interviewer.
Omit empty contexts, skills, and secrets lists. Each secrets entry has exactly
one unique name (no COGA_ prefix); env: reads the operator's environment and
op:// reads a 1Password item at launch, exposing the value under the left-hand
name. An unavailable reference prevents launch. Never put a literal secret here.

A workflow must be selected before activation. Creation with --workflow, or
activation of a draft reference, freezes its steps. CLI transitions manage step;
do not rewrite a live snapshot or advance it by editing YAML. Frozen example:

    workflow:
      name: code/with-review                # Selected workflow name.
      steps:
        - name: implement                  # Ordered step name.
          skills:                          # Optional procedures for this step; plural, never skill.
            - code/implement
          assignee: agent                  # Role: owner, agent, or other-agent (the configured peer).
          requires: branch                 # Optional completion gate: branch or pr.
    step: 1 (implement)                    # One-based position plus name; CLI removes this on completion.

An omitted step assignee inherits the previous role; the first defaults to
owner. The current step determines who holds the ticket. There is no top-level
assignment field. Removed keys slug, human, assignee, and watchers are invalid.
There is no execution-mode field: a sibling ticket.py supplies a script phase.

Repo extensions are string fields declared under [ticket.fields.<name>] in
coga.toml: description explains the field, values restricts its choices,
default seeds it, and required prevents activation while it is empty. Actual
values live below the extensions marker comment in the YAML header. Preserve
them; do not invent extension fields or change their definitions in config.

Machine-owned fields: delegate freezes a recurring parent's bootstrap/<name>
target; period_generation identifies its materialized run. Both belong only on
period tasks directly under tasks/recurring/. launch_generation is megalaunch's
session claim. Preserve these fields; do not add or clear them yourself.

BLACKBOARD (BELOW THE FENCE)
Keep current decisions and their reasons, verification, next actions, and
blockers here. Update current values in place instead of appending stale copies.

Optional ## Dev: branch: <name> when created; pr: <full /pull/ URL> when opened;
worktree: <path> only for a sandbox clone. One field per line, notes on separate
lines, omit unknown values. For multiple owned branches, the first branch is
the workflow branch.

Optional ## PR: one fenced YAML mapping of PR-preparation receipts (title,
author, head/base OIDs, review depth, files, review, checks). Record only actual
implementation and evidence, never placeholders; coga/pr-publication/
preparation owns the fields and the publishing workflow the review rules.

Optional ## Blockers and ## Blocker reminders are CLI-maintained. Preserve
blocker IDs, timestamps, actor names, resolved answers, and reminder fingerprints
with last_reminded timestamps; use lifecycle commands to block or resolve them.

Recurring parents (coga/recurring/<name>/ticket.md) take schedule and related
template settings owned by coga/recurring/templates; do not add them to an
ordinary ticket.
-->

<!-- coga:blackboard -->

## Design handoff

The implementable proposal, acceptance checklist, verification matrix and
source inventory are above the fence under Description/Context. Only this
ticket changed; no branch, implementation, PR or manual log/config edit.
Main was refreshed during investigation from `676a7b173` to `9bff7b617`;
the intervening change added an unrelated draft ticket and two log events.
The final measurement uses the newer log and includes the retention exceptions.

Recommendations: 30 days; complete histories for tickets still on disk;
Monday 04:00 repo-scoped maintenance even when inactive; shared guarded log
deletion and append reconciliation, with native Git conflicts replacing log
union; fingerprint-based phone-home cursor; explicit feature adoption for
existing repos. Measured retained log: 1,053,921 of 2,550,793 bytes (58.7% saved).

The non-obvious coupling is the runner's ledger-diff cache: it treats removed
historical ledger entries as competitor activity today. The implementation
must distinguish benign evidence compaction. Also verify other-checkout
fast-forward locking, exact rollback deletion and already-published proofs;
a trim-only lock or isolated filter does not cover these paths.

## Open Questions

For the owner at `review-design`, after the independent evaluator:

1. Approve the proposed **30-day default** and the preservation exceptions,
   especially retaining complete on-disk task histories and unread phone-home
   movement. They make this a soft age bound; work never retired or a consumer
   never run can retain older data. The measured alternatives are in Context.
2. Approve the native-Git tradeoff: Coga appends reconcile through its publisher,
   but competing direct Git log edits can require explicit conflict recovery
   after replacing `merge=union` with `-merge`. The proposal prefers a visible
   conflict over silent loss/resurrection and includes recovery tests/docs.
3. Confirm the explicit existing-repo adoption trigger (upgrade all writers,
   then the feature-specific `--install` operation). Fresh init is default-on;
   existing repos become default-on when these reviewed repo files are adopted.
   A wheel-only upgrade cannot truthfully promise delivery of a new schedule.

These are design-gate choices, not missing input needed to finish this step.
No periodic telemetry undercount is proposed for acceptance: the design fixes
the cursor instead. No owner approval has been inferred.

## Verification

- Read-only measurement used the log SHA-256 and source revision recorded in
  Context, the actual task inventory, shared period parser and movement parser.
- A scratch native-Git trim-versus-append probe with `log.md -merge` returned
  exit 1 and three unmerged index stages; both the trimmed side and the peer's
  full append remained recoverable. This verifies the proposed attribute
  behavior, not the unimplemented Coga reconciliation design.
- `.venv/bin/python -m coga.cli validate --task
  commit-journal/trim-the-audit-log --json`: one task valid, no issues.
- `compose.compose_prompt_report` (read-only Python call) confirmed acceptance,
  proposed shape, verification, out-of-scope, measurement and reader inventory
  all reach the prompt; the blackboard fence is unique.
- `git diff --check` passed. Implementation tests and the full pytest suite
  remain obligations of the implementation step; no feature code exists yet.

## Evaluator review

Reviewed cold on 2026-10-27 against current control
`c3ecc4540664205749a30d64ce60184126810ebf`. **Not ready for implementation:
resolve the three must-fix findings below at the owner design gate.** These
are design findings, not operational blockers and not an owner approval.

The Description/Context heading structure reaches the implementer correctly;
the frozen `code/design-then-implement` workflow places the owner gate next.
The config, ledger ordering, pause/reset, edge-entry and machine-commit claims
match the inspected source. The proposed shared modules have real consumers
and the job stays at the edge. The breadth of publication and telemetry work
is relevant to safe retention, rather than unrelated scope. The three product
choices in Open Questions still belong to the owner.

### Must fix before implementation

1. **P1 — Resolve the conflict between forgotten movement fingerprints and
   stale-event suppression.** The proposed schema-2 cursor replaces its hash
   set with the currently retained movement set. Consider a consumed, expired
   movement event A for a retired ticket: trim removes A; the next phone-home
   reservation drops its hash; a stale feature checkout whose HEAD predates
   A's publication still carries A. Publication can therefore consider A an
   incoming event, and A is provably in reachable control history. However,
   applying keep-rule 5 to that candidate now calls A *unconsumed*, so the
   proposed "eligible under the current retention policy" prerequisite
   prevents suppressing it. The next report counts A again. The design must
   define which snapshot determines unread protection and how source/archive
   provenance distinguishes this forgotten, previously consumed event from
   genuinely unread input. Hash absence alone cannot establish unreadness
   for an incoming replay candidate. Add the combined
   consume → trim → reserve → stale publish → report test, asserting no
   resurrection/recount while a genuinely new backdated movement still counts.
   Evidence: this ticket's retention keep-rule 5, ordinary-publication rules
   and schema-2 set-replacement rule; `src/coga_edge/phone_home.py::_movement`
   and `_cursor`; `tests/test_git.py::test_publish_from_a_far_back_merge_base_lands_no_duplicate`.
   A read-only model using the existing movement recognizer reproduced the
   proposal's missing-hash/protected-again/count-1 sequence; this is a design
   counterexample, not a claim that schema 2 already exists.

2. **P1 — Define recovery across the period-script process boundary.** The
   ordered transaction retains local output after uncertain publication and
   prohibits an ordinary sweep from reinterpreting it, but only names an
   in-memory `log_mutation` argument and a nonzero retryable exit. Name the
   mechanism that keeps the log/parent transaction recognizable after the
   child exits or crashes, the exit propagated by an ordinary recurring
   period, and the exact recovery action for accepted-but-unacknowledged and
   definitely-unpublished outcomes. A receipt may be reconstructible from
   retained Git evidence; this finding does not require a second archive.
   Current machinery cannot be assumed to supply this isolation:
   `src/coga/launch_script.py::run_script_chain` invokes `between_phases`
   before returning a stateful script failure; its early exit-75 bypass is
   bootstrap-only. `src/coga/launch.py::_CheckoutBoundary.settle` explicitly
   calls `git.sync_coga_state`, and `cli.main` also sweeps ordinary nonzero
   exits. A mocked stateful exit-75 probe invoked the settlement callback
   once. The proposed publisher's unreceipted-truncation refusal must cover
   these paths and later commands, or the lifecycle contract must change;
   merely returning nonzero is insufficient. Add real launch/sweep tests for
   a crash after log replacement, uncertain push, teardown, and the next
   unrelated mutating command. Also account for `git._guard` appending
   `sync refused` evidence: that changes the planned postimage and defeats a
   rollback that only recognizes an unchanged whole output.

3. **P2 — Preserve opaque-block attribution in existing history readers.**
   The parser keeps unexpected continuations after v1 events as opaque blocks
   while allowing their expired preceding event to be removed. Today
   `src/coga/logfile.py::task_log_lines` attaches *every* unmatched line to the
   most recent matching ref, regardless of v1. For physical order
   `recent [existing] event`, `expired [removed] v1 event`, `opaque line`,
   deleting only the middle event makes the opaque line appear in
   `existing`'s history and `views.render_show`. A scratch fixture using the
   current reader reproduced that change. Specify whether conservative
   retention also pins the boundary event needed to prevent reattachment,
   or explicitly extend the reader/parser migration with its compatibility
   rule. Preserving opaque bytes alone does not meet the promised unchanged
   existing-task display semantics. Add this case, including a malformed
   timestamp-looking opaque header, to the before/after reader fixtures.

### Optional recommendations

- Make the adoption file allowlist explicit about
  `recurring/trim-log/operations.md`: the current wording installs only the
  ticket/shim pair and workflow, while separately requiring that persistent
  runbook. Also name the concrete live-repo activation handoff and temporary
  twin policy. `git._candidates` / `_routine_state_areas` and the checkouts
  contract confirm that committed recurring files publish ahead of the code
  PR; the cited alternative "documented compatible two-phase rollout" has
  no corresponding procedure in the current contexts. A named post-merge
  operator step would make the proposed staging option reviewable.
- Include a representative history-scan cost receipt, especially repeated
  publication from an unmoving stale HEAD. "One transient history scan per
  publication" bounds the scan count, not its cost as reachable log history
  grows. This is an implementation feasibility check, not a request for a
  cache, tombstone store, or broader performance project.

### Evidence and scope

- `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q tests/test_logfile.py tests/test_telemetry.py`
  → **111 passed in 4.08s**. These establish existing reader/cursor behavior;
  they do not validate the unimplemented retention feature.
- Read-only `git show` plus Python hashing reproduced the pinned measurement
  input: 2,550,793 bytes, 9,552 LF lines and SHA-256
  `1122f575a28c8f74ceb568e6dbba361b36c2b5f382a9d7ffb548fe2853ab32e7`.
  The retained-size results remain the design prototype's figures, to be
  rechecked against the implemented selector as the ticket requires.
- Inspected the attached contexts, cited configuration/microkernel/merge/
  scheduling/edge contracts, current publisher and checkout proofs, both
  retraction paths, recurring ledger cache, telemetry and installation tests.
  The live usage-report attachment delegates to `usage.load_records`; it
  does not add another independent audit parser.
- No ticket intent, lifecycle frontmatter, implementation, branch, PR, live
  log or configuration was edited. Only this blackboard review is authored;
  the lifecycle command performs the eventual handoff.
- `.venv/bin/python -m coga.cli validate --task commit-journal/trim-the-audit-log --json`
  → one valid task, no fixes or issues. `git diff --check` passed; the diff
  contains only this evaluator review, and above-fence bytes match the saved
  preimage exactly.
- Final `git fetch origin main` succeeded; HEAD and `origin/main` remain at
  the reviewed revision. No reconciliation conflict or occupied checkout.
## Dev

pr: https://github.com/FastJVM/coga/pull/1129
branch: coga/trim-the-audit-log

Post-merge obligation (not discharged by the merge): activation in this repo is filed as draft
`commit-journal/activate-trim-log-in-this-repo-after-retention-mer`.

## Implementation handoff — 2026-10-27

Feature commits are pushed on `coga/trim-the-audit-log` at
`8e1805b146e20cc7de86b5ea900437dbb5b81730`, based on current control
`fa9070d1c3bb742df8491f169c42fad13e16e7a2`. The manual checkout has returned
to fast-forwarded main. No PR was opened. The human's audit-recorded advance
to implement at 2026-10-27 18:27 supersedes the earlier design-gate questions.
Actual implementing agent: Codex (GPT-6). This resumed session also used
Codex (GPT-6) for reconciliation, verification and the implement handoff.

The evaluator's three must-fix findings are addressed:

- Replay classification uses unread protection from pinned control, plus
  exact reachable Git evidence, so consume → trim → forget → stale publish
  does not recount an old movement; genuinely new backdated movement counts.
- A per-checkout receipt and pinned Git intent survive child crashes and
  uncertain pushes. Settlement and later publishers refuse pending deletion;
  recovery distinguishes accepted/unpublished outcomes and preserves later
  diagnostic appends. Real stateful launch and later-publication tests cover it.
- Opaque blocks retain their preceding attribution boundary, preserving
  existing task history/show semantics. Legacy continuations remain whole.

Other verification includes both append/trim publication orders, merge-only
archive evidence, native conflict recovery, both rollback writers under the
state lock, inventory/cursor changes during rejected pushes, trim between
another sweep's publications, repeated cursor/report alternation, parked
reporters, and fresh/pre-feature installed-wheel adoption with explicit 0,
custom/parked files and effective attribute refusal. Protocol corruption
refuses before deleting history. Retire-worklist union behavior remains intact.

Activation handoff: after the code PR merges, quiesce and upgrade every writer,
then run the documented interpreter-resolved `python -m coga_edge.trim_log
--install`, review/publish its five named repo artifacts and remove the temporary
attribute twin exception once copies match. `rollout/trim-log/coga` keeps the
new live schedule outside swept roots until then. The persistent runbook and
`docs/release-notes/audit-retention.md` announce default-on retention, its
exceptions, historical report limits, native conflicts and explicit adoption.
This session did not edit live config, manually trim the live log, or adopt
the feature into another live repository.

Read-only measurement uses the shared selector with local date fixed to
2026-10-27. The resumed run reproduces the pinned
`9bff7b617e5aec1c195bee5e79082c6061771094` result exactly: **1,053,921 /
2,550,793 bytes**, 3,814 retained LF lines and 5,181 removed events.
At verification control `fa9070d1c3bb742df8491f169c42fad13e16e7a2`, SHA-256
`af19580002dbeebba79837fc73c74c9e95344b7ff6a5d5bbf806dd8abc888b83`, the result
is **1,074,214 / 2,571,086 bytes**, 3,862 / 9,600 LF lines, 9,012 events,
150 tasks and the same 5,181 removals. All 20,293 additional bytes versus the
pinned design input are retained recent events. The historical scan-cost
receipt remains a review limitation; no permanent history cache or tombstone
store was added.

The owner cleared the baseline-test blocker in this resumed session after
main's separate repair `51e15ec238cda9c994f1a1464ce3267d89bbe48b` was verified.
`coga unblock` recorded the answer; no waiver was used. All three feature
commits rebased unchanged (`git range-diff` reports equality) onto the control
revision above. The fresh full suite passed: **4,200 passed, 10 skipped in
415.63s**, on Linux/Python 3.12.12. Fixture validation has no issues; live and
control validation match at 150 valid tasks, zero errors and 48 identical
kind/task/severity warnings. The feature was pushed and this manual checkout
returned to clean, fast-forwarded main before this handoff edit.

The PR preparation below replaces superseded test receipts with the executed
fresh checks, retains the historical scan-cost evidence, and removes an extra
separator that made the old preparation unparsable. No implementation change
was needed. Independent code review is still pending; no PR has been opened.
The final action for this step is `coga bump commit-journal/trim-the-audit-log`.

## Peer review — 2026-10-27

Direct Codex review **completed** on head
`99c9e1a0f8f3be58afde13fec1bf82cae8267d61`, base
`9b0103a99c18dcbda36f3941293bdda48859adf1`. Reviewed the complete diff and
publication/checkout, parsing/selection, recurring, cursor, recovery and
adoption contracts. Fresh session, but the implementing identity is also
Codex and this session authored fixes: recorded as **self-review**. No child
review tool/agent. Recommendation: **deep**. No unresolved feature findings.

Four reproduced findings fixed and re-reviewed in `99c9e1a0f`:

- P1: failed ancestry inspection could restore an accepted trim; now retains
  outputs and receipt instead of declaring it unpublished.
- P2: JSON attempt OIDs were unpinned; the receipt ref now retains every attempt.
- P2: publication/recovery normalized CRLF survivors; exact local log/cursor
  bytes now survive, with mixed-ending and uncertainty regression tests.
- P2: a retained failure report blocked retry as dirty inventory; only this
  period's appended report publishes under an exact guard before replanning.
  Other inventory edits still refuse.

Full final suite: **4,209 passed, 10 skipped in 413.57s**, Linux/Python 3.12.12.
Exact commands/receipts are in PR below. Earlier focused trim/launch checks:
`PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q tests/test_trim_log.py tests/test_launch_script.py`
→ 107 passed in 28.38s. Real subprocess and installed-wheel tests cover the
headless surface; no terminal UI changed. Python 3.11/native Windows/macOS
were not run. The historical ~20.5s archive-scan receipt was not remeasured.

An initial reordered focused run (log retention, trim, telemetry, launch,
recurring, Git) had 984 passes/3 sweep failures; those three passed alone.
This minimal reproduction also fails unchanged main (2 passed, 1 failed):

```sh
PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q tests/test_recurring.py::test_recurring_scan_relays_into_existing_control_worktree tests/test_git.py::test_recurring_all_child_retains_the_control_worktree_sweep
```

It identifies an existing `control_relay_started` test-order leak, not a
retention regression; the standard full-suite order passes. No waiver.
Baseline validation used `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m coga.cli validate --json > /tmp/coga-trim-peer-control-validation.json`:
150 valid tasks, zero errors, the same 48 kind/task/severity warnings as the
feature. Seeded validation has 4 valid tasks and no issues.

Fetched/rebased before review; range-diff proved all three implementation
commits unchanged. Final fetch showed no main movement. Pushed with
`--force-with-lease`, returned the manual checkout to current main, and
prepared all 81 PR paths. No live trim, config edit, activation or PR opening.
New review/PR prose was condensed from 35.7 to 31.8 KiB; earlier historical
notes and blocker records remain unchanged. Final scoped validation: one valid
ticket, no issues.

## PR

```yaml
title: Add default 30-day audit retention with guarded weekly maintenance
author: codex
author_evidence: The implementation handoff records Codex (GPT-6). This fresh Codex review session authored
  the fixes in 99c9e1a0f; shared recorded identity means self-review.
head: 99c9e1a0f8f3be58afde13fec1bf82cae8267d61
base: 9b0103a99c18dcbda36f3941293bdda48859adf1
depth: deep
rationale: Deletion authority, publication/checkout proofs, crash recovery and cursor identity warrant
  deep owner inspection. Direct self-review completed; all four feature findings are fixed and the full
  suite passed.
implementation: Default 30-day shared retention (0 disables), weekly edge maintenance and explicit adoption.
  Whole events preserve live ticket histories, recurring state, unread movement and opaque bytes. Guarded
  deletion, Git-backed receipts and fingerprint cursors prevent stale resurrection and isolate failed
  publication. Review fixes preserve CRLF bytes, pin attempts, keep failed ancestry checks uncertain and
  unblock report-and-retry.
deviations: The live enabling files are staged under rollout/trim-log/coga, outside swept roots, using
  the ticket-authorized two-phase rollout. The live log attribute remains an intentional temporary twin
  exception until post-merge adoption.
limitations: Requires quiesced adoption and compatible writers. Retention is a soft age bound; older usage
  may be incomplete. Native Git edits can conflict. Historical stale-input proof cost ~20.5s, not remeasured
  here. Verified on Linux/Python 3.12.12 only; no 3.11 or native Windows/macOS run. Self-review.
files:
  coga/recurring/dream/ticket.md: Describe retained audit history.
  coga/recurring/phone-home/ticket.md: Specify schema-2 cursors; preserve runtime state.
  coga/skills/coga/autoclose/sweep/SKILL.md: Remove obsolete audit-log append-only/union claims while
    preserving the owning process.
  coga/skills/coga/show/SKILL.md: Remove obsolete audit-log append-only/union claims while preserving
    the owning process.
  docs/contexts/coga-dev/internals/recurring-admission/SKILL.md: Specify benign ledger compaction during
    admission.
  docs/contexts/coga-dev/internals/spool-merge/SKILL.md: Specify event merging, mutation, locking and
    recovery.
  docs/contexts/coga-dev/internals/state-publication/publish/SKILL.md: Document the guarded mutation publication
    API.
  docs/contexts/coga/architecture/SKILL.md: Summarize retained audit history.
  docs/contexts/coga/checkouts/launch-boundary/SKILL.md: Document pending-mutation checkout refusals.
  docs/contexts/coga/configuration/SKILL.md: Specify retention settings, validation and the local calendar
    cutoff.
  docs/contexts/coga/edge-code/SKILL.md: Link compatible wheel/repo retention adoption.
  docs/contexts/coga/init/SKILL.md: Describe default-on fresh-init retention and link adoption.
  docs/contexts/coga/install/SKILL.md: Link the explicit compatible retention adoption procedure.
  docs/contexts/coga/prompt-composition/SKILL.md: Replace the obsolete append-only audit summary.
  docs/contexts/coga/recurring/scheduling/SKILL.md: Preserve ledger/pause meaning during valid evidence
    compaction.
  docs/contexts/coga/recurring/templates/SKILL.md: Name the limited cursor writer and inactivity exemption.
  docs/contexts/coga/script-tickets/SKILL.md: Explain receipt handling across stateful script teardown.
  docs/contexts/coga/state-publication/SKILL.md: Own guarded audit publication, deletion and recovery.
  docs/contexts/coga/usage/SKILL.md: Limit historical queries to retained records.
  docs/release-notes/audit-retention.md: Announce default-on retention, exceptions, historical reporting
    limits, native conflicts and adoption.
  rollout/trim-log/coga/.gitattributes: Stage activation outside swept roots until core lands.
  rollout/trim-log/coga/recurring/trim-log/operations.md: Stage activation outside swept roots until core
    lands.
  rollout/trim-log/coga/recurring/trim-log/ticket.md: Stage activation outside swept roots until core
    lands.
  rollout/trim-log/coga/recurring/trim-log/ticket.py: Stage activation outside swept roots until core
    lands.
  rollout/trim-log/coga/workflows/trim-log/run.md: Stage activation outside swept roots until core lands.
  src/coga/atomicio.py: Provide atomic byte replacement shared by log mutation and recovery.
  src/coga/cli.py: Use the publisher disposition for unpublished-event diagnostics after trimming.
  src/coga/config.py: Validate shared-only retention_days, default 30 and explicit 0.
  src/coga/create.py: Remove the obsolete append-only audit summary.
  src/coga/git.py: Reconcile events, guard deletions and checkout proofs, lock writes, preserve equivalent
    local CRLF bytes.
  src/coga/launch.py: Retract the exact provisional append through the shared event mutation API.
  src/coga/launch_script.py: Preserve a pending mutation across stateful exit-75 teardown.
  src/coga/log_publication.py: Share pinned policy/inventory/cursor reads and exact reachable-history
    replay proofs.
  src/coga/log_retention.py: Select original event spans with age and required-state preservation.
  src/coga/log_transaction.py: Pin intent/attempts; preserve uncertainty on inspection failure and exact
    log/cursor bytes in recovery.
  src/coga/logfile.py: Parse byte-preserving events and serialize append, atomic mutation and whole-event
    retraction.
  src/coga/megalaunch.py: Hold rollback transactions from their before-snapshots through retraction.
  src/coga/movement_cursor.py: Share movement identity, schema validation and lossless prefix migration.
  src/coga/paths.py: Describe the retained audit path.
  src/coga/recurring.py: Correct obsolete union/append-only audit explanations.
  src/coga/recurring_runner.py: Lock rollback transactions and distinguish benign ledger compaction from
    competitor admission.
  src/coga/resources/prompt.md: Describe the command-written audit trail as retained history.
  src/coga/resources/templates/coga/.gitattributes: Ship the matching canonical contract or artifact.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/architecture/SKILL.md: Ship the matching canonical
    contract or artifact.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/launch-boundary/SKILL.md: Ship the
    matching canonical contract or artifact.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/configuration/SKILL.md: Ship the matching
    canonical contract or artifact.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/edge-code/SKILL.md: Ship the matching canonical
    contract or artifact.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/init/SKILL.md: Ship the matching canonical
    contract or artifact.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/install/SKILL.md: Ship the matching canonical
    contract or artifact.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/prompt-composition/SKILL.md: Ship the matching
    canonical contract or artifact.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/SKILL.md: Ship the matching
    canonical contract or artifact.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/templates/SKILL.md: Ship the matching
    canonical contract or artifact.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/script-tickets/SKILL.md: Ship the matching
    canonical contract or artifact.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/state-publication/SKILL.md: Ship the matching
    canonical contract or artifact.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/usage/SKILL.md: Ship the matching canonical
    contract or artifact.
  src/coga/resources/templates/coga/bootstrap/skills/bootstrap/dream/scan/scan-protocol/SKILL.md: Ship
    the matching canonical contract or artifact.
  src/coga/resources/templates/coga/bootstrap/skills/coga/autoclose/sweep/SKILL.md: Ship the matching
    canonical contract or artifact.
  src/coga/resources/templates/coga/bootstrap/skills/coga/show/SKILL.md: Ship the matching canonical contract
    or artifact.
  src/coga/resources/templates/coga/recurring/dream/ticket.md: Ship the matching canonical contract or
    artifact.
  src/coga/resources/templates/coga/recurring/phone-home/ticket.md: Ship the matching canonical contract
    or artifact.
  src/coga/resources/templates/coga/recurring/trim-log/operations.md: Ship the matching canonical contract
    or artifact.
  src/coga/resources/templates/coga/recurring/trim-log/ticket.md: Ship the matching canonical contract
    or artifact.
  src/coga/resources/templates/coga/recurring/trim-log/ticket.py: Ship the matching canonical contract
    or artifact.
  src/coga/resources/templates/coga/workflows/trim-log/run.md: Ship the matching canonical contract or
    artifact.
  src/coga/retire_worklist.py: Keep the retire worklist union contract distinct from the audit log.
  src/coga/taskfile.py: Describe the separate retained audit history.
  src/coga_edge/phone_home.py: Reserve schema-2 movement fingerprints without changing delivery, identity,
    payload or run policy.
  src/coga_edge/trim_log.py: Run retention, cursor migration/recovery and bounded adoption; publish its
    appended failure report before retry.
  tests/fixtures/seeded-repo/coga/.gitattributes: Keep the seeded retention fixture representative.
  tests/fixtures/seeded-repo/coga/recurring/trim-log/operations.md: Keep the seeded retention fixture
    representative.
  tests/fixtures/seeded-repo/coga/recurring/trim-log/ticket.md: Keep the seeded retention fixture representative.
  tests/fixtures/seeded-repo/coga/recurring/trim-log/ticket.py: Keep the seeded retention fixture representative.
  tests/fixtures/seeded-repo/coga/tasks/declined-dream-finding.md: Keep the seeded retention fixture representative.
  tests/fixtures/seeded-repo/coga/workflows/trim-log/run.md: Keep the seeded retention fixture representative.
  tests/test_edge_distribution.py: Exercise actual wheels, documented interpreter adoption, opt-out/fork/parking
    preservation and headless completion.
  tests/test_launch_script.py: Exercise stateful exit-75/crash isolation, teardown and later publication
    with a durable receipt.
  tests/test_log_retention.py: Verify byte parsing, calendar boundaries, required readers/state, cursor
    migration and config rejection.
  tests/test_packaging.py: Enforce staged/package twins, the temporary attribute exception and schema-2
    seed.
  tests/test_recurring.py: Verify the new inactive exemption and a peer trim between sweep publications.
  tests/test_telemetry.py: Adapt cursor assertions to schema 2 while preserving wire and reporting behavior.
  tests/test_trim_log.py: Cover Git races, archives, native merges, cursor/CRLF recovery, reachable attempts
    and report-and-retry.
review:
  reviewer: codex
  kind: self
  status: passed
  head: 99c9e1a0f8f3be58afde13fec1bf82cae8267d61
  base: 9b0103a99c18dcbda36f3941293bdda48859adf1
  detail: 'Direct review completed on this head/base. Four reproduced findings fixed and re-reviewed:
    failed ancestry inspection, unpinned attempts, CRLF normalization, and failure reports blocking retry.
    No unresolved feature findings. Same recorded implementing identity and authored fixes: self-review.
    Real subprocess/wheel tests cover the headless surface; no terminal UI changed.'
checks:
- command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest > /tmp/coga-trim-peer-pytest.txt
    2>&1
  status: passed
  head: 99c9e1a0f8f3be58afde13fec1bf82cae8267d61
  base: 9b0103a99c18dcbda36f3941293bdda48859adf1
  detail: 4,209 passed, 10 skipped in 413.57s, Linux/Python 3.12.12. Full standard-order suite, including
    installed wheels, real-Git recovery, cursor alternation and packaging. No failures or waivers.
- command: env -u SLACK_WEBHOOK_URL PYTHONPATH=/home/n/Code/coga/src /home/n/Code/coga/.venv/bin/python
    -m coga.cli validate --json > /tmp/coga-trim-peer-fixture-validation.json
  status: passed
  head: 99c9e1a0f8f3be58afde13fec1bf82cae8267d61
  base: 9b0103a99c18dcbda36f3941293bdda48859adf1
  detail: 'Cwd tests/fixtures/seeded-repo/coga: 4 valid tasks, no fixes or issues.'
- command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m coga.cli validate --json > /tmp/coga-trim-peer-validation.json
  status: passed
  head: 99c9e1a0f8f3be58afde13fec1bf82cae8267d61
  base: 9b0103a99c18dcbda36f3941293bdda48859adf1
  detail: 150 valid tasks, no fixes, zero errors and 48 warnings. The exact kind/task/severity multiset
    matches the fresh control validation at 9b0103a99c18dcbda36f3941293bdda48859adf1; no new findings.
    Idle-hour text is ignored.
- command: git diff --check origin/main...HEAD
  status: passed
  head: 99c9e1a0f8f3be58afde13fec1bf82cae8267d61
  base: 9b0103a99c18dcbda36f3941293bdda48859adf1
  detail: No whitespace errors in the complete committed feature diff.
```

## Blockers

- [x] [2026-10-27 20:41] [agent:claude] id=20261027T204134 Repair the pre-existing docs/README.md link to ../README.md#key-concepts on main, or explicitly waive that baseline test failure for this implement step. The clean baseline reproduces it. Feature branch coga/trim-the-audit-log is pushed at 55759e68f123bb8be3de6d27d39303c2b6fc338f; full verification has 4199 passed, 10 skipped and this one failure. Fresh checks after state-only reconciliation have 174 passed and the same failure. Handoff and PR preparation are published; no PR or bump yet. code/implement requires escalating unrelated failures.
  resolved: [2026-10-27 21:33] [human:nicktoper] The owner authorized clearing this blocker and resuming verification. The separate owner-authorized repair is already on main in 51e15ec238cda9c994f1a1464ce3267d89bbe48b: docs/README.md now links to README.md#what-lives-in-your-repo. The previously failing navigation check passed on current main (1 passed in 0.40s). No test waiver or further link edit is needed; reconcile the feature and rerun verification.
