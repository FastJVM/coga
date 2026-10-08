---
title: 'validate-drift: blackboard hygiene — two oversized blackboards and one unsynthesized
  draft blackboard'
status: done
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

## Work log (implement, 2026-10-06)

State-only ticket: every change is Coga state on `main`, so no feature branch, no code diff, and no PR. Live class at start (`coga validate --json`): `large-blackboard` × 4 (launch-locks/checkout-exclusivity-lock 37.1 KiB [new since filing], launch-locks/ticket-ownership-lock 32.9, reconcile-recurring-wrapper-tty-admission-guidance 54.0, recurring/dream 51.5). `unsynthesized-draft-blackboard` was already empty, so marketing/readme-top had been resolved elsewhere.

- **launch-locks/ticket-ownership-lock, launch-locks/checkout-exclusivity-lock**: applied the coga/blackboard remedy. Converted both to directory form and moved each `## Design (step 1, …)` section verbatim (diff-checked against HEAD) to sibling `design.md`, which opens with an HTML comment recording the move. The blackboard keeps a same-named `## Design` pointer section, so evaluator-review references still resolve. Line 55 of each body now points at `design.md`. Open Questions, Decisions, and Evaluator review stay inline because they are the inputs to the review-design owner gate. Before → after: 32.9 → ~11.8 KiB and 37.1 → ~11.9 KiB; neither is flagged any more. Published in `0342c8f4c Sync coga state`.
- **reconcile-recurring-wrapper-tty-admission-guidance** (done; checkout and branch already gone): ran `coga retire … --no-launch`, which created `retire-reconcile-recurring-wrapper-tty-admission-guidance` (active). Running it extracts the pending K39 knowledge and deletes the ticket, which clears the warning. Not launched from here (nested launch is forbidden).
- **recurring/dream**: not trimmed. It holds Dream's per-run report, its phase writers replace those sections every firing, and coga/period-task says to own only your keys. Filed draft `dream-s-own-blackboard-trips-large-blackboard-ever` for the owner decision (attachment vs exemption vs accepted warning). Consider that member handed off.

Remaining before close: the reconcile warning, which clears when the retire task runs. Blocked on that task.

## Already satisfied (close, 2026-10-08)

- reconcile-recurring-wrapper-tty-admission-guidance: the retire task is `done` and the ticket is deleted. It is no longer flagged.
- launch-locks/ticket-ownership-lock and checkout-exclusivity-lock: not flagged (fixed 2026-10-06).
- marketing/readme-top: `unsynthesized-draft-blackboard` is empty.
- Remaining `large-blackboard` member: recurring/dream (51.5 KiB). It is an accepted residual handed off to draft `dream-s-own-blackboard-trips-large-blackboard-ever`, which owns the attachment/exemption/accept decision. Dream rewrites its own report sections every run, so trimming it here would just be overwritten.

---

## Blockers

- [x] [2026-10-06 16:54] [agent:claude] id=20261006T165439 Waiting on task retire-reconcile-recurring-wrapper-tty-admission-guidance (created by coga retire --no-launch): launching it retires the 54 KiB reconcile-recurring-wrapper-tty-admission-guidance blackboard, the last large-blackboard member this ticket owns. The launch-locks members are fixed. recurring/dream is handed off to draft dream-s-own-blackboard-trips-large-blackboard-ever. Once the retire task finishes, close this ticket with coga mark done.
  resolved: [2026-10-08 11:22] [human:nicktoper] Retire task retire-reconcile-recurring-wrapper-tty-admission-guidance is done and the reconcile ticket is deleted; coga validate --json (2026-10-08) shows only recurring/dream under large-blackboard, owned by draft dream-s-own-blackboard-trips-large-blackboard-ever. Close this ticket.

---

## Blocker reminders

- 3963fb99f82c last_reminded: 2026-10-07 11:24
