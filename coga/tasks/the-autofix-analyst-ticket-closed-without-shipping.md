---
slug: the-autofix-analyst-ticket-closed-without-shipping
title: The autofix analyst ticket closed without shipping any of its three defects
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

`coga/tasks/fix-the-autofix-analyst.md` is `status: done`, but none of the
three fixes its `## Description` scoped ever reached `src/coga/recurring_autofix.py`.
Verified in the tree during this Dream run:

1. **Both labelled streams in `AutofixUnavailable`.** The ticket asks for the
   stderr *and* stdout streams to be included instead of collapsing them.
   `src/coga/recurring_autofix.py` still reads
   `detail = (result.stderr or result.stdout or "").strip()` — the principle-6
   "loudly wrong" error detail the ticket calls out by name.
2. **`stdin=subprocess.DEVNULL` on the analyst `subprocess.run`.**
   `grep -n stdin src/coga/recurring_autofix.py` returns nothing.
3. **An `[autofix].agent` config key read by `_analyze_agent` before the
   `default_agent()` fallback.** `_analyze_agent` still goes straight from
   `agent_override` to `cfg.default_agent()`, and `src/coga/config.py` has no
   `[autofix]` table.

What actually shipped under this ticket (its blackboard `## Implemented`, PR
#724) is a different change entirely — the Claude subscription auth fallback —
which the Description never asked for. The ticket was marked done on the
strength of that unrelated work, and closing it removed the surface that would
have kept the three defects visible.

A partial prior record exists and has not helped: Dream 2026-W36 captured
defects 1 and 2 as backlog item 8 of
`coga/tasks/dream-2026-w36-extract-backlog-18-findings-phase-4.md`, correctly
flagging them as "a bug carrier, not just knowledge — it likely deserves its own
ticket". That ticket is still `status: draft` and unactioned a Dream cycle
later, and it never captured defect 3.

## Context

This is a real bug ticket carrying all three defects, not another backlog
line — the backlog-line route has already been tried and demonstrably did not
drain.

Re-verify each defect against `src/coga/recurring_autofix.py` and
`src/coga/config.py` before implementing; they were confirmed on 2026-09-08 but
line-level details will move.

Two adjacent decisions for the review step:
- whether `dream-2026-w36-extract-backlog-18-findings-phase-4` should be closed
  or narrowed once this ticket carries its item 8 (note item 2 of that same
  backlog — the validate-before-write rule — is also unlanded, and item 1's
  `append_report` duplication still exists as three private copies in
  `skill_update.py`, `dream_validate_drift.py` and `dream_cleanup_orphan_markers.py`);
- whether `fix-the-autofix-analyst` should be reopened instead of superseded by
  this ticket. It is done with a recorded feature checkout, so it is retirement
  debt; reopening a retired-shape ticket is an owner call.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
