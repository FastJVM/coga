---
title: Move lifecycle verbs to ticket operations
status: draft
owner: nicktoper
agent: codex
contexts:
  - coga-dev/principles
  - coga/lifecycle
  - coga/workflows
  - coga/notifications/producers
  - coga-dev/codebase
  - coga-dev/testing
  - coga-dev/current-direction
  - coga-dev/microkernel
  - coga-dev/project-stage
  - coga/cli
  - coga/checkouts
workflow: code/design-then-implement
---

## Description

Settle the placement of the lifecycle heads that sit in the kernel by
registration rather than by the launch-closure test: `coga block` /
`coga unblock`, and the `coga owner` head (a `mark`-shaped locked write of
`owner:`).

`block`/`unblock` stay in the kernel: the owner-confirmed v1 kernel line in
`coga-dev/current-direction` (2026-10-16) includes them. This ticket writes their
co-versioning proof; it does not move them unless the owning context is
deliberately revised first. Only `owner` is open: either write its
co-versioning proof or move it to the edge without changing semantics.

`coga mark` and `coga bump` are **out of scope**: `coga-dev/microkernel`
keeps them in the kernel because launch calls them mid-flight, and the owner
confirmed that boundary for v1 on 2026-10-16.

### Acceptance criteria

- [ ] The design names, for `block`, `unblock` and `owner`, the internal
      state-write primitive each head calls, and separates the primitive from
      the user-facing head.
- [ ] `block` and `unblock` end with a written co-versioning proof (the
      package-private invariant or atomic transaction an edge implementation
      could not preserve) recorded in `coga-dev/microkernel`.
- [ ] `owner` ends either with such a proof or moved to the edge with
      unchanged behavior.
- [ ] Lifecycle invariants are preserved: status transitions, blocker asks
      and their resolution, `COGA_EXPECTED_TASK`/`COGA_EXPECTED_STEP` guards,
      session termination under a supervisor, logging, git sync and
      notifications.
- [ ] The `owner` row leaves the "Open command placements" table in
      the local-only `coga-dev/microkernel` topic; the kernel bullet there
      states the reason `block`/`unblock` stay;
      `coga/lifecycle`, `coga/tickets/ownership` and the `coga/cli` index
      match.
- [ ] Tests cover the changed surface; the full suite and
      `coga validate --json` pass.

## Context

Group: `microkernel/README.md` (v1 scope since 2026-10-16).

Coordinate with `microkernel/launch-decomposition`, which isolates
launch's lifecycle writes (`_auto_activate`, `mark_in_progress`,
blocked-resume re-block, script step/done) in the launch service. If moving
`block`/`unblock` needs a launch hook, record that dependency there rather
than adding one here.

Out of scope: `mark`, `bump`, `create`, `skill *`, and the launch executor.

### Premise check (2026-10-16, pull-forward to v1)

- Subject exists: `src/coga/commands/{block,unblock,owner,mark,bump}.py`.
- Delivered in part (Dream W39 F46): `coga-dev/microkernel` now classifies
  `mark`/`bump` as kernel (launch closure). Owner kept that rule on
  2026-10-16, and the v1 kernel line in `coga-dev/current-direction` also keeps
  `block`/`unblock`, so scope narrowed to their written proof plus the
  placement of the newer `owner` head, whose table row had no review.
- Frontmatter `title` still reads "Move lifecycle verbs to ticket
  operations"; owner may rename it.

<!-- coga:blackboard -->

Created under `v2/cleanup-core-commands/` as part of the command-surface breakdown.
