---
name: coga-dev/internals/state-publication
description: State publication invariants, shared root membership, the end-of-command sweep's selection and skips, guided-authoring finalization, and the strict recipe's wiring; the publish primitive lives in its leaf.
---

# State publication implementation

## Invariants

1. **Control is canonical.** `[git].remote` + `[git].control_branch`
   (`origin` / `main` by default) is the only durable home of Coga state —
   every eligible file under the [Coga roots](../../../coga/state-publication/SKILL.md#the-coga-roots); a write is
   durable when it is on that ref. `publish` builds a commit on control's tip and pushes it; it never
   commits on the checked-out branch, stashes, or rebases, and never pushes a
   hand commit as such — it lands that commit's state in a commit of its own.
   The local control branch fast-forwards, or *realigns* (the ref moves to
   the control commit) when `_local_control_subsumed` proves every local-only
   commit is Coga state already on control
   ([`coga-dev/internals/git-refresh`](../git-refresh/SKILL.md)). With no remote,
   local control is canonical.
2. **Nothing is lost.** The markdown on disk is the write. A publish that
   cannot reach control leaves the file as written, reports on stderr (and
   usually `coga/log.md`), and is retried by the next command's sweep.
3. **Nothing moves backward.** Every published path is compare-and-swapped
   against control (`coga-dev/internals/git-regressions`).
4. **One integrate path.** `git.refresh` is the only way an exempt or
   recurring checkout is brought level; `fast_forward_control` is the only
   code that moves the local control ref after a publish or in `refresh`, by
   fast-forward or realignment. `prepare_control_checkout` (the launch
   boundary) applies the same realignment proof.

## Shared root machinery

`git.coga_root_paths(cfg)` is the one membership definition: `Config.repo_root`
plus `Config.contexts_root` (which `[layout] contexts` may move outside the
Coga root), a root nested in the other listed once. In the root layout the
Coga root is the checkout itself. The sweep, guided authoring, checkout
preparation and return (`coga/checkouts/launch-boundary`), state-only commit recovery
(`_local_control_subsumed`), the recorded assist-checkout alignment, and the
`mark done` stranding guard all read it.

During launch checkout return, this helper also accepts the pre-session
contexts root. Both publication and cleanup retain it for that return, so a
move between two relocated roots includes the old-path deletions together
with the destination and config. Subsequent commands use only the new roots.

Owner decision (2026-10-07): everything in the Coga roots publishes
automatically, with no separate knowledge PR; the accepted tradeoff is that
instruction edits land directly, and Git history is the record and the
correction mechanism. The user contract is
[coga/state-publication](../../../coga/state-publication/SKILL.md).

## The end-of-command sweep

`cli.main` calls `_sweep_coga_state` after a command returns or raises, except
on exit code `RETRY_WITHOUT_SWEEP_EXIT_CODE` (75), which a command uses when it
deliberately left retryable state dirty (stale recurring control, refused
`bump` rewind, a launch checkout-boundary entry refusal). The launch checkout
boundary also calls `sync_coga_state` itself, at entry and before each
checkout return. The sweep:

- runs only when `cli._should_sweep_coga_state(argv)` is true: never for a
  bare `coga`, an option, `--help`/`-h`, `_NON_SWEEPING_COMMANDS` (`status`,
  `show`, `validate`, `usage`, `init`, `uninstall`), `secret`, `recurring
  --all`, `run publish-state`, `run prepare-checkout`, `bump
  --backward`/`--to`, or `skill`/`mark`/`recurring` subcommands outside
  their sweeping sets. `prepare-checkout` is skipped on success, failure,
  and a configuration refusal before dispatch alike: a chat calls it
  repeatedly over unfinished contexts and skills, which only its launcher's
  return and final sweep publish;
- is skipped when authoring finalization failed, or a launch's checkout
  preparation or return refused or stopped part-way
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

## Strict recipe wiring

`coga run publish-state` is `publish_state.run_publish_state_recipe`: fetch
the configured remote control branch, then one `publish` over
`coga_root_paths` with the named files as `require_paths`. `runner` appends
the `## Recipe Failure` section to an inherited task blackboard. The CLI
excludes the recipe from its exit sweep even on success or a configuration
failure before dispatch. `build/onboarding` runs it before offering
`coga launch` for its starter tickets and neither hands over nor bumps on a
non-zero exit.

## Guided-authoring finalization

`authoring.finalize_authored` fingerprints the eligible files under
`coga_root_paths` (`authoring_sync_roots`) before the interview: file mode
plus content hash, so a mode-only edit is a change; Git lists the files, so
ignored ones are never hashed, and symlinks are never followed. After it,
finalization reloads and validates configuration before discovering files or
validating tickets. A Git-destination change refuses as at the launch
boundary and keeps the edits: the handoff publishes only where the interview
started. The changed set compares the original snapshot with the new roots,
so a context relocation carries the old-path deletions, destination files,
and layout config in the same publication. A regular file still on disk but
excluded from the new eligible inventory (for example by a new ignore rule)
stays local; it is not a deletion or a required publication path. If a
previously snapshotted path now has a symlinked ancestor, finalization
refuses instead of treating it as a deletion and following its new target.
Invalid configuration refuses before publication and keeps the edits. An
existing target is validated even when unchanged, but its task path is
selected only when its ticket or attachments changed; file-to-directory
conversions include both paths; a deleted target is skipped. Bootstrap
interviews discover and validate changed or new tasks.

The publish carries the authored task paths and every changed file outside
the tasks directory (the log is left to its writers and the sweep), and
requires the changed knowledge files through `require_paths`: committed
feature-branch edits, mode included, must already be on control or
finalization fails with a review/merge remedy before publishing the task. A
bootstrap interview that only writes a context still publishes it, so the
next ticket launch finds it on control with no extra branch. A refused or
failed publish raises `AuthoringError`, and the invocation withholds its
final sweep so it cannot publish a task separately from the knowledge the
transaction refused; a later command may retry eligible dirty files. A
successful publish names the non-task files it carried on stderr. The
boundary is identical with or without launch metadata, on control and
feature checkouts.

The [publish primitive](publish/SKILL.md) owns the transaction mechanics.
