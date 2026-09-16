---
title: Document when to attach a large context versus cite it for direct reading
status: in_progress
owner: nicktoper
agent: claude
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 4 (review)
---

## Description

Three independent tickets each decided, on their own, to leave the largest
contexts off their `contexts:` frontmatter and instruct the reader in prose
instead — and each wrote its own paragraph explaining why.
`run-recurring-agent-templates-off-the-control-bran` and
`reuse-the-existing-control-worktree-for-recurring` both say
"`coga/contexts/coga/recurring/SKILL.md` is deliberately not attached — at
~9.2k tokens it dominates the composed prompt for a handful of facts. Read it
directly"; `detect-stranded-ticket-writes-across-checkouts` says "The
`coga/sync` context (57.8 KiB, not attached — read it in the repo)".

The sizes are real: `coga/contexts/coga/sync/SKILL.md` is ~67 KB,
`coga/contexts/coga/architecture/SKILL.md` ~74 KB, and
`coga/contexts/coga/recurring/SKILL.md` ~54 KB, so a two-context ticket can
spend over 100 KB of prompt to carry a handful of facts.

Nothing acknowledges the tradeoff. Neither the prompt-composition section of
`coga/contexts/coga/architecture/SKILL.md`, nor `coga/contexts/coga/principles/SKILL.md`,
nor the `bootstrap/ticket` authoring skill names a size threshold or blesses
the read-it-directly workaround, so every ticket author re-derives it and the
inconsistency is invisible at review.

## Context

Write the practice down where prompt composition is defined: when to attach a
context versus cite it for direct reading, and — importantly — that citing it
does **not** relieve the same-PR context-update rule.

Related but distinct: the parked draft
`coga/tasks/v2/enforce-a-prompt-token-budget-in-compose` proposes a mechanical
budget in `compose`. This ticket is the authoring-guidance half and does not
depend on it.

A neighbouring Dream finding (`launch-internals` quoting its own byte size as
"~19 KiB" when the file is 29,083 bytes) shows why a documented threshold should
avoid pinning literal per-file sizes that rot.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

pr: https://github.com/FastJVM/coga/pull/821
branch: attach-vs-cite
worktree: /home/n/Code/claude/coga-attach-vs-cite

## Implement — findings and decisions

- Owner of the new rule: `coga/contexts/coga/architecture/SKILL.md`, new
  `### Attach or cite` subsection at the end of `## Prompt composition`
  (immediately before `## Where a fact lives`). Packaged twin
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/architecture/SKILL.md`
  mirrored byte-for-byte; `tests/test_packaging.py` passes against the
  worktree package (`PYTHONPATH=<worktree>/src`, since the venv's editable
  install resolves `coga` from the primary checkout otherwise).
- The rule as written: attach when the step must have the facts without being
  told to look (same test as fact ownership); cite when the step uses a
  handful of facts from a context that would outweigh every other layer
  combined, or when the ticket edits the context. Threshold is measured with
  `coga launch <slug> --prompt-report` (verified it works on a draft) — no
  literal per-file sizes anywhere in the rule, per the `launch-internals`
  Dream finding.
- Citation form fixed: one sentence naming ref + path, "cited, not attached",
  sections to read, then the needed facts by module+symbol; no size/token
  justification in the ticket.
- Stated explicitly that citing does not relieve the same-PR sync rule; the
  `Where a fact lives` sentence about attaching the owner now says "attaches
  or cites the owner per `Attach or cite`".
- `bootstrap/ticket` (package-only skill, no live twin) got one bullet in the
  selection contract pointing at the owner plus one evaluator-checklist item.
  `coga/principles` left untouched: the rule is composition guidance, not a
  non-negotiable, and one owner per fact.
- Docs checked (`docs/README.md`, `docs/concepts.md`, `docs/vision.md`): only
  summaries of "contexts are composed when attached"; no restatement to fix.
- The three cited tickets (`run-recurring-agent-templates-off-the-control-bran`,
  `reuse-the-existing-control-worktree-for-recurring`,
  `detect-stranded-ticket-writes-across-checkouts`) were not rewritten — they
  are live tickets with their own lifecycle; the rule now governs new tickets.
- Full suite: 2561 passed. Branch rebased on current `origin/main`
  (no new commits). Not pushed; no PR.

## Peer review

- `codex review --base main` **returned** in the recorded worktree with no
  actionable findings. Its targeted packaging, composition, and prompt-report
  checks passed: 44 tests.
- Additional manual review found that a report omits a context already left
  off `contexts:`, and that the CLI report performs the normal state sweep.
  The guidance now measures with candidate refs present, names the control
  checkout/publication precondition, and offers `compose.compose_prompt_report`
  on an in-memory ticket copy for read-only comparisons. Both authoring-skill
  measurement pointers lead to that procedure.
- Because all steps inherit one ticket-wide context list, the attach/cite
  decision and evaluator check now account for every planned step. The example
  no longer implies that changing specified behavior alone requires attachment.
- Manual composition probe: compared implement and peer-review prompts with
  `coga/architecture` omitted and present on in-memory copies; only the latter
  reports include its context layer. Ticket bytes stayed unchanged. This diff
  changes prose only; no terminal, pager, or Slack rendering surface changes.
- `git fetch origin main && git rebase FETCH_HEAD` completed without conflicts
  onto `9947daea`. `git diff --check`, direct architecture-twin `cmp`, and
  `coga validate --task document-when-to-attach-a-large-context-versus-cit`
  passed. Full suite against the feature source: **2561 passed** in 184.44s;
  the exact command is in the PR test plan below.
- Corrections committed as `468f31fb` (`peer-review: clarify context
  measurement`). Final feature worktree is clean, two commits ahead of the
  fetched `origin/main` and none behind. PR body is ready below; no findings
  remain open.

## Open PR

- `coga open-pr` run from the primary control checkout on `main`; origin/main had advanced only through non-overlapping task/log state, so the branch published without a rebase. PR #821 opened and `pr:` recorded under `## Dev`.

## PR

Ticket authors now have a shared rule for attaching a context or citing its
path and relevant sections for direct reading. The architecture contract uses
current prompt proportions across workflow steps, documents how to measure
candidates safely, and keeps same-PR context updates mandatory. The bundled
ticket-authoring checklist links to that rule, and the packaged architecture
copy stays synchronized.

Test plan: `PYTHONPATH=/home/n/Code/claude/coga-attach-vs-cite/src /home/n/Code/claude/coga/.venv/bin/python -m pytest` (2561 passed, including packaging/twin checks); `git diff --check`; `coga validate --task document-when-to-attach-a-large-context-versus-cit`.
