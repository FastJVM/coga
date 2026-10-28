---
title: Move lifecycle verbs to ticket operations
status: active
owner: nicktoper
agent: codex
contexts:
- coga-dev/principles
- coga-dev/testing
- coga-dev/project-stage
- coga/checkouts
- coga-dev/internals/state-publication/publish
- coga/extension-model
- coga/script-tickets
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
  - name: peer-review
    skills:
    - code/peer-review
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
step: 1 (design)
---

## Description

Settle the placement of the lifecycle heads that sit in the kernel by
registration rather than by the launch-closure test: `coga block` /
`coga unblock`, and the `coga owner` head (a `mark`-shaped locked write of
`owner:`).

`block`/`unblock` stay in the kernel: the owner-confirmed v1 kernel line in
`coga-dev/current-direction` (2026-10-16) includes them. This ticket writes their
co-versioning proof; it does not move them unless the owning context is
deliberately revised first. Only `owner` is open: assess and ratify the
co-versioning argument already recorded in `coga-dev/microkernel`, or reject
it with reasons and move the head to the edge without changing semantics.

`coga mark` and `coga bump` are **out of scope**: `coga-dev/microkernel`
keeps them in the kernel because launch calls them mid-flight, and the owner
confirmed that boundary for v1 on 2026-10-16.

### Acceptance criteria

- [ ] Apply the group's [reduction objective](README.md#reduction-objective):
      identify redundant wrappers or duplicated state-write scaffolding in
      the three owned heads, reuse existing shared primitives where justified,
      and report the resulting code and dependency reduction separately from
      placement changes. Preserve the lifecycle invariants below and the
      confirmed kernel home of `block`/`unblock`.

- [ ] The design names, for `block`, `unblock` and `owner`, the internal
      state-write primitive each head calls, and separates the primitive from
      the user-facing head.
- [ ] `block` and `unblock` end with a written co-versioning proof (the
      package-private invariant or atomic transaction an edge implementation
      could not preserve) recorded in `coga-dev/microkernel`.
- [ ] `owner` ends either with its existing argument reviewed and ratified as
      such a proof, or moved to the edge with unchanged behavior.
- [ ] Lifecycle invariants are preserved: status transitions, blocker asks
      and their resolution, existing per-path `COGA_EXPECTED_TASK` /
      `COGA_EXPECTED_STEP` guards, session termination under a supervisor,
      owner-gate and launch-claim refusals, logging, git sync and notifications.
      Preserve concurrent edits and the distinct definite-failure rollback,
      uncertain-publication and soft-skip outcomes; do not assume every head
      implements the same transaction or guard coverage.
- [ ] The `owner` row leaves the "Open command placements" table in
      the local-only `coga-dev/microkernel` topic; the kernel bullet there
      states the reason `block`/`unblock` stay;
      `coga/lifecycle`, `coga/tickets` ("Owner and relationships") and the `coga/cli` index
      match.
- [ ] Tests cover the changed surface; the full suite and
      `coga validate --json` pass.

## Context

Group: read `coga/tasks/microkernel/README.md`, "Reduction objective".
Report production-code counts at named before/after revisions across core,
edge and ticket/skill scripts in scope; state the counting method, separate
tests, documentation and packaged copies, and distinguish relocation from
deletion or deduplication. There is no line-count quota. A size-neutral change
must identify its boundary gain and name a follow-up for deferred reduction.
The group's historical archive-audit instruction does not authorize archive
access or add an archive deliverable to this ticket.

### Current source and remaining review (2026-10-28)

- `src/coga/commands/block.py`, `block`, combines
  `blackboard.append_blocker` with `mark.mark_blocked` and the task-scoped
  supervisor completion marker. Its blocker append is locked separately
  from the subsequent status transition.
- `src/coga/commands/unblock.py`, `_apply_unblock`, resolves asks under
  `git.state_lock`, then uses `mark.mark_active` for a blocked ticket or
  resolve-only audit/sync paths for `in_progress` and paused recurring tasks.
- `src/coga/commands/owner.py`, `owner`, holds `git.state_lock` across read,
  prospective validation, exact local-byte comparison, write, audit and
  `git.sync_task_state(strict=True, expect=...)`. It preserves concurrent
  edits, rolls back only its own bytes and audit on definite failure, retains
  uncertain publication for reconciliation, and exits 75 on those failures
  to suppress the sweep. Documented Git soft-skips keep the local result.
  `tests/test_owner.py` exercises these distinctions. The existing argument
  under microkernel's open-placement table is evidence to review, not a
  ratified classification; the `owner` row remains open.
- These heads are not interchangeable wrappers. Inventory their real
  primitives and guard coverage before selecting reductions. In particular,
  `commands.bump._assert_supervised_step_is_current` belongs to the
  out-of-scope `bump` head, not automatically to every lifecycle command.

### Launch dependency

The group originally ordered `microkernel/launch-decomposition` first. At
this premise check that ticket is paused at its owner `review-design` gate,
but its inventory is stale: `commands.launch.launch` already delegates to
`coga.launch`, and `src/coga/launch_script.py` has no `advance_step` or
`mark_done` calls. Work from current source rather than the sibling's old
description of script completion or lifecycle migration.

Design may proceed now. Before the owner approves implementation, identify
any concrete launch-service prerequisite and either verify that it has landed
or record it on the sibling and defer the dependent implementation. If none
is needed, record why the existing boundary suffices. This ticket does not
add launch hooks or take over the executor. The sibling's older proposal to
move `mark`/`bump` does not override their confirmed kernel placement.

Out of scope: `mark`, `bump`, `create`, `skill *`, launch execution and script
completion semantics. This ticket originated under
`v2/cleanup-core-commands/` and returned to v1 scope on 2026-10-16.

### Required reads and owning topics

The following topics are cited rather than attached; read the named sections.
Editing targets must be opened from disk. Update any changed contract and its
packaged twin in the same PR; `coga-dev/` topics remain local-only.

- `coga-dev/microkernel`, `docs/contexts/coga-dev/microkernel/SKILL.md`:
  "The microkernel rule", "Open command placements", "Migrating a built-in
  to the edge", and "The kernel tier and its edges". A command needs a
  package-private invariant or transaction that stable CLI/filesystem access
  cannot preserve; registration or merely calling shared Python is not proof.
  Write the placement decisions here and remove the resolved `owner` row.
- `coga/lifecycle`, `docs/contexts/coga/lifecycle/SKILL.md`: "Status: whether
  work happens" and "Blocking and resume". Blocking retains the step;
  unblocking activates a blocked task but only resolves asks on an
  `in_progress` task or a paused recurring period. Preserve interactive
  blocked-resume behavior and supervised termination.
- `coga/tickets`, `docs/contexts/coga/tickets/SKILL.md`: "Owner and
  relationships". Reassignment preserves status, step and body, refuses
  terminal records, own supervised sessions and outstanding launch claims,
  and requires a stopped assist for an in-progress owner gate; an agent step
  must first stop and pause. This is the owner contract, not the nonexistent
  `coga/tickets/ownership` ref.
- `coga/cli`, `docs/contexts/coga/cli/SKILL.md`: "Tickets and state" and
  "Aliases and recipes". Keep the index aligned with the reviewed command
  spelling and contract owner; it does not substitute for those contracts.
- `coga-dev/current-direction`,
  `docs/contexts/coga-dev/current-direction/SKILL.md`: "In force", the
  2026-10-16 microkernel decision. V1 keeps `mark`/`bump` and
  `block`/`unblock` in core; only `owner` placement is open here.
- `coga-dev/codebase`, `docs/contexts/coga-dev/codebase/SKILL.md`: "Source
  map". CLI heads live in `commands/`; shared lifecycle, blackboard and Git
  behavior lives in `mark.py`, `blackboard.py` and `git.py`. The symbols above
  are the starting inventory, not a mandate to add another wrapper.
- `coga/workflows`, `docs/contexts/coga/workflows/SKILL.md`: "Frozen snapshot,
  live content" and "Roles are the routing". Preserve frozen step metadata
  and derived owner/agent routing, including inherited roles; reassignment
  does not rewrite the workflow or main agent.
- `coga/notifications/producers`,
  `docs/contexts/coga/notifications/producers/SKILL.md`: "Live surface" and
  "Silent"; and `coga/notifications`,
  `docs/contexts/coga/notifications/SKILL.md`: "When a post fails".
  Block posts to flow with the owner identified; ordinary activation and
  owner reassignment remain silent. A failed block announcement is reported
  without undoing the written transition or preventing session completion.

The attached publication topic supplies the strict/best-effort, expectation,
lock-scope and failure contracts required to assess the proof. The attached
extension and script-ticket topics govern the possible edge alternative:
preserve deterministic behavior and create no per-invocation task. If design
selects wheel-owned edge code, first read
`docs/contexts/coga/edge-code/SKILL.md` in full and attach `coga/edge-code`
for implementation; core must never import the edge implementation.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
