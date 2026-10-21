---
name: coga/state-publication/sweep
description: When and how the end-of-command sweep publishes Coga state from control and feature checkouts, and the strict on-demand `coga run publish-state` recipe for handoffs that must know a file landed.
---

# The end-of-command sweep and strict publication

Part of [coga/state-publication](../SKILL.md).

## The end-of-command sweep

`cli.main` calls `_sweep_coga_state` after a command returns or raises, except
on exit code `RETRY_WITHOUT_SWEEP_EXIT_CODE` (75), which a command uses when it
deliberately left retryable state dirty (stale recurring control, refused
`bump` rewind, a launch checkout-boundary entry refusal). The launch checkout
boundary also calls `sync_coga_state` itself, at entry and before each
checkout return, so routine state lands before the checkout moves
([dev/checkouts](../../../dev/checkouts/launch-boundary/SKILL.md)). The sweep:

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

### Recovering a failed publication

A failed best-effort publication keeps the local write, and the transition it
recorded has already happened: rerunning `bump` (or any lifecycle command)
would advance again, never republish. Recover with the same recipe, from the
same checkout, once Git can write where the failure said it was writing
(including an external object directory). The report names the command,
run from the Coga root it prints: `coga run publish-state <ticket file>
<log>` after task sync (a directory-form task names its `ticket.md`), or the
no-path form after the sweep, log-only sync, or a deletion (a deleted path is
not a valid argument, but the root sweep includes it). The named files are
only the ones that must land; the recipe publishes every eligible file under
the Coga roots. It adds no transition, an immediate repeat is a no-op
(`already on`), and while access is still denied it exits 1 with the files
kept. Coga never changes permissions, sandbox configuration, Git environment
routing, or object storage to recover; restoring access is the operator's
call ([coga/sandboxes](../../sandboxes/SKILL.md#restricted-sandboxes)).
