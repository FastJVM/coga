---
name: coga/checkout-cleanup/branch-sweep
description: What the branch sweep protects and archives before deleting — patch-equivalent merged-PR verdicts, the shared skill-update branch, the `retired/<branch>` remote archive — and the `[git] worktrees_ticket_owned` assumption for unrecorded worktrees.
---

# Branch-sweep protection, archive, and unrecorded worktrees

Part of [coga/checkout-cleanup](../SKILL.md).

## Branch-sweep protection and archive

A local ref whose PR merged, with no open PR for the same branch name, is
released when its extra commits are patch-equivalent copies of the merged
commits or touch only generated task/log state, so a local pre-rebase copy of
a squash- or normally-merged branch can go. Any doubt keeps the ref. Remote
refs still require the exact merged head.

The shared `coga/skill-update` branch is always preserved, even between
update runs with no live ticket or open PR. This is an exact-name exemption,
not an exemption for every `coga/` branch.

After the landing and claim gates, the sweep publishes a `retired/<branch>`
tag to the configured Git remote before removing any associated worktree or
deleting either branch ref; worktree claim and cleanliness proofs run again
before removal. The tag archives the authorized tip. When the local and
remote tips diverge, a tip that is a merged PR's head is already preserved by
GitHub at `refs/pull/<number>/head`, so the tag covers the remaining tip and
the run record names the PR ref; divergent tips that no PR ref covers
preserve both refs for human reconciliation.

An existing remote `retired/<branch>` that already contains the tip counts as
the archive. One holding unrelated history is never moved or forced; the
sweep publishes `retired/<branch>@<sha12>` instead. When neither name is
usable, or a remote read, fetch, or tag push fails, the sweep preserves the
branch and worktree, records the reason in `## Branch Sweep`, and makes the
recipe exit 2 after checking other branches. Restore archived work with
`git fetch <remote> tag <tag>` and `git switch -c <new-branch> <tag>`, where
`<tag>` is `retired/<branch>` or the `@<sha12>` name the run record reports.

Every branch-sweep pass shares this gate. It does not change ticket-scoped
retire/autoclose disposal into an archival operation, except for the owned
branches the disposal passes to the restricted sweep, which archive like any
sweep deletion.

## Unrecorded worktrees: `[git] worktrees_ticket_owned`

The [checkout proofs](../SKILL.md#the-checkout-proofs) only touch worktrees a ticket or worklist recorded. An ad-hoc
worktree pins its branch forever, and `coga run branch-sweep` reports it
`skipped-worktree-pinned`. A repo may assert, with
`worktrees_ticket_owned = true` under `[git]` in shared `coga.toml` (default
`false`):

> Every linked worktree of this repository belongs to a Coga ticket. A
> landed, locally pristine linked worktree that no non-terminal ticket
> records is finished work, not someone's scratch checkout.

With it set, the branch sweep removes such a worktree before deleting
its landed branch, under the same linked-worktree, exact-branch, pristine, and
unclaimed proofs. Setting it is the owner's call: afterwards a scratch checkout
worth keeping must be dirty, unlanded, or recorded on a live ticket. The sweep
also runs `git worktree prune` repo-wide first, because a wiped `/tmp`
worktree's registration keeps pinning its branch.

The branch sweep is a clone-scoped recurring template: every clone runs it
daily for its own refs and worktrees. Cadence and scope live in
[recurring scheduling](../../recurring/scheduling/SKILL.md#repo-scope-and-clone-scope).
It preserves and reports local refs with unpushed non-bookkeeping commits. A closed but unmerged PR alone is not evidence that its work landed,
and it authorizes nothing without a terminal owner
([coga/checkout-cleanup/terminal-owners](../terminal-owners/SKILL.md)).
