---
name: git/open-branch
description: Switch to the ticket branch or create it from HEAD, record the Git fields, and bump.
---

Use this skill as a workflow `run: git/open-branch` step. Run its sibling
`run.py --no-bump` to prepare a branch during an existing step. Use
`--base <branch>` to supply the base explicitly. The script uses the
current ticket environment.
