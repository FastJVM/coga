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
launch_generation: d43911f1-5f15-472a-b96a-3b9e4597b046
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

- [x] Preserve the incident diagnosis with the two publication commits, source
  commits, HEAD/main reflog evidence, log evidence, and a clean-checkout
  reproduction. Distinguish what history proves from the unavailable original
  index/worktree snapshot; neither dirty files nor a commit on local main is
  required to reproduce the leak.
- [x] With a feature or detached HEAD, sweeping committed changes under the
  configured recurring directory leaves control's existence, content, and
  modes unchanged. Cover additions, edits, deletions (including deletion of
  the entire directory), and renames of templates and siblings. An unrelated
  publishable task/log write in the same sweep still lands; the branch's HEAD,
  index, and working files are preserved.
- [x] Repeated sweeps, including one after control reverts a previously
  published template to its branch-point content, cannot re-adopt those clean
  committed recurring changes. Committed contexts, skills, workflows, shared
  config, and source outside the roots remain excluded on a feature checkout.
- [x] Dirty eligible recurring files still publish from control and feature
  checkouts, including scripts, parent blackboard updates, and machine-written
  siblings. A staged but uncommitted change is still dirty. Routine committed
  task-directory state (including materialized `tasks/recurring/` periods) and
  the log still adopt subject to existing guards. Clean control-checkout hand
  commits of recurring files still publish through the existing recovery path.
- [x] The configured Coga root, including root layout, determines the paths;
  no literal `coga/recurring` prefix or repository-specific twin rule enters
  the implementation. Relocated contexts retain their current exclusion.
- [x] Requiring an excluded, differing committed recurring file through
  `coga run publish-state` exits 1 with the existing merge/review remedy,
  before publishing accompanying dirty task/log state. Requiring one already
  identical to control succeeds. Naming the file does not bypass selection.
- [x] Update `coga/state-publication` and its packaged twin with the new
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

## Dev

branch: coga/v1-03-recurring-publication-boundary

## Implementation — 2026-10-29

Implemented and pushed `coga/v1-03-recurring-publication-boundary` at
`6a73bbf4dbe5ed16593ab4121470db4578ff4ed1`; merge base with current control is
`b2f1ab8745dfd8afc1aedfc10d65f8114691d07b`. Actual implementing agent was
**Codex**, overriding the ticket's configured Claude routing. No PR opened.

Started from clean main at `8cc4d55bf`, created the recorded branch without
switching, and strictly published the linkage on main before switching.
Committed implementation and canonical/package twins together. Fetch/rebase
before final verification reported up to date; the final fetch before push
and checkout return found no intervening main commits. All final receipts
below ran against the committed head above with a clean tree. Pushed the
branch and returned this checkout to clean main before writing this handoff.

### What changed and evidence

- `src/coga/git.py`, `_routine_state_areas()`, now permits only the configured
  task directory and log for clean committed adoption off control. No change
  to `_candidates()`' dirty arm, root membership, provenance, guards or callers.
- The generated real-Git matrix covers feature/detached HEAD; nested, custom
  and root layouts; additions, edits, deletions, entire-directory deletion,
  renames, and modes. It verifies control trees and unchanged branch HEAD,
  index entries, status, working bytes and modes before/after repeated sweeps,
  both clean and alongside unrelated dirty task/log writes. A separate case
  preserves control's revert even with prior publication provenance.
- Retained paths are pinned by committed contexts (including relocation),
  skills, workflows, config and source; task/period/script/log adoption;
  clean control hand commits; staged and unstaged recurring runtime writes.
  Runtime checks use `taskfile.replace_blackboard()` and
  `retire_worklist.reconcile_worklist()`. A dirty template publishes its whole
  committed definition while a clean committed sibling remains excluded.
- Strict CLI tests prove a differing required recurring file refuses before
  accompanying task/log writes, including mode mismatch, without an exit
  sweep. An excluded file already identical to control succeeds.
- Updated the owning user topic and both shipped twins, the checkout summary,
  and three implementation topics. Live-documentation searches found no
  remaining early-adoption contract; no archives were searched or read.
  Task layout, composition and workflow semantics did not change, so no
  seeded-repo fixture update was needed.
- All original incident investigation and evaluation evidence above is
  preserved, including both publication/source commits, reflogs, log evidence,
  the clean-checkout reproductions and the unavailable original index/worktree
  snapshot. The regression suite uses generated content, not those objects.

Pre-fix command (Python 3.12.12):

```sh
PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q tests/test_git.py -k 'keeps_committed_recurring or readopt_committed_recurring' tests/test_publish_state.py -k 'keeps_committed_recurring or readopt_committed_recurring or required_recurring'
```

Result: **38 failed, 8 passed, 264 deselected in 15.69s**, demonstrating clean
committed leakage and strict publication bypass. Mode-only cases already
passed. Two later focused attempts each had 308 passes and 2 setup failures
in the newly extended contexts fixture: configuration requires an existing,
trackable contexts root. Creating its context before config load fixed the
fixture; the final focused run passed all **310** cases. No product change
was made to satisfy those setup failures.

### Verification blockers and next action

The implementation is ready for resumed verification, but acceptance item 8
is **not satisfied**, so this step must block rather than bump:

1. Full fresh-venv Python **3.11.15** suite: **1 failed, 4362 passed,
   10 skipped in 516.70s**. The sole failure is
   `tests/test_clean_install_harness.py::test_release_check_requires_completed_logged_clean_task`
   with `ModuleNotFoundError: No module named 'yaml'`. The unchanged
   `release_env` fixture still uses `python.symlink_to(sys.executable)`, which
   loses the originating venv's packages. A separate run reproduced **1
   failed in 0.31s**. Existing dependency
   `v1/12-fix-release-env-fixture-interpreter-symlink-in-fre` owns the fix;
   the fixture and clean-install script match control byte-for-byte.
2. Repo-wide validation: **98 OK, 16 warnings, 4 errors**. All four are
   `unsynthesized-draft-blackboard` from `## Documentation coordination`
   notes in these unchanged control tickets:
   - `v1/19-install-link-for-claude-code-yields-the-desktop-ap`
   - `v1/26-make-the-readme-install-section-the-only-install-p`
   - `v1/27-link-uninstall-from-the-readme`
   - `v1/31-test-install-on-windows`
   Synthesize their durable intent or place deliberate launch notes under
   `## Production notes` through their owning work, then rerun validation.
   This ticket validates **1 OK, no issues**. The validator also matches
   control; these errors were not silently accepted as a baseline.

Resolve those checks (or explicitly waive the unmet whole-repository checks),
then resume this recorded branch, reconcile with current main and refresh the
receipts before bumping. No independent code review or native Windows run
occurred. The dirty-file hazard remains intentional and documented; the
separate `v1/04-stop-the-contexts-root-sweep-from-publishing-canon` remains
outside this change. Do not rerun incident lifecycle commands.

## PR

```yaml
title: Keep committed recurring files on feature branches
author: codex
author_evidence: This implementation session ran as Codex, overriding the ticket-configured Claude agent;
  see Implementation handoff.
head: 6a73bbf4dbe5ed16593ab4121470db4578ff4ed1
base: b2f1ab8745dfd8afc1aedfc10d65f8114691d07b
depth: deep
rationale: Changes publication eligibility; no code review yet, and required whole-repository checks have
  unrelated failures that must be resolved or explicitly waived before advancing.
implementation: Restricts committed adoption off control to the configured task directory and log. Clean
  committed recurring files wait for merge; dirty whole-file writes, provenance guards and control hand-commit
  recovery retain their existing behavior. Adds real-Git regressions and updates owning documentation
  and twins.
deviations: No implementation deviation. The step cannot advance because the full Python 3.11 suite and
  repository validation are not green; their exact failures and existing owners are recorded below.
limitations: Dirty runtime blackboard writes still publish the whole template, including committed definition
  changes. Native Windows was not run on this Linux host. Independent code review has not run. No PR has
  been opened.
files:
  src/coga/git.py: Remove recurring from the off-control committed-adoption allowlist and its unused import;
    retain shared dirty selection and guards.
  tests/test_git.py: Exercise clean feature/detached sweeps across change kinds and layouts, checkout
    preservation, revert/retry, retained dirty writers, task/log adoption and control recovery.
  tests/test_publish_state.py: Prove required recurring-file refusal is atomic and cannot fall through
    to the CLI sweep; allow files already identical to control.
  docs/contexts/coga/state-publication/SKILL.md: Own the committed recurring boundary, strict refusal
    and remaining whole-file dirty hazard.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/state-publication/SKILL.md: Ship the byte-identical
    user-facing publication contract.
  docs/contexts/coga/checkouts/SKILL.md: Replace the obsolete early-adoption workaround with a link to
    the owning boundary.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/SKILL.md: Ship the byte-identical
    checkout summary.
  docs/contexts/coga-dev/internals/state-publication/SKILL.md: Describe task-directory/log-only committed
    selection off control.
  docs/contexts/coga-dev/internals/state-publication/publish/SKILL.md: Explain the narrowed allowlist
    and independent dirty-path arm shared by all callers.
  docs/contexts/coga-dev/internals/git-refresh/SKILL.md: Retain the incident as historical evidence and
    remove the claim that committed recurring adoption remains current.
review:
  reviewer: none
  kind: none
  status: not-run
  detail: This was the implement step; no independent code review was requested or run. The earlier design
    evaluation is not a code-review receipt.
checks:
- command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q tests/test_git.py tests/test_publish_state.py
  status: passed
  head: 6a73bbf4dbe5ed16593ab4121470db4578ff4ed1
  base: b2f1ab8745dfd8afc1aedfc10d65f8114691d07b
  detail: 'Python 3.12.12: 310 passed in 68.96s.'
- command: PYTHONPATH=/home/n/Code/coga/src /tmp/coga-v1-03-py311/bin/python -m pytest -q
  status: failed
  head: 6a73bbf4dbe5ed16593ab4121470db4578ff4ed1
  base: b2f1ab8745dfd8afc1aedfc10d65f8114691d07b
  detail: 'Python 3.11.15, fresh venv with declared test extras: 1 failed, 4362 passed, 10 skipped in
    516.70s. Only failure: tests/test_clean_install_harness.py::test_release_check_requires_completed_logged_clean_task,
    ModuleNotFoundError: yaml. Existing v1/12-fix-release-env-fixture-interpreter-symlink-in-fre owns
    the unchanged fixture defect.'
- command: PYTHONPATH=/home/n/Code/coga/src /tmp/coga-v1-03-py311/bin/python -m pytest -q tests/test_clean_install_harness.py::test_release_check_requires_completed_logged_clean_task
  status: failed
  head: 6a73bbf4dbe5ed16593ab4121470db4578ff4ed1
  base: b2f1ab8745dfd8afc1aedfc10d65f8114691d07b
  detail: 'Python 3.11.15: 1 failed in 0.31s, independently reproducing the same missing-yaml error.'
- command: PYTHONPATH=/home/n/Code/coga/src /tmp/coga-v1-03-py311/bin/python -m coga.cli validate --json
  status: failed
  head: 6a73bbf4dbe5ed16593ab4121470db4578ff4ed1
  base: b2f1ab8745dfd8afc1aedfc10d65f8114691d07b
  detail: 'Python 3.11.15: exit 1; 98 OK, 16 warnings, 4 unsynthesized-draft-blackboard errors. Affected
    tickets: v1/19-install-link-for-claude-code-yields-the-desktop-ap, v1/26-make-the-readme-install-section-the-only-install-p,
    v1/27-link-uninstall-from-the-readme, v1/31-test-install-on-windows. These files and the validator
    match control.'
- command: PYTHONPATH=/home/n/Code/coga/src /tmp/coga-v1-03-py311/bin/python -m coga.cli validate --task
    v1/03-state-sync-published-unmerged-recurring-templates --json
  status: passed
  head: 6a73bbf4dbe5ed16593ab4121470db4578ff4ed1
  base: b2f1ab8745dfd8afc1aedfc10d65f8114691d07b
  detail: 'Python 3.11.15: 1 OK, no issues.'
- command: git diff --check origin/main...HEAD
  status: passed
  head: 6a73bbf4dbe5ed16593ab4121470db4578ff4ed1
  base: b2f1ab8745dfd8afc1aedfc10d65f8114691d07b
  detail: No whitespace errors in the final branch diff.
- command: 'cmp docs/contexts/coga/state-publication/SKILL.md src/coga/resources/templates/coga/bootstrap/contexts/coga/state-publication/SKILL.md

    cmp docs/contexts/coga/checkouts/SKILL.md src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/SKILL.md'
  status: passed
  head: 6a73bbf4dbe5ed16593ab4121470db4578ff4ed1
  base: b2f1ab8745dfd8afc1aedfc10d65f8114691d07b
  detail: Both edited canonical/package pairs are byte-identical after reconciliation. The full suite
    also passed all packaging tests.
```

---

## Blockers

- [ ] [2026-10-29 22:24] [agent:claude] id=20261029T222441 Implementation is pushed at 6a73bbf4d; resolve required checks or explicitly waive them before advancement. v1/12-fix-release-env-fixture-interpreter-symlink-in-fre must fix the unchanged release_env symlink that loses PyYAML in a fresh Python 3.11 venv (full suite: 1 failed, 4362 passed, 10 skipped). Also synthesize draft coordination notes or place intentional launch notes under Production notes in v1/19-install-link-for-claude-code-yields-the-desktop-ap, v1/26-make-the-readme-install-section-the-only-install-p, v1/27-link-uninstall-from-the-readme, and v1/31-test-install-on-windows; these cause four repository-validation errors. Focused publication tests pass (310); exact evidence is on the blackboard.
