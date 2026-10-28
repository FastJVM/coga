---
name: coga-dev/internals/state-publication/publish
description: The `git.publish` primitive step by step, its wrappers, how best-effort and strict callers handle a refused or failed publish, and the `state_lock` it runs under.
---

# `publish`, its callers, and the state lock

Part of [coga-dev/internals/state-publication](../SKILL.md).

## `publish` and its wrappers

`git.publish(cfg, paths, message, *, expect=None, guard=None,
fast_forward=True, require_paths=(), log_mutation=None)` returns `True` (pushed), `False` (control already held
the tree), or `None` (soft-skipped). Soft-skips write one stderr line and
nothing else: `[git].enabled = false`, not a git repo, git unavailable, or the
control branch missing locally and on the remote
(`control_branch_mismatch_message` names the `coga.toml` fix).

1. **Candidates** (`_candidates`): every file under `paths` dirty against
   HEAD, plus a clean file whose HEAD copy changed since the merge base and
   moved past control from a copy this checkout derived from (a feature
   branch that committed state it had published, or a hand commit of state on
   local control). On a feature or detached checkout that committed adoption
   is limited to routine state — the tasks and recurring directories and the
   log — because a commit there is review work: a code PR's committed context
   or skill edit waits for its merge rather than landing ahead of review (and
   ahead of any packaged twin). A clean file merely behind control — HEAD's
   copy unchanged since the merge base, even when control holds a copy this
   worktree published — is not a write.
   Each file in `require_paths` must be selected or already match control;
   otherwise publication refuses before writing anything. This check repeats
   against each retry's base, so authoring cannot report a completed handoff
   when committed feature-branch knowledge was excluded from its transaction.
2. **Base**: `refs/remotes/<remote>/<control>` without a fetch on the hot
   path; local `<control>` when there is no remote or no tracking ref yet.
3. **Guard** (`_guard`): the provenance and generation checks; any refusal
   raises `StateRegressionError` before anything is pushed.
   A directory read reports `EACCES` on Windows and `EISDIR` on POSIX;
   `_working_tree_bytes` normalizes that case so the tree-mode guard can
   report its submodule refusal and preserve the entry.
4. **Tree and push**: a temporary `GIT_INDEX_FILE` seeded from base, each
   candidate overlaid (or removed when deleted), the configured audit log
   reconciled by whole events (explicit deletion requires `LogMutation`), and `merge=union` paths
   three-way union-merged without re-adding a line control already has
   (the duplicate filter in `coga-dev/internals/spool-merge`); `commit-tree` on base, then
   `push <remote> <new>:refs/heads/<control>`. A non-fast-forward rejection
   refetches and rebuilds, at most `MAX_PUBLISH_ATTEMPTS` (5) times. Any other
   push failure rereads control once: `True` if control now carries the
   commit, `GitError` if it definitely does not, `UncertainPublishError` if it
   cannot be reread. Push output is redacted.
5. **Record and integrate**: the landed blobs are recorded under
   `refs/worktree/coga/published` (per-worktree provenance), then
   `fast_forward_control` runs unless `fast_forward=False` (Retro's isolated
   delete). It fast-forwards local control, or — when local control carries
   hand commits whose state this publication (or an earlier one) already put
   on control — realigns it, refusing first if a Git operation is in progress
   in this checkout; anything else leaves local control alone with a note
   (`coga-dev/internals/git-refresh`). A refusal here does not undo the push.
   With no remote, a refused fast-forward is a failed publish (`GitError`);
   the write stays dirty.

Wrappers: `sync_task_state(cfg, task_path, *, message, expect=None,
strict=False, command=None)` publishes one task plus the log; `sync_log(cfg, *, message)`
publishes the log alone with `require_paths` naming that log (stateless launches,
usage records). It preserves `publish`'s `True`/`False` distinction for newly
published versus already-held state and returns `None` on a reported failure
or soft-skip. Failure recovery names the retained log as a required path.
Failures remain stderr-only; `spawn_agent_session` checks for
`None` to add the [session-end warning](../../../../coga/state-publication/SKILL.md#when-coga-publishes).
`sync_coga_state(cfg)` is the sweep.

## Best-effort versus strict

By default a refusal or failure is reported — `StateRegressionError` on
stderr (the guard also appends `sync refused` lines), any other `GitError` on
stderr plus a `git` log line — and swallowed, so the local transition stands.
`strict=True` re-raises after reporting. Strict callers (megalaunch claim and
activation, the recurring delegator's start, completion, and pause, a
strict `mark done`) restore their pre-write bytes and retract their audit
lines (`logfile.retract_log_lines`) on `StateRegressionError` and
`GitError`, and keep the write on `UncertainPublishError` as evidence for
reconciliation. A strict `mark done` publishes before announcing; the
ordinary path announces, then publishes. Launch-specific strict publication
is `coga-dev/internals/launch-claims` and `coga/pr-publication`.
Launch's ordinary managed startup uses the explicit group below. Outside
that group, branch preparation publishes linkage with
`sync_task_state(strict=True, expect=...)`, then proves the bytes on fetched
control; a failure keeps the edit, branch, and reservation for the next
launch. Recording a projected ticket's provenance
(`git.record_projected_baseline`) is likewise strict and verified, unlike
the best-effort `PUBLISHED_REF` update after an ordinary publish: a failure
refuses the spawn.

## Ordinary managed startup

`launch._LaunchInvocation._publish_startup` is an explicit finalizer, not a
global queue or a lifecycle-helper option. `_prepare_agent` retains the
captured source bytes and prospective activation/start across the first
`_supervise_steps` iteration. Only armed ordinary agent-only launches opt in;
scripts, blocked resumes, assists, queue and guarded/recurring callers keep
their existing routes. `prepare_active` still owns freezing and agent
selection; standalone `mark_active` and `mark_in_progress` are unchanged.

`checkouts.plan_ticket_checkout(source_bytes=...)` proves clean control against
the source, reserves/creates or validates the branch, and returns prospective
ticket bytes. It writes no ticket or log. Composition uses that prospective
ticket and notice. Under `state_lock`, `recheck_ticket_checkout` repeats the
source, policy, target, occupancy, stranded-ticket and path-eligibility checks,
and prospective task validation precedes all writes. The finalizer writes
only a changed ticket, appends applicable activation/start events and the
launch audit, and calls `publish` once for the ticket and required log.
`expect` pins the source ticket; a `guard` also checks it on every push retry,
because an unchanged ticket in a log-only resume is not a candidate.
`True` or `False` confirms publication; `None` does not.

`confirm_ticket_checkout` re-proves fetched clean control, metadata/routing,
workflow, policy and branch/worktree identity for every plan, including a
control-only resume. Compatible body notes trigger recomposition. A created
reservation becomes published only after linkage is confirmed. Entry retains
its clean-control and exact-ticket checks, switch/projection and strict
provenance verification. Only then is the successful-start notification sent;
its non-fatal failure line has the normal report and later usage/return/sweep
publishers. Spawn receives the verified prompt and `record_launch=False`.

Before materialization, refusal leaves the source and log unchanged. Once
writes begin, failures retain evidence and withhold return/sweep. A publication
refusal, failure, soft-skip or uncertainty exits 75 and starts no agent; no
transition is rolled back, even when post-push verification fails. The next
entry settles the already-recorded state rather than replaying activation or
start. Handoff and teardown stay independent; their accounting is owned by
[launch publication boundaries](../../../../coga/state-publication/launch-boundaries/SKILL.md).

## Failure reporting

Writing a checkout file and writing Git's object database are separate
operations; a sandbox can permit one and deny the other. When `_hash_blob`'s
`git hash-object -w` fails (from `_guard`'s candidate blobs, `expect`, or tree
construction), it raises `ObjectWriteError(GitError)` carrying the relative
file, the absolute checkout, and the effective object directory, resolved
only after the failure with `git rev-parse --path-format=absolute --git-path
objects` under the same inherited environment. That is the write destination
Git actually used: `<checkout>/.git/objects`, a linked checkout's shared
store, or a `GIT_OBJECT_DIRECTORY` override, never assumed. A failed lookup
reports the directory as `unavailable` and keeps the original error. The
summarized Git stderr is kept and redacted like any `run_git` failure. The
error names the operation, not a cause: a failing clean filter reaches the same
branch, so permission or sandbox causation is never asserted.

`git.sync_failure_report` formats the stderr for the sync handlers
(`sync_task_state`, `sync_coga_state`, `sync_log`, `mark._publish`, `coga
delete`); each caller keeps its own logging, raising, and sinks. The first
line keeps the recognizable `[git] sync failed:` / `[git] log sync failed:`
prefix and the publication subject (`Message was: ...`), which tells task
sync from the `Sync coga state` sweep. A best-effort caller adds a second
line: local state was saved (task sync, `mark`) or retained (sweep, log,
deletion); Git publication failed, or "could not be confirmed" for
`UncertainPublishError`; do not rerun the command (`coga bump` names itself
through `command=`); then the [recovery](../../../../coga/state-publication/SKILL.md#recovering-a-failed-publication).
Only an `ObjectWriteError` adds the conditional step "if Git could not write to
the object storage shown above, restore permitted access to it first". A
refusal keeps its own reconciliation guidance and gets no retry hint. Strict
callers and recurring create/adoption print only the neutral first line, since
they may still restore or replace the local write. The `git` audit line stays
`sync failed: <error>`; remedy prose goes only to stderr.
`record_sync_failure` writes that audit line and turns its own `OSError` into
a stderr note, so a log that cannot be written never masks the original
failure or makes a best-effort sync fatal.

## `state_lock`

`publish` runs steps 2–5 under `git.state_lock`, the same-checkout lock
lifecycle writers hold around read-modify-write; its contract is
[`coga-dev/internals/launch-claims`](../../launch-claims/SKILL.md). It serializes one
checkout only; across checkouts the push compare-and-swap decides. Two
sessions editing one working tree remain an unserialized hazard.

Pending guarded audit deletion receipts are checked before every publication,
including an unrelated path-only request. Only the matching mutation can
publish until recovery. A refusal may append diagnostics; recovery preserves
those suffix events instead of requiring unchanged whole-output bytes. Trim
and rollback share `logfile.LogMutation` and `replace_log`; details live in
[spool-merge](../../spool-merge/SKILL.md). Stateful script exit 75 with a pending
receipt bypasses between-phase settlement and remains a sweep stop signal.

Size exception: the publication primitive, strict caller obligations, and failure diagnostics stay together so a new caller can preserve the entire transaction contract; the writer inventory lives in a separate leaf.
