## Rollout 0

I’ll check how this invocation selected its analyst instructions and where those instructions are maintained.

---

VERDICT: problem
TITLE: Create the report output directory before writing
---
`recurring/trial` exited with code 7 and remained `in_progress` because report generation tried to open a missing output directory. Inspect its `ticket.py` report-writing path; create required parent directories before writing and ensure failures leave an appropriate task status.

The effective analyst criteria come from `build_prompt()` in [src/coga/recurring_autofix.py](/home/n/Code/coga/src/coga/recurring_autofix.py:528). The invocation’s `recurring_autofix.analyze_record` source selected this procedure, which calls `build_prompt()`.

To customize what counts as an analyst problem, edit the criteria in that function: it directly supplies the “What counts as a problem” and “What is NOT a problem” instructions. No files were changed.