---
slug: ticket-specs-should-cite-symbols-not-line-numbers
title: Ticket specs should cite symbols, not line numbers
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: codex
contexts: []
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
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
secrets: null
step: 2 (peer-review)
---

## Description

Source citations in a ticket body rot before the ticket is implemented, and three independent
tickets each hand-wrote their own warning about it because no skill carries the rule.
`launch-ignores-the-recorded-worktree-stranding-bla` opens its `## Context` with "Citations here
name **symbols, not line numbers**. An earlier draft pinned line numbers twice; both sets had
drifted within days."

Add the rule to `coga/skills/code/design/SKILL.md` and its packaged twin
`src/coga/resources/templates/coga/bootstrap/skills/code/design/SKILL.md` (edit both — they are a
synchronized pair).

## Context

Found by Dream 2026-08-24, Phase 2 knowledge scan — shard-03 and shard-05 reported this
independently from different evidence and were merged at reconciliation.

This run produced fresh evidence for it: Phase 3 shard ca-07 found `docs/cli-extension-audit.md`
citing a stale `cli.py:74-93` range for command registration, which had drifted exactly as
predicted.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: design-cite-symbols
worktree: /home/n/Code/claude/coga-design-cite-symbols

## Implement (2026-09-02)

**What changed.** `coga/skills/code/design/SKILL.md` and its packaged twin
`src/coga/resources/templates/coga/bootstrap/skills/code/design/SKILL.md` gain a new
`Order of operations` step 3, **"Cite symbols, not line numbers"** (old steps 3-6
renumbered to 4-7), plus an Acceptance bullet: "Every source citation in the spec names
a file and a symbol. No claim rests on a bare line number."

The rule carries the two refinements the evidence asked for, rather than a flat ban:
- a range is allowed when it aids navigation of a long module, but only after the symbol
  and only marked as expected to drift;
- best is to state the *relationship* that makes a fact load-bearing ("nothing between
  `spawn_agent_session` and the subprocess chooses the cwd"), because relationships
  survive refactors and coordinates do not.

**Decision — placement.** Its own numbered step, between "Investigate" and "Write the
spec", not a Gotcha. Gotchas are advisory; this is a form rule for the step's actual
output, and pairing it with an Acceptance bullet makes it checkable in `review-design`.

**Decision — verified example symbols.** `git.sync_task_state`, `spawn_agent_session`,
and the anti-example are grepped from live source, so the skill does not itself ship a
stale citation. (`git.py:597-640` appears only as the anti-example; its drifting is the
point.)

**Sync enforcement.** The design pair was *not* in `IDENTICAL_LIVE_PACKAGED_PAIRS` in
`tests/test_packaging.py`, so nothing guarded the "synchronized pair" the ticket depends
on. Registered it. New `tests/test_code_design_skill.py` asserts the rule's content,
mirroring `tests/test_code_implement_skill.py`.

**Tests.** `python -m pytest` in the feature worktree: 2203 passed, 1 failed.
The one failure is `tests/test_packaging.py::test_wheel_includes_bootstrap_batteries`,
which fails identically on unmodified `main`: the repo `.venv` has no `pip`, so the test's
`python -m pip wheel` subprocess cannot run. Environmental, not caused by this change.
No `example/` fixture carries a `code/design` copy, so no fixture update was needed.

## Adjacent, not fixed here

`coga/tasks/no-rule-says-ticket-context-must-cite-symbols-not.md` (status `draft`) is the
sibling of this ticket, from the same Dream scan. It targets the *ticket-authoring* skill
`bootstrap/ticket`, and explicitly leaves open "whether this belongs in `bootstrap/ticket`
alone, or also in `code/design` and in the ticket `_template`". This ticket answers the
`code/design` half. Whoever picks that one up should treat `code/design` as done and decide
only on `bootstrap/ticket` and `_template`; the wording here is reusable.
