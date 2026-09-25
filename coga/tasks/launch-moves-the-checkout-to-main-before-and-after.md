---
title: Launch moves the checkout to main before and after a ticket session
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
step: 2 (evaluate-design)
agent: claude
---

## Description

Ticket launches should bring the invoking checkout to a clean, current control
branch before work starts and after each supervised session ends. Bootstrap and
chat targets retain their current branch behavior. Today a session ending on a
feature branch leaves the next ticket reading and composing from that branch;
agent-operated start/end instructions cover only some code steps.

Here `main` and `origin` mean configured `[git].control_branch` and
`[git].remote`. The owner approved publishing supervised code-step handoffs and
running `bump` from the feature branch, then letting launch return to main.
This replaces the rule requiring those handoffs to be written on main first.

### Acceptance criteria

- [ ] Ordinary ticket execution normalizes the invoking checkout before
  authoritative ticket reads, script discovery/execution, activation, skill-view
  generation, or prompt composition. Initial target resolution and the minimal
  read needed to recognize a recorded assist are classification only. After
  normalization, reload config and resolve the same canonical task identity;
  never silently select a different prefix match if the original disappeared.
- [ ] Run the same boundary before each chained step, including script steps,
  and after each started session/phase before deciding whether to chain. All
  subsequent routing, secrets, script paths, and prompts use refreshed files.
  A ticket removed on control ends the chain without resurrecting it.
- [ ] With Git enabled and a configured remote, fetch the configured control
  ref and pin its commit. Require local control to exist and be equal to or an
  ancestor of that commit. Reject ahead/diverged control, detached HEAD,
  merge/rebase/conflict state, control held in another worktree, and any unsafe
  dirty path before changing HEAD, the index, working files, or local branches.
  Fetch may update remote-tracking metadata even when admission refuses.
- [ ] Examine tracked, staged, and untracked changes throughout the checkout.
  Only state under the configured tasks directory, recurring directory, and
  log file may be cleaned, and only when its working content and existence
  already match the pinned remote tree. Preserve staged-only content: an index
  version distinct from both HEAD and the proven published version refuses.
  Account for deletion and both sides of renames; reject ambiguous types,
  symlinks/submodules, or mode changes rather than treating equal bytes as
  sufficient. Ignored files are not cleanup candidates and never deleted.
- [ ] Validate the complete cleanup set and switch/fast-forward prerequisites
  before cleaning any path. Recheck the observed branch, index, and candidate
  contents immediately before mutations; changed evidence refuses. Restore
  only proven published tracked state to HEAD and remove only individually
  proven published untracked files, then switch to control and fast-forward
  to the pinned commit. Verify a clean tree and HEAD at that commit. Never
  stash, reset hard, force-switch, delete branches, or push feature code.
- [ ] Predictable safety refusals leave checkout contents and local refs
  unchanged, name the blocking paths/branch and remedy, and start no work.
  Use exit 75 for this retryable entry refusal so the outer CLI sweep does
  not publish the rejected dirt. Other existing preflight exits remain intact.
  Unexpected Git/I/O failures after mutation begins report exactly where the
  routine stopped; do not promise filesystem transactionality or force a
  rollback over concurrent edits.
- [ ] After success, crash, timeout, handled interruption, script failure,
  terminal transition, or owner handoff, attempt return in the invoking
  checkout. A cleanup failure is prominent on stderr, preserves remaining
  work and the original session result, and stops chaining. It never rewinds a
  completed step or marks it failed. Suppress the outer generic sweep after
  such a safety failure without changing a successful child's exit to failure.
  Uncatchable termination (SIGKILL/power loss) is recovered by the next entry.
- [ ] Bootstrap targets, including chat and delegated bootstrap agent sessions,
  and `--prompt-report` do not acquire branch-switching or cleanup behavior.
  Preserve their existing behavior; fixing prompt-report's existing sweep is
  outside scope. Preserve the verified recorded human-assist branch path and
  its publication rules. Never follow a ticket's `worktree:` into a sandbox
  clone to normalize it; a launch invoked in a positively identified recorded
  sandbox clone is exempt too. Do not exempt all `/tmp` paths indiscriminately.
- [ ] Preserve recurring owner, lease/generation, local-only, and stale-control
  admission gates. Direct recurring entry continues to require control before
  admission; this ticket does not replace recurring's routing with an automatic
  switch. Admitted nondelegated periods receive per-session return and chained
  step preparation in the checkout the runner selected. No sibling or temporary
  runner checkout is traversed or cleaned by this routine.
- [ ] Preserve Git-disabled, non-Git, and remote-less launch compatibility by
  skipping the new normalization there; do not claim remote freshness. An
  expected remote/control ref disappearing during a run is an error, not a
  newly inferred local-only exemption. Nondefault remote/control names and
  configured state layouts work.
- [ ] Supervised code steps confirm the entry branch, commit/test/push their
  code, write handoff state, publish it through the existing lifecycle command,
  and bump last without manually returning. Coga state never enters a feature
  commit. Failed publication leaves dirty work and makes automatic return
  refuse. Preserve the manual/API session return procedure and the recorded
  assist and sandbox-clone exceptions explicitly.
- [ ] Update the owning topics and all affected step-skill restatements and
  packaged twins in the implementation PR. Meaningful real-Git tests prove
  the safety and ordering cases below, alongside existing launch regressions.

### Proposed shape

1. Add a focused checkout-preparation operation alongside shared Git
   infrastructure in `src/coga/git.py`, invoked by launch entry and teardown.
   Return a structured outcome distinguishing prepared, exempt, and refused,
   with actionable reasons. Keep classification and launch policy in
   `src/coga/commands/launch.py`; do not change `git.refresh` globally into a
   branch-switching primitive. This belongs to the co-versioned launch
   machinery: prepare, re-read, compose, and spawn must share the same target
   and checkout witness, which an edge pre-launch script cannot preserve.
2. Restructure `commands/launch.py` `_launch` around an outer preparation and
   cleanup boundary. Classify bootstrap/report/recurring/recorded-assist
   exceptions before mutation. Keep initial resolution pinned by canonical
   identity; after switching discard branch-derived routing data and reload
   config. If reloaded config changes the Git destination or state layout,
   refuse and request a retry rather than cleaning with mixed configurations.
   Do not put this policy in `spawn_agent_session`: authoring and megalaunch
   also call that lower-level spawn seam with different admission contracts.
3. Surround each actual session with cleanup after existing usage publication
   and blocked-resume restoration, then reload before chain eligibility and
   the next preflight. Keep an outer finally for early exits after preparation
   has begun, and avoid a second mutation attempt following a safety refusal.
   Review `src/coga/launch_script.py` `run_script_chain`, which loops internally:
   an outer agent-loop hook alone does not cover each deterministic step.
   Add a narrow preparation boundary or return control to the supervisor
   between script steps without changing their routing or exit semantics.
4. Reuse the existing entry exit-75 sweep suppression. For warn-only teardown
   refusal, add a scoped invocation-level sweep suppression mechanism consumed
   by `src/coga/cli.py` `main` / `_sweep_coga_state`, also safe for in-process
   recurring callers. Do not use process-global sticky state or change child
   exit classification. Normal successful lifecycle publication still happens;
   cleanup must never publish dirt merely to make it safe to discard.
5. `docs/contexts/dev/checkouts/SKILL.md` owns start/work/end policy, including
   the newly approved supervised feature-branch handoff and manual-session
   fallback. `docs/contexts/coga/launch/SKILL.md` owns placement in dispatch,
   chaining, exclusions, and exits, linking to the checkout policy.
   Update `coga/internals/agent-spawn` and `coga/internals/git-refresh` for
   changed caller relationships without duplicating the procedure. Update
   `coga/skills/code/{implement,self-qa,open-pr,address-pr-comments}/SKILL.md`
   to link to the owner and remove conflicting instructions and acceptance
   items. Find other restatements before finishing. Keep canonical/packaged
   twins byte-identical per `tests/test_packaging.py`.
6. Extend real-Git tests in `tests/test_git.py`, `tests/test_launch.py`,
   `tests/test_launch_script.py`, and `tests/test_cli.py`. Cover clean feature
   to control; behind/ahead/diverged control; published tracked/untracked/
   deleted state; mixed safe/unsafe paths with no partial cleanup; staged-only
   content; custom layout; active Git operation; control held elsewhere;
   changing evidence; ignored-file collision; fresh prompt/config/script
   selection; exact target disappearance; two chained steps; publication miss;
   cleanup after nonzero/timeout; sweep suppression with preserved exits;
   report/bootstrap/assist/sandbox exclusions; recurring lease/owner behavior;
   and local-only compatibility. Update the seeded fixture only if needed to
   keep its launch smoke representative. Run focused tests, then the full
   suite (including packaging) and task-scoped validation; record exact commands
   and counts in the implementation handoff.

### Out of scope

No new command, config switch, recipe, worktree allocator, branch deletion,
rebase, automatic publication of rejected state, or change to PR lifecycle.
Do not redesign recurring admission, megalaunch's independent claim/spawn
transaction, general Git refresh/publication, or bootstrap/chat checkout
policy. This design step changes only the ticket; code and shipped contracts
change during implementation.

## Context

Requested in a `bootstrap/orient` chat on 2026-09-25 after a session started
on leftover `daily-autoclose-branches`. #896 (`stop-using-worktrees`) added the
agent-operated procedure that this ticket moves into launch.

Cited rather than attached: read `dev/checkouts` at
`docs/contexts/dev/checkouts/SKILL.md` (Start, work, end; Publish pre-branch
ticket edits; sandbox fallback), `coga/launch` at
`docs/contexts/coga/launch/SKILL.md` (preflight and chain), and
`coga/internals/git-refresh` at
`docs/contexts/coga/internals/git-refresh/SKILL.md` (refresh and fast-forward).
Read `coga/testing` and `coga/packaging` before verifying the implementation.
These are existing contracts to update, not evidence that this proposal is
already implemented.

- `src/coga/commands/launch.py` `_launch` resolves targets, reads frozen
  delegation, aligns recorded assists, discovers scripts, and later runs an
  agent loop; preparation must precede its authoritative branch-dependent
  reads. `_recorded_single_checkout_assist_branch` checks recorded branch,
  worktree, and PR against the invoking checkout; `_align_recorded_assist_checkout`
  and `_verify_recorded_assist_pr_head` protect that exceptional route.
- `src/coga/commands/launch.py` `_refresh_launch_checkout` delegates to
  `src/coga/git.py` `refresh`. That function fetches but returns success
  without moving feature or detached checkouts; it is not proof of readiness.
  `fast_forward_control` may update a different branch holder, so do not reuse
  it blindly for an operation confined to the invoking checkout.
- `src/coga/commands/launch.py` `launch_recurring_period` calls
  `_refresh_recurring_period_before_launch` before `_launch`; direct period
  admission inside `_launch` calls `src/coga/recurring_runner.py`
  `_refuse_non_control_branch` and `_sync_control_checkout_ahead`. Preserve
  authorization and exact period leases across any new preparation boundary.
- `src/coga/git.py` `sync_task_state` publishes ticket/log state through
  `publish` without committing it on the feature branch; its default failure
  is nonfatal. `src/coga/commands/bump.py` `bump` calls the lifecycle transition
  before `emit_done_marker`. Publication failure therefore cannot be inferred
  from a successful completed-session result.
- `src/coga/cli.py` `main` normally invokes `_sweep_coga_state` after success
  and failures, except `git.RETRY_WITHOUT_SWEEP_EXIT_CODE`. Tests must invoke
  the actual CLI boundary as well as calling launch helpers.

<!-- coga:blackboard -->

## Design findings

Investigated launch, script chaining, Git publication/refresh, recurring
admission, CLI sweep, and code-step instructions. No code, branch, or PR
created in this step. Existing `coga/log.md` dirt was present before edits
and was not edited manually.

Owner decision (2026-09-25): supervised code steps may publish handoff state
and bump from the feature branch; launch performs the return to main.
This is essential to remove the circular requirement that the agent return
before the supervisor can take over. Manual/API and recorded-assist paths
remain explicitly different.

Conservative compatibility choices in the proposed spec: recurring keeps its
existing entry admission; reports and bootstrap sessions do not normalize;
Git-disabled/non-Git/remote-less use remains supported. New entry safety
refusals use 75 to prevent the generic sweep from publishing rejected dirt.
Warn-only teardown refusal requires separate sweep suppression so successful
work remains successful without silently publishing preserved dirt.

Verification: `coga validate --task launch-moves-the-checkout-to-main-before-and-after --json` reported `ok_count: 1`, no issues; `git diff --check` passed. Validation emitted the existing installed/source version-skew warning. No implementation tests run for this ticket-only design.

## Open Questions

None awaiting owner input for this draft. The evaluator should specifically
check exception classification, script-step boundary coverage, and sweep
suppression across in-process recurring calls.
