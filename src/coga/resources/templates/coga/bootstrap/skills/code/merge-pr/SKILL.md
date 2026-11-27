---
name: code/merge-pr
description: Complete and merge an approved change using its exact reviewed head.
---

The workflow runs the sibling `run.py`. For an older frozen agent step,
switch to the recorded branch if needed and stop if Git refuses. Invoke the
script with the ticket environment. It reads `reviewed:` from `## Dev`,
verifies the reviewed head, pushes the code and waits for the PR's checks.
After merging the pinned head it runs the final bump, which publishes the
finished ticket to the base.

If Git or the PR checks fail before merge, resolve the reported failure in the
ticket branch and rerun the merge step. If the final bump writes `done` but fails
to publish, follow the exit recovery in `coga/git`.
