---
name: code/merge-pr
description: Complete and merge an approved change using its exact reviewed head.
---

The workflow runs the sibling `run.py`. For an older frozen agent step,
switch to the recorded branch if needed and stop if Git refuses. Invoke the
script with the ticket environment. It reads `reviewed:` from `## Dev`,
checks that subsequent commits change only the ticket and log, marks the
ticket done, and commits and pushes state. It waits for the PR's checks and
merges the pinned head.

If the script fails after the final bump, keep the local state and report the
failed operation. Re-run the script directly from the ticket branch to retry
the remaining push, checks or merge.
