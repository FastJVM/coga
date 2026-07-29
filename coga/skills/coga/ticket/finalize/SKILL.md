---
name: coga/ticket/finalize
description: Finalize a guided ticket-authoring session by validating authored tasks and syncing changed task/support files.
---

# Ticket Authoring Finalize

`coga ticket` calls the shared `coga.authoring.finalize_authored` helper after
the authoring interview exits. That deterministic finalize phase:

1. load the pre-authoring file/task snapshot,
2. validate every authored task,
3. reject a draft left without a workflow, and
4. git-sync changed task, context, and skill files.

The command owns this lifecycle directly; this skill documents the shared
behavior and does not provide an executable entry point.
