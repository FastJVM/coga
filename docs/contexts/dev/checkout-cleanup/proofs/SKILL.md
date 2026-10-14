---
name: dev/checkout-cleanup/proofs
description: The checkout proofs `coga retire` and autoclose share before removing a recorded worktree, the restricted owned-branch sweep that follows, local-before-remote branch deletion, and which ignored state preserves a checkout.
---

# The checkout proofs

Part of [dev/checkout-cleanup](../SKILL.md).

A recorded worktree is removed only when:

- Git identifies it as a linked worktree of the same repository, still on the
  recorded branch;
- no other non-terminal ticket in any Coga workspace of the same Git checkout
  records that branch or worktree (claim discovery scans every workspace,
  including a recurring runner's temporary control checkout, via
  `discover_coga_repos(..., allow_control_worktree_root=True)`; a refused or
  incomplete claim scan keeps even a branch-only disposal pending, which
  autoclose reports and retains);
- no PR for that head is open;
- the branch has landed on control or still equals the recorded merged PR head.

After these proofs, every branch the ticket owns (each `## Dev` `branch:`
line, the recorded one included) that is still present locally or on the
remote goes through the branch sweep restricted to those names
(`checkout_disposal._sweep_owned_branches`). The sweep applies the
[terminal-owner rule](../terminal-owners/SKILL.md) and the
[archive gate](../branch-sweep/SKILL.md). A kept branch is reported
with its reason, and the disposal stays pending while its local ref
survives. This step is skipped while the recorded worktree survives.
Every candidate, including additional merged branches, gets its own
cross-workspace live-claim check before the restricted sweep. An incomplete
claim scan preserves it.

Local cleanup precedes remote deletion; local deletion re-checks the authorized
tip on both the ancestry and merged-PR paths. On the ancestry path, a tip already
reachable from the landed ref that `git branch -d` still refuses only on its own
merge check ("is not fully merged" — `-d` measures against the branch's
configured upstream, or HEAD when there is none, and either may lag the landed
ref) escalates to `git branch -D`, but only after re-reading the branch and
requiring it to still equal the authorized tip and still be reachable from the
landed ref; a worktree refusal or any other error is never forced, and the
deleted tip SHA is logged for reflog recovery. Remote deletion re-verifies the exact
head and uses force-with-lease, so a reused branch is never deleted on stale
PR state.

**Ignored state.** Tracked, untracked, and ignored files all preserve the
checkout, except the regenerable entries in
`branchcleanup.REGENERABLE_IGNORED_DIRS` (`__pycache__`, `.pytest_cache`,
`.ruff_cache`, `.mypy_cache`, and Coga's rebuilt `.agent-skills/` symlink
view), which retire deletes and counts. A copied `coga.local.toml` is judged
by content: byte-identical to the operator's own (`local_config_path`, so
`COGA_LOCAL_CONFIG` when set) it is deleted and counted, since the original
survives; an edited copy preserves the checkout. Other machine-local state
(`.env`, `.venv/`, `.coga/`, agent discovery links) preserves it. For ignored-only state
retire prints and records the explicit opt-in
`git worktree remove --force '<path>'`; it never offers that over tracked or
untracked work.

Reported for manual disposal: a stale linked worktree now on another branch; a checkout shared with another live ticket or an open PR; a locked or
dirty worktree; and a recorded path already gone (reported, not pruned).
