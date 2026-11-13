## Rollout 0

VERDICT: problem
TITLE: Create the report output directory before writing recurring reports
---
The `recurring/trial` run failed during report generation because its output directory was missing. The sweep records `ticket.py` exiting with code 7 and the task remaining `in_progress`. No open autofix ticket covers this failure.

Investigate the report-writing code invoked by `ticket.py` for `recurring/trial`, particularly output-path setup. The referenced script is not present in this checkout, so the exact implementation location needs confirmation.

Ensure the required output directory exists before opening the report file, including any missing parent directories. Ensure report-generation failures leave the task in an appropriate terminal failure state rather than stuck `in_progress`.

Verify that running with an absent output directory successfully creates the report, and that an actual write failure is reported clearly and finalizes the task state.