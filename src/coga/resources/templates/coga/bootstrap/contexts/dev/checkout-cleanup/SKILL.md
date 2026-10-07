---
name: dev/checkout-cleanup
description: How finished tickets and their feature checkouts are disposed of: `coga retire`, `coga delete`, the shared checkout proofs, terminal-owner cleanup of closed-PR branches, ignored-state rules, and the `[git] worktrees_ticket_owned` assumption.
---

# Retiring tickets and checkouts

You do not delete your own feature branch. `coga retire` (manual, while the
ticket and its `## Dev` lines exist) and the daily autoclose sweep (for every
ticket it closes and every open `retires.md` entry) run one shared set of
proofs: `checkout_disposal.py` over the per-checkout proofs in
`branchcleanup.py`. Ticket work no longer creates linked worktrees
([dev/checkouts](../checkouts/SKILL.md)), so a current ticket records only
`branch:` and the disposal is branch-only. A ticket from the retired
linked-worktree layout may still record `worktree:`; the disposal removes that
worktree first, since a branch checked out in a linked worktree cannot be
deleted, then prunes the branch. Keep `worktree:` accurate where it exists; it
is what they act on.

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
- the branch has landed on control or still equals the recorded merged PR head.

After these proofs, every branch the ticket owns (each `## Dev` `branch:`
line, the recorded one included) that is still present locally or on the
remote goes through the branch sweep restricted to those names
(`checkout_disposal._sweep_owned_branches`). The sweep applies the
terminal-owner rule below and the archive gate. A kept branch is reported
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

## Terminal owners and closed PRs

Owner decision, 2026-10-05: a branch whose PR was closed without merging may
be deleted, but only when its ticket finished. Every branch-sweep pass applies
the rule: the daily autoclose pass, the weekly retry, and the restricted pass
retire and autoclose run for a disposed ticket.

**Ownership.** A ticket owns a branch only through a `## Dev` `branch:` line
(`autoclose.parse_branch_names`; a ticket may record several, see
[dev/dev-record](../dev-record/SKILL.md)). An open `retires.md` entry also
counts, because autoclose records it for a ticket it closed and that ticket
may since be gone. An entry whose recorded `owner` is another clone does not
count. A surviving ticket cannot bypass this with its own branch lines:
when it records `worktree:`, that path must be a readable primary or linked
checkout of this repository. A foreign or unavailable recorded checkout
grants no terminal-ticket deletion authority here and is reported.
When disposal itself has just proved and removed a same-repository linked
worktree, it carries that exact path's proof into its restricted branch pass.
That successful removal does not revoke the surviving ticket's ownership;
an already-missing path or a path recreated as a foreign checkout gets no such
exception. All other deletion gates are still checked.
The owner must be `done` or `canceled`
(`branchsweep._terminal_owners`). These never count as ownership: a closed PR
on its own, a prose or attachment mention, a fenced or indented code example,
and a ticket or worklist that
cannot be read.

**Durable branch debt.** Worklist entries retain additional owned branches
in an optional `branches` list beside the primary `branch`. Autoclose records
that list even when checkout disposal was skipped. Before discharge,
reconciliation backfills a legacy entry from its surviving ticket's exact
slug; an unreadable ticket refuses reconciliation. A union-merged older line
cannot erase an existing additional branch list. The entry stays open until
every recorded local branch is gone in its owning repository and the existing
worktree gate clears. This keeps secondary branch ownership and retries alive
after the first branch or the ticket disappears. Remote leftovers retain the
existing best-effort sweep policy. Field syntax is documented in the
`coga/autoclose/sweep` invocation skill.

**Authorization.** A closed, unmerged PR for a terminal-owned branch vouches
for it the way a merged PR does (`merged_pr_verdict`'s `closed` PRs). The
existing gates still apply:

- No live ticket in this workspace mentions the branch, and no live ticket in
  any workspace of the Git checkout records it (`live_checkout_claim`). One
  terminal owner and one live claimant means the branch stays. Every recorded
  branch counts, including secondary branches on recurring period tickets.
- No PR for the head is open.
- The remote ref still equals the closed PR's exact head. A remote moved past
  that head is kept and reported, even when the local ref goes.
- Every local commit beyond the closed head, other than a patch-equivalent
  copy, touches only Coga task/log state. A source commit added after the PR
  closed keeps the ref and names the paths, because that work was never
  reviewed.
- Divergent tips follow the archive rule below. GitHub keeps
  `refs/pull/<number>/head` for closed PRs as well as merged ones.
- The control branch, the checked-out branch, the shared skill-update branch
  and worktree-pinned branches stay protected.

A terminal-owned branch with no merged or closed PR is reported for a human
decision, never inferred.

**When it runs.** `coga mark done`, `coga mark canceled` and a final-step
`coga bump` delete nothing and make no network call. A checkout therefore
never disappears beneath the session that finished the ticket. Cleanup
happens at `coga retire`, at the autoclose disposal of a ticket it closes,
and at the next daily autoclose branch pass (or `coga run branch-sweep`).
A refusal is visible in that pass's `## Branch Sweep` or retire report and is
retried on every later pass while an owner record exists. A canceled ticket
deleted before any pass ran leaves no owner record: its branch is then kept
and reported as having no vouching PR, the safe failure.

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
checkout and every owned branch under the proofs above. A worktree or owned
branch the proofs kept is a bug: the ticket is its only owner record, so Retro
must not delete it. Retire then skips the worklist discharge, creates the retire task
already `blocked` with what it kept and why (which notifies the owner
on Slack, as `coga block` does), launches nothing and exits 2. The owner fixes
the checkout by hand, then runs `coga unblock` and `coga launch` on the retire
task. Run it from a checkout on `[git].control_branch`:
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

The daily autoclose branch pass and standalone weekly sweep share this gate.
It does not change ticket-scoped retire/autoclose disposal into an archival
operation, except for the owned branches the disposal passes to the
restricted sweep, which archive like any sweep deletion.

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
commits. A closed but unmerged PR alone is not evidence that its work landed,
and it authorizes nothing without a terminal owner
([above](#terminal-owners-and-closed-prs)).
