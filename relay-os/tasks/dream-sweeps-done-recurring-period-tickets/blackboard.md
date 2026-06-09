The blackboard is a notepad to be written to often as the human and agent works through a task.

## Investigation (2026-06-08, interactive)

### Decision: reuse retro-first pass, NO dedicated worker
The `retro/done-ticket` skill (Dream **Phase 4**) already processes *every
eligible done ticket* in one run, generically. A `recurring-<name>-<period>`
period ticket carries nothing durable (output is the Slack post / PR), so it
classifies as no-durable-knowledge → **direct-deleted via `relay delete <slug>`**
(working-tree `git rm` + `Ticket: <slug> — deleted` commit). The period ledger
line in `relay-os/recurring/<name>/log.md` is left untouched, so the period is
not re-scaffolded. This already satisfies the acceptance criteria *for the
deletion itself*. No new known-skill worker is warranted.

### The only thing to change in Dream: drop Phase 6 self-delete
`relay-os/recurring/dream/ticket.md` Phase 6 ends with:
> Then, as the very last action, run `relay delete <this-dream-task>` …
> Dream cleans up after itself in the same run …

That self-delete is the special case stage 3 removes. After this change a Dream
period ticket (`recurring-dream-<period>`) finishes `done` and **stays on disk**;
the **next** Dream run's Phase 4 retro pass deletes it like any other done
recurring ticket. Phase 4 gets explicit language that done `recurring-*`
tickets (including the prior Dream run) are knowledge-less and direct-deleted.

### Idempotency
Phase 4 eligibility already guards against double-delete: a ticket whose dir is
gone is not a candidate; an open PR touching it excludes it. Direct `relay
delete` on an already-gone slug is the failure to avoid — retro only ever passes
slugs whose dirs still exist, so no double-delete.

### Dependency on sibling (`dream-recurring-persist-done-stop-inline-delete`)
Sibling is **paused, design-only — no code landed**. BUT concretely the current
`relay recurring` command does **not** delete real `done` period tickets today:
its only deleters are `_finalize_debug_run` / `_reap_debug_orphans`, which touch
**only** `-dbg-` debug scratch, plus Dream's own self-delete. So making Dream the
deleter of real `done` recurring tickets now does **not** create a double-delete
on any real ticket — the two paths don't overlap on real period tickets. Stage 3
is therefore safe to land independently. (Confirmed with nick — see below.)

### Files to change
- `relay-os/recurring/dream/ticket.md` + packaged copy
  `src/relay/resources/templates/relay-os/recurring/dream/ticket.md` (in sync now):
  remove Phase 6 self-delete; clarify Phase 4 owns recurring-* done cleanup.
- `relay-os/contexts/relay/recurring/SKILL.md` (+ packaged copy): drop
  self-delete prose, name Dream as the recurring janitor for done period tickets.
- `relay-os/contexts/relay/current-direction/SKILL.md`: note stage 3 reflected.
- Tests: `tests/test_dream_worker_templates.py` / retro template test — assert
  the Dream template no longer self-deletes and Phase 4 covers recurring-*.

## Dev

branch: dream-recurring-janitor
worktree: /home/n/Code/relay-dream-recurring-janitor

## Implementation done (2026-06-08)

Scoped, committed on `dream-recurring-janitor`. Changes:

1. **Dream template** (`relay-os/recurring/dream/ticket.md` + packaged copy,
   in sync): Phase 4 now explicitly states a done `recurring-<name>-<period>`
   ticket is an eligible done ticket like any other → knowledge-less →
   direct-deleted via `relay delete`, ledger line preserved; includes the
   prior `recurring-dream-<period>` run. **Phase 6 self-delete removed** —
   Dream marks itself `done` and stops; the next run sweeps it. Intro line 22
   reworded ("a later Dream run retires…").
2. **`relay/recurring` context**: updated the period-ledger parenthetical and
   added a "## Dream is the recurring janitor" section. Left the `*-dbg-*`
   debug-reap prose alone — that's the **sibling's** scope (stages 1–2).
3. **`relay/current-direction`**: pulled in the staged redesign section (per
   nick) and updated its note to mark stage 3 landed; debug-reap prose stays
   pending the sibling.
4. **`src/relay/recurring.py`**: corrected 4 code comments that asserted "Dream
   self-deletes" (comment-only; behavior unchanged) to "a later Dream run's
   retro pass deletes…". Left the debug machinery / scan logic untouched
   (sibling territory).
5. **Tests**: added `test_dream_is_the_single_deleter_of_done_recurring_tickets`.

### Verification
- `python -m pytest`: **577 passed, 1 skipped, 1 failed**. The 1 failure is
  `test_cleanup_orphan_markers_declares_contract` — **pre-existing on clean
  main** (a line-wrap mismatch in the cleanup-orphan-markers SKILL text:
  "reports eligible candidates as\n`human-needed`" vs the test's spaced
  phrase). NOT caused by this change; left for a follow-up (out of scope).
- `relay validate --json`: worktree reduces to the **same 2 pre-existing
  `missing-step` errors** as clean main (`relay-additions-spec`,
  `split-context-to-doc-user-accessible-and-editable`) once `relay-os/bootstrap`
  batteries are materialized. No new validation errors.

### Decision recorded (acceptance criterion)
No dedicated worker needed — reused retro/done-ticket (Phase 4), which already
processes every eligible done ticket generically. Confirmed with nick.
