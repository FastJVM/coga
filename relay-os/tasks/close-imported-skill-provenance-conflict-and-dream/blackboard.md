The blackboard is a notepad to be written to often as the human and agent works through a task.

## Evaluator review

Independent cold review (general-purpose subagent, had not seen the authoring
discussion). Verdict: **ready-with-fixes**. Every technical claim in the ticket
was verified correct against the code.

### Verified claims (all TRUE)
- `_url_metadata()` (skill_manager.py:896-917) has no `local_adaptation_notes`.
- `install_url_skill` overwrites via `gh skill install` (skill_manager.py:161)
  with no pre-overwrite dirty guard; the `target.is_dir()` check (163) is
  post-install validation. No `--force` exists.
- `_update_url_skill_dir` early-returns `skipped-local-adaptation`
  (704-716) BEFORE the `download_url` at 736.
- No Dream phase invokes `relay skill update` (zero refs in either ticket.md
  copy). No `conflict` status exists today.
- The two Dream ticket.md copies are currently byte-identical — keep-in-sync
  instruction is accurate; renumber must hit both.

### Findings to address
1. **Gap 4 (Dream phase) is disproportionate.** Authoring a new bundled worker
   skill is comparable to existing workers (validate-drift/run.py ~19KB,
   cleanup-orphan-markers ~10KB), plus the `git add -f` + live-copy mirror, plus
   renumbering — and the renumber touches the "six phases" / "Phases 4-6 execute"
   framing sentences (dream ticket.md:39-52), not just the disposition heading.
   The ticket understated this. Decide: split gap 4 into its own ticket, or keep
   bundled with an explicit acknowledgment.
2. **Missing acceptance criteria / test names.** Name the new tests (conflict
   path, dirty-overwrite refusal, notes-preservation, PR-body conflict section),
   require `python -m pytest` + `relay validate --json` green, assert the exact
   new status string `conflict`.
3. **status/update asymmetry.** `_status_url_skill` (784-847) has a parallel
   `locally-adapted` early-return. The ticket only rewires `_update_url_skill_dir`.
   Decide whether `relay skill status --check` must also surface `conflict` for
   vocabulary consistency.
4. **`--force` underspecified.** Scope to `install-url` only (only path with a
   Relay digest to compare). Define what `--force` does to `installed_tree_digest`
   and `local_adaptation_notes` after overwrite.
5. **Fixtures.** Per CLAUDE.md, state whether `example/relay-os/` / the seeded
   fixture needs the new Dream phase/worker reflected (likely yes for the smoke
   path).

### Resolution applied to ticket
Fixes 2-5 folded into the ticket body (Acceptance Criteria added; `--force`
scoped to install-url with defined digest/notes behavior; status `--check` set
to also surface `conflict`). Fix 1: **nick chose to split.** This ticket now
covers gaps 1-3 only (CLI/metadata/conflict, code+tests). Gap 4 (Dream phase)
moved to its own ticket `add-dream-skill-update-maintenance-phase`. The
Dream-authoring gotcha and fixture criterion were removed from this ticket
accordingly (gaps 1-3 are pure src+tests, no fixture impact).
