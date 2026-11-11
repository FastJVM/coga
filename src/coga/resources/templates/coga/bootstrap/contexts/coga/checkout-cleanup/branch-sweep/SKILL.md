---
name: coga/checkout-cleanup/branch-sweep
description: What the branch sweep protects and archives before deleting, how to review and release a retained local draft, and when unrecorded worktrees pin a branch.
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

When the sweep cannot establish local state, it stops before any local or
remote delete, records the reason in `## Branch Sweep` as "the sweep stopped
early", and makes the recipe exit 2. That covers a failed local branch
enumeration (including a listed branch whose tip cannot be resolved), a failed
worktree probe, and an unlocatable Coga root prefix. A missing local branch
would otherwise make its remote ref look remote-only. A successful listing
with no branches is not a failure.

Every branch-sweep pass shares this gate. It does not change ticket-scoped
retire/autoclose disposal into an archival operation, except for the owned
branches the disposal passes to the restricted sweep, which archive like any
sweep deletion.

## Review and release a retained local draft

The ordinary sweep can report a **retained local draft** when comparison
with a merged PR finds unmatched source changes. The report names the
branch, its full local commit OID, the merged PR and its head, and example
paths. If several merged PRs have unmatched changes, it shows the one with
the lowest PR number. These differences can be an earlier draft or later
follow-up work. The sweep keeps both branch refs and any worktrees.
A visible worktree hold or an incomplete comparison with another PR makes
manual release unavailable. Live-ticket claims and incomplete claim scans
suppress the draft entry.

In the clone that has the draft, inspect the commits with
`git log --stat <pr-head>..<full-local-oid>` and `git show <commit>`. If you
need the PR head object, fetch `refs/pull/<pr-number>/head` from the configured
remote. Review the commit and the history it would expose to readers of that
remote. When you want to publish that exact draft and release its local
branch, run:

```sh
coga run branch-sweep --publish-and-release-local <branch> <full-local-oid>
```

Use the full OID you reviewed. The command looks up PRs in the configured
remote's GitHub repository and requires matching fetch and push destinations.
It checks for unmatched source work, ordinary cleanup eligibility, open PRs,
protected names, live-ticket claims, and worktree occupancy. The claim check
includes mentions in the current workspace's live tickets and attachments and
recorded `## Dev` branch claims across the Git checkout's Coga workspaces.
The command archives the reviewed commit under the retirement tag rules
above and deletes only the named local branch. It rechecks open PRs, claims,
occupancy, and the tip after archival. Keep the target branch free of concurrent
updates during the command. Git's worktree-aware deletion runs separately
from the final tip check.

The command reports the commit, tag, remote, and local deletion outcome.
A detached rebase or bisect can make Git refuse deletion after archival.
The reported tag remains on the remote if deletion fails after publication.
To restore the exact draft, fetch the reported tag and switch at the reported
OID. The tag itself can point to a descendant that already contains the draft.

```sh
git fetch --no-tags <remote> refs/tags/<tag>
git switch -c <new-branch> <full-local-oid>
```

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
A closed but unmerged PR can authorize cleanup only with a terminal owner
([coga/checkout-cleanup/terminal-owners](../terminal-owners/SKILL.md)).
