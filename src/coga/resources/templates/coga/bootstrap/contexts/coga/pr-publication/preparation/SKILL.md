---
name: coga/pr-publication/preparation
description: How a PR is presented — the advisory review-depth rubric and title format, the blackboard `## PR` preparation record and its receipts, and how `coga open-pr` formats the body and forces `deep` on missing or stale evidence.
---

# PR presentation and preparation record

Part of [coga/pr-publication](../SKILL.md).

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
The section holds only that fence up to the next `##` heading; any prose,
horizontal rule, or second block makes `coga open-pr` refuse with "use one
complete fenced yaml mapping under ## PR".
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
