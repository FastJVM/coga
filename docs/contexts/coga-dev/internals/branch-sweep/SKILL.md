---
name: coga-dev/internals/branch-sweep
description: How checkout disposal and the branch sweep implement the coga/checkout-cleanup contract — checkout classification, claim discovery, the restricted owned-branch sweep, forced local deletion, the merged-PR patch-equivalence verdict, retirement-tag collisions, and worklist branch-debt reconciliation.
---

# Branch sweep and checkout disposal

The user contract is [coga/checkout-cleanup](../../../coga/checkout-cleanup/SKILL.md)
and its leaves; this page is what a change to `checkout_disposal.py`,
`branchcleanup.py`, `branchsweep.py`, or `retire_worklist.py` must keep.
`checkout_disposal` runs the shared proofs for `coga retire` and autoclose
over the per-checkout proofs in `branchcleanup`.

## Classification and ownership

`git.classify_checkout` identifies another repository's primary as
`foreign-primary`, with its root as `owner`;
`retire_worklist.is_primary_checkout` exempts its directory.
`retire_worklist.worktree_owner` records the owning repository for foreign
primary and foreign linked checkouts. Autoclose captures ownership before
dropping a primary's directory from the closure, and infers missing ownership
on legacy entries before any branch cleanup or discharge check.

Owner decisions: a missing independent-clone directory discharges its entry
(2026-10-01); a closed-unmerged PR's branch may be deleted only under a
terminal owner (2026-10-05).

## Claims and the restricted sweep

Claim discovery scans every workspace of the Git checkout, including a
recurring runner's temporary control checkout, via
`discover_coga_repos(..., allow_control_worktree_root=True)`;
`checkout_disposal.live_checkout_claim` answers per branch or worktree. The
owned branches then go through `checkout_disposal._sweep_owned_branches`.
When disposal has just proved and removed a same-repository linked worktree,
it carries that exact path's proof into the restricted pass.

## Local deletion

Local deletion re-checks the authorized tip on both the ancestry and
merged-PR paths. On the ancestry path, a tip already reachable from the
landed ref that `git branch -d` still refuses only on its own merge check
("is not fully merged" — `-d` measures against the branch's configured
upstream, or HEAD when there is none, and either may lag the landed ref)
escalates to `git branch -D`, but only after re-reading the branch and
requiring it to still equal the authorized tip and still be reachable from
the landed ref. A worktree refusal or any other error is never forced, and
the deleted tip SHA is logged for reflog recovery.

Ignored-state exemptions are `branchcleanup.REGENERABLE_IGNORED_DIRS`; a
copied `coga.local.toml` is compared with `local_config_path`.

## Merged-PR verdict

For a local ref with a merged PR and no open PR for the same branch name,
`branchsweep.merged_pr_verdict` inspects commits beyond the merged head and
the locally available control refs. Non-merge commits with matching
`git patch-id --verbatim` IDs on the merged head are excluded; remaining
commits must touch only generated task/log state. Each merged patch matches
at most one local commit, so a later reapplication needs its own match.
Patch comparison preserves whitespace (including indentation and line
endings), disables external diff and text conversion, fixes submodule diffs
to the short gitlink format, and compares against the merged head's history
without excluding control. Different patch context can conservatively keep a
ref; comparison failures keep it too. Merge commits always face the
`git diff-tree --cc` state-only check. A missing merged-head object is
fetched from `refs/pull/<number>/head` without writing a ref before
comparison. Closed PRs flow through the same verdict for terminal-owned
branches; ownership is `branchsweep._terminal_owners` over
`autoclose.parse_branch_names`.

`branchsweep.sweep_branches` preserves `skill_manager.SKILL_UPDATE_BRANCH`
before any PR lookup or deletion.

## Retirement tags

`_publish_retirement_tag` archives the actual authorized tip, fetching
missing remote objects first. `_containing_tip` first looks for a tip that
contains all the others. If none exists, tips covered by `pr_heads` are
excluded and the remaining tips must have a containing tip for the tag;
otherwise publication refuses. The user-facing recovery contract is the
[archive rule](../../../coga/checkout-cleanup/branch-sweep/SKILL.md#branch-sweep-protection-and-archive).
The second worktree proof also requires the worktree's HEAD to still be the
archived local tip; an initial refusal leaves the archive untouched.

The sweep reads the remote tag with `git ls-remote` before publishing. A
remote `retired/<branch>` whose commit equals or contains the selected commit
already preserves it (another clone may have archived a later tip, or a
partial cleanup left an older remote ref), so nothing is published. A remote
tag holding unrelated history or a non-commit object (blob or tree, including
through an annotated tag) is never moved or forced: the selected commit goes
under the deterministic `retired/<branch>@<sha12>`, which a retry then finds
already archived. (`retired/<branch>/<sha>` is impossible: a ref cannot nest
under an existing tag ref.) A local tag of either name pointing at an
unpublished, different commit or a non-commit object makes that name
unusable. Object availability is checked separately from ancestry: an
unreadable remote object still refuses retirement. The local tag is created
only after the remote holds the archive, and advanced only when the archive
contains its commit, so a failed pass never leaves a local tag that replays a
conflict. The push names one explicit tag refspec without force and disables
`push.followTags`.

## Worklist branch debt

Before discharge, reconciliation backfills a legacy `retires.md` entry's
`branches` list from its surviving ticket's exact slug; an unreadable ticket
refuses reconciliation. A union-merged older line cannot erase an existing
additional branch list. Field syntax is in the `coga/autoclose/sweep` skill.

## Known failure mode: non-UTF-8 ref and worktree names

`branchsweep._git` decodes Git output as strict UTF-8 (`encoding="utf-8"`,
no `errors=`), while `branchcleanup._git` adds `errors="surrogateescape"`.
On a POSIX host whose locale admits bytes UTF-8 rejects, a ref or worktree
path holding such bytes makes the sweep's `for-each-ref` or
`worktree list --porcelain` read raise `UnicodeDecodeError`, which aborts the
whole branch sweep for that repository; before the Windows port forced UTF-8
(PR #1093) the locale encoding decoded it. Unresolved: raised as an
unanswered P2 review thread on PR #1093 (`src/coga/branchsweep.py`), reported
by autoclose on 2026-10-26; no ticket owns it. The suggested fix is
`errors="surrogateescape"` as `branchcleanup._git` does, or limiting the
encoding override to Windows. Not yet reproduced in a test.
