---
name: marketing/map
description: Index of Coga marketing documents, their authority, source material, and owning tickets. Use to find the relevant material without composing the whole library.
---

# Marketing document map

Start with `marketing/plan` for the work sequence. This map locates the
material behind it; each linked file owns its subject. Read or attach only
what the current task needs. Paths below are relative to the repo root.

Coverage checked on 2026-09-09: the marketing contexts, marketing writing
skill, every current ticket/attachment under `coga/tasks/marketing/`, and
related strategy, evidence, cleanup and documentation work. Incidental mentions
in infrastructure tickets are not additional marketing source documents.

## Reusable knowledge and public entry points

| Material | Authored home | Role |
|---|---|---|
| Marketing work sequence, deliverables, phase gates | [marketing/plan](../plan/SKILL.md) | Current launch decisions and links to execution owners. |
| Pitch direction, audience, voice, honest limits | [marketing/positioning](../positioning/SKILL.md) | Reusable message; final pitch prose is a writing deliverable. |
| Channels, account evidence, audience measurement | [marketing/distribution](../distribution/SKILL.md) | Dated observations, distribution policy, scorecard and response branches. |
| Product purpose and bet | [docs/vision.md](../../../../docs/vision.md) | Product thesis; an output ratio is a bet, not a measured result. |
| Strategic reasoning and competitor research | [docs/market-thesis.md](../../../../docs/market-thesis.md) | Long argument and dated research; verify changing facts before using them in copy. |
| Reader's first screen | [README.md](../../../../README.md) | Introduction, example, install path and links; `marketing/readme-top` owns the launch revision. |
| Documentation and installation | [docs/README.md](../../../../docs/README.md), [getting started](../../../../docs/getting-started.md), [release guide](../../../../docs/releasing.md) | Reader path and release procedure. |
| Public operational observations | [docs/velocity-report.md](../../../../docs/velocity-report.md) | Dated evidence and counting limits; no productivity multiplier. |
| Retired launch programs | [marketing/launch-history](../launch-history/SKILL.md) | Historical reference; never attach as a live launch instruction. |

## Writing and evidence

| Material | Home | Role |
|---|---|---|
| Post production and checks | [marketing/write-post](../../../skills/marketing/write-post/SKILL.md) | Brief, objection check, outline, draft, review and publication gates. |
| Prose craft | [clarity](../../../skills/clarity/SKILL.md) and its `references/`, `scripts/` | The writing skill's craft dependency. |
| Audit observations | [step-1-findings.md](../../../tasks/marketing/phase-0-audit/step-1-findings.md) | September 2–3 evidence, preserved with a historical label. |
| Prior decisions and superseded audit brief | [audit-history.md](../../../tasks/marketing/phase-0-audit/audit-history.md) | Provenance for extracted facts, not an instruction to rerun the audit. |
| Private-repo narrative attachment | `coga/tasks/marketing/phase-0-audit/narrative-candidates.md` | Owner ruled every quotation unpublishable. Exclude it from writing source packets; the existing confidentiality ticket owns its disposition. |
| Usage tooling | `scripts/human_minutes.py`, `coga usage`, `--prompt-report` | Operational/historical tools; the marketing token experiment was dropped on 2026-09-09. |

## Execution and decisions that live outside contexts

| Work | Owning ticket |
|---|---|
| Audit extraction and current needs/drop ledger | [marketing/phase-0-audit](../../../tasks/marketing/phase-0-audit/ticket.md) |
| Make and decide the story and examples | [Story/example decision ticket](../../../tasks/marketing/plan/collect-public-examples-for-the-launch.md) — the existing collection ref is retained; its brief now requires creation and an owner decision. |
| Pitch, narrative, and supported copy | [marketing/plan/write-the-pitch-and-narrative](../../../tasks/marketing/plan/write-the-pitch-and-narrative.md) |
| Final campaign choices and keep/drop review | [marketing/build-the-launch-plan](../../../tasks/marketing/build-the-launch-plan.md) |
| Essays | [post 1](../../../tasks/marketing/post-async-megalaunch.md), [post 2](../../../tasks/marketing/post-you-own-it.md), [post 3](../../../tasks/marketing/post-doc-as-cache.md) |
| Landing page and community | [marketing/readme-top](../../../tasks/marketing/readme-top.md), [marketing/discord](../../../tasks/marketing/discord.md) |
| Product fixes, release, video and repo hygiene | [cleanup/README.md](../../../tasks/cleanup/README.md) and its nine sibling tickets |
| Audience follow-up | `marketing/phase-1-retro` — planned; create before post 1 with the baseline and dated checkpoints. |
| Telemetry proposal | [marketing/add-telemetry](../../../tasks/marketing/add-telemetry.md) — scope and any policy decision belong to that ticket; indexing it does not amend the current distribution policy. |
| Newer pitch and proposed library relocation | [documentation-reorganization ticket](../../../tasks/redo-documentation-dir-and-merge-it-with-context-b.md) |
| Audit lifecycle reconciliation | [existing status ticket](../../../tasks/phase-0-audit-is-complete-per-the-plan-but-still-i.md) |
| Confidential attachment disposition | [existing confidentiality ticket](../../../tasks/narrative-candidates-md-publishes-log-text-the-own.md) |
| Completed extraction of writing procedure | [writing-skill ticket](../../../tasks/no-comms-writing-skill-the-process-is-smeared-thro.md) — history only. |

## Authority and pending migration

The owner clarification recorded on 2026-09-08 in the documentation ticket
leads with managing the intent, instructions, knowledge and state an AI session
works from. `marketing/positioning` now records that direction. Final wording
and changes to the retained three-post campaign need owner review; a source
ticket's proposed opening is not approved copy.

Product purpose belongs in vision, product behavior in the relevant Coga
contexts/source, public message in positioning, and campaign policy in plan
and distribution. Resolve a conflict by its subject and dated owner decision;
do not propagate mutually overriding claims between documents.

The proposed move to `docs/contexts` is still at its own review gate. The
current configured root remains `coga/contexts`; this extraction does not
change configuration, install behavior, or the public documentation tree.
