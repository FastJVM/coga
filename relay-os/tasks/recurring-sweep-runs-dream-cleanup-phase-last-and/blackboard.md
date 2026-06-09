The blackboard is a notepad to be written to often as the human and agent works through a task.

## Evaluator review

Cold independent review of the draft (evaluator had not seen the authoring
conversation). Verbatim:

---

## Verdict: Promising ticket, but built on a factual error about deletion that will mislead the implementer. Do not launch as-is.

### 1. Is the description clear enough to start cold?

Mostly yes. The intent is legible: run Dream last as a cleanup/retro phase, and unify ticket-deletion. The "Done looks like" line gives a concrete acceptance scenario (digest + dream + relay-dev-update; Dream runs after the other two and reaps their tickets). The two design options (hardcode vs. generic `phase:` field) are surfaced rather than silently chosen, with a stated lean. That's good ticket hygiene.

The problem is that the central factual premise — "deletion is scattered across three mechanisms, consolidate them" — is wrong, and an agent who trusts it will go looking for code that does not exist (see #5). That undercuts the clarity.

### 2. Does code/with-review fit?

Yes, with one caveat. This is a real engine behavior change plus context updates plus tests — squarely a code change that benefits from peer review. The workflow's structure (implement → peer-review → open-pr → human review) fits.

Caveat: this ticket carries genuine unresolved design ambiguity (Option A vs. Option B, and — more importantly — the false "consolidate three deleters" framing). code/with-review's peer-review step catches implementation defects, not "the ticket asked for the wrong thing." If the implementer picks up the bad premise, peer-review may not save it. Consider resolving the design question (below) before launch rather than leaving it to the implement step.

### 3. Are the attached contexts right? Anything that should have been copied into ## Context?

`relay/recurring` is the correct and sufficient context — it is exactly the SKILL.md that documents the sweep, the scaffold contract, and the deletion model, and the ticket already says to update it in the same PR. Good.

One thing worth inlining: the SKILL.md's "Dream is the recurring janitor" section already states the deletion model authoritatively — "The recurring command does not delete real done period tasks... Dream-acting-on-`done` is the only cleanup path." That fact directly contradicts the ticket's ## Context, and the implementer needs it front-and-center. It would have been better to quote that sentence into ## Context so the contradiction is visible at authoring time.

### 4. Is the scope reasonable?

The ordering change alone is small and well-contained. The ticket correctly fences off catch-up/backfill as out of scope and names the un-built `recurring-catch-up-for-missed-runs` ticket. Good.

But the "consolidate deletion" half inflates scope around a non-problem. Once the false premise is corrected, the deletion-consolidation work largely evaporates (there is nothing real to consolidate — see #5), which actually makes the ticket smaller and cleaner. Re-scope it to "ordering only" and it's a tight single ticket.

### 5. Are the code pointers accurate? (verified against source)

Line numbers are stale/approximate but close enough to navigate — the function *names* all resolve:
- `main()` — ticket says ~124; actually defined at line 51. Line 124 is roughly where the launch loop body sits (the `for` is at 126). Misleading as written ("main(), ~line 124").
- `_launch_all_debug()` — ticket says ~165; actually line 145.
- `_finalize_debug_run()` — ticket says ~223; actually line 225. Close.
- `_reap_debug_orphans()` — ticket says ~254; actually line 256. Close.
- `scan_due` / `scan_debug` `sorted(root.iterdir())` — accurate: lines 187 and 382 of `src/relay/recurring.py`. The "ordering is alphabetical" root cause is correct.

The serious inaccuracy is conceptual, not line-number:

The ticket frames `_finalize_debug_run()` and `_reap_debug_orphans()` as two of "three mechanisms" that delete a sweep's tickets and should be folded into Dream. They are not. Both operate exclusively on `*-dbg-*` throwaway debug scratch (the `relay recurring --all` path), guarded by `is_debug_slug(...)`. They never touch real period tickets. The only deleter of real done period tickets is Dream's Phase 4 retro pass. The `recurring/SKILL.md` says this explicitly ("The recurring command does not delete real done period tasks... Dream-acting-on-`done` is the only cleanup path"), and so does the dream ticket body (lines ~178–185).

So there is no scattered real-ticket deletion to consolidate. There is exactly one real-ticket deleter (Dream) and two debug-only scratch reapers that are part of a separate, explicitly-acknowledged-as-temporary debug subsystem (the SKILL.md even says "`relay recurring --all` debug scratch is still reaped by the recurring command until the sibling redesign removes that debug path"). Folding debug-scratch cleanup into Dream's retro phase would be wrong — Dream doesn't run on the `--all` debug path at all.

### 6. Assumptions to question before launch

- **"Deletion is scattered across three mechanisms."** False, per #5. This is the load-bearing error. Before launch, either drop the consolidation half entirely (recommended — deletion is already centralized in Dream) or rewrite it precisely to say what, if anything, actually needs moving. As written it sends the implementer to consolidate debug-scratch reapers into Dream, which would break the debug path.

- **"Dream is just another template in the rotation, ordered alphabetically, so it can run before the tasks it cleans up."** The ordering observation is correct and is the real, valid bug. But note the mitigation that already exists: a period whose ticket Dream *missed* this sweep is not lost — it sits on disk as `status: done` and the next Dream run's Phase 4 reaps it (SKILL.md and dream ticket both state this). So the bug is "cleanup lags by one sweep," not "tickets leak forever." That weakens the urgency framing but not the correctness of fixing ordering. Worth stating accurately so the implementer doesn't over-engineer.

- **Option B's `phase:` field interacts with two scanners, not one.** If the implementer takes Option B (declare `phase: cleanup` in frontmatter), the sort must be applied in `scan_due` *and* the launch ordering — and note `DueScan.due` already re-sorts by `(not resuming, last_fire)` (recurring.py line 162). A cleanup-phase ordering has to compose with the existing resume-first / most-overdue-first ordering, not replace it. The ticket doesn't mention this; the implementer should be told the sort key is layered.

- **Dream runs `mode: interactive`, weekly (`0 9 * * 1`).** In a normal bare sweep, Dream and the daily/weekly templates rarely all fire in the same sweep, and Dream requires a TTY. The "Done looks like" scenario (digest + dream + relay-dev-update in one sweep) is most naturally reproduced via `relay recurring --all` (the debug path) — which is exactly the path the live 2026-06-09 diagnosis used (suffix `20260609T151909`). But `--all` uses `scan_debug` + `_launch_all_debug`, and on that path Dream does *not* delete anything (debug scratch is reaped by `_finalize_debug_run`, not by Dream). So the acceptance scenario as worded ("Dream is the thing that reaps their spent period tickets") is not reproducible on the `--all` path and only partially observable on a bare sweep. The implementer needs a clear answer to: *which path is this ticket fixing — bare sweep ordering, `--all` ordering, or both?* The diagnosis came from `--all`; the deletion behavior lives in the bare path. That mismatch should be resolved before launch.

- **Sync touchpoint is partly moot.** The ticket says keep `relay-os/` and the packaged copy under `src/relay/resources/templates/relay-os/` in sync. Verified: there is **no packaged copy of `contexts/relay/recurring/SKILL.md`** — the packaged `relay-os/contexts/` ships only `_template` and `browser`, not the `relay/` tree. So the SKILL.md edit has no packaged twin to sync. The packaged `recurring/dream/ticket.md` *does* exist and is currently in sync with live, so if this ticket touches the dream template, that one must be kept in sync. The generic sync instruction is fine, but the implementer shouldn't burn time hunting for a packaged recurring context that isn't shipped.

### Bottom line

Fix the ordering — real bug, correctly diagnosed, pointers good enough. But strike or rewrite the "consolidate three deleters" half: there is one real deleter (Dream) and two debug-only scratch reapers that must not be merged into it, and the attached SKILL.md already says so. Decide explicitly whether the target is the bare sweep, the `--all` debug path, or both, because the diagnosis and the deletion behavior currently live on different paths. With those corrections this becomes a tight, single, low-risk ticket.

---

## Author response to the review (applied before launch)

All three load-bearing claims verified against source and accepted:
- `_finalize_debug_run` / `_reap_debug_orphans` only `rmtree` `*-dbg-*` scratch
  (`is_debug_slug` guard) — they never delete real tickets.
- `relay/recurring` SKILL.md lines 102–122: Dream's Phase-4 retro pass is the
  *only* deleter of real done period tickets ("no recurring-command deletion").
- No packaged copy of `contexts/relay/recurring/SKILL.md` ships.

Ticket rewritten to **ordering-only**: struck the false "consolidate three
deleters" goal, reframed urgency to "cleanup lags one sweep" (not a leak),
scoped the fix to the **bare sweep** path (the `--all` debug path is out of
scope — Dream doesn't delete there), added the layered-sort-key note for
Option B, corrected line numbers, and fixed the sync touchpoint (no packaged
context twin; only the dream template has one).
