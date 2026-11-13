## Rollout 0

VERDICT: problem
TITLE: Create the report output directory before writing reports
---
The `recurring/trial` recipe failed while generating its report because the output directory did not exist. The sweep records `ticket.py` exiting with code 7 and the task remaining `in_progress`.

Investigate the report-writing code in the `ticket.py` used by `recurring/trial`, along with its output-path configuration. Ensure the destination directory is created, including missing parents, before opening the report file. Preserve clear failures for invalid or unwritable destinations.

Ensure recipe failures move the task out of `in_progress` into the appropriate failed state.

Verify that running with a missing output directory creates the directory and report successfully, and that a report-writing failure leaves the task in a terminal failure state.