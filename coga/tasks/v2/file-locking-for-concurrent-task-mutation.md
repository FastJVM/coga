---
slug: v2/file-locking-for-concurrent-task-mutation
title: File locking for concurrent task mutation
status: draft
mode: agent
owner: nick
human: nick
agent: claude
assignee: nick
contexts: []
skills: []
workflow: null
---

## Description

Priority: low now, blocker-if-we-scale. Documenting the single biggest
gap between Relay's stated concurrency model and the code.

"Locking" appears throughout the docs (`CLAUDE.md`, `architecture/SKILL.md`) and
in test/function names (`..._fails_before_lock`, the `test_launch.py:1017`
comment "No lock file left behind; in fact none was ever written"), but **no
mutual-exclusion primitive exists**. `fcntl` appears in the source exactly once
— `repl_supervisor.py:292`, for terminal window-size ioctl, not locking.
Concurrency safety rests entirely on the advisory `in_progress` status flag. Two
concurrent `relay launch` (or a recurring sweep racing a human `relay mark`) on
the same task are not prevented, and there is no test that even attempts it. The
only real lock anywhere is a pidfile in the shipped `cron.sh` template, never
executed in tests.

This is acceptable under the explicit single-operator / sequential-launch bet
(`recurring.py:70` "each launch blocks until the agent session exits"), which is
why this is low priority *today*. But it is the first thing that breaks the
moment two relay processes touch the same task, and it directly undercuts the
"multiple agents operating on a git-backed task store" framing.

Decide and document the stance:
- (a) Make the single-operator constraint explicit and enforced (a repo-level or
  per-task advisory `flock` that refuses a second concurrent mutation with a
  clear message), or
- (b) Accept it as a known limitation and remove the "locking" vocabulary from
  docs/tests so the code and the claims agree.

Acceptance: code and documentation agree on the concurrency model; if locking is
adopted, a test launches two concurrent mutations and asserts the second is
rejected cleanly (no lost update).

## Context

Code: `src/relay/repl_supervisor.py:292` (only `fcntl` use, ioctl not lock),
`src/relay/ticket.py` (non-atomic write), `src/relay/commands/launch.py`,
`tests/test_launch.py:1017`. Pairs with `atomic-writes-for-ticket-log-and-done-
marker-files`.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
