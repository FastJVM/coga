---
name: git/push-and-open-pr
description: Push the recorded ticket branch, open or reuse its pull request, and advance the workflow.
---

Use this skill as a workflow `run: git/push-and-open-pr` step. Commit
implementation changes before entering the step. The script uses the current
ticket environment and the `branch:`, `remote:` and `base:` fields in
`## Dev`. It records the pull request URL there and commits the handoff.
