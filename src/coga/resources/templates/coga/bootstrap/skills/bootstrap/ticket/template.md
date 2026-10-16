---
title: Replace with a one-line task title
status: draft  # CLI-owned after creation; do not hand-advance a ticket.
owner: replace-with-human-name  # Human accountable for this task.
# Optional. The task's main-agent choice — not the current operator, which coga
# derives from the current workflow step's role every time it is read. Leave it
# out and `coga mark active` selects the configured default at activation.
# agent: replace-with-agent-nickname
# Optional. Omit empty lists. Contexts supply facts; skills supply procedures.
# contexts:
#   - namespace/some-context
# skills:
#   - namespace/some-skill
workflow: null  # Draft idea only; choose a workflow before activation.
# Optional. Secrets this task needs, declared inline — one `- NAME: <ref>` list
# entry per secret, where `<ref>` is an `op://vault/item/field` 1Password
# reference or an `env:VAR` indirection. An absent declaration injects nothing;
# a list injects only those keys (and fails loud at launch if any ref is unset).
# secrets:
#   - SOME_TOKEN: env:SOME_TOKEN
# Do not add step or runtime generation fields: the CLI writes those.
# The current operator comes from the workflow role, not an assignment field.
# --- extensions ---
# Repo-declared fields (see `[ticket.fields.<name>]` in coga.toml) are
# injected by `coga create` / `coga ticket` below this marker. No
# extensions configured → nothing here, marker is harmless.
---

## Description

What needs to happen, why now, and what would count as done. Use `###`
subheadings here for acceptance criteria, constraints, and proposed shape.
Only Description and Context compose above the fence; another `##` heading
ends the preceding section and is omitted from the launch prompt.

## Context

Task-specific knowledge that isn't a reusable skill or context file.
One-off details: where in the codebase, what to watch out for, what not
to touch. Cite code as module plus symbol (`git.sync_task_state`), never
a bare line number — lines drift within days; if a range helps, name the
symbol first and mark the range as an aid.

<!-- coga:blackboard -->

Working notes: current decisions and reasons, verification, next actions,
and blockers. Update throughout the task; keep current values in place.

## Dev

<!-- Optional for code work: add branch: <name> when created, pr: <full URL> when opened, and worktree: <path> only for a sandbox clone; one field per line, current values only, notes on separate lines. -->
