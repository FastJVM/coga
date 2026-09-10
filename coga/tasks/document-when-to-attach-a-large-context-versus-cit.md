---
title: Document when to attach a large context versus cite it for direct reading
status: draft
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
step: 1 (implement)
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
