---
name: coga-dev/internals/state-publication
description: State publication invariants and shared root membership machinery in src/coga/git.py; the publish primitive lives in its leaf.
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


The [publish primitive](publish/SKILL.md) owns the transaction mechanics.
