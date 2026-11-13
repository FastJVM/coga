## Rollout 0

VERDICT: problem
TITLE: Create the report output directory before writing reports
---
The `recurring/trial` task failed because report generation tried to open a file in a missing output directory.

The sweep records `ticket.py` exiting with code 7 and the task remaining `in_progress`. The blackboard explicitly reports that report generation failed opening a missing output directory.

Inspect the report-writing path in `ticket.py` and the output-path configuration for the template under `coga/recurring/` that materializes `recurring/trial`.

Ensure the configured output directory exists before writing the report, including any required parent directories. Preserve actionable errors for directory-creation or write failures, and ensure failed execution transitions the task out of `in_progress` into the appropriate failure state.

Verify that running with an absent output directory creates the directory and produces the report, and that an actual write failure leaves the task in a terminal failure state.