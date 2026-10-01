---
title: Name phone-home as the record_failure=False caller after PR 911 lands
status: in_progress
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
step: 2 (peer-review)
agent: claude
launch_generation: pending:d5f204e1-fcee-4ea0-9214-da1260c3ffcc
---

## Description

Filed by Dream 2026-W40, Phase 6 (proposal-ownership overlap). `docs/contexts/coga/notifications/failures/SKILL.md` "What reaches `coga/log.md`" says `record_failure=False` is accepted by `post`/`notify` but "no current caller passes it" (Dream shard ks-19, class stale). The shipped `recurring/phone-home/ticket.py` (live and packaged, ~line 240) calls `notification.post(..., fatal=False, record_failure=False)` for its weekly receipt, and `coga/notifications/producers` already documents that. Open PR #911 (branch `slack-oserror-delivery-miss`) edits this file without carrying the fix. After #911 merges or closes, name phone-home's receipt as the current caller and why (a best-effort telemetry receipt that must not dirty `coga/log.md`), in the live and packaged copies. Verify with `python -m pytest tests/test_packaging.py`.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

---

## Blockers

- [x] [2026-09-30 11:09] [agent:claude] id=20260930T110945 Start check failed: /home/n/Code/coga is not a clean main. It has an unpublished, unstaged blackboard edit on another ticket (coga/tasks/autofix/make-branch-sweep-retirement-survive-an-existing-r/ticket.md, the 16-line 'Diagnosis (from recurring/autoclose-merged period agent, 2026-09-30)' section). Please publish (commit+push to main) or discard that edit, then unblock and relaunch. The precondition is met: PR #911 merged 2026-09-29, so the docs fix in coga/notifications/failures (live + packaged) is ready to implement.
  resolved: [2026-09-30 22:35] [human:nicktoper] Resolved by state: the other ticket's Diagnosis section is now published on origin/main, and the checkout is a clean main at origin/main (24e9e1aef). PR #911 merged 2026-09-29. Proceeding with implement.

## Dev

branch: phone-home-record-failure-caller

Plan: in `coga/notifications/failures` "What reaches `coga/log.md`" (live
`docs/contexts/` + packaged bootstrap copy), replace "no current caller passes
it" with phone-home's weekly receipt (`recurring/phone-home/ticket.py`
`_receipt`) and why: best-effort telemetry receipt from a bounded worker whose
failure must not affect capture or completion, so a miss must not dirty
`coga/log.md`.

## Implement handoff (2026-09-30)

- Commit 0103033f8 on `phone-home-record-failure-caller` (pushed, rebased on
  origin/main 86ae9ca7f, which was only a Coga state sync).
- Changed `coga/notifications/failures` "What reaches `coga/log.md`" in
  `docs/contexts/` and the packaged bootstrap twin (byte-identical): replaced
  "no current caller passes it" with the phone-home weekly receipt
  (`ticket.py` `_receipt`) and its reason, linking `coga/telemetry`.
- Verified: `pytest tests/test_packaging.py` 23 passed; full suite 3135 passed.
- No code or fixture change; `coga/notifications/producers` already named it.
