---
name: coga/ticket/finalize
description: Finalize a guided ticket-authoring session by validating authored tasks and syncing changed task/support files.
script: run.py
---

# Ticket Authoring Finalize

This skill is the script-shaped home for the deterministic finalize phase of
guided ticket authoring. It runs the same Python used by `coga ticket` after the
authoring interview exits:

1. load the pre-authoring file/task snapshot,
2. validate every authored task,
3. reject a draft left without a workflow, and
4. git-sync changed task, context, and skill files.

The script imports `coga.authoring.finalize_authored_from_env` and calls it
directly, so it does not depend on `coga` being on `PATH` inside the script
environment.

Required environment:

- `COGA_AUTHORING_REF`: authored task ref or bootstrap ref.
- `COGA_AUTHORING_SNAPSHOT`: path to a JSON snapshot written by
  `coga.authoring.write_authoring_snapshot`.
