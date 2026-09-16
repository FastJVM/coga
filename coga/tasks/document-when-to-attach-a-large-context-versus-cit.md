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
step: 2 (peer-review)
launch_generation: pending:7cff53e1-4e50-4e2c-ad27-66423685f035
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
