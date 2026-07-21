---
slug: commands-as-tickets-open-pr-pilot
title: 'Commands as tickets: open-pr pilot'
status: active
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
- coga/architecture
- coga/principles
- coga/codebase
- dev/code
skills: []
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 1 (design)
---

## Description

Pilot the "commands as tickets" direction using `coga open-pr` as the worked
example, then generalize. The owner's thesis (2026-07-21): everything but
`launch` could in principle be a ticket — the microkernel should shrink to
launch + the ticket state machine, with verbs living as launchable
ticket/skill work. open-pr is deliberately chosen as the *hardest* case: if
it works as a ticket, the pattern generalizes; where it can't, the failure is
the finding.

Two deliverables:

1. **The pilot** — make open-pr runnable as a ticket (or stateless launch
   target), solving the structural problems listed in Context, with the
   `requires: pr` bump gate still enforced.
2. **The generalization** — from what the pilot proves, write the rules for
   which remaining commands follow (including whether read-only surfaces —
   `status`, `show`, `validate`, `usage` — become stateless launch targets),
   and amend the microkernel policy text accordingly.

This is a co-design ticket: the owner launches it attended and shapes the
design in-session with the agent.

## Context

Origin: review-design discussion on
`agree-the-core-vs-skills-move-list-then-execute` (2026-07-21). That ticket
lands the three recipe moves + microkernel policy docs and rules open-pr
stays-core *pending this pilot* — this ticket may amend the policy text that
ticket lands.

History that must inform the design (the #517 → #585 oscillation):

- PR #517 moved `open_pr.py` into the `code/open-pr` skill.
- PR #585 reversed it: `code/open-pr` became an *agent step* that calls a
  deterministic core `coga open-pr` command; the completion gate moved into
  `coga bump` as declarative `requires: pr`; the command owns
  control-checkout enforcement and lease-safe rebase retries. Read that PR
  before proposing a third shape — the design must say explicitly why the new
  shape won't oscillate back.

Structural problems the design must solve (identified 2026-07-21):

1. **Argument channel** — open-pr operates *on another ticket* (reads its
   blackboard `branch:`/`worktree:`, writes `pr:` back). Launch targets take
   no arguments today; the alternatives are parameterized launches (new
   design) or a machine-authored ticket per invocation (sprawl for a
   30-second verb).
2. **Nested launch** — the `code/open-pr` step runs mid-workflow, inside a
   supervised session; "don't `coga launch` from inside a launch" is
   currently a hard prohibition. Possible wedge: script-mode nested launches
   are already sanctioned (a script step's launch releases its session via
   the slug-scoped sentinel).
3. **Write ownership** — a separate open-pr ticket's session and the code
   ticket's session would both write the code ticket's `ticket.md`; the
   divergent-writers mode "status is the signal" tolerates would become the
   normal path for every PR.
4. **Kernel residue** — the `requires: pr` gate (in `bump`) and the
   branch/PR parsers (shared infra in `autoclose.py`) stay core regardless;
   be honest in the design about how much actually leaves.

Out of scope: the three recipe moves and policy-doc landing (owned by
`agree-the-core-vs-skills-move-list-then-execute`); changing `bump`'s
ownership of step gates.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
