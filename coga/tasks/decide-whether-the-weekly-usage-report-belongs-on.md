---
title: Decide whether the weekly usage report belongs on coga-important
status: blocked
owner: nicktoper
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
agent: claude
---

## Description

Filed by Dream 2026-W40, Phase 6 (shard ks-19, class stale, target `docs/contexts/coga/important/SKILL.md`). `coga/important` says the important destination is only for notifications that need a human to act ("Nothing else goes there"). This repo's local recurring template `coga/recurring/usage-report` (`ticket.py` ~line 30, `post(cfg, text, important=True, fatal=False)`; its `ticket.md` step 3) posts a weekly token-usage FYI there, a routing the owner chose explicitly in done ticket `agent-usage-report`. Contract and repo disagree; the owner decides which yields: move the usage report to the flow webhook, or record in `coga/important` (and its packaged twin) that a repo may deliberately route a low-volume periodic report there and why. State also whether repo-local templates are in scope for the `coga/notifications/producers` inventory.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Implement attempt 2026-09-30 (megalaunch) — blocked on owner decision

Evidence:
- `docs/contexts/coga/important/SKILL.md` opening: important is "for notifications that need a human to act. Nothing else goes there."
- `coga/recurring/usage-report/ticket.py` (module-level `post(cfg, text, important=True, fatal=False)`, comment "on the important route the owner chose for it") and `ticket.md` step 3 route the weekly FYI to important.
- `docs/contexts/coga/notifications/producers/SKILL.md` inventories only package/bundled producers (e.g. `recurring/phone-home` → flow); no repo-local template rows.

Recommendation (agent, not decided): move the usage report to flow (drop `important=True`, update its `ticket.md` step 3). That keeps `coga/important` strict, needs no twin edit, and matches phone-home (the closest analog: a weekly FYI that goes to flow). Scope the producers inventory to package and bundled producers, and add one sentence saying repo-local templates own their routing in their own `ticket.md`.
Alternative: add a carve-out to `coga/important` and its packaged twin for deliberate low-volume periodic reports.

Also: the start check failed because `coga/tasks/autofix/make-branch-sweep-retirement-survive-an-existing-r/ticket.md` has unstaged edits on main, so no branch was cut.

---

## Blockers

- [ ] [2026-09-30 11:09] [agent:claude] id=20260930T110914 Owner decision needed: should the weekly usage report (coga/recurring/usage-report/ticket.py, important=True) move to the flow webhook (agent recommendation, matches the phone-home precedent), or should coga/important plus its packaged twin get a carve-out for deliberate low-volume periodic reports? And should the coga/notifications/producers inventory cover repo-local templates (recommendation: no, they own their routing in their own ticket.md)? Note: main is also dirty (unstaged edits to autofix/make-branch-sweep-retirement-survive-an-existing-r/ticket.md), so no branch was cut.
