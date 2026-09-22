---
name: dev/dev-record
description: The `## Dev` blackboard record that links a code ticket to its branch, checkout, and PR, the `requires: branch` / `requires: pr` gates, `coga open-pr`, stranded-write repair, and the review-step reading rules.
---

# The `## Dev` record

Every code ticket records its linkage explicitly near the top of its
blackboard instead of letting tools infer it from the slug:

```
## Dev
branch: <branch-name>
worktree: <path-to-feature-checkout>
pr: <pr-url>
```

A bare `branch:` or `worktree:` value runs to end of line (paths may contain
spaces); a bare `pr:` value ends at the first whitespace. To annotate, wrap the
value in backticks before the note (``branch: `feature/x` (Magicator repo)``)
or put the note on its own line. Update lines in place; `## Dev` is current
linkage, not history. Lifecycle history is in `coga/log.md`; abandoned plans go
to [dev/design-history](../design-history/SKILL.md).

## When to write each line

- **`branch:`** the moment the branch exists, so a crash or handoff can find
  the work.
- **`worktree:`** the moment the checkout exists. In the separate layout use a
  path outside the primary checkout; in the single-checkout layout record the
  primary checkout's own path ([dev/checkouts](../checkouts/SKILL.md)).
- **`pr:`** the full URL containing `/pull/<number>`; a trailing note is fine,
  a placeholder reads as no PR. Where the workflow's PR step uses
  `code/open-pr`, `coga open-pr` writes it; in a hand-run flow write it as soon
  as `gh pr create` returns.

Write `branch:` and `worktree:` into the ticket copy of the checkout you will
bump from: the primary checkout on control in the separate layout, the feature
branch in the single-checkout layout. The implement step declares
`requires: branch`, so `coga bump` refuses until that copy has both lines.

Know the gate's limits. It checks presence, not freshness: on a retry the
earlier attempt's lines pass while this attempt's write strands. And it is
cheaply satisfiable by hand-copying the lines, which leaves the stranded write
to resurface later.

## Stranded ticket writes

A `## Dev` or blackboard write made in a separate feature checkout and then
bumped from the primary checkout strands on the feature branch. It resurfaces
as `coga open-pr`'s "Recorded worktree has uncommitted changes" refusal (which
names this ticket's file separately) or, once committed, as a stranded ticket
write that `open-pr`'s freshness gate refuses and `bump` warns about on stderr.
The comparison is one-directional; a branch copy control already absorbed is
silent.

Repair: inspect the branch copy, preserve anything still needed in the primary
ticket, then restore the merge base's copy on the branch and commit:

```sh
git restore --staged --worktree --source=$(git merge-base <control> <branch>) -- <path>
```

Do not rebase to fix it, and do not restore control's copy (it goes stale at
the next transition). In the separate layout, a dirty task/log hunk is a
duplicate only after its content is preserved in the primary ticket or
verified in the authoritative log; discard only confirmed duplicates, never
commit or stash them to pass the clean-tree gate, and never hand-edit
`coga/log.md`. Intentional ticket-body changes, `ticket.py`, and attachments
under `coga/tasks/` can be implementation work and stay in the diff. None of
this applies to the single-checkout layout, where the ticket is the live copy:
commit task/log edits separately from implementation work.

## `coga open-pr <slug>`

The default alias for `coga run open-pr <slug>` (implementation
`coga.open_pr`). Run it from the checkout that owns the live ticket. It reads
`branch:` and `worktree:`, pushes the recorded branch by name, opens the PR,
prints the bare URL, and writes `pr:` back; it fails loud when linkage is
missing or there is nothing to PR. In the single-checkout layout it publishes
the launcher's pending log append, excludes live task, log, and recurring
state from its clean-tree gate, requires at least one committed non-generated
path (`_single_checkout_publishable_paths`), and publishes its `pr:` write to
control only. The PR step declares `requires: pr`. Publication guarantees are
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
the assist or blocking merges, `autoclose-merged` should name unresolved,
reply-less threads report-only. That detection is not shipped yet (ticket
`autoclose-should-name-unanswered-review-threads-on`).

Reading rules: a ticket still on `review` with a merged PR is not backlog
(autoclose closes it on its next run); count only open PRs as the live queue.
A measurement over retired tickets and merged PRs should gate on a closed time
window, never on an empty live queue, which normal throughput never produces.
