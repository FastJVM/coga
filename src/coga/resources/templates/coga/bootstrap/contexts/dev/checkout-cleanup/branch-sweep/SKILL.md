---
name: dev/checkout-cleanup/branch-sweep
description: What the branch sweep protects and archives before deleting — patch-equivalent merged-PR verdicts, the shared skill-update branch, the `retired/<branch>` remote archive — and the `[git] worktrees_ticket_owned` assumption for unrecorded worktrees.
---

# Branch-sweep protection, archive, and unrecorded worktrees

Part of [dev/checkout-cleanup](../SKILL.md).

## Branch-sweep protection and archive

For a local ref with a merged PR and no open PR for the same branch name,
`branchsweep.merged_pr_verdict` inspects commits beyond the merged head and
the locally available control refs. Non-merge commits with matching
`git patch-id --verbatim` IDs on the merged head are excluded; remaining
commits must touch only generated task/log state. Each merged patch matches
at most one local commit, so a later reapplication needs its own match.
Patch comparison preserves
whitespace (including indentation and line endings), disables external diff
and text conversion, fixes submodule diffs to the short gitlink format, and
compares against the merged head's history without
excluding control. Thus both squash and normal merges can release a local
pre-rebase copy. Different patch context can conservatively keep a ref;
comparison failures keep it too. Merge commits always face the existing
`git diff-tree --cc` state-only check. Remote refs still require an exact
merged head, never patch equivalence. A missing merged-head object is fetched
from `refs/pull/<number>/head` without writing a ref before comparison.

`branchsweep.sweep_branches` preserves the shared `coga/skill-update` branch
(`skill_manager.SKILL_UPDATE_BRANCH`) before any PR lookup or deletion. It
does so even between update runs with no live ticket or open PR. This is an
exact-name exemption, not an exemption for every `coga/` branch.

After the existing landing and claim gates, the sweep must publish
`retired/<branch>` to the configured Git remote before removing any associated
worktree or deleting either branch ref. Worktree claim and cleanliness proofs
run before publication and again before removal, and the second pass also
requires the worktree's HEAD to still be the archived local tip; an initial
refusal leaves the archive untouched. `_publish_retirement_tag` archives the
actual authorized tip, fetching missing remote objects first. If both local
and remote refs will be deleted, one of those tips must contain the other;
the tag points to that descendant. When they diverge, a tip that is a merged
PR's head is already preserved by GitHub at `refs/pull/<number>/head`, so the
tag covers the remaining tips and the run record names the PR ref. This is
the rebased-copy shape: the remote ref sits at the merged head while the
local ref keeps its pre-rebase commits. Divergent tips that no PR ref covers
preserve both refs and need human reconciliation. This keeps later Coga
bookkeeping and lagging local refs recoverable without inventing a merge.

The remote tag is the archive; the sweep reads it with `git ls-remote`
before publishing. A remote `retired/<branch>` whose commit equals or contains
the selected commit already preserves it — another clone may have archived a
later tip of the same branch, or a partial cleanup left an older remote ref
behind — so the sweep publishes nothing and proceeds to deletion. A remote tag
holding unrelated history or a non-commit object (blob or tree, including
through an annotated tag) is never moved or forced:
the sweep publishes the selected commit under the deterministic
`retired/<branch>@<sha12>` instead, which a retry then finds already archived.
(`retired/<branch>/<sha>` is not possible: a ref cannot nest under an existing
tag ref.) A local tag of either name that points at an unpublished, different
commit or a non-commit object makes that name unusable, so it is skipped
rather than published over. Object availability is checked separately from
commit ancestry: an unreadable remote object still refuses retirement.
The local tag is created only after the remote holds the archive, and
advanced only when the archive contains its commit, so a failed pass never
leaves a local tag that replays a conflict. The push names one explicit tag
refspec without force and disables `push.followTags`. When both names are
taken by other objects, or a remote read, object fetch, or tag push fails,
the sweep preserves the branch and worktree, records the reason in
`## Branch Sweep`, and makes the recipe exit 2 after checking other branches.
Restore archived work with `git fetch <remote> tag <tag>` and
`git switch -c <new-branch> <tag>`, where `<tag>` is `retired/<branch>` or
the `@<sha12>` name the run record reports.

Every branch-sweep pass shares this gate.
It does not change ticket-scoped retire/autoclose disposal into an archival
operation, except for the owned branches the disposal passes to the
restricted sweep, which archive like any sweep deletion.

## Unrecorded worktrees: `[git] worktrees_ticket_owned`

The [checkout proofs](../proofs/SKILL.md) only touch worktrees a ticket or worklist recorded. An ad-hoc
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
[recurring scheduling](../../../coga/recurring/scheduling/SKILL.md#repo-scope-and-clone-scope).
It preserves and reports local refs with unpushed non-bookkeeping commits. A closed but unmerged PR alone is not evidence that its work landed,
and it authorizes nothing without a terminal owner
([dev/checkout-cleanup/terminal-owners](../terminal-owners/SKILL.md)).
