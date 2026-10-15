---
name: coga/internals/state-publication
description: How `src/coga/git.py` publishes Coga state — every eligible file under the Coga root and the contexts root — onto the control branch: the invariants, the shared root membership and eligibility, and the pre-review publication hazard; `publish`, the end-of-command sweep and guided authoring live in its leaves.
---

# State publication

Overview: [`coga/sync`](../../sync/SKILL.md). Refusals are
[`coga/internals/git-regressions`](../git-regressions/SKILL.md); bringing a
checkout level is [`coga/internals/git-refresh`](../git-refresh/SKILL.md);
append-only merging is [`coga/internals/spool-merge`](../spool-merge/SKILL.md).

Leaves:

- [coga/internals/state-publication/publish](publish/SKILL.md) — the
  `publish` primitive and its wrappers, best-effort versus strict callers,
  and `state_lock`.
- [coga/internals/state-publication/sweep](sweep/SKILL.md) — the
  end-of-command sweep and strict publication on demand
  (`coga run publish-state`).
- [coga/internals/state-publication/authoring](authoring/SKILL.md) — what
  guided authoring publishes from control and feature checkouts.

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
preparation and return (`dev/checkouts/launch-boundary`), state-only commit recovery
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
