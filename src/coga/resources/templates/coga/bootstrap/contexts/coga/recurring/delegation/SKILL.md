---
name: coga/recurring/delegation
description: The `delegate:` contract — a recurring period serviced by one in-process bootstrap agent launch, its frozen dispatch, one-step workflow bound, sentinel completion, and why a template never shells out to a nested `coga launch`.
---

# Recurring delegation

`delegate: bootstrap/<name>` on a template declares *which* stateless bootstrap
target an agent period hands its work to — something no file's presence can
express. It does not choose deterministic versus agent execution; that stays
deduced from `ticket.py`, and the two are mutually exclusive.

## Why delegate instead of a nested launch

A template whose work is "run another Coga command" must declare `delegate:`,
never have its agent shell out to `coga launch`. An agent's tool subprocess has
no TTY on stdin or stdout, so a nested agent launch exits 2; faking a terminal
(`script -qec …`) is not sanctioned. With `delegate:` the sweep itself launches
the target in the operator's terminal — under the sweep's `--agent` override,
queue session conduct and idle/max-session bounds — and keeps the period's
lifecycle bookkeeping, with no wrapper session in between. The rejected
alternatives are recorded in
[recurring-admission](https://github.com/FastJVM/coga/blob/main/docs/contexts/coga-dev/internals/recurring-admission/SKILL.md#why-delegation-rather-than-a-nested-launch).

## Rules

A materialized period freezes a stateless agent-backed `bootstrap/<name>`
target. Deterministic phases belong in a workflow script or `ticket.py`.
The delegated workflow has one agent-held step and no completion gate.
After preflight the runner records the period start locally and executes the
bootstrap agent. Its done signal completes the local period. An unexpected
exit reports failure and retains the ticket.
