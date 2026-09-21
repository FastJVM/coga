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
`coga/log.md` with the template's `report.py` — total tokens and sessions,
the four token categories, a per-model split, the unknown-session floor — and
posts it once to the important Slack route with `fatal=False`, so a delivery
miss is reported without leaving the period `in_progress`. The same text is
printed ad hoc by `python coga/recurring/usage-report/report.py`.
