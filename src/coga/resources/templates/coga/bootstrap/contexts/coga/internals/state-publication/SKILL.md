---
name: coga/internals/state-publication
description: How `src/coga/git.py` publishes Coga task, log, and recurring state onto the control branch — the invariants, the `publish` primitive and its wrappers, best-effort versus strict callers, and exactly what the end-of-command sweep publishes from control and feature checkouts.
---

# State publication

Overview: [`coga/sync`](../../sync/SKILL.md). Refusals are
[`coga/internals/git-regressions`](../git-regressions/SKILL.md); bringing a
checkout level is [`coga/internals/git-refresh`](../git-refresh/SKILL.md);
append-only merging is [`coga/internals/spool-merge`](../spool-merge/SKILL.md).

## Invariants

1. **Control is canonical.** `[git].remote` + `[git].control_branch`
   (`origin` / `main` by default) is the only durable home of `coga/tasks/**`,
   `coga/log.md`, and `coga/recurring/**`; a write is durable when it is on
   that ref. `publish` builds a commit on control's tip and pushes it; it never
   commits on the checked-out branch, stashes, or rebases, and the local
   control branch only fast-forwards. With no remote, local control is
   canonical.
2. **Nothing is lost.** The markdown on disk is the write. A publish that
   cannot reach control leaves the file as written, reports on stderr (and
   usually `coga/log.md`), and is retried by the next command's sweep.
3. **Nothing moves backward.** Every published path is compare-and-swapped
   against control (`coga/internals/git-regressions`).
4. **One integrate path.** `git.refresh` is the only way a checkout is
   brought level; `fast_forward_control` is the only code that moves the local
   control ref.

## `publish` and its wrappers

`git.publish(cfg, paths, message, *, expect=None, guard=None,
fast_forward=True)` returns `True` (pushed), `False` (control already held
the tree), or `None` (soft-skipped). Soft-skips write one stderr line and
nothing else: `[git].enabled = false`, not a git repo, git unavailable, or the
control branch missing locally and on the remote
(`control_branch_mismatch_message` names the `coga.toml` fix).

1. **Candidates** (`_candidates`): every file under `paths` dirty against
   HEAD, plus a clean file whose HEAD copy moved past control from a copy this
   checkout derived from (a feature branch that committed state it had
   published). A clean file merely behind control is not a write.
2. **Base**: `refs/remotes/<remote>/<control>` without a fetch on the hot
   path; local `<control>` when there is no remote or no tracking ref yet.
3. **Guard** (`_guard`): the provenance and generation checks; any refusal
   raises `StateRegressionError` before anything is pushed.
4. **Tree and push**: a temporary `GIT_INDEX_FILE` seeded from base, each
   candidate overlaid (or removed when deleted), `merge=union` paths
   three-way union-merged; `commit-tree` on base, then
   `push <remote> <new>:refs/heads/<control>`. A non-fast-forward rejection
   refetches and rebuilds, at most `MAX_PUBLISH_ATTEMPTS` (5) times. Any other
   push failure rereads control once: `True` if control now carries the
   commit, `GitError` if it definitely does not, `UncertainPublishError` if it
   cannot be reread. Push output is redacted.
5. **Record and fast-forward**: the landed blobs are recorded under
   `refs/worktree/coga/published` (per-worktree provenance), then
   `fast_forward_control` runs unless `fast_forward=False` (Retro's isolated
   delete). With no remote, a refused fast-forward is a failed publish
   (`GitError`); the write stays dirty.

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
[`coga/internals/launch-claims`](../launch-claims/SKILL.md). It serializes one
checkout only; across checkouts the push compare-and-swap decides. Two
sessions editing one working tree remain an unserialized hazard.

## The end-of-command sweep

`cli.main` calls `_sweep_coga_state` after a command returns or raises, except
on exit code `RETRY_WITHOUT_SWEEP_EXIT_CODE` (75), which a command uses when it
deliberately left retryable state dirty (stale recurring control, refused
`bump` rewind). The sweep:

- runs only when `cli._should_sweep_coga_state(argv)` is true: never for a
  bare `coga`, an option, `--help`/`-h`, `_NON_SWEEPING_COMMANDS` (`status`,
  `show`, `validate`, `usage`, `init`, `uninstall`), `secret`, `recurring
  --all`, `bump --backward`/`--to`, or `skill`/`mark`/`recurring` subcommands
  outside their sweeping sets;
- is skipped in a process that relayed a recurring run into the worktree
  holding the control branch (the relayed child sweeps there), and for the
  off-control `run recurring-scan --require-fresh-control` child, whose
  temporary control worktree already swept;
- reloads config first, so a command that edited `coga.toml` or moved the
  Coga root is swept at the new location (an invalid config skips the sweep
  with a warning);
- publishes every dirty path under the tasks directory, `coga/log.md`, and
  the recurring directory — nothing else. Contexts, skills, workflows, and
  config are review work and are never swept.

One non-sweep path does publish hand-authored files: `coga ticket` guided
authoring (`authoring.finalize_authored`) hashes the tasks, contexts, and
skills roots before the interview (`authoring_sync_roots`, which follows a
relocated `[layout] contexts` root) and publishes the authored task plus every
context or skill file the session created, changed, or deleted.

**Pre-review publication hazard.** Both paths run from whichever checkout the
command ran in. A feature checkout's dirty ticket prose, log, or recurring
template (including `ticket.py`) — and any context or skill a `coga ticket`
interview touched — lands on control before review. Keep deliberate edits to
those paths on the control branch, or expect them on `main` out of band;
checkout practice is `dev/checkouts`.

Never `git add` `coga/tasks/**` or `coga/log.md` into a PR; `coga open-pr`
excludes that state from its cleanliness gate and refuses a branch whose only
commits are Coga state.
