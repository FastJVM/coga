---
name: coga/internals/pr-publication
description: What `coga open-pr` (the `open-pr` recipe behind the `requires: pr` gate) must prove and in what order — the checkout gate, the by-name branch and sandbox-clone checks, the non-empty guard, freshness and stranded-ticket checks, the leased push, and where the `pr:` record is published.
---

# PR publication (`coga open-pr`)

The `requires: pr` gate itself is a data check run by `coga bump`
(`coga/lifecycle`): it passes once `## Dev` records `pr:`. This leaf is what
produces that record. `coga open-pr <slug>` is the default alias for the
registered recipe `coga run open-pr <slug>` (`src/coga/open_pr.py`). Stdout
carries only the bare PR URL, so `$(coga open-pr <slug>)` captures it; every
refusal goes to stderr and exits 2, so the gate stays unmet. Exactly one task
argument is accepted.

## Checkout gate (`_checkout_mode`)

open-pr runs from the launch checkout on the control branch, where the live
ticket is, and refuses any other branch. The launch checkout boundary puts a
launched step on control before it starts, and a manual session returns
itself ([dev/checkouts](../../../dev/checkouts/SKILL.md)), so there is no
feature-branch mode, and a sandbox clone's stale ticket copy can never be
updated.

## Checks, in order

1. The ticket is not terminal; `## Dev` has a usable `branch:` (not
   `(`-prefixed). Without `worktree:` (or with one naming this checkout, left
   by the retired single-checkout layout) the branch is checked by name as
   `refs/heads/<branch>`, which must exist locally. With a recorded sandbox
   clone the checks run inside it: the directory must exist, be on that
   branch, and be clean; dirt on the live ticket's own file gets a
   restore-don't-commit remediation, since committing it strands a duplicate.
2. At least one commit ahead of the base (local ref, else `<remote>/<base>`).
3. Freshness: `github_preflight.check_branch_contains_control(head=...)`
   fetches control into its remote-tracking ref and reads that ref, not
   `FETCH_HEAD`. Only non-overlapping generated Coga state is accepted as
   drift, reported on stderr.
4. An unsafe overlap on the live ticket's own file is reported as a stranded
   ticket write, not ordinary staleness: `stranded_task_state_paths` (run
   against `FETCH_HEAD`) says whether control ever absorbed the branch's
   blob, and the remediation restores the merge base's copy on the branch and
   merges control, never a rebase.
5. `gh` auth for the remote host, before anything is pushed.
6. Prepare presentation from the pinned head and merge base; check any existing
   PR for presentation conflicts and the expected base (see below). Push with `--force-with-lease` pinned to the remote OID observed just
   before, so a rebased retry publishes but a concurrent remote update is
   refused.
7. Refresh an open PR for the branch (running `gh pr ready` on a draft), or
   `gh pr create --base <control> --head <branch>`.
8. Write `pr:` under `## Dev` with `update_blackboard_under_barrier`, a
   byte splice under the state lock. A replaced stale link is noted on
   stderr.

## Where the record lands

The `pr:` write lands in the control checkout's live ticket, and the CLI exit
sweep publishes it. The successful `requires: pr` bump and the teardown usage
record also land on control only; nothing publishes to the feature branch.

## Bump's stranded-write advisory

Before a forward transition, `coga bump` runs the same stranded comparison
between `refs/heads/<control>` and `refs/heads/<branch>`, and prints a
`[bump]` note on stderr. It never blocks, writes, or changes the exit code,
and stays silent when this checkout is on the recorded branch, when
`worktree:` resolves to this checkout (both left by the retired
single-checkout layout), or when any probe fails.

## Presentation and review-depth rubric

The preparation agent chooses an advisory depth; the owner always decides
whether to merge. Titles use `[<depth> · A:<author> R:<reviewer>] <change>`.
Use actual session/tool identities and receipts, never ticket assignments or
the GitHub publisher. `unknown` means unavailable evidence, `none` means no
review, and `<name>(self)` distinguishes self-review from independent review.
The complete title stays within GitHub's 256-character limit: retain the
prefix and shorten an oversized change title with an ellipsis. The full change
title remains in the body, and the literal ticket snapshot stays unshortened.

| Depth | Judgment and representative evidence | Example title |
| --- | --- | --- |
| `merge` | Small, low-risk, fully understood change; independent review returned on this diff, applicable checks passed, no unresolved concerns or deviations. Tests alone never suffice. | `[merge · A:codex R:claude] Fix help-text typo` |
| `skim` | Bounded, understood change; read the description for a tradeoff or limitation. Explain why the recorded verification suffices; disclose self-review and justified omissions. | `[skim · A:claude R:codex] Clarify retry diagnostics` |
| `deep` | Inspect the diff: significant behavior/risk, uncertainty, unresolved findings, failed/pending checks, absent review or missing evidence. | `[deep · A:codex R:none] Change PR publication behavior` |

A typo example can use a passed rendered-help comparison with a reason the
runtime suite is inapplicable. The diagnostics example can use passed focused
error-path tests and a completed independent review, with broader tests omitted
because execution behavior is unchanged. The publication example warrants deep
review even with green tests because it changes evidence and overwrite rules;
if independent review was not performed, say why. These are examples of agent
judgment, not a risk classifier in Python. Workflow test/review obligations
remain in force; publication adds no universal suite gate.

## Preparation record

The last judgment step reads this section and writes one fenced `yaml` mapping
under `## PR` on the blackboard (ticket-body `## PR` is a legacy location).
Implement records actual authorship and checks; the final review step refreshes
it after the final freshness/rebase pass, fixes, and required checks. Prepare
the record last so its head/base and receipts describe the resulting revision.
Design approval is not code review. Do not copy a
configured identity, infer execution from a planned command, or re-stamp an old
receipt. Resolve the full feature OID with `git rev-parse <branch>` and the
reviewed diff base with `git merge-base origin/main <branch>`. Every executed
check and review has its own `head` and `base`; omit those only for `not-run`.

```yaml
title: Explain retry failures without changing retry behavior
author: claude
author_evidence: Implement session used Claude; see implement handoff.
head: <full feature commit OID>
base: <full merge-base OID>
depth: skim
rationale: Bounded diagnostics change; read the description for the wording choice.
implementation: Adds the exhausted-attempt count to the existing diagnostic.
deviations: None; retry behavior is unchanged.
limitations: No interactive terminal rendering check; plain stderr only.
files:
  src/retry.py: Expose the attempt count in the failure diagnostic.
  tests/test_retry.py: Cover exhausted retries and unchanged successful retries.
review:
  reviewer: codex
  kind: independent
  status: passed
  head: <full reviewed feature commit OID>
  base: <full reviewed merge-base OID>
  detail: Codex review returned with no unresolved findings.
checks:
  - command: python -m pytest tests/test_retry.py
    status: passed
    head: <full tested feature commit OID>
    base: <full tested merge-base OID>
    detail: 12 passed.
  - command: python -m pytest
    status: not-run
    detail: Workflow permits focused checks; only diagnostic wording changed.
```

`files` maps every path in the actual base-to-head diff to why it belongs,
including both old and new names for a rename. Identical explanations can
repeat. `review.kind` is `independent`, `self`, or `none`; check/review status
is `passed`, `failed`, `pending`, or `not-run`. Every receipt needs a detail
(result/counts or reason for omission). With no independent review, use self
or none and explain why; do not turn an absent tool into a passed review.

The formatter enumerates paths using Git's NUL-delimited rename-aware diff.
The file table shows only each path and its change type (`M`, `A`, `D`, or the
rename/copy status). Per-file explanations stay in preparation as coverage
evidence; they are not repeated in a Why column. Missing preparation paths
are reported as unexplained; extra prepared paths are reported as outside
the current diff. The body starts with
the recommendation/rationale, then authorship/review, implementation,
deviations/limitations, every file, and actual check receipts. Checks are a list:
each result or omission reason comes first, with its command in a separate
fenced shell block below, so long commands do not squeeze the explanations
into table columns. A separate collapsible section renders the ticket title
and the complete Description and Context as Markdown, preserving their source
text, excluding frontmatter, blackboard and PR preparation. The snapshot has no
outer code fence: its headings, lists, links and own code blocks render normally.
Snapshot extraction happens at publication.
The closure marker remains machine-readable outside that snapshot.

Missing/unstructured preparation publishes a `deep` fallback with unknown
identity and explicit missing implementation, file, test and review evidence.
Legacy free-form `## PR` prose is shown as unverified implementation text,
never as check or review evidence. An empty blackboard `## PR` does not shadow
a populated ticket-body one. Malformed YAML or fields refuse with a repair
message. A top-level head/base mismatch is a visible stale-preparation gap that
forces `deep` but keeps the prepared explanations; each receipt is judged
against its own head/base, and stale ones are displayed as historical, not as
verification of the current diff. An `independent` review whose reviewer equals
the author is shown and judged as self-review. Missing or stale evidence, unexplained paths,
and failed/pending checks force `deep`; `merge` also requires a passed independent
review and at least one passed applicable check. Reasons for unrun checks stay
visible; deciding applicability remains the preparation agent's job.

## Updating an existing PR

New bodies wrap generated content in `coga:pr:v1` HTML comment markers with
SHA-256 digests of the generated title and content. These are change detectors,
not authentication. LF and CRLF line endings compare equally; other generated
content edits still conflict. Human notes outside the marked region retain
their exact bytes, including line endings, during updates.
On reuse, title/body are fetched: unchanged generated content is refreshed,
including the ticket snapshot and evidence, before a draft is readied or `pr:`
is recorded. An unchanged rerun does not edit. An existing PR targeting another
base refuses because the prepared comparison would not describe its diff.

An unmarked PR from before the markers is adopted when its title is still the
plain ticket title Coga used to publish: the generated region is placed first
and the entire old body is kept below it as human-owned notes, so nothing is
lost and later reruns refresh only the region. An unmarked PR whose title a
human changed, a modified generated title, or a modified/malformed generated
region refuses instead of silently keeping stale text or overwriting human
edits. Reconcile with the owner: preserve wanted human prose outside the
markers, move intended generated changes into `## PR`, and restore the last
generated title/region (for an unmarked PR, the ticket title) before
rerunning. There is no force-overwrite flag. Resolve detected
conflicts before pushing. Lookup uses `gh pr view <branch>`, whose bare-branch
finder excludes same-named fork heads. Only its explicit branch-not-found
response or a valid closed/merged PR proves no open PR exists. API/auth errors,
malformed or incomplete results, and cross-repository heads refuse before push.
Re-read after
push to catch intervening edits before updating. GitHub has no atomic
compare-and-set for these title/body edits, so
a simultaneous edit after that last read can still race; avoid co-editing
presentation during publication. `gh` edit errors refuse without advancing.
