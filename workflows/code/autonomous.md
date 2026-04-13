---
name: code/autonomous
description: Code workflow without approval gate. Agent implements and merges directly. Use only for low-stakes, well-specified changes.
steps:
  - name: implement
    skill: infra/testing-conventions
  - name: merge
---

## merge

Commit the change to `main` directly. Post a `relay feed` noting the
commit SHA and a one-line summary.
