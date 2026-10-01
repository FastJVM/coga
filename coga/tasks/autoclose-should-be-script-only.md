---
title: autoclose should be script only
status: draft
owner: nicktoper
workflow: code/with-review
---

## Description

Make autoclose entirely deterministic: the owner wants no LLM involved in
executing, resuming, or automatically analyzing an autoclose run. The sweep
already has a Python entry point, but failed period tasks can reach an agent
through megalaunch, and recurring runs also invoke a post-run autofix analyst.
Done means scheduled autoclose, `coga autoclose`, and direct or queued resumes
cannot compose or launch an autoclose agent or send autoclose results to
automatic LLM analysis; successes complete through the script, failures stay
visible through deterministic reports, and regression tests prove these paths
without invoking real agents or cleanup operations.

Preserve the existing close predicates, checkout disposal proofs, daily
branch-sweep ordering, durable retire worklist, and deterministic notifications
and reports. The accepted tradeoff is losing automatically LLM-authored autofix
tickets for autoclose failures; unrelated recurring jobs retain their existing
analysis behavior. In a mixed recurring sweep, autoclose must neither trigger
analysis nor contribute its results to another job's analyst input.

## Context

### Verified current behavior

Verified from source, the audit log, and existing tests on 2026-09-30:

- `coga/recurring/autoclose-merged/ticket.py` invokes `runner.run_recipe` for
  `autoclose`, then `branch-sweep`, exiting immediately on either nonzero
  result. It invokes `coga bump` only after both succeed. Its packaged twin
  is `src/coga/resources/templates/coga/recurring/autoclose-merged/ticket.py`.
- `launch_script.script_entry_point` recognizes the exact `ticket.py` sibling.
  `launch_script.run_script_chain` stops on a nonzero exit; a successful script
  that leaves its step open can hand off to an agent under the generic hybrid
  contract. That general capability is not evidence autoclose needs an agent.
- `megalaunch._candidate_result` does not exclude script tickets, and
  `megalaunch._launch_until_stop` uses `_preflight_agent_launch` and
  `spawn_agent_session` without running their script. An in-memory copy of the
  actual autoclose period, restored to `in_progress` at `1 (sweep)`, passed
  that admission guard despite having a `ticket.py` sibling.
- The audit log records `recurring/autoclose-merged` exiting its script with
  code 2 at 10:00 on 2026-09-30, being resumed by megalaunch at 10:48, and being
  marked done by `agent:claude` at 10:50. The failure was a branch-sweep
  retirement-tag collision. The agent follow-up did not make the failed script
  successful. This evidence is in `coga/log.md`; the period ticket may be
  replaced, so do not depend on its continued existence.
- `recurring_runner.run_recurring_named` calls `recurring_autofix.run_autofix`
  after a run; scheduled scans do likewise. `run_autofix` calls
  `analyze_record`, which starts a one-shot agent subprocess. Analysis is
  enabled unless `COGA_AUTOFIX` disables it; that environment switch affects
  all recurring work and is not the requested autoclose-specific fix.

Cover normal completion, no-op completion, either recipe failing, retries of
unfinished periods, and megalaunch bare/picked/relaunch admission. A queue may
route autoclose through deterministic execution or refuse it with an actionable
message, but must never substitute an agent. Account for missing script
attachments or an unexpectedly open step without silently falling through to
an LLM. Keep failure evidence and unsuccessful status honest. Preserve existing
hybrid script/agent behavior for unrelated tickets; this is not a general
redesign of megalaunch or recurring autofix.

Identify autoclose independently of the current presence of `ticket.py`,
including existing period tasks. Keep the complete deterministic run record
separate from filtered analyst input: `recurring_autofix.run_autofix` currently
writes the run log before analysis, so bypassing it wholesale could lose
reporting. Exclude autoclose failure notes and scan errors from mixed-sweep
analyst input while preserving them in local reports. Explicitly requested
manual analysis is outside this ticket's automatic-execution scope.

### Owning contracts and verification

Cite rather than attach `coga/script-tickets`
(`docs/contexts/coga/script-tickets/SKILL.md`), sections **Classifier**,
**One deterministic phase**, and **Chaining**: script presence controls
dispatch, nonzero exits stop, and open steps currently allow agent handoff.
Cite rather than attach `coga/megalaunch`
(`docs/contexts/coga/megalaunch/SKILL.md`), **Sessions**, **Bare sweep**, and
**Explicit selection**: the queue currently composes agent sessions directly.
Cite rather than attach `coga/recurring/autofix`
(`docs/contexts/coga/recurring/autofix/SKILL.md`), **The loop** and
**Operating it**: automatic analysis consumes run records and is separate from
script execution. These are prospective editing targets; update the owning
contracts and their packaged twins in the same change.

Also inspect `coga/recurring/autoclose-merged/ticket.md`,
`coga/workflows/autoclose-merged/sweep.md`, and
`coga/skills/coga/autoclose/sweep/SKILL.md`, keeping their packaged twins in sync
when changed. The daily recipe composition is owned by
`docs/contexts/coga/recurring/scheduling/SKILL.md` (**What a sweep does per
template**); period attachment copying and failure reports are owned by
`docs/contexts/coga/recurring/templates/SKILL.md` (**The template-to-period
transform**, **ticket.py completion and reporting**).

Verification baseline: `.venv/bin/python -m pytest -q
tests/test_launch_script.py tests/test_recurring_shims.py
tests/test_autoclose_sweep.py` passed 54 tests; `.venv/bin/python -m pytest -q
tests/test_recurring_autofix.py` passed 66 tests. Add meaningful regression
coverage at the dispatch and analyst boundaries, including mixed sweeps, and
run the relevant megalaunch and packaging checks. Do not run a live autoclose
sweep just to reproduce the routing bug: its cleanup and notifications are real.

Prompt review identified the reusable implementation, PR, and PR-comment
skills as separate trimming candidates. Changing those shared skills is
outside this ticket; retain the chosen workflow and focused context citations.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
