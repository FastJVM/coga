The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: patterns-spool-doc (off main / eb4e7ef)
worktree: none — built directly in the primary checkout per human request
  (external worktrees were being cleaned up off-disk; we don't want stray ones).
  The primary was on `recurring-launch-all` (divergent, 37 behind main) with
  unrelated uncommitted work; that work was `git stash`ed before switching to
  `patterns-spool-doc`, to be restored on switch-back.

## Decisions (resolved with human during implement)

- **Home:** new `relay/patterns` context (not a section in architecture). Keeps
  architecture lean; gives future patterns a home. Added a one-line pointer
  from `relay/architecture`'s "does NOT cover" list for discoverability.
- **Code:** documentation-only — confirmed by fact, not preference:
  `src/relay/spool.py` already exists (shipped in #275) with `append_record`,
  `read_records`, `drain`. Nothing to extract.
- **Concurrency framing:** the ticket's original "lock-guarded" premise was
  wrong and contradicted shipped reality + `relay/architecture`'s no-mutex
  model. Corrected everywhere. The true story, which the doc now states:
  single-CLI-process serialization keeps append/drain from overlapping;
  `atomic_write_text` gives crash-safety (no torn file), NOT mutual exclusion.
  Genuinely concurrent producers would need the not-yet-built
  `file-locking-for-concurrent-task-mutation` primitive — until then, not
  lock-guarded. (Human steered here: "we can maintain by blocking/rejecting
  exec while producer is producing" = that future lock; we don't need it
  while single-process holds.)

## What changed (the diff)

- NEW `relay-os/contexts/relay/patterns/SKILL.md` — the pattern doc.
- NEW packaged mirror `src/relay/resources/templates/relay-os/bootstrap/contexts/relay/patterns/SKILL.md`
  (force-added: that template tree is gitignored but existing relay contexts
  there are tracked the same way).
- EDIT both `relay/architecture` copies (local + packaged) — discoverability
  pointer to `relay/patterns`.
- EDIT this ticket's body — corrected the stale "lock-guarded" wording in the
  Shape / Deliverables / Related sections and marked the Open questions resolved.

NOTE: live `relay-os/bootstrap/` is gitignored (init-materialized), so there's
no third tracked copy to maintain — only the local context + the packaged
template under `src/`.

## Verification

- `relay validate --json` → exit 0 (only pre-existing warn-level missing-workflow
  notes on unrelated draft tickets).
- `python -m pytest` → 554 passed. (First run showed 16 failures in
  recurring/repl_supervisor — a stale NON-editable relay in the venv. After
  `pip install -e .` in `relay-os/.relay/.venv`, all green. Unrelated to this
  change; no failing test references contexts.)
