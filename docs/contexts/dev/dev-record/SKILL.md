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

Write every `## Dev` line on `main`, the checkout state you bump from: ticket
edits made on a feature branch are not published before the end-of-step
return and would be refused there. The implement step declares
`requires: branch`, so `coga bump` refuses until that copy has `branch:`.

Know the gate's limits. It checks presence, not freshness: on a retry the
earlier attempt's lines pass while this attempt's write strands. And it is
cheaply satisfiable by hand-copying the lines, which leaves the stranded write
to resurface later.

## Stranded ticket writes

A ticket write committed on the feature branch strands there: control keeps
rewriting the same file at every transition. `open-pr`'s freshness gate
refuses it and `bump` warns about it on stderr. In a sandbox clone an
uncommitted ticket edit surfaces as `coga open-pr`'s "Recorded worktree has
uncommitted changes" refusal, which names this ticket's file separately.
The comparison is one-directional; a branch copy control already absorbed is
silent.

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
Intentional ticket-body changes, `ticket.py`, and attachments under
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
