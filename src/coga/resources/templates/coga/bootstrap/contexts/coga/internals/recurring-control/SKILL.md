---
name: coga/internals/recurring-control
description: Where recurring runs may start — the control-branch requirement, relaying an off-branch single-repo run into an existing control worktree, the --all entry gate and config-error exemption, and how the owner gate reads authorization from the fetched control tip.
---

# Recurring control-branch and owner gates

## Recurring runs start on the control branch

Every launching entry point reads and writes period state from the configured
control branch: the bare sweep, `--force`, `coga run recurring-scan`,
`coga recurring launch <name>` (and aliases such as `coga dream`), and direct
`coga launch recurring/<name>` of a frozen delegating period. There is no
override; `--force` bypasses schedule and status filters, not this. Repos with
`[git].enabled = false` or outside a git checkout have no managed control
checkout and are exempt, but only a *confirmed* non-git workspace self-skips —
a Git inspection failure refuses (and never relays).

**Relay (single-repo sweep and named launch).** Off the control branch, these
look for another worktree of the same repo that already has control checked out
and re-run themselves there, from the mirrored position of the Coga workspace
(so nested monorepo layouts work), returning the child's exit code
(`recurring_runner._relay_off_control_single_repo_run`). Nothing is created,
copied or deleted and the operator's checkout is never switched or stashed. The
child is an ordinary on-control run, so:

- it runs the control tip's templates, periods and log, not your feature tree;
- agent templates and `delegate:` work — stdio and the TTY are inherited, and a
  dirty control worktree is not gated, as on control;
- `coga.local.toml` is not copied; `COGA_LOCAL_CONFIG` points at yours;
- one hop only: `COGA_RECURRING_CONTROL_RELAY` stops a second relay.

The forwarding parent skips its end-of-command state sweep (even on failure) so
it never commits dirty files; it forwards SIGTERM, waits, and returns 143;
Ctrl-C reaches the child via the foreground process group and is not resent.

With **no** worktree on control, the refusal names the current and control
branches and the absence, offering `git worktree add ../<repo>-<control>
<control>` or `git switch <control>`. A holder that cannot be relayed into (no
`coga.toml` at the mirrored position, or a missing directory) gets a separate
refusal naming it and suggesting `git worktree remove` / `git worktree prune`.
Direct `coga launch recurring/<name>` has no relay and its refusal says nothing
about worktrees.

A create made from a feature checkout by a direct call publishes to control like
any write ([coga/sync](../../sync/SKILL.md)); normal recurring commands refuse
that checkout first.

## The `--all` child entry gate

Each `--all` child must have `[git]` enabled and must fetch and fast-forward the
control branch before reading or writing period state; a stale child exits
with `STALE_CONTROL_EXIT_CODE`. An off-branch child is serviced from a temporary
worktree ([recurring-temp-worktrees](../recurring-temp-worktrees/SKILL.md)). An
*ahead or diverged* control checkout still fails loud, once, naming
`git pull --rebase` — Coga never rebases a human's commits. Duplicate
checkouts of one remote workspace are grouped by resolved remote URL plus
workspace path; one runs (preferring one already on control) and the rest are
named and skipped.

**Parent config exemption.** `cli.main` catches `ConfigError` from its eager
`find_repo_root()` / `load_config(require_user=False)` and `_validate_aliases`,
and only for `coga init`, `coga uninstall` or a cross-repo `coga recurring
--all` warns (`Note: ignoring current config error so the cross-repo recurring
sweep can run`) and dispatches on `_DEFAULT_ALIASES`. Every other command still
exits 2. Keep this when tightening config validation: the parent checkout may be
half-migrated while every target, loaded in its own process, is fine. Targets
failing an intentional config guard (e.g. no local `user`) are unconfigured
non-targets, counted once, not failures.

## Owner authorization

With `owner = "<name>"` in committed `coga.toml`, every launching entry point
refuses an operator whose machine-local `user` differs, naming the owner.
Unset means ungated. Authorization never trusts the loaded config or an
uncommitted edit: it fetches the control branch into the remote-tracking ref and
reads `owner` from that commit's `coga.toml`, fetching from the remote's sole
effective **push** URL; several push URLs are refused. Checkout-wide
`FETCH_HEAD` is never a source. Only a checkout with no configured remote reads
`owner` from local `HEAD`; `[git].enabled = false` does not qualify, since a
machine-local setting must not override committed policy. The `--all` parent
checks the same control-tip value; if it cannot confirm it, it dispatches the
child, whose freshness gate fails first. A locally owner-less repo stays
best-effort offline; once opted in, an apparent owner cannot launch offline.

Implementation: `recurring_runner._refuse_non_control_branch`,
`_relay_to_control_worktree`, `_control_tip_owner`, `run_recurring_all_repos`.
