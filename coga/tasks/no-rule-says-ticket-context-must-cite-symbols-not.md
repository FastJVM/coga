---
slug: no-rule-says-ticket-context-must-cite-symbols-not
title: No rule says ticket Context must cite symbols, not line numbers
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
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
secrets: null
step: 1 (implement)
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
