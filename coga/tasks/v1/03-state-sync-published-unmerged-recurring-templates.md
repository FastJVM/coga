---
title: State sync published unmerged recurring templates from a feature branch
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
step: 4 (implement)
contexts:
- coga/sync
- coga/state-publication
- coga-dev/internals/state-publication
- coga-dev/internals/git-refresh
- coga-dev/packaging
- coga-dev/testing
- coga/checkouts
agent: claude
launch_generation: 2592a1ab-df2c-4244-9456-c9cf01cd5a22
---

## Description

On 2026-10-16, sweep commit `0591ae8bd` (11:24 PDT) published six
`coga/recurring/{autoclose-merged,branch-sweep,upstream-coga}/ticket.{md,py}`
files from the unmerged `clone-scoped-recurring` branch. Main's runner did
not yet understand `scope: clone`: autoclose lost its branch pass, upstream
periods stopped completing, and live templates diverged from their packaged
twins. Checkout-return commit `cf40ef440` (12:14 PDT) then published the two
updated compatibility shims from that branch. Restoration PR
[#1032](https://github.com/FastJVM/coga/pull/1032) and the intended clone-scope
feature PR [#1033](https://github.com/FastJVM/coga/pull/1033) have both merged;
this ticket fixes the publication rule that remains on main.

Investigation reproduced the leak from a completely clean feature checkout.
`src/coga/git.py`, `_publish_locked()`, passes `_routine_state_areas()` to
`_candidates()` for feature and detached checkouts. That allowlist includes
the entire recurring directory, so committed template definitions and scripts
are adopted as routine state. The same rule exists in the incident's source
revision. Reflogs place HEAD on the feature branch during both publications;
the evidence and its limits are on the blackboard.

Treat committed recurring files as reviewed knowledge: when clean against
HEAD on a feature or detached checkout, they must wait for the branch to
merge. Keep the existing dirty-file publication contract, task-directory and
log adoption, control-checkout hand-commit recovery, and provenance guards.
The boundary is file-based: it also holds a committed recurring blackboard or
`retires.md` on its branch. Ordinary runtime writes to those files remain
dirty and publish as before. No template parsing or packaged-twin lookup is
needed to decide eligibility.

### Acceptance criteria

- [ ] Preserve the incident diagnosis with the two publication commits, source
  commits, HEAD/main reflog evidence, log evidence, and a clean-checkout
  reproduction. Distinguish what history proves from the unavailable original
  index/worktree snapshot; neither dirty files nor a commit on local main is
  required to reproduce the leak.
- [ ] With a feature or detached HEAD, sweeping committed changes under the
  configured recurring directory leaves control's existence, content, and
  modes unchanged. Cover additions, edits, deletions (including deletion of
  the entire directory), and renames of templates and siblings. An unrelated
  publishable task/log write in the same sweep still lands; the branch's HEAD,
  index, and working files are preserved.
- [ ] Repeated sweeps, including one after control reverts a previously
  published template to its branch-point content, cannot re-adopt those clean
  committed recurring changes. Committed contexts, skills, workflows, shared
  config, and source outside the roots remain excluded on a feature checkout.
- [ ] Dirty eligible recurring files still publish from control and feature
  checkouts, including scripts, parent blackboard updates, and machine-written
  siblings. A staged but uncommitted change is still dirty. Routine committed
  task-directory state (including materialized `tasks/recurring/` periods) and
  the log still adopt subject to existing guards. Clean control-checkout hand
  commits of recurring files still publish through the existing recovery path.
- [ ] The configured Coga root, including root layout, determines the paths;
  no literal `coga/recurring` prefix or repository-specific twin rule enters
  the implementation. Relocated contexts retain their current exclusion.
- [ ] Requiring an excluded, differing committed recurring file through
  `coga run publish-state` exits 1 with the existing merge/review remedy,
  before publishing accompanying dirty task/log state. Requiring one already
  identical to control succeeds. Naming the file does not bypass selection.
- [ ] Update `coga/state-publication` and its packaged twin with the new
  committed-state boundary and remaining dirty-file hazard. Correct the
  affected checkout and implementation topics listed below in the same PR;
  every shipped twin remains byte-identical.
- [ ] The full suite and `coga validate --json` pass after implementation and
  reconciliation. Record exact commands, interpreter, counts, and any actual
  verification gap under the testing context's rules.

### Proposed shape

1. Add real-Git regression cases in `tests/test_git.py` around
   `git.sync_coga_state()`. Pair a committed recurring template/script change
   with an ordinary task/log write and a packaged-copy stand-in outside the
   roots; verify control and the feature checkout separately. Parameterize
   feature versus detached HEAD and the important change/layout cases. Use
   generated fixture content rather than depending on retained incident SHAs
   or live dogfooded templates. Reproduce the current failure before the fix.
2. Narrow `src/coga/git.py`, `_routine_state_areas()`, to `tasks_dir(cfg)`
   plus `log_path(cfg)`, removing `recurring_dir(cfg)` from this committed-only
   allowlist and its now-unused import. Adjust the caller's comments and
   helper documentation. Keep `_candidates()`' dirty-path arm, `_state_areas()`,
   `coga_root_paths()`, `_provenance()`, and `_guard()` semantics unchanged.
   This shared selection point covers ordinary sweeps, launch checkout return,
   and strict publication without caller-specific exceptions.
3. Change `tests/test_git.py`,
   `test_sweep_publishes_a_committed_deletion_of_an_absent_state_directory()`,
   which currently requires the offending feature-branch deletion to publish:
   use a task directory for its existing absent-directory recovery coverage
   and add a recurring-directory case that must stay on the branch. Extend
   the existing committed-knowledge and control-hand-commit tests to pin the
   retained behavior. Add a strict recurring-file case beside
   `tests/test_publish_state.py`,
   `test_publish_state_refusal_does_not_sweep_tickets_without_their_vision()`,
   proving that the required-file refusal cannot fall through to an exit sweep.
4. Make `docs/contexts/coga/state-publication/SKILL.md` the user-facing owner
   of the corrected rule. Update its packaged fallback under
   `src/coga/resources/templates/coga/bootstrap/contexts/`. Fix the summary and
   obsolete early-adoption workaround in `docs/contexts/coga/checkouts/SKILL.md`
   and its twin, linking the owner rather than adding another specification.
   Reconcile the selection descriptions in
   `docs/contexts/coga-dev/internals/state-publication/SKILL.md`, its
   `publish/SKILL.md` leaf, and the historical recurring-template paragraph in
   `docs/contexts/coga-dev/internals/git-refresh/SKILL.md`. Keep the incident
   explanation historical and remove any claim that early adoption remains
   the current contract. Search live documentation for further restatements;
   do not read archives for this task.
5. Run focused Git/strict-publication tests, then the full suite and validation
   with an absolute `PYTHONPATH` pointing to the implementation checkout.
   Commit canonical documentation with its packaged twins before running a
   sweeping command on the feature branch. The fix deliberately retains the
   dirty-file hazard, so it cannot protect its own uncommitted topic edits.

### Out of scope

- Changing which dirty Coga-root files publish, adding twin comparison or
  repository-specific exclusions, or automatically publishing source outside
  the roots. The separate task
  `v1/04-stop-the-contexts-root-sweep-from-publishing-canon` concerns that hazard.
- Field-level merging or separating recurring intent from blackboard state;
  a committed file is held as a whole. Reclassifying attachments inside the
  task directory is also outside this change.
- Changing clone-scope scheduling, template compatibility shims, checkout
  ownership/return, lifecycle transitions, or control hand-commit policy.
- Reverting the now-merged clone-scope feature or replaying the incident's
  lifecycle commands. No new configuration, CLI flag, or recipe is needed.

## Context

- Publication ownership is attached as `coga/state-publication`. Also read
  the cited `coga-dev/internals/state-publication/publish` topic at
  `docs/contexts/coga-dev/internals/state-publication/publish/SKILL.md`,
  especially "publish and its wrappers": strict callers share the same
  selection and require a file to be selected or already on control.
- In `src/coga/git.py`, `sync_coga_state()` supplies `coga_root_paths()` to
  `publish()`, which calls `_publish_locked()` under `state_lock()`.
  `_publish_locked()` chooses unrestricted committed adoption only when
  `symbolic_head()` equals the configured control branch; other checkouts
  receive `_routine_state_areas()`. `_candidates()` adds dirty paths first,
  then allows clean committed differences only inside those areas and when
  control's blob is in `_provenance()` after excluding the HEAD blob.
- `src/coga/cli.py`, `_sweep_coga_state()`, and `src/coga/launch.py`,
  `_CheckoutBoundary.settle()`, both call `git.sync_coga_state()`; the latter
  does so before returning the checkout. Fixing only the CLI hook would leave
  the second incident's path open. `src/coga/publish_state.py`,
  `_publish_state()`, calls `git.publish(..., require_paths=...)` over the
  same roots, so its refusal should follow from shared selection.
- For runtime state distinctions, cite `coga/recurring/templates` at
  `docs/contexts/coga/recurring/templates/SKILL.md`, "The template-to-period
  transform" and "Cross-run state surfaces". `src/coga/retire_worklist.py`,
  `reconcile_worklist()`, writes a recurring sibling through
  `atomic_write_text()`; its ordinary dirty write must remain publishable.
  `coga/recurring/` holds persistent templates, whereas `coga/tasks/recurring/`
  holds the materialized tasks this design keeps in the routine allowlist.
- Existing test seams in `tests/test_git.py` are `_hand_commit()`,
  `test_sweep_leaves_knowledge_committed_on_a_feature_branch_for_its_pr()`,
  `test_sweep_publishes_committed_state_from_a_feature_checkout()`, and
  `test_sweep_publishes_a_hand_committed_skill_from_a_clean_control_checkout()`.
  They use `tests/conftest.py`'s `git_repo` fixture with a local bare remote.
- Incident content remains addressable by `5abc520d5`, `dad626011`, and the
  PR links above. The old branch ref is no longer present in this checkout;
  use commit objects, not an assumption that `origin/clone-scoped-recurring`
  still exists. Scope support has since merged, but the allowlist defect is
  still present at investigation revision `97fabd526`.

Previous ref: `state-sync-published-unmerged-recurring-templates` (renamed 2026-10-27); earlier audit lines retain that ref.

<!-- coga:blackboard -->

2026-10-16: it happened again. `cf40ef440` ("Sync coga state before checkout
return", the launch checkout-return sweep) published the branch's later
`branch-sweep/ticket.py` and `upstream-coga/ticket.py` (from `dad626011`, which
was already committed on `clone-scoped-recurring`). That points at the
checkout-return sweep publishing committed feature-branch files, not only
dirty ones. Reverted again in #1032; the real change is PR #1033.

## Design investigation — 2026-10-26

Started on clean `main`; fetched and fast-forwarded from `475444ce6` to
`97fabd526`, then to `92bf46129` before editing. This task is still at design,
with no recorded implementation branch or PR. GitHub confirms #1032 merged
at 2026-10-16 20:04:48Z (`bf4f7f422`) and #1033 at 22:40:48Z (`1c2b47d35`).
Those resolve the restoration/feature work, not this selection defect.

Evidence from this checkout's surviving reflogs (times below are PDT):

- HEAD switched from main to `clone-scoped-recurring` at 10:55:34, rebased to
  `5abc520d5` at 11:16:05, and committed source-map follow-up `c0b9271bc` at
  11:16:30. It remained on that feature tip at the 11:24:29 publication;
  main's separate reflog advanced to `0591ae8bd` at 11:24:30.
- Compatibility commit `dad626011` was written at 12:07:14 and rebased to
  `625a19be3` at 12:07:52. Main advanced to `cf40ef440` at 12:14:47; only
  at 12:14:48 did HEAD switch from the feature branch to main.
- All six recurring blobs in `0591ae8bd` equal `5abc520d5` and the actual
  11:24 HEAD `c0b9271bc`. Both script blobs in `cf40ef440` equal `dad626011`
  and the actual pre-return HEAD `625a19be3`. For every affected file, the
  publication parent's blob equals the feature/control merge-base blob
  (`c8db8ab52` for the first event, `4c2f2f887` for the second). Thus the
  committed-candidate provenance condition accepts every leaked file.
- `coga/log.md` records the feature's implementation launch at 10:49,
  advancement to peer-review at 12:14, and the implementation session's
  outcome explicitly anticipating publication of its compatibility shims
  through the same adoption path. Successful sweeps do not leave a separate
  path-by-path log receipt; their Git commits carry the file evidence.
- `src/coga/git.py` at `c0b9271bc` has the same recurring-directory exception
  in `_routine_state_areas()` and the same `_publish_locked()` selection
  relationship as current main. No control-hand-commit explanation is needed.
  Reflogs do not preserve the original index/worktree dirt, so the exact
  dirty/committed candidate arm used by that process cannot be recovered.

Reproduction on `97fabd526`, using Python 3.12.12 with
`PYTHONPATH=/home/n/Code/coga/src .venv/bin/python` and a disposable local
working repository plus bare remote: seed control with `0591ae8bd^`'s six
templates and matching packaged-copy stand-ins; commit `5abc520d5`'s six
template versions, changed packaged copies, and a context on a feature
branch; assert porcelain status is empty; call `git.sync_coga_state(cfg)`.
Result: all six recurring files selected and published, all six packaged
copies and the committed context stayed at control's old versions, feature
HEAD stayed unchanged, and status remained clean. No dirty file or hand commit
on local control was necessary. The temporary fixture was removed afterwards.

The existing tests also confirm the current boundary. Command:

```sh
PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q tests/test_git.py::test_sweep_leaves_knowledge_committed_on_a_feature_branch_for_its_pr tests/test_git.py::test_sweep_publishes_a_committed_deletion_of_an_absent_state_directory tests/test_git.py::test_sweep_publishes_committed_state_from_a_feature_checkout tests/test_git.py::test_sweep_publishes_a_hand_committed_skill_from_a_clean_control_checkout
```

Result: **4 passed in 0.97s**, Python 3.12.12. The recurring deletion test
currently asserts the behavior this ticket will change; a green run is
diagnostic evidence, not evidence that the bug is fixed. Full-suite
verification belongs to implementation; this step changes only this ticket.

Design checks: `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m coga.cli
validate --task state-sync-published-unmerged-recurring-templates --json`
returned **1 OK, no issues**. A direct `compose_prompt_report()` check verified
that acceptance criteria, proposed shape, out-of-scope items, investigation,
and open questions reach the next prompt; frontmatter remained byte-identical
and there is exactly one blackboard fence. `git diff --check` passed. Ready
for independent design evaluation; no implementation files, branch, or PR
were created by this step.

Design choice for review: remove the whole recurring directory from committed
adoption. This avoids inferring author intent from extensions, blackboard
content, or installed twins. Dirty runtime writes remain supported; someone
who hand-commits recurring runtime state on a feature branch must merge it or
deliberately reconcile it on control. The separate dirty-context/twin ticket
is related, not a dependency or a solution supplied by this design.

Handoff reconciliation: fetched and fast-forwarded to `ff78e6886`, preserving
and verifying the ticket backup before the move. Intervening changes clarify
the sweep command allowlist and checkout race limitations; the candidate
implementation and this ticket were unchanged, so the design still applies.

## Open Questions

None requiring unavailable input to finish design. The proposed boundary and
its hand-committed-runtime-state tradeoff await the workflow's independent
evaluation and owner design review; this step does not approve its own spec.

## Evaluator review

2026-10-26: **Ready for owner design review; no must-fix findings.** The
Description and Context are sufficient to implement this as one focused PR
once the owner accepts the boundary. Acceptance criteria, Proposed shape,
and Out of scope are correctly nested under Description. The frozen
`code/design-then-implement` workflow and attached contexts fit the work;
the next step remains the owner's approval gate.

### Evidence and assessment

- `src/coga/git.py`, `_publish_locked()` and `_routine_state_areas()`, match
  the diagnosis. The helper has one caller and `recurring_dir` has no other
  use in this module. Removing that directory changes only committed
  adoption off control: `_candidates()` first selects dirty paths
  independently, while control still receives `adopt_only=None`. Task
  attachments, materialized periods, and the log retain their current
  treatment and guards. `tasks_dir()` and `log_path()` derive from the
  configured root, including root layout.
- The fix reaches `cli._sweep_coga_state()`,
  `launch._CheckoutBoundary.settle()`, and `publish_state._publish_state()`
  through the same publish primitive. `_publish_locked()` checks excluded
  required files, including their modes, before building or pushing a
  publication commit. `cli._should_sweep_coga_state()` separately excludes
  `run publish-state`, so its refusal cannot fall through to an unguarded
  sweep. No new CLI surface or architectural exception is needed.
- The named test seams and local-bare-remote fixture exist. In particular,
  `test_sweep_publishes_a_committed_deletion_of_an_absent_state_directory()`
  asserts the offending recurring deletion today; moving its positive case
  to tasks while adding the recurring negative case preserves its original
  discovery coverage. The proposed cases distinguish clean committed state,
  staged/uncommitted writes, provenance, strict handoff, and retained control
  recovery rather than relying on the incident objects as fixtures.
- Independently checked both publication commits: all six recurring blobs
  in `0591ae8bd` equal `5abc520d5` and `c0b9271bc`; both in `cf40ef440` equal
  `dad626011` and `625a19be3`. Their parent blobs equal the corresponding
  branch-point blobs at `c8db8ab52` and `4c2f2f887`. Surviving HEAD/main
  reflogs and `cf40ef440:coga/log.md` support the recorded sequence, and
  `c0b9271bc:src/coga/git.py` contains the same allowlist. GitHub confirms
  #1032 and #1033 are merged. None of this reconstructs the original index
  or working-tree dirt; the design correctly distinguishes that limit.
- The documentation plan names the current restatements and their owning
  user topic. The checkout warning and publish leaf need the listed edits;
  the incident paragraph in git-refresh should become historical. The
  canonical/package mapping matches the packaging contract. No archive was
  read.

### Optional recommendation

Make the retained dirty-file hazard concrete in the owning topic: committing
a template definition does not protect that definition if a later runtime
blackboard write makes the same `ticket.md` dirty. `_candidates()` then
publishes the whole file, including its committed definition changes. This
is consistent with the explicitly retained file-level contract, not a reason
to expand scope. A mixed regression case with a dirty template and a clean
committed sibling would make this distinction especially clear.

### Verification and reconciliation

Reviewed unmodified source at `2d3fa0847`, using Python **3.12.12**:

```sh
PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q tests/test_git.py tests/test_publish_state.py
```

Result: **253 passed in 50.14s**. These are baseline checks, not evidence of
an implemented fix. A separate inline probe using `tests/conftest.py`'s
`init_git_repo()` and generated content independently reproduced the defect
in **2/2** clean checkouts (feature and detached): template, script, and
sibling committed changes all published; a committed context and packaged
stand-in stayed excluded; HEAD, index entries, and working bytes stayed
unchanged. Reverting the template on control to its branch-point bytes led
the next sweep to re-adopt it in both cases. The disposable repositories
were removed.

Fetched and fast-forwarded clean main to `9c844c29c` before writing this
review. Intervening changes are documentation and template comments; this
ticket, the selection code, and the exercised tests are unchanged. No
implementation branch, code change, PR, or ticket-body edit was produced.
The full suite, native Windows, and Python 3.11 were not run in this design
evaluation; implementation retains the specified verification obligations.

Review handoff checks:

```sh
PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m coga.cli validate --task state-sync-published-unmerged-recurring-templates --json
git diff --check
```

Validation returned **1 OK, no issues**; the diff check passed. A byte
comparison with HEAD confirmed that frontmatter, ticket body, and all prior
blackboard content were preserved, with exactly one evaluator review and one
blackboard fence. Only this ticket's blackboard changed.
