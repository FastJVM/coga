---
name: coga/pr-publication
description: "What `coga open-pr` (the `open-pr` recipe behind the `requires: pr` gate) must prove and in what order — the checkout gate, the by-name branch and sandbox-clone checks, the non-empty guard, freshness and stranded-ticket checks, the leased push, refreshing an existing PR's generated region, and where the `pr:` record is published; presentation and the preparation record live in its leaf."
---

# PR publication (`coga open-pr`)

The `requires: pr` gate itself is a data check run by `coga bump`
(`coga/lifecycle`): it passes once `## Dev` records `pr:`. This topic is what
produces that record. `coga open-pr <slug>` is the default alias for the
registered recipe `coga run open-pr <slug>`. Stdout carries only the bare PR
URL, so `$(coga open-pr <slug>)` captures it; every refusal goes to stderr
and exits 2, so the gate stays unmet. Exactly one task argument is accepted.

[coga/pr-publication/preparation](preparation/SKILL.md) owns the
review-depth rubric, the blackboard `## PR` preparation record, and how the
PR body is formatted from it.

## Checkout gate

open-pr runs from the launch checkout on the control branch, where the live
ticket is, and refuses any other branch. The launch checkout boundary puts a
launched step on control before it starts, and a manual session returns
itself ([coga/checkouts](../checkouts/SKILL.md)), so there is no
feature-branch mode, and a sandbox clone's stale ticket copy can never be
updated.

## Checks, in order

1. The ticket is not terminal; `## Dev` has a usable `branch:` (not
   `(`-prefixed). Without a sandbox-clone `worktree:` the branch is checked
   by name as `refs/heads/<branch>`, which must exist locally. With a
   recorded sandbox clone the checks run inside it: the directory must
   exist, be on that branch, and be clean; dirt on the live ticket's own file
   gets a restore-don't-commit remediation, since committing it strands a
   duplicate.
2. At least one commit ahead of the base (local ref, else `<remote>/<base>`).
3. Freshness: the branch must contain the freshly fetched control branch.
   Only non-overlapping generated Coga state, exactly `tasks/**` and `log.md`
   under the Coga root, is accepted as drift, reported on stderr. Any other
   control change, including `recurring/**`, contexts, skills, or config,
   requires rebasing or merging control first.
4. An unsafe overlap on the live ticket's own file is reported as a stranded
   ticket write, not ordinary staleness, and the remediation restores the
   merge base's copy on the branch and merges control, never a rebase
   ([coga/checkouts](../checkouts/SKILL.md#stranded-ticket-writes)).
5. `gh` auth for the remote host, before anything is pushed.
6. Prepare presentation from the pinned head and merge base, and check any
   existing PR for presentation conflicts and the expected base (below).
   Push with `--force-with-lease` pinned to the remote OID observed just
   before, so a rebased retry publishes but a concurrent remote update is
   refused.
7. Refresh an open PR for the branch (readying a draft), or create one
   against the control branch.
8. Write `pr:` under `## Dev`. A replaced stale link is noted on stderr.

## Updating an existing PR

Generated content sits between `coga:pr:v1` HTML comment markers carrying
digests of the generated title and content. They are change detectors, not
authentication; LF and CRLF compare equally. Human notes outside the marked
region keep their exact bytes. On reuse, unchanged generated content is
refreshed, including the ticket snapshot and evidence, before a draft is
readied or `pr:` is recorded; an unchanged rerun does not edit. An existing
PR targeting another base refuses, because the prepared comparison would not
describe its diff.

An unmarked PR from before the markers is adopted when its title is still
the plain ticket title: the generated region goes first and the whole old
body is kept below it as human notes. An unmarked PR whose title a human
changed, a modified generated title, or a modified or malformed generated
region refuses instead of keeping stale text or overwriting human edits.
Reconcile with the owner: keep wanted human prose outside the markers, move
intended generated changes into `## PR`, and restore the last generated title
and region (for an unmarked PR, the ticket title) before rerunning. There is
no force-overwrite flag. A failed or ambiguous open-PR lookup (API or auth
error, malformed result, cross-repository head) refuses before push. GitHub
has no atomic compare-and-set for title and body edits, so avoid co-editing
the presentation while publication runs.

## Where the record lands

The `pr:` write lands in the control checkout's live ticket, and the CLI exit
sweep publishes it. The successful `requires: pr` bump and the teardown usage
record also land on control only; nothing publishes to the feature branch.

## Bump's stranded-write advisory

Before a forward transition, `coga bump` runs the same stranded comparison
between the local control branch and the recorded branch, and prints a
`[bump]` note on stderr. It never blocks, writes, or changes the exit code,
and stays silent when this checkout is on the recorded branch or when any
probe fails.

The first `branch:` record is the workflow checkout; multiple tickets may
link to the same branch and PR. Cleanup's ownership rules are in
[terminal owners](../checkout-cleanup/terminal-owners/SKILL.md). Function
names, record parsing, and retired-layout tolerances are in
[coga-dev/internals/git-refresh](https://github.com/FastJVM/coga/blob/main/docs/contexts/coga-dev/internals/git-refresh/SKILL.md#coga-open-pr-source-notes).
