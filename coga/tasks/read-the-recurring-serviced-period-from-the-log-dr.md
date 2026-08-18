---
slug: read-the-recurring-serviced-period-from-the-log-dr
title: Read the recurring serviced-period from the log, drop the blackboard marker
status: in_progress
owner: nick
human: nick
agent: claude
assignee: nick
contexts:
- coga/recurring
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
    skills:
    - code/address-pr-comments
    assignee: owner
secrets: null
step: 4 (review)
---

## Description

`coga recurring` decides "has this period already been serviced?" from
`last_serviced_period`, a single line in the recurring template's blackboard
region. Make the repo-global `coga/log.md` the ledger instead and delete the
marker outright.

### Why the marker fails

The blackboard is a shared free-text region, so a co-writer that rewrites part
of it can destroy the mark. The digest recipe does exactly that: `_STATE_RE`
matches `### Digest State` through EOF, and `_write_digest_state` replaces the
whole match — including a `last_serviced_period` line appended after it.

Observed in Magicator on 2026-07-27 (one-off) and again on 2026-08-13 as an
unbounded loop: three consecutive `coga recurring` invocations each printed
`digest ... → launch` / `Replaced completed recurring/digest` and posted a
separate Slack digest (7, then 2, then 8 items). Template git history shows the
writers alternating every cycle — a `recurring create` commit adding
`last_serviced_period: 2026-08-13`, the following digest `Sync coga state`
commit removing it. Each erasure sends `create_template` down the prior-period
branch (`done` and `not _period_already_serviced`), which deletes the completed
period task, recreates it, and reruns the recipe.

The loop is silent: the scan table prints `ready` / `→ launch`, which is
indistinguishable from a legitimate first firing.

### Why the log is the right ledger

- **It already holds the answer.** Every path that advances the marker also
  appends a line carrying the same period key —
  `_advance_serviced_period` → `_record_run`, and the two force paths →
  `_append_forced_reused_log`. No path advances the marker silently, so the log
  can never under-report a serviced period. In the 2026-08-13 incident the log
  recorded `deleted completed prior-period task before 2026-08-13` four lines
  after `created recurring/digest for 2026-08-13`; the proof was already on
  disk and simply never read.
- **Append-only is the anti-clobber property.** A co-writer rewriting a region
  cannot destroy an appended line.
- **It outlives the task.** Dream's Retro pass direct-deletes completed period
  tickets, so for most templates the task is gone and the ledger is the only
  surviving record. The log is repo-global, so it covers the reaped case and
  the surviving-task case identically.
- **Precedent exists.** `_append_forced_reused_log` already dedups by scanning
  `task_log_lines` for `reused <slug> for <period>`.
- **The marker is forbidden state.** `coga/principles` #3 forbids
  "derived/denormalized state that hides what a file already says". A cache of
  what the log records is precisely that, which is why this drops the marker
  rather than repairing it.

### No migration

The log record predates the marker — `_record_run`'s ancestor lands 2026-05-22,
`last_serviced_period` 2026-06-13 — so there is no historical period that
advanced the marker without a log line. Existing repos work from their existing
log.

### Scope

- Read the serviced period from `coga/log.md`, keyed by the `recurring/<name>`
  tag, in **one reverse pass** that short-circuits once every template resolves.
  The log is designed to grow unbounded, so do not scan it once per template.
- Give the log line one shared constant used for both write and parse, and pin
  the format with a test. Dedup now depends on the wording, so a reworded
  message must break a test rather than silently disable dedup.
- Delete `read_`/`write_`/`merge_last_serviced_period_text`,
  `set_last_serviced_period_text`, `_last_serviced_period_from_text`,
  `_local_blackboard_with_control_period`, and the cross-branch marker
  reconciliation in `recurring_runner.py`. The scanner should stop writing the
  template during a scan.
- Repoint `coga recurring list` and the `coga status` recurring footer, which
  read the marker for `ran this period — task reaped`.
- Strip the vestigial `last_serviced_period` line from shipped templates.
- Update the `coga/architecture` context — it currently states the log is "not
  the dedup source" — in both the live copy and the packaged copy.

### Out of scope

- Period keys compare as strings, so `2026-W33` and `2026-08-13` sort
  lexically. That is
  `recurring-last-serviced-period-compares-as-a-strin...`; the log-based read
  inherits the same comparison and neither fixes nor worsens it. Note on that
  ticket that the two now share a code path.
- The sync path committing a conflicted working tree (the 2026-08-13 run left
  `<<<<<<<` / `>>>>>>>` markers committed in `coga/recurring/digest/ticket.md`
  via a single-parent `Sync coga state` commit). Separate defect.

### Acceptance criteria

- Erasing or hand-removing any template blackboard content cannot cause a
  serviced period to re-fire.
- Repeated `coga recurring` invocations inside one period launch each template
  at most once.
- No `last_serviced_period` read or write remains in the source tree.
- Rollback paths that remove generated audit lines are checked: confirm a
  rolled-back create re-fires (correct) rather than wedging.

## Context

- `src/coga/recurring.py` — `_period_already_serviced`, `_advance_serviced_period`,
  `_record_run`, `create_template`'s replace-done branch, and the marker
  read/write helpers.
- `src/coga/recurring_runner.py` — the cross-branch marker reconciliation
  (~1101, 1311, 1340, 1421-1441, 1459, 1566, 1856) and
  `_append_forced_reused_log`, the existing log-as-dedup precedent.
- `src/coga/logfile.py` — `task_log_lines`; needs a reverse/single-pass read.
- `src/coga/views.py` and `src/coga/commands/recurring.py` — the template
  footer and `recurring list` period column.
- `src/coga/commands/digest.py` — `_STATE_RE` / `_write_digest_state`, the
  co-writer that exposed the bug; no longer needs to defend the marker.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

pr: https://github.com/FastJVM/coga/pull/699
branch: fix/recurring-log-reverse-pass
worktree: /home/n/Code/claude/coga-recurring-log-reverse-pass

## Implement notes

- PR #688 (`f5543446`) landed the main marker-to-log conversion before this
  workflow step started. The remaining ticket gaps are the required reverse,
  bounded ledger read and rollback coverage; source/help prose also still
  describes the removed blackboard marker.
- Preserve the exact `created|reused <task-ref> for <period>` contract while
  making scan/list callers supply the finite recurring refs they need, so one
  reverse pass can stop as soon as all of them resolve.

## Implement result (2026-08-17)

Commit `abb4eaca` on `fix/recurring-log-reverse-pass`. Everything else in the
ticket had already landed in PR #688 (`f5543446`) and PR #697 (`f3e6e322`);
re-verified before writing any code:

- No `last_serviced_period` read or write remains under `src/` — the eight
  prose sites the note below flags were fixed by #697. Shipped templates under
  `coga/recurring/` and `src/coga/resources/` carry no vestigial line. (The
  only surviving mention is historical prose in the *done* period task
  `coga/tasks/recurring/resolve-conflicts/ticket.md` — a reapable run
  blackboard, not shipped state.)
- `coga/architecture` already says the log line **is** the ledger.
- `coga recurring list` and the `coga status` footer already read the ledger.

So this step closed the two real gaps:

**1. Bounded reverse ledger read.** `read_serviced_ledger(cfg, refs)` takes the
finite ref set the caller needs, reads the log backwards through a new
`logfile.iter_log_messages_reverse`, and stops once every ref resolves.
`refs=None` keeps the whole-log forward read. Callers repointed: `scan_due` and
`list_templates` (via `_template_refs`, from directory names, before
`Template.load`), `create_template`, `_period_already_serviced`, and
`recurring_runner._sync_recurring_create`. Both directions fold through one
`_LedgerAccumulator` so they cannot disagree.

**Decision — a slack window, not "stop at the first hit."** `merge=union` can
leave a template's newest record *above* an older one, so pure reverse order is
a recency heuristic. Stopping at the first hit would under-report a serviced
period, which is the exact failure this ticket exists to kill. The read keeps
taking the maximum calendar position and continues `_LEDGER_TAIL_SLACK_LINES`
(500) past the last resolution. Tradeoff: a fixed 500-line tail overhead in
exchange for tolerating any realistic merge block.

Two behavior changes fall out of bounding the read, both documented in the
docstring and in `coga/recurring`:
- A template with **no** record yet never resolves, so its first firing still
  walks the whole log — the previous cost, paid once.
- A malformed record *older* than a valid one is no longer reached, so a
  template heals by servicing a period instead of staying wedged behind ancient
  bad state. A malformed record *newer* than the valid one is still surfaced.

**2. Rollback coverage.** `test_rolled_back_create_re_fires_once_its_ledger_line_is_gone`
checks both halves: line intact + task reaped → reads as handled (correct, the
Dream-reaped case); line removed as well (reverting the create) → the next scan
re-creates. No wedge.

Other tests added: reverse reader (newest-first, block-boundary seams, missing
trailing newline, absent log) in `tests/test_logfile.py`; bounded-read stop,
union-merge disorder in the tail, and per-ref error isolation in
`tests/test_recurring.py`.

### Verification

- `PYTHONPATH=$PWD/src python3.12 -m pytest` → 1789 passed, 1 skipped, 3 failed.
  All three fail identically on unmodified `main` (confirmed by running them
  there): `test_autoclose.py::test_recipe_preflights_live_summary_before_closing`,
  `test_recurring.py::test_named_launch_keeps_control_only_malformed_ledger_blocked_on_retry`,
  `test_recurring.py::test_sweep_retry_revalidates_control_only_malformed_ledger`.
  Not caused by this change; not fixed here (out of scope).
- `python -m coga.validate --json` → issue list identical to `main`'s apart
  from two environmental warnings for the feature checkout (no local `user`,
  and this ticket's own idle warning).

### Follow-up owed on the sibling ticket

Per the ticket's out-of-scope note,
`recurring-last-serviced-period-compares-as-a-strin` should record that the two
now share `_period_key_position` / `period_key_at_least`. That ticket already
landed (#697) and the shared code path exists; nothing further changed here.

## Note from `admin/carry-three-verified-coga-bugs-upstream` (2026-08-15)

The "source/help prose also still describes the removed blackboard marker" gap
above was independently verified during the 2026-08-15 Dream run in the `admin`
repo. Nothing reads or writes `last_serviced_period` any more, so these are
documentation only — but they are what makes the drift easy to reintroduce, and
it did reintroduce it: `admin`'s `dream` and `digest` recurring templates
carried the wrong claim until Dream PR #115. The eight surviving source/help
sites, including two semantic matches that no longer name the old field, so the
sweep does not have to be rediscovered:

- `src/coga/recurring.py:43`, `:102`, `:146`, `:309-310`, `:488-490`
- `src/coga/recurring_runner.py:76`, `:619`
- `src/coga/commands/recurring.py:60`

Each names the template blackboard as the high-water-mark carrier; they should
name the `coga/log.md` ledger instead. The two semantic matches matter because a
literal `last_serviced_period` grep cannot find them. Filed here rather than as
its own ticket because this ticket's acceptance criterion ("No
`last_serviced_period` read or write remains in the source tree") and its
implement note already own the scope.

## Peer review (2026-08-17)

`codex review --base main` found one P1 correctness issue in `abb4eaca` and
reproduced it: the fixed 500-line tail slack is not a safe bound for a
`merge=union` log. A long-lived branch can append an older serviced-period
record at EOF while the newer record sits arbitrarily far above it; the reader
then returns the older period and can relaunch already-serviced work.

Fix direction: replace the heuristic slack with a proof-bearing target per
template. A reverse read may stop for a ref only after finding a valid record
whose normalized period is at or after the exact period the caller is deciding.
An older record does not resolve the ref, so a due template scans to EOF; a
current-period record makes repeated same-period scans tail-bounded. This gives
up the claim that every new-period firing is bounded, which is impossible on an
unordered union-merged source without adding an index or denormalized marker,
in exchange for preserving exact dedup correctness and the markdown/log-only
architecture.

## Peer review result (2026-08-18)

The provisional fixed-slack decision above is superseded. Review produced and
closed three correctness/performance findings:

- `bc78bcae` replaced the unsafe 500-line heuristic with an exact target per
  template. A ref resolves only when the reverse pass finds a valid serviced
  period at or after the period the caller is deciding, so arbitrary
  `merge=union` disorder cannot make an already-serviced period re-fire.
- `70dcf6f0` made resolution independent per ref. A template that has reached
  its target stops accumulating immediately even when another template keeps
  the shared pass open, so its older malformed history cannot become an error
  merely because another ref is unresolved.
- The same commit carried the pre-create local ledger snapshot into the
  control guard after a successful control-branch catch-up. Normal git-backed
  sweeps therefore retain bounded reverse I/O instead of materializing the
  entire control Git blob; the best-effort fallback applies all targets to one
  pinned control read.

The branch was fetched and rebased unconditionally onto `origin/main` at
`4c29ba92`; it is clean and three commits ahead. A final
`codex review --base main` found no patch-introduced correctness defects.

Verification after the rebase and review fixes:

- Targeted reverse/control regressions: 7 passed.
- `tests/test_logfile.py tests/test_recurring.py`: 212 passed, 2 known
  branch-gate failures reproduced on `main`.
- Full suite: 1793 passed, 1 skipped, 3 failed. The failures are the same
  baseline/environment failures recorded above (`test_recipe_preflights_live_summary_before_closing`
  plus the two stale branch-gate tests); the final Codex review independently
  observed the same result.
- `coga validate --task read-the-recurring-serviced-period-from-the-log-dr --json`:
  1 OK, no issues.
- `git diff --check main...HEAD`: clean.

## PR

Make the append-only repo log the durable recurring-period ledger and keep its
unbounded read safe: scan all requested templates in one reverse pass, stop
each ref only on a proof-bearing target period, reuse the pre-create snapshot
for the control guard, and cover union-order, malformed-history, reverse-reader,
and rollback behavior. This removes the blackboard marker's clobber/re-fire
failure mode without adding a second state source.

Test plan: `PYTHONPATH=$PWD/src python3.12 -m pytest` (1793 passed, 1 skipped;
the 3 remaining failures reproduce on `main`).
