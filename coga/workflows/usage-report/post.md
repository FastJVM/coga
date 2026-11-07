---
name: usage-report/post
description: One-step lifecycle for the usage-report recurring task's deterministic half.
steps:
  - name: post
    skills:
      - coga/usage-report/post
    assignee: agent
---

## post

Script-backed recurring task. `coga launch` runs the period task's reserved
`ticket.py`, which renders last completed ISO week's agent token usage from
`coga/log.md` with the template's `report.py` — a header naming the
configured user, total tokens split into non-cache-read and cache-read
amounts, sessions, the four token categories, labeled per-agent and per-model
splits, the unknown-session floor — and
posts it once to the important Slack route with `fatal=False`, so a delivery
miss is reported without leaving the period `in_progress`. The same text is
printed ad hoc by `python coga/recurring/usage-report/report.py`.

## No other-agent code review

This is the one-step lifecycle of a recurring task's deterministic
half. It produces no code, so no `other-agent` step reviews it.
