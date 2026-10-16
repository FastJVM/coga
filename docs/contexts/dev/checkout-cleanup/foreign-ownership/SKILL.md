---
name: dev/checkout-cleanup/foreign-ownership
description: Why a primary checkout is never directory debt, how branch debt stays with the clone that owns it, and the accepted disappearance policy for a self-owned clone whose recorded path is missing.
---

# Primary checkouts and foreign branch ownership

Part of [dev/checkout-cleanup](../SKILL.md).

A primary checkout is never directory debt, including another clone's primary
and independent sandbox clones. `git.classify_checkout` identifies another
repository's primary as `foreign-primary`, with its root as `owner`;
`retire_worklist.is_primary_checkout` exempts its directory. Git topology
cannot establish whether an independent clone is disposable, and neither its
path nor its current branch proves that. Autoclose preserves the directory and
never recommends deleting it. This also preserves local untracked and ignored
data there.

The branch remains debt in the repository that owns it. `worktree_owner`
records that owner for both foreign primary and foreign linked checkouts.
Autoclose captures ownership before dropping a primary's directory from the
closure, and infers missing ownership on legacy worklist entries before any
branch cleanup or discharge check for primary entries. For those entries it
does not delete a same-named branch in the sweeping clone. A remaining foreign
branch is reported for inspection and
manual branch cleanup in its owning clone. The owning clone's own daily
branch sweep runs the ordinary proofs on the entries that record it as
`owner`, then discharges and publishes them (`coga/recurring/scheduling`), so the
manual step remains only for a clone that does not run `coga recurring`; an unreadable owner or branch
list keeps the entry pending, and so does a missing owner of a foreign linked
worktree. For an independent clone recorded as its own owner, a missing
directory is treated as deletion of the clone and its branch, so the entry
clears. Once that owner's branch is gone, the
primary-checkout entry discharges automatically, with no directory deletion or
manual `retires.md` edit. Foreign linked worktrees still owe their directory
cleanup as well.

**Accepted disappearance policy (owner decision, 2026-10-01).** A missing
self-owned path does not prove deletion: relocation or a temporarily
unavailable filesystem looks the same. Automatic discharge is deliberate so
deleted sandbox clones do not generate reminders forever. It can forget a
surviving clone's branch cleanup if the recorded path disappears.

Before moving or renaming a clone, pause autoclose sweeps in every participating
checkout, update both `owner` and `worktree` in its `retires.md` entries to the
new path (using the worklist's field encoding), and update any surviving
ticket's recorded `worktree:`. Move the clone and verify the new path is
accessible before resuming sweeps. For a temporary unmount, keep sweeps paused
until the original path is accessible again; otherwise its cleanup record may
be discharged. This policy drops bookkeeping only; it never deletes a clone.

This replaces the repeated-posting failure and manual workaround documented in
[the September incident](../../../../archive/evidence/independent-clone-worklist-2026-09.md).
An independent fallback clone can still be removed deliberately by its operator
(or vanish with `/tmp`), which also discharges its entry; the worklist tracks its
branch rather than requiring removal of its primary directory. Publish ephemeral
work before removing any such clone.
