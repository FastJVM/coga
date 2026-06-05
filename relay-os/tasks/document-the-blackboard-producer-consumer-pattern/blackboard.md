The blackboard is a notepad to be written to often as the human and agent works through a task.

## ⟶ READ FIRST IF YOU ARE THE (RE)LAUNCHED `implement` STEP

**Implement is already DONE.** Do NOT re-implement. The change is committed and
pushed:

- Branch `patterns-spool-doc` (off main), commit `f107be8`, pushed to origin.
- `554 passed`, `relay validate` exit 0 (see Verification below).
- The diff is the new `relay/patterns` context (+ packaged mirror), an
  architecture pointer, and this task's ticket/blackboard. All scoped.

Your only action: confirm the working tree is on `patterns-spool-doc` with a
clean tree (`git status`), then run `relay bump` to advance to **peer-review**
(assignee flips to Codex). Nothing else to build.

Context: this session was a bare manual `claude` run on an `active` ticket, so
it couldn't bump (bump needs `in_progress`). `relay launch` flips that and
drives the rest.

---


## Dev

branch: patterns-spool-doc (off main / eb4e7ef)
PR: https://github.com/FastJVM/relay/pull/284 — opened directly at owner's
  request (Codex peer-review step bypassed; straight to owner review). The
  relay ticket stayed parked at implement/active because this manual session
  could not flip active→in_progress (only `relay launch` does that), so no
  bump fired. If you want the formal workflow state, `relay launch` the task
  and let it advance; otherwise merge the PR and let automerge mark it done.
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

## Workflow switch (human-directed)

Human switched the frozen workflow `dev/with-self-review` → `code/with-review`
mid-implement (they hand-edited the snapshot; agents don't touch it). New
steps: implement → **peer-review (other-agent = Codex)** → open-pr → review
(owner: nick). Step stays `1 (implement)` at switch time; the implement commit
already exists, so the bump lands us straight into peer-review.

## Handoff — peer-review (Codex)

You're reviewing a **documentation-only** change. Code (`src/relay/spool.py`)
already shipped in #275 and is NOT modified here.

- Branch: `patterns-spool-doc` (pushed to origin), one commit `f107be8`.
  Diff vs main: `git diff main..patterns-spool-doc`. Six files — the new
  `relay/patterns` context (local + packaged mirror), a 2-line pointer added
  to both `relay/architecture` copies, and this task's `ticket.md`/blackboard.
- What to scrutinize most: the **"Durability and concurrency"** section of
  `relay-os/contexts/relay/patterns/SKILL.md`. The core claim — the spool is
  NOT lock-guarded; correctness rests on single-CLI-process serialization, and
  `atomic_write_text` provides crash-safety only — is the load-bearing,
  previously-wrong-in-the-ticket part. Verify it against `src/relay/spool.py`'s
  docstring + `relay/architecture`'s no-mutex model + `relay/sync`'s digest
  section. Flag any drift between the doc and what spool.py actually does.
- Also check: the `relay.spool` API names match `__all__`; cross-refs resolve;
  the local context and the packaged `src/.../bootstrap/contexts/relay/patterns`
  copy are byte-identical (they were at author time).
- NOTE on checkout: this was built in the primary checkout (no worktree). The
  primary may be sitting on `recurring-launch-all` with the human's unrelated
  WIP; `git checkout patterns-spool-doc` to review the change.

## Retro

status: processed
skill: retro/done-ticket
result: no-new-durable-knowledge
title: No new durable knowledge for document-the-blackboard-producer-consumer-pattern
