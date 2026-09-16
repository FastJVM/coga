---
title: Persist autoclose retire follow-ups
status: in_progress
owner: nicktoper
agent: claude
contexts:
- coga/principles
- coga/architecture
- coga/codebase
- coga/recurring
workflow:
  name: code/with-self-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: self-qa
    skills:
    - code/self-qa
    assignee: agent
  - name: pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 2 (self-qa)
launch_generation: 86a8861d-938e-40b9-b695-8b34d944f96a
---

## Description

Keep autoclose's unfinished `coga retire` follow-ups across recurring runs.
The 2026-09-03 Multiply sweep recorded its cleanup reminder only in
`coga/tasks/recurring/autoclose-merged/ticket.md`. The next period replaces that
completed task, so the reminder disappears even though the checkout or branch
may still need attention. Autoclose only rediscovers tickets it closes in the
current run, so this debt is not reconstructed automatically.

This is a Coga defect observed in a consuming repository. It replaces Multiply
ticket `autofix/persist-autoclose-retire-follow-ups-beyond-the-per` and the
implementation proposed in [Multiply PR #46](https://github.com/FastJVM/multiply/pull/46).
The owner redirected the work upstream on 2026-09-04. The reusable writer,
worklist maintenance, documentation, and regression coverage belong in Coga;
Multiply should consume the shipped fix without a separate maintenance script
or a dependency on an unpushed editable Coga branch.

### Required outcome

1. Give recurring autoclose follow-ups a durable, explicitly documented home
   outside the period task. The existing implementation uses `retires.md`
   beside the recurring template. Resolve the actual template instead of
   hardcoding `autoclose-merged`; retain ordinary non-recurring report surfaces.
2. Make recording idempotent by task ref, preserve unrelated pending entries,
   and define how entries clear once their recorded worktree and branch no
   longer need retirement. Ship that maintenance through Coga's existing
   autoclose/retire surfaces so consuming repositories need no custom Python.
3. Preserve the separation between recording a follow-up and destroying a
   checkout. Autoclose must not remove worktrees or branches; `coga retire`
   remains responsible for its existing safety checks.
4. Reconcile the live and packaged autoclose skill, recurring template, and
   applicable context/documentation with the actual writer and maintenance
   behavior. Document how existing installations adopt the fix, including any
   old local template/workflow overrides; a local editable source checkout is
   not the delivery mechanism.
5. Cover period-task deletion/recreation, reruns and duplicate slugs,
   completed versus still-live cleanup debt, and ordinary non-recurring
   reporting. Recheck parsing and write consistency when integrating the
   preserved patches with current main.

### Existing work to reuse

The old ticket's initial claim that emission was agent-side was incorrect.
`src/coga/autoclose.py::_report_retire_followups` performs the write and uses
`blackboard_from_env`, which points at the ephemeral period ticket. This path
is still present in `/home/n/Code/coga` at handoff inspection.

An implementation and a self-QA correction are already committed in the
separate local checkout `/home/n/Code/claude/coga`, on
`autoclose-retires-durable-home`:

- `fa3880b1` — Write autoclose retire follow-ups to a durable worklist.
- `c5cb1548` — Correct the sweep skill's surfaces and harden worklist parsing.

No PR for that upstream branch was found at handoff. The attached
`coga-existing-implementation.patch` preserves both commits, so resuming does
not require that local checkout to survive. It is a starting point for review
and integration, not evidence that current main passes validation.

`multiply-support.patch` preserves the companion script, tests, worklist seed,
and template/workflow changes from Multiply PR #46. Use its behavior and
regressions as input when completing the upstream implementation; do not add
the Multiply script as a requirement for consumers. The historical seed has 14
entries, of which the old investigation found only four still actionable.
Re-derive current cleanup debt before any backfill or retirement operation.

The earlier review recorded two concerns to resolve during integration: the
durable worklist used a non-atomic read/modify/write, and the companion prune
script resolved relative worktree paths against the process working directory.
Union merges can also resurrect removed entries; the old design relied on an
idempotent daily prune to clear them again. Evaluate these together with the
chosen packaged maintenance path.

## Context

- `multiply-run-log.md` is the captured 2026-09-03 sweep evidence, including the
  follow-up for `v1/persistent-codex-m-managed-checkout`.
- `multiply-ticket-history.md` preserves the original investigation,
  decisions, prior test reports, and Multiply-specific cleanup inventory.
  Its earlier proposal to land changes in both repositories is superseded by
  this ticket's upstream ownership decision.
- `handoff-manifest.md` records the source commit IDs and attachment hashes.
- Previous test counts in the archived history belong to the old checkouts;
  rerun relevant tests against the integrated Coga change.

This ticket captures and relocates the existing defect. Implementation and
review proceed through its normal code workflow; the handoff itself does not
launch that work or dispose of any recorded checkout.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: autoclose-retire-worklist
worktree: /home/n/Code/claude/coga-autoclose-retire-worklist

## Plan (implement, 2026-09-16)

- The preserved branch `autoclose-retires-durable-home` (fa3880b1, c5cb1548)
  is 905 commits behind `main` and its doc hunks no longer apply (main's
  template/skill now describe the defect and name this ticket). Re-implemented
  from current `main` on a fresh branch; the old branch is left untouched.
- Durable home: `coga/recurring/<template>/retires.md`, template derived from
  `COGA_TASK_SLUG` (`recurring/<name>`), gated on the env blackboard being
  inside this root's `tasks/` (same scoping as `blackboard_from_env`). Entry
  format is byte-compatible with the Multiply seed
  (`- \`slug\` — branch \`b\`, worktree \`w\`, recorded \`YYYY-MM-DD\``).
- Shared module `src/coga/retire_worklist.py`: two real consumers — the
  autoclose recipe (record + prune every recurring run) and `coga retire`
  (discharge its own slug after checkout cleanup). Prune rule: drop an entry
  when its worktree path is not a directory AND its branch is not a local
  branch; relative worktree paths resolve against the git toplevel, never the
  CWD; when `git for-each-ref` cannot be run the branch is unknown and the
  entry is kept (fail closed on debt).
- Write path: read bytes under `git.state_publication_barrier`, parse, prune,
  merge, render; write only when bytes change, atomically, refusing if the
  file moved underneath (fixes the non-atomic read/modify/write review note).
- Union merge: `**/retires.md merge=union` in `coga/.gitattributes` (+ packaged
  twin). A resurrected entry is re-pruned by the next sweep; duplicates
  collapse by slug on read (first `recorded` date survives).
- Per-run report keeps its surfaces: period blackboard (autofix analyst reads
  it) / task blackboard / stdout; the recurring report also names the worklist.
- Adoption for existing installs goes in `docs/operations.md`.

## Implemented (commit 91d31cf5 on `autoclose-retire-worklist`)

- `src/coga/retire_worklist.py` (new, shared infra with two consumers):
  `parse_worklist` / `render_worklist` (byte-compatible with the Multiply
  seed format; duplicates collapse by slug on read, first `recorded` date
  survives), `is_discharged` (worktree dir gone AND branch gone; `branches is
  None` = unknown = keep; relative worktree resolved against `root`),
  `local_branches` (one `git for-each-ref`, `None` on failure),
  `reconcile_worklist` (barrier-held read/prune/merge/render; writes only when
  bytes change; refuses if the file moved underneath; never mints an empty
  file), `worklist_for_period_task` (derives the template from the scoped
  period-task blackboard path `tasks/recurring/<name>/ticket.md`, requires the
  template `ticket.md` to exist), `discharge_slug` (retire's hook).
- `src/coga/autoclose.py`: `_report_retire_followups` reconciles the worklist
  on every recurring period run (pending or not) and prints one
  `[autoclose] retire worklist <path>: N open, ...` line when it wrote or has
  open entries; the per-run report keeps its surfaces (period/task blackboard
  or stdout) and names the worklist under a period task. `RetireWorklistError`
  on the success path → `[autoclose] ...` on stderr, exit 2 (closures stay).
  The old no-pending fast path is preserved when no `COGA_TASK_BLACKBOARD`
  is set (`test_autoclose_sweep` passes a sentinel cfg there).
- `src/coga/commands/retire.py`: `_discharge_worklist_entry` after
  `_cleanup_checkout`; best-effort, echoes `Retire: dropped <slug> from
  <path>.`; a preserved checkout keeps its line.
- `**/retires.md merge=union` in `coga/.gitattributes`, packaged twin, and
  `example/coga/.gitattributes`. `git.union_merge_paths` picks it up, so the
  sync layer lands it by union and `open-pr` counts it as generated state.
- Docs (owner → summary): `coga/autoclose/sweep` skill owns the surfaces and
  the discharge rule; recurring template + `autoclose-merged/sweep` workflow
  (both twins) point at it; `coga/recurring` context gains the sibling
  worklist paragraph under "Last-run state" and corrects the autofix bullet;
  `coga/codebase` lists the module; package-only `coga/cli` gets one
  paragraph each under `coga retire` and `coga autoclose`;
  `docs/operations.md` › "Autoclose's retire worklist" carries the adoption
  procedure (upgrade package; add the gitattributes line; re-copy/edit local
  template + workflow prose; hand-backfill lines; drop any private script).

## Decisions

- Prune is state-derived (on-disk worktree + local branch), applied by the
  daily sweep and by retire, rather than an event-only removal: survives
  branch-sweep deletions, manual `git worktree remove`, and union-merge
  resurrection with a single rule. Cost: a retire refused by its safety
  proofs leaves the line (correct — debt remains).
- A ticket that no longer exists is *not* consulted by the discharge rule:
  the list is about the checkout, and a gone ticket with a live branch is
  still branch-sweep's concern; keeping the line is the loud option.
- Kept the per-run report on the period blackboard (not only the worklist):
  the autofix analyst and run record read it, per `coga/recurring`.
- Backfill for consumers is a documented hand-edit of `retires.md`, not a new
  command; the next sweep validates (fails loud on a malformed line) and
  prunes. The Multiply script's `add`/`prune` are covered by sweep + retire.
- Union merge kept (human's earlier choice); resurrection heals within one
  period because the prune is idempotent.

## Verification

- `PYTHONPATH=$PWD/src /home/n/Code/claude/coga/.venv/bin/python -m pytest -q`
  from the worktree → **2601 passed**. New tests: 30 in
  `tests/test_retire_worklist.py` (28 functions, one parametrized ×3), 8 in
  `test_autoclose.py`, 2 in `test_retire.py`; the three files alone →
  115 passed.
- `python -m coga.cli validate --json` from the worktree: 207 ok; the four
  `unsynthesized-draft-blackboard` errors are pre-existing `v2/` drafts
  untouched here.
- Twins byte-identical (`cmp`) for the skill, template, workflow, recurring
  and codebase contexts; `tests/test_packaging.py` passed in the suite.
- Branch contains `origin/main` tip (`ccedb3fb`, 0 commits behind at handoff).

## Notes for self-QA / review

- The superseded local branch `autoclose-retires-durable-home` (fa3880b1,
  c5cb1548) is untouched; it can be deleted by a human once this merges.
- `discharge_slug` reconciles the whole file it touches, so a `coga retire X`
  may also drop an unrelated *already discharged* entry Y — documented in
  the module and skill; same rule, same file rewrite.
- Not done (out of scope, ticket says re-derive before backfill): no backfill
  of this repo's or Multiply's historical debt. This repo has no
  `retires.md` yet; the next `autoclose-merged` period creates it on the
  first stranded close.
- Adjacent, not fixed: `git._current_branch` still uses `rev-parse
  --abbrev-ref HEAD` (known, recorded in `coga/codebase`).

