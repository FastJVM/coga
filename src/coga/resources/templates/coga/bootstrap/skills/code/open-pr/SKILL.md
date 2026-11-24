---
name: code/open-pr
description: Run the PR workflow script for older frozen workflows.
---

Read `branch:` under `## Dev`. Switch to that branch if needed and stop if
Git refuses. To backfill missing `base:` or `remote:`, run
`git/open-branch/run.py --no-bump`. Then run the local-first
`git/push-and-open-pr/run.py` with the current ticket environment. It opens
or reuses the PR, records the URL and bumps the current step.
