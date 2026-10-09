---
name: coga/internals/state-publication
description: How `src/coga/git.py` publishes Coga state — every eligible file under the Coga root and the contexts root — onto the control branch: the invariants, the shared root membership, the `publish` primitive and its wrappers, best-effort versus strict callers, and exactly what the end-of-command sweep and guided authoring publish from control and feature checkouts.
---

# State publication

Overview: [`coga/sync`](../../sync/SKILL.md). Refusals are
[`coga/internals/git-regressions`](../git-regressions/SKILL.md); bringing a
checkout level is [`coga/internals/git-refresh`](../git-refresh/SKILL.md);
append-only merging is [`coga/internals/spool-merge`](../spool-merge/SKILL.md).

## Invariants

1. **Control is canonical.** `[git].remote` + `[git].control_branch`
   (`origin` / `main` by default) is the only durable home of Coga state —
   every eligible file under the [Coga roots](#the-coga-roots); a write is
   durable when it is on that ref. `publish` builds a commit on control's tip and pushes it; it never
   commits on the checked-out branch, stashes, or rebases, and never pushes a
   hand commit as such — it lands that commit's state in a commit of its own.
   The local control branch fast-forwards, or *realigns* (the ref moves to
   the control commit) when `_local_control_subsumed` proves every local-only
   commit is Coga state already on control
   ([`coga/internals/git-refresh`](../git-refresh/SKILL.md)). With no remote,
   local control is canonical.
2. **Nothing is lost.** The markdown on disk is the write. A publish that
   cannot reach control leaves the file as written, reports on stderr (and
   usually `coga/log.md`), and is retried by the next command's sweep.
3. **Nothing moves backward.** Every published path is compare-and-swapped
   against control (`coga/internals/git-regressions`).
4. **One integrate path.** `git.refresh` is the only way an exempt or
   recurring checkout is brought level; `fast_forward_control` is the only
   code that moves the local control ref after a publish or in `refresh`, by
   fast-forward or realignment. `prepare_control_checkout` (the launch
   boundary) applies the same realignment proof.

## The Coga roots

Owner decision (2026-10-07): everything in the Coga root and the configured
contexts root publishes automatically — tickets, the log, recurring
templates, skills, workflows, shared `coga.toml`, `context.md`, and contexts.
There is no separate knowledge PR for files inside these roots; the accepted
tradeoff is that instruction edits there land directly, and Git history is
the visible record and the correction mechanism.

`git.coga_root_paths(cfg)` is the one membership definition: `Config.repo_root`
plus `Config.contexts_root` (which `[layout] contexts` may move outside the
Coga root), a root nested in the other listed once. In the root layout the
Coga root is the checkout itself. The sweep, guided authoring, checkout
preparation and return (`dev/checkouts`), state-only commit recovery
(`_local_control_subsumed`), the recorded assist-checkout alignment, and the
`mark done` stranding guard all read it.

During launch checkout return, this helper also accepts the pre-session
contexts root. Both publication and cleanup retain it for that return, so a
move between two relocated roots includes the old-path deletions together
with the destination and config. Subsequent commands use only the new roots.

**Eligible** means a regular file Git does not ignore. Every consumer asks Git
(`status`, `ls-files --exclude-standard`), so `coga.local.toml`, `.coga/` run
records, generated agent-skill views, caches, and other ignored artifacts stay
local and are never force-added. Untracked symlinks discovered through a
directory pathspec are skipped; explicitly named or tracked symlinks and paths
with symlinked ancestors are refused before reading their working bytes. Root
membership and Git path conversion are lexical: a directory link never adds
its target to the publication scope. Checkout cleanup rejects the same links.
Submodules are refused, including a dirty, staged, or
removed gitlink; a directory is never published as a submodule deletion.
Source
outside the roots, including the packaged copies under `src/`, is ordinary
code: it reaches control only through a branch and reviewed PR.

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
   three-way union-merged; `commit-tree` on base, then
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
[`coga/internals/launch-claims`](../launch-claims/SKILL.md). It serializes one
checkout only; across checkouts the push compare-and-swap decides. Two
sessions editing one working tree remain an unserialized hazard.

## The end-of-command sweep

`cli.main` calls `_sweep_coga_state` after a command returns or raises, except
on exit code `RETRY_WITHOUT_SWEEP_EXIT_CODE` (75), which a command uses when it
deliberately left retryable state dirty (stale recurring control, refused
`bump` rewind, a launch checkout-boundary entry refusal). The launch checkout
boundary also calls `sync_coga_state` itself, at entry and before each
checkout return, so routine state lands before the checkout moves
([dev/checkouts](../../../dev/checkouts/SKILL.md)). The sweep:

- runs only when `cli._should_sweep_coga_state(argv)` is true: never for a
  bare `coga`, an option, `--help`/`-h`, `_NON_SWEEPING_COMMANDS` (`status`,
  `show`, `validate`, `usage`, `init`, `uninstall`), `secret`, `recurring
  --all`, `run publish-state`, `bump --backward`/`--to`, or `skill`/`mark`/`recurring` subcommands
  outside their sweeping sets;
- is skipped when authoring finalization failed, or a launch's checkout return refused or stopped part-way
  (`git.state_sweep_withheld`, reset per `cli.main` invocation, so it also
  covers an in-process `coga recurring` run): the preserved dirt is what the
  sweep must not publish, the command's exit status is unchanged, and the
  next launch entry publishes routine state again;
- is skipped in a process that relayed a recurring run into the worktree
  holding the control branch (the relayed child sweeps there), and for the
  off-control `run recurring-scan --require-fresh-control` child, whose
  temporary control worktree already swept;
- reloads config first, so a command that edited `coga.toml` or moved the
  Coga root is swept at the new location (an invalid config skips the sweep
  with a warning);
- passes `coga_root_paths` to `publish`, on control and feature checkouts
  alike — nothing outside them. `_candidates` then selects every dirty,
  unignored path there (new, modified, deleted, or renamed) plus eligible
  committed state (a hand commit whose control copy has not moved since;
  routine state only on a feature checkout), so a clean checkout can still
  publish; clean state behind control is never republished, and a committed
  path whose control copy moved beyond its provenance stays unselected until
  the operator rebases. Overlapping roots are one pathspec, so nothing is
  examined twice.

## Strict publication on demand

The sweep cannot tell its caller whether a file landed. A handoff that hands
files to someone else's fresh clone runs `coga run publish-state [--message M]
[PATH...]` (`publish_state.run_publish_state_recipe`) instead: first fetch the
configured remote control branch (a missing branch or unreachable remote fails),
then one `publish` over `coga_root_paths` with the named files as `require_paths`. Exit 0 means
every named file is on control (landed now or already matching), listed on
stdout, or that `[git].enabled = false` leaves no control branch (stdout says
so). Exit 1 means refused, failed, uncertain, not a repository, or no control
branch; files stay as written, stderr names the cause, and `runner` appends a
`## Recipe Failure` section to an inherited task blackboard. Exit 2 means bad
argv or a named path that is not a regular file inside the Coga roots, before
any publication write. The CLI excludes `run publish-state` from its exit
sweep, even on success or a configuration failure before recipe dispatch.
Only the explicit recipe publishes, so no fallback can publish tickets
separately from a required context the strict transaction refused.
`build/onboarding` runs it before offering `coga launch` for its
starter tickets and neither hands over nor bumps on a non-zero exit.

## Guided authoring

`coga ticket` guided authoring (`authoring.finalize_authored`) fingerprints
the eligible files under the Coga roots before the interview — file mode plus
content hash, so a mode-only edit is a change
(`authoring_sync_roots` is `coga_root_paths`; Git lists the files, so ignored
ones are never hashed, and symlinks are never followed). After it, finalization
reloads and validates configuration before discovering files or validating
tickets. An authored change to the Git destination (`[git]` enabled, remote,
or control branch) refuses, as at the launch boundary, and keeps the edits:
the handoff publishes only where the interview started. The changed set compares the original snapshot with the new roots,
so a context relocation carries the old-path deletions, destination files,
and layout config in the same publication. A regular file still on disk but
excluded from the new eligible inventory (for example by a new ignore rule)
stays local; it is not a deletion or a required publication path. If a previously snapshotted path
now has a symlinked ancestor, finalization refuses instead of treating it as
a deletion and following its new target. Invalid configuration refuses
before publication and keeps the edits. An existing target is validated even when
unchanged, but its task path is selected only when its ticket or attachments
changed; file-to-directory conversions include both paths; a deleted target
is skipped. Bootstrap interviews discover and validate changed or new tasks.

After validation, the authored task paths and every changed file outside the
tasks directory (contexts, skills, workflows, config; the log is left to its
writers and the sweep) land in **one** guarded publish. Finalization
requires its changed knowledge files through `require_paths`: committed
feature-branch edits, mode included, must already be on control or finalization fails with a
review/merge remedy before publishing the task. A bootstrap interview
that only writes a context still publishes it, so the next ticket launch finds
it on control with no extra branch. Validation errors propagate before
anything is published. A refused or failed publish keeps every edit on disk,
exactly as authored, and raises `AuthoringError` — `coga ticket` exits
non-zero rather than reporting a completed handoff. That invocation withholds
its final sweep so it cannot publish a task separately from the knowledge the
authoring transaction refused; a later command may retry eligible dirty files.
A successful publish names the non-task files it carried on
stderr. The boundary is identical with or without launch metadata, on control
and feature checkouts.

Ordinary manual edits inside the roots publish the same way, through the next
command's sweep. Local prompt composition still reads local edits. This is an
automatic publication boundary, not a permission barrier against explicit Git
commands; a human may still choose a PR for a change they want reviewed.

**Pre-review state publication hazard.** The sweep and authoring finalizer run
from whichever checkout invoked them. A feature checkout's *dirty* files in
the roots — ticket prose, log, recurring template (including `ticket.py`),
context, skill, or workflow — land on control before review. Committed ones
on a feature branch stay with the branch unless they are routine state, so
commit an edit you want reviewed before running a sweeping Coga command in
that checkout. Checkout practice is `dev/checkouts`.

Never `git add` `coga/tasks/**` or `coga/log.md` into a PR; `coga open-pr`
excludes that state from its cleanliness gate and refuses a branch whose only
commits are Coga state.
