---
name: dev/checkout-cleanup
description: How finished tickets and their feature checkouts are disposed of: `coga retire`, `coga delete`, the shared checkout proofs, ignored-state rules, and the `[git] worktrees_ticket_owned` assumption.
---

# Retiring tickets and checkouts

You do not delete your own feature branch. Terminal transitions, `coga retire`
(manual, while the ticket and its `## Dev` lines exist), and the daily/weekly
sweeps share ownership and disposal proofs: `checkout_disposal.py` over the per-checkout proofs in
`branchcleanup.py`. Ticket work no longer creates linked worktrees
([dev/checkouts](../checkouts/SKILL.md)), so a current ticket records only
`branch:` and the disposal is branch-only. A ticket from the retired
linked-worktree layout may still record `worktree:`; the disposal removes that
worktree first, since a branch checked out in a linked worktree cannot be
deleted, then prunes the branch. Keep `worktree:` accurate where it exists; it
is what they act on.

## Ownership and terminal cleanup

Ownership is explicit: each `branch:` line in the blackboard's `## Dev`
section owns that exact branch. The first remains the working branch for PR
and workflow consumers; additional lines retain ownership of earlier attempts.
A `worktree:` applies to the first branch. Fenced examples, ticket prose,
attachments, PR links alone, and generated sweep reports are not ownership.
Scan every supported Coga workspace in the Git checkout. A failed or incomplete
scan preserves all candidates. Another non-terminal owner's claim protects
both refs, including a second or later branch record.

A surviving `done` or `canceled` owner permits cleanup against a deliberately
closed, unmerged PR for the same head. Closure alone never authorizes deletion.
Without a terminal owner, the existing merged/landed proof is still required.
Any open PR protects both refs, even if the local tip is already on control.
The control branch, shared skill-update branch, and invoking branch remain
protected. Unknown or foreign recorded checkouts preserve the branch for
inspection in its owning clone, never deletion of a same-named local branch.

For a closed-unmerged PR, compare local history with its head without excluding
control history; commits beyond it must be patch-equivalent to that head or
Coga task/log state. Source changes that fail this proof are named and kept.
Merged PRs keep the broader landed-history proof below. Remote deletion always
requires an exact eligible PR head, freshly read and leased. Divergent refs
are judged separately: a refused local ref keeps the remote; an authorized
local ref may be archived and deleted while a newer remote remains, with its
SHA and refusal reported. Never infer a disposition for unreviewed source work.

Published terminal transitions attempt only their explicitly owned branches,
from control, without removing worktrees. A supervised/task session or an
off-control transition records deferral instead. Cleanup never rolls back the
terminal verdict. `## Branch cleanup` records the outcome on the ticket;
`coga run branch-sweep`, the daily autoclose branch pass, and the weekly sweep
retry from the surviving Dev records. A failed publication does not initiate
cleanup. Retire processes every branch record before its retro can delete the
ticket. The existing `retires.md` format remains legacy checkout debt, not a
substitute for terminal ownership: after the ticket disappears it cannot
newly authorize a closed-unmerged PR. Resolve such debt before deleting the
ownership record, or inspect it manually.

## The checkout proofs

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
- the branch passes the eligible PR or landed-history proof below;
- the retirement archive has been published before removal.

Local cleanup precedes remote deletion; local deletion re-checks the authorized
tip on both the ancestry and merged-PR paths. Remote deletion re-verifies the exact
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

## Primary checkouts and foreign branch ownership

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
manual branch cleanup in its owning clone; an unreadable owner or branch
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
[the September incident](../../../evidence/independent-clone-worklist-2026-09.md).
An independent fallback clone can still be removed deliberately by its operator
(or vanish with `/tmp`), which also discharges its entry; the worklist tracks its
branch rather than requiring removal of its primary directory. Publish ephemeral
work before removing any such clone.

## `/tmp` checkouts do not survive; the branch does

Treat any checkout under the system temp dir (a sandbox clone, a Dream or
Retro run checkout, an ad-hoc review worktree) as ephemeral: it is routinely
gone by the time anyone acts on it. Leaving work "preserved" in one, or
recording its path in `worktree:` or a blackboard note, preserves nothing.
Before the run ends, push the branch or land its commits on `main`.

When a linked `/tmp` worktree vanishes, Git keeps two things: a stale
registration (`git worktree prune` clears it; the branch sweep runs it) and
the local branch, which may now be the only copy of unlanded commits. A stale
`worktree:` line pointing at a gone path is therefore not evidence the work
landed. Recover from the primary checkout after refreshing `main` from `origin`
(here, as in `dev/checkouts`, `origin` and `main` stand for the configured
`[git].remote` and `[git].control_branch`):

1. Inspect `git log main..<branch>` for candidate commits. Squash merges and
   cherry-picks may already have landed their changes; check merged-PR
   history or patch equivalence before selecting commits to recover.
2. Recover only work still missing and wanted: cherry-pick onto `main` through
   the normal publication path, or `git push origin <branch>` and open a PR.
3. Only then `git branch -D <branch>`.

## `coga retire <slug> [--agent <type>] [--no-launch]`

Refuses unless the ticket is `status: done`. It first disposes of the
checkout and branch under the proofs above (best-effort: a cleanup failure is
reported, never aborts). Run it from a checkout on `[git].control_branch`:
off control (or with `[git].enabled` false, or outside a git work tree) it
skips disposal and says so (`Retire: checkout cleanup skipped ...`) rather
than failing, leaving the checkout and branch to autoclose or `branch-sweep`.
It then drops the slug from any recurring template's
`retires.md` worklist, but only once its local branch is gone (judged in the
owning repository when the entry records another clone as `owner`) and its recorded
worktree directory is gone or is a repository's primary checkout (which
nobody disposes of). Finally it scaffolds a `retire-<slug>` task straight to `active`,
whose body invokes the `retro/done-ticket` skill; that skill opens the PR that
records `## Retro`, edits knowledge if warranted, and deletes the source task
in the same PR. Retire launches the task unless `--no-launch`, which prints the
`coga launch` command instead. Branches with no live ticket are the
`branch-sweep` job's.

## Branch-sweep protection and archive

For a local ref with an eligible PR and no open PR for the same branch name,
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

The daily autoclose branch pass and standalone weekly sweep share this gate.
Ticket-scoped disposal with a surviving terminal owner uses this same archive
gate. Owner-less legacy `retires.md` entries retain their merged-only proofs.

## `coga delete <slug>`

Removes a task directory (ticket, blackboard, attachments) and syncs the
removal; recovery is `git restore`, with no Slack broadcast. Use it for an
abandoned ticket with nothing to retro. The removal lives in
`coga.delete_task`, also reachable as `coga run delete-task <slug>`, which does
not sync. Both hold the checkout-local state lock. Bootstrap tickets are not
deletable. `--keep-control-checkout` is the Retro-only form: accepted only from
a linked worktree, it still pushes to the remote control branch but does not
fast-forward another checkout that has control checked out; from the primary
checkout it fails before deleting. In a sandbox that cannot create a linked
worktree, Retro may use an independent clone and plain `coga delete`.

## Unrecorded worktrees: `[git] worktrees_ticket_owned`

The proofs only touch worktrees a ticket or worklist recorded. An ad-hoc
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

The daily autoclose template also runs this existing branch pass after its
ticket/worklist cleanup, including on days when no ticket closes. The standalone
weekly sweep remains a retry; cadence and failure ordering live in
[recurring scheduling](../../coga/recurring/scheduling/SKILL.md).
Both passes preserve and report local refs with unpushed non-bookkeeping
commits. A closed but unmerged PR alone is not evidence that its work landed.
