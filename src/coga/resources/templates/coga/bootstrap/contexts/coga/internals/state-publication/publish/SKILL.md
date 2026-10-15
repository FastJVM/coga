---
name: coga/internals/state-publication/publish
description: The `git.publish` primitive step by step, its wrappers, how best-effort and strict callers handle a refused or failed publish, and the `state_lock` it runs under.
---

# `publish`, its callers, and the state lock

Part of [coga/internals/state-publication](../SKILL.md).

## `publish` and its wrappers

`git.publish(cfg, paths, message, *, expect=None, guard=None,
fast_forward=True, require_paths=())` returns `True` (pushed), `False` (control already held
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
4. **Tree and push**: a temporary `GIT_INDEX_FILE` seeded from base, each
   candidate overlaid (or removed when deleted), `merge=union` paths
   three-way union-merged without re-adding a line control already has
   (the duplicate filter in `coga/internals/spool-merge`); `commit-tree` on base, then
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
   (`coga/internals/git-refresh`). A refusal here does not undo the push.
   With no remote, a refused fast-forward is a failed publish (`GitError`);
   the write stays dirty.

Wrappers: `sync_task_state(cfg, task_path, *, message, expect=None,
strict=False)` publishes one task plus the log; `sync_log(cfg, *, message)`
publishes the log alone with stderr-only failures (stateless launches, usage
records); `sync_coga_state(cfg)` is the sweep.

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
is `coga/internals/launch-claims` and `coga/internals/pr-publication`.

## `state_lock`

`publish` runs steps 2–5 under `git.state_lock`, the same-checkout lock
lifecycle writers hold around read-modify-write; its contract is
[`coga/internals/launch-claims`](../../launch-claims/SKILL.md). It serializes one
checkout only; across checkouts the push compare-and-swap decides. Two
sessions editing one working tree remain an unserialized hazard.
