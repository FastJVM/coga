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

Preserve the diagnostic-friendly default and add
`coga validate --execution-ready`. In that mode the existing `missing-user`
issue becomes an error and the command exits 1.

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
- Implementation anchors are `src/coga/commands/validate.py` and
  `src/coga/validate.py` (`_missing_user_issue`, `run`, `validate_task`, and
  `_main`), with coverage in `tests/test_cli.py` and
  `tests/test_validate.py`.

CLI contract:

- Default validation keeps `missing-user` at warning severity and exits 0 when
  there are no other errors.
- `--execution-ready` keeps issue kind `missing-user`, promotes severity to
  `error`, and exits 1. Text and `--json` output must agree.
- The flag works for whole-repo and `--task` validation. With `--fix`, it
  remains an error because Coga must not invent the actor.
- It composes normally with `--check-slack` and `--check-github`; their existing
  incompatibility with `--task` is unchanged.
- Both the Typer command and `src/coga/validate.py::_main` expose identical
  behavior.

Done means:

- `coga validate --execution-ready` returns 1 and a clear `missing-user` error
  when the local actor is absent;
- ordinary `coga validate`, `status`, `show`, and other intended read-only
  fresh-clone diagnostics retain their current behavior;
- text and JSON output, both CLI entrypoints, `--task`, `--fix`, and the network
  check combinations follow the contract above;
- `docs/operations.md`, `docs/reference.md`, and the packaged
  `contexts/coga/cli` command reference show strict validation as the preflight
  before invoking recurring work. No external repository documentation is
  required by this ticket.

Out of scope: automatically choosing or copying an actor identity. Worktree
local-config propagation belongs to sibling ticket
`op/propagate-local-coga-config-into-worktrees`. This ticket does not change
`recurring --all` discovery or its intentional skip-unconfigured behavior;
each real scheduler target must run strict validation in its own checkout
before the sweep.
<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
