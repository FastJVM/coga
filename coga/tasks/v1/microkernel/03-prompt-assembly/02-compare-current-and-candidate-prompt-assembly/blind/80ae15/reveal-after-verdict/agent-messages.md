## Rollout 0

VERDICT: problem
TITLE: Create the report output directory before writing reports
---
### Failure

The `recurring/trial` run failed because report generation attempted to open a file in a missing output directory. `ticket.py` exited with code 7, and the task remained `in_progress`.

No open autofix ticket covers this failure.

### Likely location and fix

Inspect the `recurring/trial` template and its report-writing code in `ticket.py`. Ensure the report destination and any required parent directories exist before opening the output file. Verify that the destination resolves correctly in recurring-run execution.

Ensure report-generation failures also transition the task out of `in_progress` into the appropriate failure state.

### Verification

Run the report-generation path with its output directory absent. Confirm that it creates the directory, writes the report, and completes successfully. Also verify that an actual write failure produces a clear error and leaves no task stuck `in_progress`.