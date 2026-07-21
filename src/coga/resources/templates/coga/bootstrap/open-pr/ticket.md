---
title: Open PR
assignee: system
secrets: null
script: run.py
---

## Description

Command ticket for the `open-pr` verb: push a code ticket's recorded feature
branch and open (or ready) its PR. `coga open-pr <slug>` is a default alias
for `coga launch bootstrap/open-pr <slug>` — a stateless script launch of
this ticket, with the target task ref carried by the launch arg channel
(`COGA_ARG_1`). This ticket is the verb's durable *definition*, launched in
place each time; no per-invocation task is ever created.

The deterministic work lives in the sibling `recipe.py`, driven by `run.py`:
read `branch:` / `worktree:` from the target ticket's `## Dev` blackboard
section, confirm the worktree is on that branch, clean, ahead of the base
branch, and free of material stale drift, push the branch by name (with an
explicit force-with-lease on a safe retry), open the PR with `gh pr create` —
or ready an existing draft, or reuse an already-open PR — and write
`pr: <url>` back under `## Dev`. Any refusal exits non-zero with nothing
pushed or advanced, so the open-pr workflow step's `requires: pr` bump gate
stays unmet until a real PR is recorded.

It must run from the primary control checkout (task resolution and the
blackboard write are authoritative there); it refuses on a feature checkout.
The `code/open-pr` agent step runs the `coga open-pr <slug>` spelling — as a
stateless nested script launch it never touches the outer session's
slug-scoped done sentinel.
