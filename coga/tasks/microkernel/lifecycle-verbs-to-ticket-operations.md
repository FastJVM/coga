---
title: Move lifecycle verbs to ticket operations
status: draft
owner: nicktoper
agent: codex
contexts:
  - coga/principles
  - coga/lifecycle
  - coga/workflows
  - coga/notifications/producers
  - coga/codebase
  - coga/testing
  - coga/current-direction
  - coga/extension-model
  - coga/project-stage
  - coga/cli
  - dev/checkouts
  - dev/dev-record
workflow: code/design-then-implement
---

## Description

Settle the placement of the two lifecycle heads that sit in the kernel by
registration rather than by the launch-closure test: `coga block` /
`coga unblock`, and the `coga owner` head (a `mark`-shaped locked write of
`owner:`). For each, either write the co-versioning proof that keeps it in
`src/coga/` or move it to the edge without changing semantics.

`coga mark` and `coga bump` are **out of scope**: `coga/extension-model`
keeps them in the kernel because launch calls them mid-flight, and the owner
confirmed that boundary for v1 on 2026-10-16.

### Acceptance criteria

- [ ] The design names, for `block`, `unblock` and `owner`, the internal
      state-write primitive each head calls, and separates the primitive from
      the user-facing head.
- [ ] Each head ends either with a written co-versioning proof (the
      package-private invariant or atomic transaction an edge implementation
      could not preserve) recorded in `coga/extension-model`, or moved to the
      edge with unchanged behavior.
- [ ] Lifecycle invariants are preserved: status transitions, blocker asks
      and their resolution, `COGA_EXPECTED_TASK`/`COGA_EXPECTED_STEP` guards,
      session termination under a supervisor, logging, git sync and
      notifications.
- [ ] The `owner` row leaves the "Open command placements" table in
      `coga/extension-model` and its packaged twin; the kernel bullet there
      states the reason `block`/`unblock` stay (or drops them if moved);
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
- Delivered in part (Dream W39 F46): `coga/extension-model` now classifies
  `mark`/`bump` as kernel (launch closure). Owner kept that rule on
  2026-10-16, so scope narrowed to `block`/`unblock` (kernel "by
  registration") plus the newer `owner` head, whose table row had no review.
- Frontmatter `title` still reads "Move lifecycle verbs to ticket
  operations"; owner may rename it.

<!-- coga:blackboard -->

Created under `v2/cleanup-core-commands/` as part of the command-surface breakdown.
