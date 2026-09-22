# Does Coga's automated upkeep repay human attention?

Evidence reviewed on 2026-09-11. This answers the owner's challenge to the
overhead discussion in [the switching evaluation](build-vs-adopt.md).

**Finding:** Coga demonstrably automates the production and maintenance of
its operating documents. The evidence also shows incomplete delivery and
closure of knowledge. AI generation addresses manual writing; it does not
by itself establish that every useful correction reaches future work or
that total human attention is lower. Treat those as separate claims.

## What was inspected

The complete proposal batch from Dream period `2026-09-08` (W37), whose run
summary is dated September 9: PRs #763–775, all 13 PR metadata records and
their discussion/review timelines; local commit history; the corresponding
Dream transcript; and the prior September 2 Dream transcript as a second
check of the interaction counter. The generation phase is distinguished from
later review, repair and merge. No alternative product was run, no production
queue was launched, and no source code was changed for this audit.

## Observed results

| Part of the loop | Evidence | Judgment |
|---|---|---|
| Generate and organize maintenance work | The September batch produced 13 proposal PRs, 18 draft tickets and seven completed-ticket deletions. Its main session has only the composed launch prompt and 22 machine task notifications in user-text records. | Substantial document work proceeded with no additional human instructions recorded in that session. Watching, launching, later review and merge time are not measured by that fact. |
| Check the generated proposals | Automated review raised 22 inline findings across 11 of the 13 PRs, including four labelled P1. The returned threads contain replies addressing every finding; one disputed the proposed remedy and another qualified an unverified version claim. | The initial material required checking. Agent review reduces the burden of discovering those errors; the finding count is not an independently adjudicated error rate. |
| Turn proposals into durable changes | All 13 PRs were confirmed merged through GitHub. #773 and #774's commits explicitly credit agent drafting and repairs after agent review. | This batch reached merged knowledge, rather than stopping at suggestions. Neither a human account name nor a merge timestamp proves who typed each reply or how long the human inspected it. |
| Apply an accepted lesson later | #773 merged a warning about `coga launch --prompt-report` on September 9. On September 10 this marketing authoring session still used it and accidentally published the initial reset as `7a3d5643`. | A useful lesson existed but did not prevent the next relevant mistake. No claim is made that the cause was specifically a model ignoring a supplied warning: the record does not establish that it was supplied. |
| Close recurring findings | The routing-hole ticket records repeated validator issues and duplicate gap tickets; the September run summary retains 27 validator issues classified as human-needed and 34 done tickets held out of Retro because they carried recorded checkouts. | Detection and summarization did not close every issue. Those are run-date observations, not a claim that every item still needs action today, or that every parked item is unwanted work. |

Sources: [Dream run summary](https://github.com/FastJVM/coga/blob/9cb722546/coga/tasks/recurring/dream/ticket.md#dream-run-summary) (the 2026-W37 period ticket as frozen at commit `9cb722546` — the live path is rewritten every period; locally: `git show 9cb722546:coga/tasks/recurring/dream/ticket.md`),
[routing-hole record](../coga/tasks/dream-findings-have-three-routing-holes-that-lose.md),
[marketing incident](../coga/contexts/marketing/launch-history/phase-0-audit/audit-ticket.md),
[#773](https://github.com/FastJVM/coga/pull/773),
[#774](https://github.com/FastJVM/coga/pull/774).

The warning now remains in
[the codebase context](../coga/contexts/coga/codebase/SKILL.md), while guided
[ticket authoring](../src/coga/resources/templates/coga/bootstrap/skills/bootstrap/ticket/SKILL.md)
still instructs use of the CLI prompt report. This is a concrete delivery
problem: adding a correct fact to a context need not correct every procedure
or ensure every relevant task loads it. Later work in this session used the
pure composition API successfully; that demonstrates recovery after the
incident, not automatic prevention before it.

## Complete PR batch

All states below were fetched on September 11. A finding is a top-level inline
review comment by the review bot; replies and summary comments are excluded.

| PR | Subject | Inline findings | State |
|---|---|---:|---|
| [763](https://github.com/FastJVM/coga/pull/763) | Stale documentation claims | 0 | Merged |
| [764](https://github.com/FastJVM/coga/pull/764) | Launch internals | 1 | Merged |
| [765](https://github.com/FastJVM/coga/pull/765) | Measurement-claim scope | 1 | Merged |
| [766](https://github.com/FastJVM/coga/pull/766) | Branch-sweep contract | 0 | Merged |
| [767](https://github.com/FastJVM/coga/pull/767) | Sync and notification contracts | 3 | Merged |
| [768](https://github.com/FastJVM/coga/pull/768) | Skill and ticket templates | 1 | Merged |
| [769](https://github.com/FastJVM/coga/pull/769) | Architecture and workflow knowledge | 2 | Merged |
| [770](https://github.com/FastJVM/coga/pull/770) | Dream scan protocol | 2 | Merged |
| [771](https://github.com/FastJVM/coga/pull/771) | Review and checkout workflow | 2 | Merged |
| [772](https://github.com/FastJVM/coga/pull/772) | Import and authoring guidance | 3 | Merged |
| [773](https://github.com/FastJVM/coga/pull/773) | Codebase and extension-model contexts | 3 | Merged |
| [774](https://github.com/FastJVM/coga/pull/774) | Recurring-task contracts | 2 | Merged |
| [775](https://github.com/FastJVM/coga/pull/775) | Skill-update behavior | 2 | Merged |

The earlier 12-commit observation was a local `Dream:` subject search, not a
count of this entire batch. The complete batch has 13 merged PRs; subject
matching omitted one of their eventual commit subjects. No productivity ratio
is derived from either count.

## The attention counter is not usable without classification

The usage row at `coga/log.md:4586` reports `human_turns: 22` for session
`67cc0035-3dd9-4423-a446-e6d13f484413`. Inspection of that exact local Coga
transcript found 23 eligible user-text records: the composed launch prompt
plus 22 complete `<task-notification>…</task-notification>` messages. Removing
the notification blocks left zero additional text in all 22. The prior
Dream session `4d174194-960b-444a-b593-04078fb9a21e` contained only its launch
prompt in the same user-text classification.

[The Claude activity parser](../src/coga/usage.py) excludes tool results,
metadata and sidechains but counts remaining user text; it does not exclude
these notification blocks. These 22 events must therefore not be presented
as 22 human interventions. Conversely, zero further human instructions does
not prove zero attention or zero review time. No raw transcript quotations
or private-repository source material are reproduced here.

GitHub replies under the operator's account are also not a reliable count
of human writing: agents can use that account, as the credited repair commits
illustrate. Elapsed run time and the interval between PR merges are not
active human time. The legacy human-minutes estimator would not resolve
these attribution problems by itself, and was not run for this audit.

## What the theory actually predicts

AI can perform drafting, summarization, retrieval, comparison, deduplication
and repair because the work and its instructions share an editable file
interface. Humans can control that material without manually transcribing
it. That explains the observed autonomous generation phase.

The benefit nevertheless requires later use. A useful correction may avoid
repeated explanation or a repeated error across several tasks; an unused
correction earns no such return. Review, escalation and runtime repair remain
costs even when the draft was cheap to generate. Summarization can lower those
costs, but a concise inaccurate proposal still needs correction, and a correct
unselected context still cannot guide the next task.

The decision condition is comparative: for equivalent useful work and quality,
total human attention with Coga must be compared with total human attention
in the alternative workflow. Include explanation, review, supervision,
intervention, rework and tool upkeep on both sides. Setup and review that
would happen anyway are not differential Coga costs; subtract only additional
effort when assessing the value of work avoided. This is the owner's
September 11 clarification. The audit establishes neither a net attention
penalty nor a saving. The relevant denominator is useful work performed, not
documents, tickets or PRs generated.

## Answer supported now

**Manual document production: demonstrated as substantially automated in the
sampled runs. Reliable compounding: partial, with a directly observed missed
lesson. Total attention saved: not identifiable from the available telemetry.**

This supports retaining Coga's integrated workflow while prioritizing delivery
of accepted lessons and disposition of recurring findings. It does not support
closing the whole overhead question merely because most text is generated.
The owner has been asked for their actual review/intervention effort for this
specific batch; no estimate is assumed in its absence. That answer can refine
the attention judgment without reopening a marketing token experiment or
adding a launch gate.
