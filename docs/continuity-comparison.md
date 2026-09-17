# Is Coga's continuity exclusive or better?

**September 13, 2026.** Follow-up to the owner's endorsed
[single-task explanation](pitch-evaluation.md#draft-explanatory-paragraph).

## Answer

**The continuity is not exclusive as an operating pattern. Coga supplies
some stronger defaults for the owner's requirements; a better overall
learning or delegation outcome has not been demonstrated.** Compound
Engineering is the strongest counterexample. Its documented path already
connects a work definition, execution, captured lessons, reviewable changes
and retrieval for later work. The earlier real CE trial exercised several
of those transitions successfully.

The useful Coga distinction is more specific: selected context enters the
launch input, the task carries its human/agent stage, and recurring upkeep
has a defined route for changes to shared operating material. These are
concrete product choices. They do not establish that Coga is the only way
to preserve continuity or that its accepted lessons reach later work more
reliably.

## What was checked

The sequence is: define one job in editable material; execute and correct
it; preserve a useful lesson or method change; inspect and accept that
change; use it in a fresh later job. A job need not recur, and agents may
author the files throughout. Acceptance concerns shared guidance, not a
requirement for the human to type every correction.

This review read current primary CE protocols and the relevant Coga source,
re-examined the saved CE trial receipts and Coga's existing upkeep audit,
and used the earlier Superset/Kortix source inspection. It ran no new model
sessions or product deployments. The earlier CE proposal still awaits the
owner's decision; no approval or post-merge run is inferred from this review.

## The closest complete path: Compound Engineering

| Transition | CE's supplied procedure or observed behavior |
|---|---|
| One job to execution | [`ce-work`](https://github.com/EveryInc/compound-engineering-plugin/blob/main/skills/ce-work/SKILL.md) accepts a concrete prompt or plan. A [non-code production-plan route](https://github.com/EveryInc/compound-engineering-plugin/blob/main/skills/ce-work/references/non-code-execution.md) reads the named sources and produces the requested artifact. |
| Correction to durable knowledge | [`ce-compound`](https://github.com/EveryInc/compound-engineering-plugin/blob/main/skills/ce-compound/SKILL.md) can update an inaccurate learning. It supports knowledge about conventions and methods as well as bugs. In the trial it proposed a provider-scoped correction from saved work evidence. |
| Knowledge to reviewable change | [`ce-compound-refresh`'s commit policy](https://github.com/EveryInc/compound-engineering-plugin/blob/main/skills/ce-compound-refresh/references/commit.md) defaults to branch/commit/PR when running non-interactively from the default branch; other modes and branches have other policies. Ordinary Git isolation and review can also surround capture. This is not a universal CE guarantee that every new learning waits for human merge. |
| Saved lesson to a later job | The [planning researcher](https://github.com/EveryInc/compound-engineering-plugin/blob/main/skills/ce-plan/references/agents/learnings-researcher.md) retrieves relevant lessons and declared packs, including workflow discoveries, and carries them into plans. The [discoverability check](https://github.com/EveryInc/compound-engineering-plugin/blob/main/skills/ce-compound-refresh/references/discoverability.md) checks whether project instructions lead fresh agents to that knowledge. |
| A changed method to later execution | The non-code execution route follows the method and sources in the current plan. Planning explicitly incorporates workflow lessons. Editable skills and project instructions can change the surrounding procedure. The trial's fresh restart honored a directly edited requirement. |

These are connected procedures in one plugin over an existing agent, not
an invented combination of unrelated products. They rule out claiming the
general continuity pattern for Coga alone.

**The actual trial adds functional evidence.** Unmodified CE 3.24.0 at
`f050478dfc2b9621a2a75fbe58b37f2468d3af4a` ran code and non-code work,
resumed an edited brief in a fresh session, proposed a scoped lesson in a
separate worktree, and applied the proposal correctly to a new input in a
fresh preview task. That last task preserved a legacy rule and refused to
invent an unknown provider's convention. The
[receipt](../coga/tasks/marketing/phase-0-audit/adoption-trial-results.json)
and [trial report](adoption-trial.md) distinguish those passes from the
pending human decision and accepted-knowledge reuse.

The trial's 26-line coordinator was for queue selection, dependencies and
multiple saved jobs. The separately invoked knowledge and preview jobs did
not use it. For the owner's one-off-task question, that queue layer is not
evidence that CE needs custom orchestration to capture and reuse knowledge.
Project guidance, explicit source references and prepared Git isolation
were still supplied. Neither those conventions nor Coga's setup/review
prove a difference in human attention.

## Where Coga has a concrete advantage, and its limits

| Requirement | What Coga supplies | Comparative judgment |
|---|---|---|
| Deliver the explicitly selected context | [`compose_prompt_report`](../src/coga/compose.py) reads each named context into the launch input and errors when the reference is missing. | A stronger built-in delivery mechanism than a prompt merely asking an agent to find/read knowledge. This covers selected context; it does not discover every needed lesson or guarantee the model uses it correctly. CE also supports named sources and active retrieval. |
| Carry a human decision across task stages | The [launcher](../src/coga/commands/launch.py) stops chaining at a recorded human/unassigned next step. The existing [isolated checks](../coga/tasks/marketing/phase-0-audit/source-inspection-results.json) exercised this and live context/method edits. | More explicit runtime support than leaving all stage routing to agent instructions. The earlier CE trial also held its human gate successfully, so the code distinction is not a demonstrated outcome advantage or a universal action-permission boundary. |
| Keep proposed shared guidance behind review by default | [Dream's disposition procedure](../coga/recurring/dream/ticket.md) sends stale context/skill and contract fixes through proposal PRs and forbids auto-merge. | A closer default fit to the owner's human-merged guidance requirement than CE's mode-dependent capture/refresh paths. This is a supplied protocol; an equivalent Git-review policy can be used with CE or other agents. |
| Maintain the working instructions as well as lessons | Dream audits repo-authored contexts, skills, recurring templates and documentation, proposes fixes and creates design tickets for gaps. CE's [refresh scope](https://github.com/EveryInc/compound-engineering-plugin/blob/main/skills/ce-compound-refresh/SKILL.md) maintains its learning store and reports contradictions with named guidance, while forbidding edits to the skill/runbook/instruction layer itself apart from its separate discoverability procedure. | Coga supplies broader upkeep of the operating material. CE can change that material through other agent work and can refine declared pack rules; broad maintenance is a difference in the provided procedure, not an exclusive capability. |
| Avoid repeating a mistake after accepting a lesson | Coga's [upkeep audit](upkeep-audit.md) found a relevant warning had merged before a later task repeated the mistake; the record does not establish whether the warning reached that task. | No established Coga superiority in reliable reuse. Producing or merging knowledge is not enough; selection, delivery and application still matter. The CE preview is a positive small example, not a matched reliability comparison. |

For someone requiring explicit task state, selected context and a standard
review route, Coga therefore has a defensible advantage in supplied controls.
For the narrower task-to-lesson-to-next-task sequence, the evidence gives no
compelling reason to call it better than CE. Output quality, repeated
explanation, interventions and total upkeep were not measured under matched
conditions. Their relative merits remain undecided, rather than equal by
default.

## The other relevant alternatives

| Alternative | Continuity and the remaining product difference |
|---|---|
| [Backlog.md](https://github.com/MrLesk/Backlog.md) | Local Markdown tasks and review already preserve the work definition and its corrections. A repository knowledge file, agent instructions and Git review can carry lessons to later tasks. That last connection is a configured working method here, not a verified stock Dream equivalent. Coga supplies more of the launch, stage and upkeep procedure. |
| [Superset](https://docs.superset.sh/tasks) | The inspected code composes task and linked context for existing agents. Reusing and reviewing repository instructions can happen within that environment; [scheduled agent work](https://docs.superset.sh/automations) can perform maintenance. A built-in equivalent of Dream was not established. Coga puts the authored task/method/context files at the center of its provided experience. Which interface is preferable is a user preference, not a quality result. |
| [Pi](https://pi.dev/) | Reusable Markdown prompts, skills, project instructions and context/memory extensions support continuity around an adaptable agent. Task-state and shared-knowledge review conventions need to be supplied or selected. Coga provides a particular method around existing agent CLIs. No Coga/Pi integration was tested. |
| [Kortix](pitch-evaluation.md#follow-up-source-inspection) | The prior source check found persisted session state, sandbox/runtime provisioning and change-request policy; its documented project model also keeps operating files in Git. Its platform approach overlaps with the broader continuity thesis. Coga's local agent layer remains a concrete architectural choice; the inspection does not establish a better operating experience in either direction. |

## Consequence for the message

Keep the endorsed explanation. It accurately communicates a useful product
choice. Do not promote continuity itself to an exclusive discovery. The
stronger claim to demonstrate is a lightweight task layer that supplies
explicit context, responsibility and reviewed upkeep while leaving the
work and method editable. Lead with the first delegated job; show the
additional controls when the job benefits from them.
