---
name: coga/launch-internals
description: The publication invariants behind coga launch, megalaunch, the recurring runner, and the requires-pr gate — the human-step assist's checkout alignment, megalaunch's claim compare-and-swap on control, recurring admission generations, and what open-pr must guarantee. Attach only to tickets that change launch.py, megalaunch.py, the recurring runner, open-pr, or the step gates.
---

# Coga launch internals

These are the concurrency and publication guarantees behind `coga launch`,
`coga megalaunch`, the recurring runner, and the `requires: pr` step gate. They
are what a change to `commands/launch.py`, `megalaunch.py`, the recurring scan,
`step_gate.py`, or `open_pr.py` must not break. Every publication below is one
`git.publish` (`coga/sync`, *Git — durable task-state sync*): control is the
only durable home, Coga never commits on a local branch, and the provenance
check is the compare-and-swap every writer shares.

**Not attached by default, on purpose.** `coga/architecture` carries the model
an agent needs to *operate* — what runs when, what advances a step, what a
handoff means. Everything here is what the implementation must *guarantee*
under concurrent writers. Add `coga/launch-internals` to a ticket's
`contexts:` list when the work touches those paths.

## The human-step assist

`coga launch <slug> --agent <type>` on a locally human-owned ticket is the
assist path. `coga/architecture` describes when it is entered; this is what
it proves before the session and what it never does.

**Alignment before composition.** When launch runs from the exact recorded
`worktree:` on the recorded `branch:` with a recorded `pr:` (primary checkouts,
linked worktrees, and independent fallback clones alike), it first requires
the PR to be open and proves its head repository, branch, and OID match the
configured remote's push URL — a same-named base-repository branch cannot
stand in for a fork PR head, and the recorded branch must not share the
control branch's name. A merely-behind checkout is fast-forwarded to the
verified PR head before the final config, ticket, skill-view, secrets,
expected-step, and prompt reads, for every resumable status; launch then
reloads that state from the aligned tree while preserving the task slug
originally resolved from any user-supplied prefix. Alignment refuses an ahead
or diverged tip and any checkout dirt other than Coga's own live state (task,
log, recurring paths). A different, missing, or mismatched checkout gets
ordinary launch handling with no alignment.

**No publication to the PR branch.** The assist's lifecycle writes — the
activation, the `in_progress` start, a `ticket.py` phase's result, in-session
`bump`/`mark`/`block`/`unblock`, the usage record at teardown — all publish to
the control branch only, exactly as every other checkout's do. The single
checkout keeps that live state dirty by design; `coga open-pr` excludes it
from its cleanliness gate. The child inherits `COGA_ASSIST_AGENT`,
`COGA_ASSIST_BRANCH`, and `COGA_ASSIST_PR` so its lifecycle commands attribute
audit lines to the assisting agent rather than the human ticket owner; the
override expires for routing once `ticket.py` advances the workflow to an
agent step, while the attribution continues through that chain.
Deterministic completion uses the system attribution contract in
`coga/architecture`, including inside an assist. Its marker is independent of
the assist capability and cannot replace the PR-head proof here.

**Activation order.** On the agent path, draft, paused, and blocked
activation and `in_progress` publication stay deferred through prompt
composition, prompt-file and argv construction, and the pre-session audit. A
`ticket.py` phase inverts that on purpose: it resolves declared secrets
through `build_launch_env`, preflights live notification configuration and
push auth, activates and starts the ticket, and only then runs the script —
a deterministic phase genuinely is work starting; CLI lookup, skill refresh,
prompt composition, and the remaining agent preflights stay deferred until
`ticket.py` actually leaves agent work open. Both paths share
`_auto_activate` and `_start_session`.

**Blocked resumes.** A resumed blocked launch is allowed to become
`in_progress` so the session can resolve the ask. Whatever ends the session
without a resolution — a script failure, a pause or close, a handoff, an agent
exit, an interrupt — `_reblock_unresolved_resume` returns the still-open ask to
`blocked` (restoring the original step when a transition cleared it) and
publishes that, so the ask stays visible to `status --blocked`, `unblock
--all`, and blocker reminders.

## Megalaunch claim publication

Megalaunch binds its preflight to exact source ticket bytes before either a
deferred activation or an `in_progress` claim writes locally. A picker launch
parses status, routing, and open blocker asks from that captured revision and
reclassifies it before activation; a blocker resolved in the read/capture
window therefore remains `blocked` and is reported as ask-less instead of
starting. An unattended sweep likewise treats its outer queue scan only as a
hint: the exact preflight reread rechecks owner, status, blockers, and current
step from the same captured bytes, so a peer edit between classification and
launch cannot cross a stale gate. That gate-only reclassification is not a
launch attempt and does not consume `--max-tasks`. A ticket removed during the
capture is absent, so that pick fails without aborting later queue entries.

With Git sync enabled, every lifecycle write is `sync_task_state(strict=True)`:
the publish's provenance check is the compare-and-swap, so two checkouts
preflighted from one control revision cannot both start — the second push is
non-fast-forward, the rebuilt publish finds control's ticket carrying a
`pending:<uuid>` it did not derive from, and is refused. A session never
reaches exec until its unique `launch_generation` claim is durably published
as `pending:<uuid>`. On `StateRegressionError` or `GitError` (definitely not
on control) megalaunch restores the pre-write ticket bytes and retracts its
own audit lines; on `UncertainPublishError` (the push reported failure and
control could not be re-read) it keeps the pending local state as the legible
evidence for reconciliation and reports.

The shared publisher treats the pending control revision as sealed: no ticket
edit, lifecycle transition, authoring write, or deletion can replace it. The
sole exception is the identical ticket with the prefix stripped — megalaunch's
post-gate admission, published with `expect` pinned to the pending copy while
the supervisor still holds `state_lock` (reentrant within the thread).
Before the audit append and again after it, `_revalidate_launch_claim_before_spawn`
rereads the local bytes and control's copy after a fresh `fetch_control`;
any difference refuses the held child. If the admission publish fails after
release, the local `released:<uuid>` witness is retained; an ordinary
`coga launch` reconciles it by fetching control, accepting only the matching
pending or admitted revision, rereading the local ticket against the exact
released bytes validated before the fetch — a manual edit made during that
network wait refuses recovery before admission or publication and is
preserved, since `state_lock` serializes Coga writers, not ordinary editors —
then publishing the plain UUID with `expect`, and restoring the witness on
any failure. The sweep never publishes a released witness on its own. Another megalaunch never reclaims any claim form.

## Recurring admission generations

`coga/architecture` describes the recurring primitive and its lifecycle; this
is the admission machinery that keeps a stale or replaced period task from
starting, completing, or parking work at a stable path.

A sweep or named recurring run performs full recurring admission at its outer
boundary (`refresh` of a checked-out control branch; an `--all` child refuses
with `STALE_CONTROL_EXIT_CODE` when it cannot be brought level), freezes each
period's exact ticket plus its creator-owned `period_generation` token, then
launches through an internal typed seam. Every lease comparison goes through
`same_period_lease`: generation and the full ticket must both match, but a
CRLF-versus-LF difference is not a change. Immediately before each ordinary
child, that seam runs `refresh` again, resolves only the exact ref, and
rechecks branch/owner plus the frozen generation; a task removed, paused,
finished, or replaced while an earlier child ran is skipped, and an
unverified remote-backed refresh (including a remote that disappeared after
admission) refuses rather than starting stale work.

The recurring create is one `publish` of the period task, the template's run
cursors, and the log, with `expect` pinned to control's exact ledger and
template copies read at the same fetch: a peer that serviced the period
between that read and the push makes the publish refuse, and the create
re-reads control — adopting the peer's period and publishing only its own log
line when the period is already handled — instead of landing a duplicate.

For a frozen delegation, the runner preflights the period task's push access
and verifies its exact ticket bytes plus generation against freshly fetched
control at start, final spawn, completion, and timeout
(`_verify_period_on_control`); completion also verifies the exact parent
recurring ticket named by the period's state snapshot, and publishes it with
the `done` transition so `done` cannot land without the child's cross-run
cursor update. Every lifecycle publication is strict: a refused or failed one
restores the leased bytes and retracts the audit lines; an uncertain one
retains the local write and refuses for reconciliation. A sweep continues
after a delegated timeout only when its guarded pause publishes. The live
completion notification waits for durable publication. Direct launch may
activate a paused/draft delegated period inline; scheduled and named scans
keep paused periods parked.

## The `requires: pr` gate's publication path

`coga/architecture` describes the gate itself — a data check on the
blackboard, run before `coga bump` advances off the step. `coga open-pr` proves
live-ticket ownership with `COGA_EXPECTED_TASK`, which the outer step
supervisor pins alongside `COGA_EXPECTED_STEP` to the exact task and frozen
step used for prompt composition; nested task re-derivation never reassigns
either witness, so they keep naming the outer session, separate a real session
from an independent fallback clone, and make `coga bump` refuse a stale
supervised session after another worker advanced the ticket.

The recipe pushes the recorded feature branch by name, opens or readies the
PR, and writes `pr:` under `## Dev`, publishing that record to control
(reported, never fatal — the PR is already open). In the single-checkout
layout it first publishes the pending launch-log append, then excludes Coga's
live task, log, and recurring state from its cleanliness gate; any other dirt
still refuses. Its freshness check (`check_branch_contains_control`) reads the
remote-tracking ref it fetched into, never `FETCH_HEAD`, and accepts only
non-overlapping generated Coga state as drift; lifecycle-only commits never
satisfy the branch's non-empty implementation guard. The successful
`requires: pr` bump and the teardown usage record both land on control only.

In the separate-checkout layout a divergent overlap on the live ticket's own
file is reported as a stranded ticket write rather than ordinary staleness:
`github_preflight.stranded_task_state_paths` says whether control ever
absorbed the branch's blob, and the refusal prescribes restoring the merge
base's copy on the branch, never a rebase. `coga bump` runs that same
comparison against the recorded `branch:` before a forward transition and
writes an advisory `[bump]` note to stderr; it never blocks, raises, or
changes the exit code, and it stays silent when this checkout stands on the
recorded branch or the recorded worktree resolves to this checkout.

## What this context does NOT cover

- The model these invariants protect — what launch does, what advances a step,
  what a handoff means — see `coga/architecture`.
- The git primitive itself — `publish`, `refresh`, the provenance check,
  `state_lock` — see `coga/sync`.
- The operator-facing behavior of the commands involved — see `coga/cli`.
- Where the code lives and how to test it — see `coga/codebase`.
- The recurring surface as a whole (schedules, templates, the autofix loop) —
  see `coga/recurring`.
