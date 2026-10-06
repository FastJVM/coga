---
title: Ticket ownership lock
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
step: 3 (review-design)
contexts:
- coga/launch
- coga/internals/launch-claims
- coga/internals/claim-recovery
- coga/internals/state-publication
- coga/internals/git-regressions
agent: claude
---

## Description

Design an independent per-ticket ownership lock that prevents concurrent launches of the same ticket across checkouts and machines. User direction: keep an inspectable lock file beside the ticket while a launch works on it, remove the claim when the launch finishes, and include metadata for garbage collection and safe crash/restart recovery. This deliberately revises the current no-task-ownership-lock contract.

Define placement for both directory-form and bare .md tickets without introducing duplicate task discovery. If the lock is shared through Git, acquisition must atomically claim absence on control and confirm publication before spawning; creating a local file alone cannot exclude another clone. Specify owner/session UUID, machine identity, process identity including a start marker, checkout path, and start time. Explain what proves a worker dead, what remains uncertain on another machine, and how restart adopts or replaces a stale claim without admitting two workers. A reused PID or matching owner is insufficient.

Hold ownership across script and agent phases, workflow bumps and chained steps, through final publication and release. Done means launch/session completion, including interrupted or refused teardown, not only terminal ticket status; preserve unpublished work during recovery. Define ambiguous acquire/release publication outcomes, compare-and-set removal of the exact claim, stale-session write rejection, and interaction with existing launch_generation and megalaunch claims. Do not promise protection against arbitrary external side effects or manual Git writes.

Evaluate a daily recurring collector for stale claims; never clear a potentially live worker solely because the claim is old. Immediate restart recovery must not depend on a daily job. Define local-only behavior when Git sync is unavailable.

Orthogonal sibling: launch-locks/checkout-exclusivity-lock protects a physical checkout, not ticket identity. This ticket must stand alone and permit different tickets in separate clones. When both ship, acquire the checkout lock first, then the ticket lock (the sibling already fixes this order); release in reverse order (ticket lock before the checkout lock, whose release follows the outer `cli.main` sweep); specify how a refusal of either unwinds the other. Include concurrency/crash acceptance scenarios and update owning contracts and packaged twins in the eventual implementation PR. The design requires owner approval before code. The design step is done when the design is on the blackboard (per `code/design`), ending with the concurrency/crash acceptance-scenario list, and names the `coga/internals/*` topic that will own the lock contract.

The design spec for this ticket lives in the sibling attachment `design.md` (moved from the blackboard's `## Design` for size on 2026-10-06), as the step instruction above requires; `## Open Questions` on the blackboard lists what the owner decides in `review-design`.

## Context

Owner priority: design and ship ticket ownership locking before checkout exclusivity; checkout collisions are considered uncommon. Keep the two deliverables independent.

The owner clarified "fast git sync" means immediate lock acquisition/release publication, not general state-sync performance work. Publish the claim immediately and confirm acquisition on control before work starts; publish removal immediately when the launch finishes. Do not depend on delayed sweeps. Failed or uncertain acquisition must not start work; failed release must remain visible for reconciliation. Fast publication alone is not mutual exclusion: simultaneous claims still require an atomic remote decision.

Contract being revised: `coga/launch` (`docs/contexts/coga/launch/SKILL.md`, "Status is the signal") currently says there is no task-ownership mutex and that megalaunch's claim and `git.state_lock` are not ownership locks. The implementation PR rewrites that paragraph and the related lines in `coga/internals/launch-claims` and `coga/internals/claim-recovery`.

Code anchors (cite by symbol; line numbers drift):

- `git.publish` with `expect={path: bytes | None}` (`None` = must not exist on control) and `guard=` is the existing atomic compare-and-set against control; the lock's acquire and exact-claim release should build on it rather than invent a new remote primitive.
- `git.ticket_regression_reason` holds the `pending:`/`released:` launch_generation seal rules; `launch._reconcile_released_launch_admission` is the existing released-witness recovery path. Define how the ownership lock composes with both.
- `git.state_lock` is the short-lived, per-checkout, reentrant `flock`; keep it separate and do not lengthen it.
- `git.fetch_control` and `git.sync_task_state` are the fetch and strict-publication helpers.
- `tasks.list_tasks` / `tasks.resolve_task` own discovery (see placement facts below).

Cited, not attached — `coga/tickets` (`docs/contexts/coga/tickets/SKILL.md`, "Where tasks live and how they are named"). Placement facts: `list_tasks` walks `coga/tasks/` at any depth; a directory holding `ticket.md` is a task and is never recursed into; a bare `<slug>.md` is a file-form task; `<slug>.md` and `<slug>/` must not both exist (`DuplicateTaskSlugError`); `README.md` is never a task and `_`-prefixed names are skipped at every level; attachments are never composed, and only the exact sibling `ticket.py` changes dispatch. Moving a task orphans its log history under the old ref.

Cited, not attached — `coga/recurring/scheduling` (`docs/contexts/coga/recurring/scheduling/SKILL.md`), for evaluating the daily collector. Facts: templates live under `coga/recurring/` and materialize one stable task per template under `tasks/recurring/`; a `ticket.py` period runs headless and is the shape for unattended schedulers, while agent periods need TTYs; a scheduled agent run must reach `done` in one launch or the sweep pauses it; repo-inactivity skips templates unless `run_when_inactive: true`; the shipped daily `autoclose-merged` template chains registered `coga run` recipes from its `ticket.py`.

Sweep interaction (main gap from the authoring review): `git.sync_coga_state`, the end-of-command sweep, publishes every dirty path under the tasks directory. A lock file beside the ticket would therefore be pushed by any unrelated `coga` command in any clone, including an unconfirmed, stale, or deleted claim. The design must state whether the sweep, `delete-task`/Retro, and moving a task skip, carry, or refuse lock paths.

Cited, not attached — `coga/internals/agent-spawn` (`docs/contexts/coga/internals/agent-spawn/SKILL.md`): read it for supervisor death with a surviving agent child, which crash recovery must handle (the sibling attaches it for the same case).

Open design questions:

- Is the cost of two extra control commits/pushes per launch, and refusing to start when control is unreachable, acceptable?
- Under megalaunch, does the admission step or the child acquire the ticket lock, and how does that compose with the `pending:` seal?
- Do `coga ticket` authoring and recurring `ticket.py` periods take the lock?
- Does "local-only when Git sync is unavailable" also cover `[git].enabled = false` and remote-less repos?
- Should the daily stale-claim collector be a recurring template with a `ticket.py` (microkernel rule) rather than core code, and is it a separate follow-up ticket?

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Design (step 1, 2026-10-01)

Moved verbatim to the sibling attachment `design.md` on 2026-10-06 (validate `large-blackboard`, coga/blackboard size remedy; ticket `validate-drift-blackboard-hygiene-two-oversized-bl`). It is the spec this ticket's review-design and implement steps work from: read `coga/tasks/launch-locks/ticket-ownership-lock/design.md` in full before reviewing or implementing. Evaluator-review references to `## Design` mean that file.

## Decisions (owner, attended design session 2026-10-01)

- Write guard: refuse **all** non-holder publications of a held ticket (Q2).
- Recurring periods take the lock uniformly; the two extra commits per run
  are accepted (Q1, recurring half).
- Daily collector is a **separate follow-up ticket** (Q5), not in this PR.

## Open Questions

Q2 and Q5 are decided above, as is the recurring half of Q1; the rest remain
for `review-design`.

1. **Cost.** Two extra control commits/pushes per launch (acquire, release),
   plus one fetch, and refusing to start when control is unreachable. Proposal:
   accept. Recurring periods add two commits each per run — accept, or exempt
   recurring because the recurring gate already admits one runner?
2. **Non-holder writes while held.** Proposal refuses every non-holder
   publication of a held ticket (another clone's `mark`/`block`/`unblock`/
   sweep, or a human in a second terminal), not just stale sessions. Stricter
   and simpler; the cost is that a human must wait or `coga unlock` before
   editing a running ticket through Coga. Alternative: only reject writers
   carrying a *different* session.
3. **`coga unlock` placement.** New top-level command (shared lock infra,
   package-private CAS invariant) vs. a `coga run` recipe. Proposal: top-level.
4. **`coga ticket` on an existing ticket**: refuse up front when held
   (proposal) or acquire the lock for the authoring session?
5. **Daily collector.** Proposal: separate follow-up ticket; a recurring
   template whose `ticket.py` calls `coga unlock --collect`, which releases
   only claims from *this* host proven dead with no unpublished state, and
   reports (never clears) every other claim with its age. Immediate recovery
   never depends on it (launch adopts). Worth building at all?
6. **Local-only scope.** Proposal: `[git].enabled = false` and non-Git →
   local `O_EXCL` lock; remote-less → normal local-control CAS; missing
   control branch → refuse rather than degrade. Confirm.

## Evaluator review

Cold review, 2026-10-01. **Not ready for implementation.** The body clearly
identifies the required outcome and explicitly locates the spec on this
blackboard. The frozen workflow matches the packaged
`code/design-then-implement` workflow: this review hands findings to the owner,
not approval to implement. The shared lock module, Git CAS foundation,
separate checkout-lock deliverable, and separate collector follow-up fit the
repo boundaries. The following protocol gaps must be resolved first.

### Must resolve before implementation

1. **P1 — The fork-to-record death proof can admit two workers.** The
   Liveness proof claims Linux's environment scan closes this window, while
   Env witness explicitly leaves the supervisor environment unchanged.
   `src/coga/repl_supervisor.py::run_with_done_marker` forks first and installs
   the supplied environment only in `os.execvpe`. An ordinary, ungated child
   stopped before exec has neither that witness nor a roster entry if the
   supervisor dies before recording it. A recoverer can declare the claim
   dead, adopt, and start a second worker before the first child resumes.
   A local fork probe confirmed the live pre-exec child's `/proc/.../environ`
   lacks the proposed key even though the future exec environment contains it.
   Specify a durable spawning barrier and child-release protocol for **every**
   spawn path (PTY, non-TTY, script), or treat incomplete spawning as uncertain
   on Linux too. Define the state's transitions and test an actual paused
   pre-exec child, not just a fake process table. Scenario 12 currently asserts
   a guarantee the proposed mechanism cannot provide.

2. **P1 — Normal/exceptional release lacks proof that workers stopped.**
   Release only requires published task bytes; it never checks the child
   roster or surviving descendants. In
   `src/coga/repl_supervisor.py::run_with_done_marker`, the PTY-loop `finally`
   restores terminal state and removes the sentinel; `waitpid` is afterwards,
   and arbitrary exceptions do not run `_trigger_term`. Wrapping `_launch`
   in a release context manager therefore does not establish child death on
   `KeyboardInterrupt` or another exception. `launch_script.run_script_phase`
   uses `subprocess.run`, with no process-group/descendant shutdown contract.
   A surviving child can coexist with a newly acquired owner after removal.
   Specify terminate/reap and descendant evidence before release, and retain
   the claim if termination is uncertain. Add interrupt, natural parent exit
   with a surviving descendant, and teardown-failure tests. This is needed
   independently of crash-time adoption and does not promise fencing of
   arbitrary external side effects.

3. **P1 — Recovery is circular and contradicts the retained-state scenarios.**
   Existing claim rule 3 refuses adoption whenever the old checkout has
   unpublished task state, including when invoked from that same checkout;
   Release and scenarios 18/23 nevertheless promise that relaunch there
   adopts, publishes/reconciles, and releases. Moreover,
   `commands/launch.py::_CheckoutBoundary.enter` publishes and calls
   `git.prepare_control_checkout` **before** the proposed acquisition point.
   The new holder guard rejects that publication under the dead session's
   claim; `git._plan_preparation` then refuses unpublished paths. A local
   `released:` witness cannot pass an ordinary sync either
   (`git.ticket_regression_reason`,
   `launch._reconcile_released_launch_admission`). Recovery is unreachable.
   Specify a narrow recovery entry before preparation, its exact CAS and
   preservation rules, and when new work may start. Cover done/canceled and
   deleted tickets with withheld releases: ordinary launch cannot resume all
   of them. Also reconcile the statement that a pending generation retains
   its lock until manual reconciliation with generic Release, which would
   remove it when ticket bytes already equal control. Extend scenarios 18/23
   to real Git checkouts with dirty state and the entry boundary enabled.

4. **P1 — Recurring holds need their own complete outer boundary.** The
   acceptance criterion includes every recurring period, but Proposed shape
   only wraps `_launch` and `megalaunch._launch_until_stop`.
   `src/coga/recurring_runner.py::_launch_due_tasks` and `_launch_created`
   call `_run_delegated_task` directly; its child is a bootstrap target,
   expressly exempt from locking. These paths would take no period lock.
   Ordinary recurring launches also return before the runner calls
   `_stop_if_unfinished_after_launch`; releasing inside `_launch` leaves that
   final pause/publication outside ownership. `_prepare_forced_launch` can
   activate before dispatch. Specify which recurring caller owns the hold
   through activation, delegation, finalization and checkout settlement, and
   how direct `coga launch recurring/...` shares it without double acquisition.
   Add sweep, named, direct, forced, delegated, timeout and failed-finalization
   scenarios. `tests/test_recurring.py::test_delegated_task_launches_target_and_owns_lifecycle`
   confirms that lifecycle ownership is in the runner.

5. **P1 — Local-only replacement/removal has no atomic decision.** `O_EXCL`
   protects first creation; reading exact bytes and then unlinking does not
   protect release or unlock. A releaser can read claim A, a concurrent
   remover can delete A and a launcher create B, then the first releaser can
   unlink B. Two adopters can likewise both read a dead A unless replacement
   is serialized. Define the local compare-and-replace/delete transaction,
   including all acquire/adopt/unlock/release participants; the existing
   short-lived `git.state_lock` is a possible checkout-local primitive without
   turning it into the long ownership hold. Add local-mode concurrent adopter
   and replacement-between-check-and-unlink tests. Scenario 26 alone only
   proves initial creation exclusion.

6. **P2 — Excluding locks from publication does not make stale local files
   harmless to checkout preparation.** Lock paths / scenario 21 promise a
   stale dirty lock cannot block preparation. `git._plan_preparation` examines
   all staged, tracked and untracked paths and rejects bytes that differ from
   pinned control; it does not consult `_candidates`. Filtering the latter
   prevents publication but leaves precisely this obstruction. Specify a
   separate, evidence-preserving stale-lock reconciliation rule, or explicitly
   make this a diagnosed refusal with a recovery procedure and revise scenario
   21. Test dirty tracked and untracked lock files, not just a clean feature
   checkout whose HEAD contains an older lock.

### Optional recommendations and owner decisions

- Tighten the new `publish(content=...)` contract before coding it. Current
  `git._guard` requires `expect=None` to mean absence even if desired bytes
  already match control (`tests/test_git.py::test_expect_none_means_the_path_must_not_exist_on_control`).
  Forced candidates therefore do not give the stated idempotent `False` acquire
  when the claim already exists. Describe explicit reconciliation of that
  case rather than treating a generic `False` as remote confirmation. Also
  preserve the distinction between observed working bytes and desired landed
  bytes in `fast_forward_control`'s staging proof; its remote-less path uses
  `merge --ff-only` when a worktree holds control, not always `update-ref`.
- Reserve or diagnose the lock-path namespace. `tasks.list_tasks` currently
  allows a group/directory task named `foo.lock` alongside `foo.md`; the
  proposed claim for `foo` collides with that directory. Do not silently
  replace a subtree in the Git tree. Add malformed-claim, path-collision and
  orphan-unlock coverage, plus the new env keys to test isolation.
- State rollout assumptions: older launchers and publishers do not enforce
  these locks. Name the writer-upgrade/quiet-window requirement or explicitly
  limit guarantees to participating versions. Include
  `coga/internals/agent-spawn`, recurring ownership topics and `dev/checkouts`
  in the eventual contract changes if the fixes above change their behavior.
- Owner still decides general launch cost/availability, `unlock` command
  placement, existing-ticket authoring, and local-only scope. The all-writer
  guard, recurring participation and separate collector were already decided;
  remove their stale alternatives from Open Questions when accepting the
  revision. No decision was made on the owner's behalf in this review.

### Verification

Read the current source, relevant tests, supplied contracts, discovery and
recurring topics, and the packaged workflow. No implementation, fixture,
ticket-body or frontmatter edits were made. An isolated fork/pipe probe
verified the pre-exec environment gap and reaped its child.

The initial ambient `python -m pytest` attempt could not collect because
`tomlkit` is absent there. The repository venv completed **12 passed** with:

```sh
.venv/bin/python -m pytest -q tests/test_git.py::test_expect_pins_the_exact_control_copy tests/test_git.py::test_expect_none_means_the_path_must_not_exist_on_control tests/test_git.py::test_guard_sees_every_base_the_publish_pushes_on tests/test_git.py::test_pending_claim_on_control_accepts_only_its_own_admission tests/test_git.py::test_a_released_witness_is_never_published tests/test_repl_supervisor.py::test_pty_child_replaces_inherited_environment tests/test_recurring.py::test_delegated_task_launches_target_and_owns_lifecycle
```

These validate existing mechanisms; they are not implementation tests for the
proposed lock. Handoff: owner resolves or explicitly dispositions the six
must-fix findings before advancing to implementation.
