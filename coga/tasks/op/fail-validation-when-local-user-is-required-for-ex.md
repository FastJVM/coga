---
slug: op/fail-validation-when-local-user-is-required-for-ex
title: Fail validation when local user is required for execution
status: draft
owner: zach
human: zach
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
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
step: 1 (implement)
---

## Description

Add an explicit validation mode for checkouts that are expected to execute
mutating or recurring work. Today `coga validate` reports a missing
`coga.local.toml` user as a warning and exits 0 so a fresh clone can run
diagnostics. That is useful for inspection, but it is a false-green when
`validate` is used as a headless-runner preflight: the real `coga recurring`
then exits 2 before doing work.

Preserve the diagnostic-friendly default while providing a stable command or
flag that treats missing execution prerequisites—at minimum the local
`user`—as fatal.

## Context

- `validate.py` intentionally emits `missing-user` with warning severity so
  read-only commands remain usable in a fresh clone. Do not remove that default
  behavior.
- Mutating commands load configuration with `require_user=True`; the recurring
  sweep does too, while `recurring list` and ordinary validation do not.
- Since Coga PR #613, `coga recurring --all` treats a missing-user checkout as
  an unconfigured non-target and does not fail the aggregate run. A real
  scheduler target can therefore be skipped while the parent exits
  successfully unless provisioning has its own strict preflight.
- The immediate downstream case is FastJVM/patents PR #130: its headless
  runbook can resolve every secret and pass `validate --check-slack`, yet the
  scheduled sweep still cannot run until `coga.local.toml` contains
  `user = "runner"`.

Done means:

- a documented execution-readiness validation surface returns nonzero and a
  clear diagnostic when the local actor is absent;
- ordinary `coga validate`, `status`, `show`, and other intended read-only
  fresh-clone diagnostics retain their current behavior;
- text and JSON output have deterministic severity and exit semantics suitable
  for shell preflights;
- tests cover direct recurring runners and the multi-repo `--all` false-green
  boundary; and
- CLI documentation and live/packaged contexts describe when to use strict
  validation.

Out of scope: automatically choosing or copying an actor identity. Worktree
local-config propagation belongs to sibling ticket
`op/propagate-local-coga-config-into-worktrees`.
<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
