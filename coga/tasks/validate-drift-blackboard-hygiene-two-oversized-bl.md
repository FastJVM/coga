---
title: 'validate-drift: blackboard hygiene — two oversized blackboards and one unsynthesized
  draft blackboard'
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

Filed by Dream 2026-W41, Phase 6, from Phase 1 validate-drift's PR Proposal bucket. These need the owning ticket's author or owner to choose, so Dream files them here instead of editing another ticket's blackboard.

validate-drift: large-blackboard
validate-drift: unsynthesized-draft-blackboard

Members this run (`coga validate --json` is the live member list):
- launch-locks/ticket-ownership-lock — large-blackboard (warn): 32.9 KiB blackboard (threshold 32.0 KiB). Ticket is in_progress; its owner should apply the coga/blackboard bloated-blackboard remedy (directory form; dated evidence to sibling attachments; superseded material to an unattached context; keep ## Dev and ## Blockers in place; move, do not delete).
- reconcile-recurring-wrapper-tty-admission-guidance — large-blackboard (warn): 54.0 KiB. Ticket is done with a recorded checkout (retirement debt); `coga retire reconcile-recurring-wrapper-tty-admission-guidance` removes it, which is likely the right remedy instead of trimming.
- marketing/readme-top — unsynthesized-draft-blackboard (error): a draft whose blackboard carries a 2026-10-01 'Clean-install coordination' note written by the clean-install run. Decision needed: synthesize the durable part into the ticket body, or move it under `## Production notes` as an intentional launch note. Do not discard it.

Done when the class is empty in `coga validate --json`, or the accepted decision (tag, decision, rationale, scope) is recorded in the appropriate context before closing with warnings remaining.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
