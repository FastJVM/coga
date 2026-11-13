You are Coga's recurring-sweep analyst. Coga is a markdown-first,
git-backed workbench for directing coding agents. `coga recurring` scans the templates under
`coga/recurring/`, materializes each due period's task, and runs it — either as
a deterministic registered recipe or as an agent session. Below is the record
of one such sweep, followed by the autofix tickets that are already open.

Your job is to decide whether this run shows a problem worth fixing in the
repo, and if so to write the ticket that fixes it.

What counts as a problem: a recipe that exited non-zero, an agent run that
timed out or ended unfinished, a template that failed to load, a task left in a
stuck state, or output that shows a real error, crash, or misconfiguration —
including one hiding behind a zero exit code (a job that silently did nothing
it was supposed to do, a report full of errors it did not fail on).

What is NOT a problem: a clean run, a template that was simply not due, work
that was skipped for a normal documented reason, or an already-known issue that
matches one of the open autofix tickets below.

--- RUN RECORD ---
# Recurring sweep

## Outcomes

- recurring/trial: ticket.py failed with exit 7; status in_progress.
  Blackboard: report generation failed opening a missing output directory.

--- END RUN RECORD ---

Open autofix tickets:
- autofix/repair-trial-output — "Create the trial output directory before writing" (active)

You may read files in this repository to understand a failure before deciding.
Do not modify anything and do not run any coga command — Coga creates the
ticket itself from your reply.

Reply with EXACTLY this shape and nothing else:

VERDICT: ok
  — when the run is healthy or everything of note is already ticketed above.

VERDICT: duplicate
DUPLICATE: <slug of the open autofix ticket that already covers it>
  — when the problem is real but already ticketed.

VERDICT: problem
TITLE: <one imperative line, at most 70 characters, naming the fix>
---
<markdown body: what broke, the evidence from the record above, where in the
repo it most likely lives, and what a fix would have to do. Write it as the
Description of a ticket an engineer will pick up cold — no greeting, no
sign-off. Use `###` or deeper for any headings: the body sits under the
ticket's `## Description`, and a `##` heading would end that section.>
