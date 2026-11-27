---
name: code/open-pr
description: Run the PR workflow script for older frozen workflows.
---

Read `branch:`, `base:` and `remote:` under `## Dev`; the workflow's `enter`
script records them and switches to the branch. If one is missing or Git
refuses, stop. Commit the code without `coga/tasks/**` or `coga/log.md`. Then
run the local-first `git/push-and-open-pr/run.py` with the current ticket
environment. It opens or reuses the PR, records the URL and bumps the current
step; the bump's `exit` script publishes the ticket to the base.
