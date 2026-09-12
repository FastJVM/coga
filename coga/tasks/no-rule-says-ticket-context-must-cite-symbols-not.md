---
title: No rule says ticket Context must cite symbols, not line numbers
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
---

## Description

Tickets keep pinning `src/coga/` line numbers into `## Context` as "verified code facts",
and those citations decay within days — but no context, skill, or workflow states the
rule. Grepping `coga/contexts/`, `coga/skills/` and `coga/workflows/` for "line number"
returns nothing.

`bootstrap/ticket`'s SKILL.md is the file that owns what goes into a `## Context` body,
and it says only *which* facts to copy, never in what form.

Deliverable: a short rule in that skill's `## Context` guidance —

- cite module plus symbol (`git.sync_task_state`, `step_gate.gate_unmet_reason`), never a
  bare line number;
- when a range is genuinely needed, name the symbol first and mark the range as an aid;
- state the *relationship* that makes the fact load-bearing rather than its coordinates,
  since the relationship is what survives a refactor.

The design judgment: whether this belongs in `bootstrap/ticket` alone, or also in
`code/design` (which writes ticket specs) and in the ticket `_template`.

## Context

Citations here name symbols and files, not line numbers — deliberately.

**Two independent tickets show the cost, and show that stating it once did not carry.**

In `coga/tasks/launch-ignores-the-recorded-worktree-stranding-bla.md` (done) the cold
evaluator tabulated **nine stale citations** against source ten days newer, one of them
naming the wrong module entirely (a `commands/bump.py` line cited for a `sync_task_state`
call that lives in `src/coga/bump.py`), and called it **blocking**. The evaluator also
noted that the only two load-bearing claims survived precisely because they were stated as
symbol relationships — "no one chooses the cwd", and "gate-checked copy == synced copy, by
construction, both off the same `TaskRef`". The ticket was then rewritten to open with:
"Citations here name **symbols, not line numbers**. An earlier draft pinned line numbers
twice; both sets had drifted within days."

The follow-up `coga/tasks/detect-stranded-ticket-writes-across-checkouts.md` shows the
lesson did not carry: it hedges "line numbers drift — re-verify before relying on them"
and then pins roughly twenty of them anyway.

That second data point is the argument for writing the rule down rather than relying on
each author to rediscover it: the same person, one ticket later, hedged instead of
complying.

Note the tension a designer should resolve: a bare symbol name is sometimes harder to
locate than a line number in a 3,000-line module. The rule should say what to do then
(name the symbol, then give the range as a navigational aid, and expect the range to rot)
rather than pretending the tradeoff does not exist.

Filed by Dream 2026-W36, Phase 2 knowledge scan (shard `ks-04`), classified `gap`.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Findings (implement, session 1)

- `bootstrap/ticket` SKILL.md exists **only packaged**:
  `src/coga/resources/templates/coga/bootstrap/skills/bootstrap/ticket/SKILL.md`.
  No live twin under `coga/skills/`, so one edit; its guard test is
  `tests/test_bootstrap_ticket_skill_template.py`.
- `code/design` (`coga/skills/code/design/SKILL.md`) and the ticket template
  (`coga/tasks/_template/ticket.md`) both have byte-identical packaged twins
  under `src/coga/resources/templates/coga/...` — any edit must land in both.
- The ticket's "grep returns nothing" is slightly off: `code/review-design`
  already says "Cite stable paths and symbol or section names in findings. Do
  not pin a finding only to a line number that will drift." — but that governs
  evaluator *findings*, not ticket `## Context`. Reusing its phrasing keeps the
  two rules recognisably the same rule.
- The second offending ticket (`detect-stranded-ticket-writes-across-checkouts`)
  had its line numbers added during an *implement* step (commit `af35b1c1`),
  not via `bootstrap/ticket`. So a rule that lives only in the interview skill
  would not have reached that author — an argument for also putting it where
  every `## Context` author looks (the template placeholder, `code/design`).

## Dev

branch: cite-symbols-rule
worktree: /home/n/Code/claude/coga
Single-checkout layout: branch created in place in the primary checkout.

## Decisions

- Rule placed in all three homes, full text once: the full "Citing code in
  `## Context`" section lives in `bootstrap/ticket` (after the context
  selection contract); `code/design` step 3 and the ticket `_template`
  `## Context` placeholder carry a one-sentence form pointing back to it.
  Reason: the second offending ticket was line-pinned from an implement step,
  which only the template would have reached.
- Range example uses a real symbol, `git.sync_task_state` (git.py is ~7,000
  lines today), so the example itself follows the rule.
- Phrased to match `code/review-design`'s existing findings rule, and the
  section says so, so the two read as one rule.
- Commit `c4086d73`. Verified with
  `.venv/bin/python -m pytest tests/test_bootstrap_ticket_skill_template.py tests/test_packaging.py`
  (19 passed) and the full `.venv/bin/python -m pytest` (2436 passed).
