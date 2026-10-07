---
name: dev/dev-record
description: The `## Dev` blackboard record that links a code ticket to its branch and PR (plus the sandbox clone, when one is used), the `requires: branch` / `requires: pr` gates, `coga open-pr`, stranded-write repair, and the review-step reading rules.
---

# The `## Dev` record

Every code ticket records its linkage explicitly near the top of its
blackboard instead of letting tools infer it from the slug:

```
## Dev
branch: <branch-name>
pr: <pr-url>
```

`worktree: <path>` is added only when the work happens in a sandbox clone
([dev/checkouts](../checkouts/SKILL.md)); otherwise the branch lives in the
launch checkout and `branch:` is the whole linkage. Tickets from the retired
linked-worktree layout may still carry a `worktree:` line; retire and
autoclose read it to dispose of that checkout.

A bare `branch:` or `worktree:` value runs to end of line (paths may contain
spaces); a bare `pr:` value ends at the first whitespace. To annotate, wrap the
value in backticks before the note (``branch: `feature/x` (Magicator repo)``)
or put the note on its own line. Update lines in place; `## Dev` is current
linkage, not history. Lifecycle history is in `coga/log.md`; abandoned plans go
to [dev/design-history](../design-history/SKILL.md).

## When to write each line

- **`branch:`** as soon as the branch exists, so a crash or handoff can find
  the work. Create it from `main` with `git branch <name>`, record the line
  while still on `main`, publish it with the pre-branch procedure in
  [dev/checkouts](../checkouts/SKILL.md), and require a clean tree before
  switching to it.
- **`worktree:`** only for a sandbox clone, as soon as the clone exists.
- **`pr:`** the full URL containing `/pull/<number>`; a trailing note is fine,
  a placeholder reads as no PR. Where the workflow's PR step uses
  `code/open-pr`, `coga open-pr` writes it; in a hand-run flow write it as soon
  as `gh pr create` returns.

Write `## Dev` lines where you bump from. In a manual session that is
`main`: ticket edits made on a feature branch are not published before the
end-of-step return and would be refused there. In a launched session that
returns the checkout, the handoff may be written on the branch after loading
control's copy of the ticket ([dev/checkouts](../checkouts/SKILL.md)); `coga
bump` publishes it. The implement step declares
`requires: branch`, so `coga bump` refuses until that copy has `branch:`.

Know the gate's limits. It checks presence, not attempt freshness: an earlier
attempt's branch record can still pass. Copying linkage lines also does not
repair a stranded ticket write.

Decision (2026-10-06, owner): do not add the proposed branch/worktree freshness
guard at bump. Its cross-checkout premise predates ordinary tickets' move to
the launch checkout. Branch existence cannot distinguish a wrong old branch
from a legitimate resumed branch; `open-pr` already checks existence and
commits ahead of the base. Revisit on a concrete wrong-branch handoff under
the current ordinary-ticket workflow. Recurring worktrees are outside this
decision.

## Stranded ticket writes

A ticket write committed on the feature branch strands there: control keeps
rewriting the same file at every transition. `open-pr`'s freshness gate
refuses it and `bump` warns about it on stderr. In a sandbox clone an
uncommitted ticket edit surfaces as `coga open-pr`'s "Recorded worktree has
uncommitted changes" refusal, which names this ticket's file separately.
The comparison is one-directional; a branch copy control already absorbed is
silent.

Decision (2026-10-06, owner): do not add a general cross-checkout detector for
uncommitted blackboard prose. The remaining working-memory loss is rare and
low stakes; missing checkout pointers, independent clones, detached worktrees,
and normal control-ahead divergence make reliable detection disproportionate.
Revisit if concrete lost-note incidents justify the complexity. Any future
comparison should report content the control copy lacks, without automatically
merging or overwriting either copy.

Repair: inspect the branch copy, preserve anything still needed in the primary
ticket, then restore the merge base's copy on the branch and commit:

```sh
git restore --staged --worktree --source=$(git merge-base <control> <branch>) -- <path>
```

Do not rebase to fix it, and do not restore control's copy (it goes stale at
the next transition). A dirty task/log hunk in a sandbox clone is a duplicate
only after its content is preserved in the primary ticket or verified in the
authoritative log; discard only confirmed duplicates, never commit or stash
them to pass the clean-tree gate, and never hand-edit `coga/log.md`.
This ticket's own file is never implementation diff: control has already
rewritten it, so a branch commit of it is an overlapping stranded write. Move
an intentional authored-body change to the live ticket in the primary
checkout and discard the clone's copy. `ticket.py` and attachments under
`coga/tasks/` can be implementation work and stay in the diff.

## `coga open-pr <slug>`

The default alias for `coga run open-pr <slug>` (implementation
`coga.open_pr`). Run it from the launch checkout on `main`
(`open_pr._checkout_mode` refuses any other branch). It reads `branch:`,
checks the branch by name — commits ahead of `main`, freshness against
`<remote>/main` — pushes it, opens the PR, prints the bare URL, and writes
`pr:` back; it fails loud when linkage is missing or there is nothing to PR.
With a recorded `worktree:` (a sandbox clone) it runs those checks inside the
clone, which must be on the branch and clean. A `worktree:` naming the launch
checkout itself, left by the retired single-checkout layout, is treated as
absent. The PR step declares `requires: pr`. Publication guarantees are
owned by [coga/internals/pr-publication](../../coga/internals/pr-publication/SKILL.md).

## Consumers and multi-ticket PRs

Frontmatter stays reserved for canonical task state; `## Dev` is legible
working state that focused consumers parse: `open-pr` writes `pr:`, autoclose
reads PR linkage and names the retire follow-up. Branch sweep instead protects
a branch that any non-terminal ordinary ticket names anywhere in its files
(a recurring period task pins only its `## Dev` line).

Each `branch:` line is the ticket's explicit ownership of that branch. A
fenced or indented code example (including fences inside lists or quotes) is
not a record; an empty `branch:` line
cannot borrow the following prose as its value. Both the single-branch and
multi-branch readers use these rules.
A ticket that produced more than one branch records one `branch:` line per
branch; the first stays the workflow's checkout (`requires: branch`,
`coga open-pr`). Once the ticket is done or canceled, terminal branch cleanup
may delete every owned branch whose PR merged or was closed unmerged
([dev/checkout-cleanup](../checkout-cleanup/SKILL.md#terminal-owners-and-closed-prs)).
A prose mention elsewhere in the ticket is not ownership. Remove a `branch:`
line for a branch the ticket does not own.

When one PR covers several tickets, each records the same `branch:` and `pr:`.
The link goes ticket to PR.

## Review step

`code/with-review` and its siblings freeze `code/address-pr-comments` on an
owner-assigned `review` step: the owner merges and resolves threads, and the
skill is an on-demand assist that never resolves or bumps. Coga does not own
GitHub merge policy, so an unresolved bot thread does not block a merge.
Decision (2026-09-13, owner): keep the human gate; rather than auto-launching
the assist or blocking merges, add post-merge detection. When
`autoclose-merged` closes a ticket it fetches that PR's `reviewThreads` once
and names every unresolved, non-outdated, reply-less thread in the closure's
`coga/log.md` line, its sweep report, and one Slack line, report-only
(`coga/autoclose/sweep` skill, "The unanswered-thread follow-up").

Reading rules: a ticket still on `review` with a merged PR is not backlog
(autoclose closes it on its next run); count only open PRs as the live queue.
A measurement over retired tickets and merged PRs should gate on a closed time
window, never on an empty live queue, which normal throughput never produces.
