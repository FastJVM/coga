# Trying a Coga replacement — 2026-09-11

**Observed so far:** unmodified Compound Engineering skills, a short queue
instruction file and ordinary Git reproduced the small prepared-work queue,
its code/non-code handoffs, a held human decision, and a fresh restart from an
edited task definition. CE also proposed a scoped correction to stale shared
knowledge in an isolated worktree. A fresh preview task applied the proposed
lesson correctly using new data and no old code or conversation. Human approval
and reuse after the actual merge remain pending; this is not yet a completed
replacement verdict.

The owner requested an actual attempt after the source comparisons. This
trial tests the useful operating model, not whether another tool copies
Coga's commands. It uses invented Cedar Workshop data in `/tmp`, with no
actual Coga migration, remote publishing or changes to the current ticket's
lifecycle. The [structured receipt](../coga/tasks/marketing/phase-0-audit/adoption-trial-results.json)
preserves the fixture, prompts, added instructions, checks and run reports.

## Candidate and integration

- Compound Engineering 3.24.0, revision
  [`f050478dfc2b9621a2a75fbe58b37f2468d3af4a`](https://github.com/EveryInc/compound-engineering-plugin/tree/f050478dfc2b9621a2a75fbe58b37f2468d3af4a),
  loaded through `--plugin-dir` into the installed Claude Code 2.1.269 CLI.
  The plugin files were not modified.
- CE's `ce-work` executed both a code plan and a non-code production plan;
  `ce-compound` proposed the knowledge correction. Each CLI run used a fresh
  session, with automatic memory and session persistence disabled. Native
  workers received separate task contexts.
- **Added:** a 26-line, 260-word `operator.md` tells the coordinator to read
  saved plan status/dependencies, dispatch eligible plans through CE, record
  evidence, hold human gates and continue other work. Project guidance names
  the accepted lesson directory and excludes unmerged proposals. These are
  custom integration instructions, not a shipped CE queue feature. The
  accompanying project guidance is 15 lines, 117 words.
- **Added:** ordinary Git worktrees isolate proposed knowledge from the
  accepted-source checkout. The evaluation operator prepared that isolation
  and invoked the knowledge task; this was not an automatic CE recurring job.
- A Python wrapper launches the CLI, limits a run and records output. It has
  no task selection, dependency, workflow or knowledge-selection logic; those
  behaviors are performed by the agent reading the maintained files.

The fixture, observation wrapper and oracle checks are test apparatus.
Neither their preparation nor the existence of review is evidence of
differential attention. No matched human-effort measurement was performed.

## Exercises and observed results

| Exercise | Result |
|---|---|
| Run an eligible engineering task | **Pass.** Corrected a case-folding bug, observed failing tests before the fix, passed seven tests and saved the expected count of three. |
| Continue a dependent non-code task | **Pass.** The coordinator observed the completed dependency, used CE's knowledge-work path and produced a brief from the saved count. |
| Hold an independent human gate | **Pass.** The announcement remained `awaiting-human`; no channel was invented and no announcement artifact was created. Other work proceeded. |
| Preserve authoritative task and working state | **Pass.** Plan files carry status, context/source refs and completion evidence; the queue report records the remaining human decision. |
| Restart after directly editing a task | **Pass.** A new coordinator used a changed word limit and exact sentence, rewrote only the reopened brief, and preserved the completed code and human gate. The new brief is 23 words. |
| Propose a correction from completed-work files | **Pass.** A separate CE session updated the stale lesson from the ticket, verification report, code/tests and recorded provider decision, without its original conversation. |
| Keep unmerged knowledge out of the accepted source | **Pass.** The correction exists only in the proposal worktree; the accepted-source file retains its pre-review content. Ordinary tasks did not modify it. |
| Preview reuse in a fresh task | **Pass, preview only.** With only the proposed lesson and new input data, a fresh CE task returned counts of two for CedarPass v2, one for LegacyPass, and `null` for a provider without a confirmed rule. It read the lesson and distinguished proposed from accepted knowledge. |
| Human edit/reject/merge | **Pending.** The owner has been shown the concrete scoped rule and a recommended removal of an unsupported causal claim. No approval is assumed. |
| New task uses accepted knowledge | **Pending.** An isolated preview may test the proposed rule, but cannot count as reuse after human merge. |

The first queue passed nine fixture checks. Restart and proposal isolation
passed eight further checks. These are checks within one small scenario,
not 17 independent trials or a reliability estimate. There was no manual
task-by-task routing or correction of the generated code between those runs.

## Problems and limits that remain visible

The initial CLI call could not reach the model inside the network sandbox;
the authorized network retry succeeded. Restrictive test-tool permissions
also rejected some shell forms, and the agent recovered through permitted
tools. Initial skill-path discovery was indirect; subsequent prompts supplied
the exact installed path. These are recorded harness issues, not evidence
that CE cannot perform the work.

The restarted worker reported that its final mandatory reread of a CE
reference was skipped as a duplicate. The output passed the independent
checks, but the prescribed protocol was not followed perfectly.

The knowledge proposal correctly preserved the distinction between
case-sensitive CedarPass v2 IDs and case-insensitive LegacyPass IDs, instead
of replacing one universal rule with its opposite. It also claimed that the
old document caused the original implementation mistake, which the available
evidence does not establish. The review version removes that causal claim.

This does not test a machine crash during an active write, concurrent
operators, launch claims, a large queue, dependency cycles, recurring-job
scheduling, or remote PR delivery. Coga's existing history and previous
isolated checks are reference evidence, not a newly matched trial. No
comparative attention, output-quality or maintenance-cost result follows
from the observed model run times.

## What this changes in the comparison

A standing collection of independent Markdown tasks is no longer merely a
theoretical CE integration: the added instructions operated this collection
and resumed it from saved files. The exercised queue did not require a new
programmatic task runner. The integration remains the operator's
responsibility, but AI authored it;
its existence is not proof of extra human attention.

The trial explicitly supplied Coga-inspired conventions and prepared Git
isolation. It establishes a working alternative for the tested capabilities;
it does not show that stock CE provides the same operating experience.
The small instruction file is not a measurement of ongoing maintenance or
human attention. Those comparisons remain open in both directions.

The initial conclusion that this materially weakens Coga's differentiation
was too broad. Reproducibility limits a claim of technical exclusivity.
The value of Coga's method, defaults and maintained runtime still depends
on the experience they give users. No loss of usefulness or reason to switch
was demonstrated. The full review-and-reuse result will determine how far
this particular replacement attempt gets; even completion would not by
itself establish a preferable product. The [positioning context](../coga/contexts/marketing/positioning/SKILL.md#pitch-candidate-your-way-of-working-made-executable)
owns the resulting pitch candidate.
