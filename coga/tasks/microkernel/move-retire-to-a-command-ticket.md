---
title: Move retire to a command ticket
status: in_progress
owner: nicktoper
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 1 (design)
contexts:
- coga/principles
- coga/extension-model
- coga/script-tickets
- coga/launch
- dev/checkout-cleanup
- dev/checkout-cleanup/proofs
- coga/recurring/scheduling
- coga/cli
- coga/codebase
- coga/testing
- coga/packaging
agent: claude
---

## Description

Move `coga retire` out of the package into a `bootstrap/retire` command ticket reached by the alias `retire = "launch bootstrap/retire"`, and let each cleanup ticket's `ticket.md` own what its job does, so an agent reads the description instead of the script. Three parts, in order, one PR: (1) let a script command ticket receive trailing argv, (2) move retire, (3) split `dev/checkout-cleanup` across the three cleanup tickets.

Part 1 is a prerequisite: a command ticket's `ticket.py` runs with no
operands today (`coga/script-tickets`), so `coga retire <slug>` would lose
its slug. Proposed: pass the trailing argv to the script (for example as an
environment variable), the same way agent-backed command tickets get a
`## Launch arguments` block. This is a launch change, so it is a kernel
change; the design step must settle the exact interface.

### Acceptance criteria

- [ ] **Argv:** a script command ticket receives its trailing argv under a
      documented contract in `coga/script-tickets` (live and packaged),
      with tests. Agent-backed command tickets behave as before.
- [ ] **Retire:** `coga retire <slug> [--agent <type>] [--no-launch]` keeps
      its spelling through an `[aliases]` default and keeps its state rule:
      a done ticket is retired deterministically with no agent; a canceled
      ticket gets a retire task. Its exit codes, refusal messages and
      `retires.md` discharge stay the same. `src/coga/commands/retire.py`
      is gone; its single-consumer logic moves unchanged ("No inversion")
      into `bootstrap/retire/ticket.py` (or `src/coga_edge/` if a repo shim
      is needed).
- [ ] **Shared proofs stay core:** `checkout_disposal.py`,
      `branchcleanup.py` and `retire_worklist.py` keep serving retire,
      autoclose and branch-sweep.
- [ ] **Descriptions own their job:** `bootstrap/retire`,
      `recurring/autoclose-merged` and `recurring/branch-sweep` each have a
      `ticket.md` that says what the job does, step by step, for an agent
      to read without opening `ticket.py`. They link the shared safety
      rules instead of restating them.
- [ ] **Topic shrinks:** `dev/checkout-cleanup` keeps only the shared rules
      (the proofs, primary checkouts and other clones, the accepted
      disappearance policy, `/tmp` recovery); the `coga retire` section
      moves to `bootstrap/retire/ticket.md`.
- [ ] `retire` leaves the "Open command placements" table in
      `coga/extension-model` (both copies); `coga/cli`,
      `docs/archive/cli-extension-audit.md` and
      `microkernel/work-orchestration-commands-to-tickets` are updated; live
      and packaged twins match; `tests/fixtures/seeded-repo/` still
      represents the smoke path; tests pass.

## Context

Group: `microkernel/README.md`. Split out of
`microkernel/work-orchestration-commands-to-tickets` on 2026-10-16 (owner
decision in an orient chat), which keeps `megalaunch` and `slack`. One
ticket rather than three because the parts depend on each other in order.

Shape to follow: the `resolve-conflicts` and `address-pr-comments` command
tickets reached by aliases, and the `recurring/autoclose-merged` and
`recurring/branch-sweep` script tickets.

Alternatives considered for the slug and rejected in that chat:
an agent-backed `bootstrap/retire` (every done-ticket retire would cost an
agent session, undoing the 2026-10-13 decision that a done retire needs no
agent), and a new `coga run retire` recipe (grows the fixed kernel recipe
registry, which `gigantic-refactor-move-recurring-recipes-out-of-co` owns).

Prior work: #1041 folded `dev/checkout-cleanup/foreign-ownership` into
`dev/checkout-cleanup`.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
