---
name: direct/body
description: Single-step workflow body. The ticket's own body IS the spec — execute the phases it lays out in order, keep the blackboard current, and finish by marking the task done. Used by machine-authored tasks (Dream/recurring, retire) whose process lives in the ticket body rather than a multi-step workflow.
---

# Run the ticket body directly

This is a one-step workflow. There is no separate skill telling you *what*
to do — **the ticket body is the spec**. Read it as the authoritative
instruction set for this run and execute it.

Use this when a task's process is fully described by its own body and does
not decompose into reusable workflow steps handed between roles. Dream (and
other workflow-less recurring templates) and retire tasks are the canonical
cases: each creates straight to `active` and carries an ordered phase list
in its `## Description`. Wrapping that body in a real one-step workflow is
what lets the task be activated, bumped, and validated like any other —
every task past `draft` carries a workflow.

## How to do it

- **Treat the body as the dispatch contract.** Do exactly the phases it
  lists, in the order it lists them. Do not auto-discover other skills,
  invent extra phases, or skip ahead. If the body says "stop and ask" on a
  precondition, stop and ask.
- **Honor the body's own stop/skip rules.** A phase that fails does not
  license a substitute — record the result and continue only with later
  phases whose inputs don't depend on the blocked one, exactly as the body
  directs.
- **Keep the blackboard current.** Capture decisions, findings, and any
  blocker as you go. This is a single step, so the blackboard is the only
  durable handoff if the run is relaunched.
- **Finish by marking the task done.** This is the workflow's only step, so
  there is no later step to bump into. When the body's work is complete, run
  `coga mark done <slug>` (with a one-line `--message` summary). If the body
  specifies its own completion command, that command IS this instruction —
  follow it. If you are blocked before completion, `coga block` with a
  reason; never stop silently.

## Product-code boundary

`direct/body` has no branch-push or PR step. Use it for work whose body owns
its complete side-effect and handoff contract, not for landing committed
product files. A ticket that produces code or other tracked product artifacts
belongs on a `code/*` workflow so its branch is pushed and reviewed before the
ticket finishes.

As a last-line guard, `coga mark done` refuses to finish a `direct/body` ticket
when the current checkout has committed paths outside Coga's state subtree that
are absent from the control branch. The error names those paths and points the
work to a `code/*` workflow. `--force` is an explicit escape hatch for a human
who has independently made the commits durable.

The guard is worktree-local: it can see product commits only when `mark done`
runs from the checkout that contains them. It does not make `direct/body` a
code-delivery workflow or recover commits stranded in another checkout.

## What this skill does NOT do

- It does not add process on top of the body. The body governs; this skill
  only frames how to run it.
- It is not a license to improvise. If the body's phases don't fit the work,
  that's a ticket-shape problem to raise, not to route around.
