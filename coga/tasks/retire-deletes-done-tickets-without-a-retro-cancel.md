---
title: Retire deletes done tickets without a retro; canceled tickets get one
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
---

## Description

Owner decision 2026-10-13. Done tickets pile up (136 done, 29 canceled): autoclose marks them done and deletes their branch but leaves the branch: line in ## Dev, and Dream's Phase 4 gate only checks that the line is present, so it skips every one (it reports 153 tickets of retirement debt each week). For 119 of them the recorded branch no longer exists. Only manual coga retire drains them, at one agent run per ticket; it has run 5 times ever. New rule: positive learning already landed in the merged PR (the sync rule updates the owning topic in the same PR), and negative learning lives in the ticket or blackboard, usually as the cancellation reason. So (1) coga retire on a done ticket disposes of its checkout and deletes the ticket deterministically, with no retro agent; (2) coga retire accepts canceled tickets and runs the retro on them to extract the cancellation reason and any other negative learning, then deletes; (3) the Dream retirement gate checks whether the recorded branch or worktree still exists (as retire_worklist already does) instead of whether the line is written; (4) update dev/checkout-cleanup, coga/dream and coga/lifecycle, plus packaged twins, in the same PR. Then drain the backlog: plain deletes for done tickets with no live branch, retire for the ~17 with a live branch, and retros for the canceled tickets.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: retire-done-deterministic

## Plan

- `coga retire` on `done`: dispose checkout (same proofs), discharge worklist, then `delete_task` + sync. No retire task, no agent. A kept checkout exits 2 and leaves the ticket (it is the owner record).
- `coga retire` on `canceled`: existing path (dispose, retire task running Retro), Retro extracts the cancellation reason / negative learning.
- Dream Phase 4 gate: done ticket eligible unless its recorded branch/worktree still exists.
- Backlog drain deferred until this merges (it needs the new retire).

## Implement handoff

Branch `retire-done-deterministic` pushed (head d50a13b2c, on origin/main 33435783a). No PR yet.

What changed:
- `src/coga/commands/retire.py`: accepts `done` or `canceled`. Both go through the same checkout disposal + worklist discharge first. `done` → `_delete_done_task`: `run_delete_task` + `git.publish` (`Ticket: <slug> — deleted (retire)`), no retire task, no agent. A kept checkout on a done ticket exits 2 and deletes/creates nothing (ticket stays as owner record; rerun `coga retire`). `canceled` → the old retire-task path unchanged (blocked task on a kept checkout).
- `src/coga/resources/retire.md`: the retire task body is now for a canceled ticket; Retro extracts the cancellation reason / negative learning. Stop condition now "not canceled".
- `bootstrap/skills/retro/done-ticket`: new `### Canceled tickets` section; status gates admit one canceled slug from `coga retire`; "Done is a status, not a receipt" skipped for canceled.
- Dream template (live + twin) Phase 4 gate: done ticket eligible unless its `## Dev` records a **live** checkout (branch still local or on the remote, or worktree dir still present and not a primary). Unanswerable probe = live. Canceled tickets listed as retirement debt.
- Dream Phase 6 routing (decision, flag for review): `done+checkout` findings now get a proposal PR (retire no longer retros done tickets, so nothing else would extract them); `canceled` findings are now listed as retirement debt with no PR (retire's Retro consumes them). Knowledge-scan `source:` definitions updated to match.
- Topics (+ packaged twins): dev/checkout-cleanup (retire section, owner decision 2026-10-13), coga/dream, coga/lifecycle, coga/tickets, coga/extension-model, coga/blackboard.
- Tests: test_retire.py (existing retire-task tests now seed canceled; new done-delete, done-kept-branch, done-worktree+worklist tests); test_dream_worker_templates.py assertions updated.

Not done here — backlog drain (needs this merged first, since it uses the new retire):
1. Done tickets with no live branch/worktree: `coga retire <slug>` (now a deterministic delete) or `coga delete`.
2. Done tickets with a live branch (~17): `coga retire <slug>` from `main`; any that exit 2 kept a checkout and need a hand fix.
3. Canceled tickets (~29): `coga retire <slug>` each (one Retro agent run per ticket).

Note: Dream Phase 4 still runs Retro over eligible done tickets; the ticket only asked to change its gate. Whether Dream should also just delete done tickets is a possible follow-up.

## PR

```yaml
title: Retire done tickets without a retro; run Retro on canceled ones
author: claude
author_evidence: Implement session ran as Claude Code (claude-opus-5-5) under coga megalaunch.
head: d50a13b2c4efb39f7eacc56fe22488d6af45a951
base: 33435783af6d35efa38985058bcd8da2412a0af7
depth: deep
rationale: Changes a destructive lifecycle command (done tickets now deleted with no agent) and Dream's routing of findings; read the Phase 6 routing change.
implementation: coga retire deletes done tickets after checkout disposal and runs Retro only on canceled tickets; Dream's retirement gate checks whether the recorded branch/worktree still exists.
deviations: Dream Phase 6 now opens proposal PRs for done+checkout findings and lists canceled findings as retirement debt (not explicitly in the ticket; follows from the new retire rule). Backlog drain deferred until merge.
limitations: Live-branch probe in Dream is agent-run prose, not code. No manual run of coga retire against real tickets yet.
files:
  src/coga/commands/retire.py: Deterministic delete for done tickets; accept canceled tickets for the Retro task.
  src/coga/resources/retire.md: Retire task body now targets a canceled ticket's negative learning.
  src/coga/resources/templates/coga/bootstrap/skills/retro/done-ticket/SKILL.md: Admit one canceled slug from coga retire and say what to extract from it.
  src/coga/resources/templates/coga/bootstrap/skills/bootstrap/dream/scan/knowledge-scan/SKILL.md: source: definitions follow the live-checkout gate and new routing.
  coga/recurring/dream/ticket.md: Phase 4 live-checkout gate; Phase 6 routing for done+checkout and canceled.
  src/coga/resources/templates/coga/recurring/dream/ticket.md: Packaged twin of the Dream template.
  docs/contexts/dev/checkout-cleanup/SKILL.md: coga retire contract for done vs canceled tickets.
  docs/contexts/coga/dream/SKILL.md: Eligibility and retirement-debt rule.
  docs/contexts/coga/lifecycle/SKILL.md: What retire does after a terminal transition.
  docs/contexts/coga/tickets/SKILL.md: retire accepts done or canceled.
  docs/contexts/coga/extension-model/SKILL.md: Retire-task example now names canceled tickets.
  docs/contexts/coga/blackboard/SKILL.md: Live-checkout wording for flagged done tickets.
  src/coga/resources/templates/coga/bootstrap/contexts/dev/checkout-cleanup/SKILL.md: Packaged twin.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/dream/SKILL.md: Packaged twin.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/lifecycle/SKILL.md: Packaged twin.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/tickets/SKILL.md: Packaged twin.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/extension-model/SKILL.md: Packaged twin.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/blackboard/SKILL.md: Packaged twin.
  tests/test_retire.py: Done-path delete/refusal tests; retire-task tests now seed canceled tickets.
  tests/test_dream_worker_templates.py: Assertions follow the new gate and routing text.
review:
  reviewer: none
  kind: none
  status: not-run
  detail: Peer review is the next workflow step.
checks:
  - command: .venv/bin/python -m pytest -q
    status: passed
    head: d50a13b2c4efb39f7eacc56fe22488d6af45a951
    base: 33435783af6d35efa38985058bcd8da2412a0af7
    detail: 3599 passed in 304.78s.
```
