---
title: Name phone-home as the record_failure=False caller after PR 911 lands
status: active
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

Filed by Dream 2026-W40, Phase 6 (proposal-ownership overlap). `docs/contexts/coga/notifications/failures/SKILL.md` "What reaches `coga/log.md`" says `record_failure=False` is accepted by `post`/`notify` but "no current caller passes it" (Dream shard ks-19, class stale). The shipped `recurring/phone-home/ticket.py` (live and packaged, ~line 240) calls `notification.post(..., fatal=False, record_failure=False)` for its weekly receipt, and `coga/notifications/producers` already documents that. Open PR #911 (branch `slack-oserror-delivery-miss`) edits this file without carrying the fix. After #911 merges or closes, name phone-home's receipt as the current caller and why (a best-effort telemetry receipt that must not dirty `coga/log.md`), in the live and packaged copies. Verify with `python -m pytest tests/test_packaging.py`.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

---

## Blockers

- [ ] [2026-09-30 11:09] [agent:claude] id=20260930T110945 Start check failed: /home/n/Code/coga is not a clean main. It has an unpublished, unstaged blackboard edit on another ticket (coga/tasks/autofix/make-branch-sweep-retirement-survive-an-existing-r/ticket.md, the 16-line 'Diagnosis (from recurring/autoclose-merged period agent, 2026-09-30)' section). Please publish (commit+push to main) or discard that edit, then unblock and relaunch. The precondition is met: PR #911 merged 2026-09-29, so the docs fix in coga/notifications/failures (live + packaged) is ready to implement.
