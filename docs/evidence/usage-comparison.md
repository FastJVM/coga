# Coga and the competing ways of working

**Within the ten-tool usage comparison, Coga is moderately differentiated
overall. Its strongest difference is the
provided operating model for an ongoing collection of jobs: maintained work
instructions, selected knowledge, saved workflow stages and human handoffs,
with proposed improvements to the shared material.** That can substantially
change the experience of someone currently managing agent conversations. It
adds much less to someone already executing maintained tasks or plans with a
satisfactory knowledge and coordination process.

The idea belongs to an established family. Editable prompts, document-driven
execution, adaptable methods and reviewed knowledge all have concrete
precedents. The most challenging alternatives are Compound Engineering with
the small coordination layer already exercised in the [adoption trial](adoption-trial.md),
and GitHub Agentic Workflows for scheduled operations. Coga's reason to exist
is the usefulness of the complete system it supplies; a claim to have
invented these ingredients would be inaccurate.

This assessment covers the ten tools in the current marketing comparison.
Primary usage documentation and execution protocols were checked on
September 12, 2026. These describe supported ways of working, not how often
customers use them. Observed execution evidence is limited to the existing
Coga records and the pinned CE trial. The other products were not run in a
matched exercise. Current upstream CE documentation is distinguished from
the revision used in that trial.

The later [source-code inspection](#source-code-distinction-from-langgraph-and-crewai)
establishes a substantial product distinction from LangGraph and CrewAI.
Those two are additional architecture comparisons, outside the original ten.
The earlier overall judgment must not be stretched into a claim that Coga is
merely another implementation of an agent application framework.

For communication, [the corresponding ten-tool message comparison](why-switch-to-coga.md#communicating-the-work-loops)
turns these procedures into an angle for each product's users. It follows
what the person directs and corrects, what carries into later jobs, and the
specific Coga experience to demonstrate. Candidate copy and its illustrative
launch story are kept there; the evidence and magnitude judgments remain here.

## Source-code distinction from LangGraph and CrewAI

**September 12, 2026.** The owner challenged the generic framework framing
and requested inspection of Coga's implementation. The source supports a
concrete distinction: **Coga operates existing agent programs from maintained
work instructions and ticket state.** The LangGraph and CrewAI execution
paths inspected supply runtimes for applications assembled from their graph,
agent and task abstractions. This changes what the operator builds, edits
and runs, even though all three can describe their work as orchestration.

### What Coga actually executes

1. **The brief and selected operating material become the launch input.**
   `compose_prompt_report()` reads repository context, each attached context,
   task skills, the current workflow step's instructions, the task's
   Description/Context and its blackboard. `_step_layers()` reads the selected
   skill files or current inline step text from disk. These are the inputs
   to execution, not documentation generated after an application runs.
   [Composition source](../../src/coga/compose.py).
2. **The worker is an existing agent CLI.** `build_agent_command()` builds
   argv beginning with the configured `agent.cli`. `spawn_agent_session()`
   passes the composed input to that command; the supervisor uses subprocess
   execution or a PTY and `exec`. Claude Code and Codex retain their own
   agent/tool loops. Coga supplies the surrounding work and lifecycle model.
   [Launch source](../../src/coga/commands/launch.py),
   [process supervisor](../../src/coga/repl_supervisor.py).
3. **The handoff belongs to the ticket.** `Workflow.load()` parses ordered
   steps with role tokens; `freeze()` records their sequence and references.
   `advance_step()` writes the new step/assignee through ticket IO, and
   `_harness_stop_reason()` checks the reread ticket to continue to another
   configured agent or return to the human. Megalaunch applies corresponding
   eligibility and blocker checks. The enduring object is the job and its
   recorded progress through a human/agent procedure.
   [Workflow](../../src/coga/workflow.py), [step movement](../../src/coga/bump.py),
   [ticket IO](../../src/coga/ticket.py), [queue](../../src/coga/megalaunch.py).
4. **Chat is also a way to author that material.** Guided ticket authoring
   copies the ticket into an authoring view, substitutes the authoring skill
   and removes the current step from that view. It then uses the same agent
   launch machinery. The real workflow remains recorded on disk while the
   discussion helps revise the work definition.
   [Authoring source, `_authoring_ticket()`](../../src/coga/commands/ticket.py).
5. **Deterministic work can use the same job container.** The exact sibling
   `ticket.py` selects a script phase, run in a subprocess before any agent
   phase. The runtime rereads the task afterward to decide what remains.
   The script is ordinary Python; a distinct name in the fixed recipe
   registry serves package-owned deterministic contracts.
   [Script dispatch](../../src/coga/launch_script.py),
   [fixed recipes](../../src/coga/runner.py).
6. **The operating method includes its own maintenance.** The `dream` alias
   expands to `recurring launch dream`. Generic recurring code loads the
   named template and materializes an ordinary task, using `direct/body`
   when the template supplies its process in the body. Dream's ordered
   phases and proposal policy are therefore executable task material too.
   Its shipped body instructs the agent to propose context/skill corrections
   through PRs and raise design tickets for missing methods. The human
   merge rule is in this operating protocol; the probe did not test agent
   adherence to it or execute a knowledge merge.
   [Alias](../../src/coga/aliases.py), [materialization](../../src/coga/recurring.py),
   [shipped Dream task](../../src/coga/resources/templates/coga/recurring/dream/ticket.md).

The distinctive relationship is that **the working instructions, the work
record and the procedure for improving the instructions are all ordinary
material in the work system**. Humans and agents operate on it through files
and commands. That is the concrete meaning behind the owner's emphasis on
the Markdown entry point and hackability of the method.

### What the framework source comparison establishes

In LangGraph, `StateGraph.add_node()` wraps actions as runnables;
`compile()` constructs a `CompiledStateGraph` with nodes, channels, stores,
checkpointing and interrupt settings. The Pregel loop schedules runnable
tasks, processes channel writes and checkpoints execution. This is an
application runtime whose executable behavior comes from the supplied graph
actions. [Graph construction](https://github.com/langchain-ai/langgraph/blob/main/libs/langgraph/langgraph/graph/state.py),
[runtime loop](https://github.com/langchain-ai/langgraph/blob/main/libs/langgraph/langgraph/pregel/main.py).

In CrewAI, `Crew.kickoff()` enters the crew execution path and `_execute_tasks()`
dispatches task execution. `Agent.create_agent_executor()` supplies an LLM,
tools, prompts and execution parameters to the chosen executor class. A
configuration or instruction file can contribute to this application, but
the inspected worker is a framework agent executor.
[Crew execution](https://github.com/crewAIInc/crewAI/blob/main/lib/crewai/src/crewai/crew.py),
[agent construction](https://github.com/crewAIInc/crewAI/blob/main/lib/crewai/src/crewai/agent/core.py).

Both frameworks can be extended to invoke CLIs, read Markdown, include
human decisions or implement maintenance workflows. The difference established
here is the provided product and its operating boundary, not an inability
to reproduce it. Upstream `main` source was read on September 12; neither
framework was executed in this follow-up.

### Verification and message consequence

An isolated fixture exercised Coga's actual composition, command construction,
handoff classifier and script classifier. Thirteen checks passed: selected
files enter the current-step prompt; edits to context, brief and live method
change its next composition; later-step instructions stay out; the frozen
step sequence stays intact; agent rotation selects another external CLI;
and the human handoff returns to the caller. The reserved script was detected
but never executed. No agent was launched and no Git publication occurred.
[Recorded checks and source revision](../archive/launch-programs/phase-0-audit/source-inspection-results.json).

The supported marketing correction is substantial: **lead with operating
work through existing agents from a shared, editable body of instructions**.
The generic phrase “hackable agentic framework” loses that distinction.
The assistant proposed **“An executable operating manual for humans and
agents”**, then withdrew it after the owner found it unclear. Preserve the
concrete explanation: tasks assign the work, contexts supply accepted
knowledge, workflows define how it proceeds, and agents can propose
improvements to those operating instructions. The owner's subsequent
[AGI-ready proposal and claim check](why-switch-to-coga.md#agi-ready-proposal-and-claim-check)
record a new positioning thesis without changing this source-code finding.

This supplies a concrete identity and a demonstration, rather than a claim
of worldwide exclusivity. The narrower alternatives remain the actual
agent-operation tools and methods assessed elsewhere in this report,
especially configured CE and GH-AW for their respective use cases. Their
overlap is not erased by the stronger contrast with an application framework.

## Core flexibility across administrative and patent work

**September 12, 2026 — owner-requested local source inspection.** The owner
identified the admin and patents repositories as examples of flexibility in
Coga's core. Read their workflows, recurring definitions, selected Python
implementations and task metadata. This records generic operating structures;
private business records and narrative quotations are not publication sources.
No job, notification, financial action or filing was executed in this review.

| Inspected example | What the implementation expresses | Implication for Coga's scope |
|---|---|---|
| Admin reminders and monthly routines | Repository scripts read maintained task/template state, calculate the relevant period and prepare notifications. A recurring workflow invokes the named script and records the run; the underlying business action remains with the human. | A completed task can mean that an obligation was surfaced, without claiming that the obligation itself was fulfilled. Recurrence and business completion are separate concepts. |
| Admin preparation and human action | The local `human-gated` workflow specifies agent preparation, owner action, then agent verification and recording. Separate browser workflows describe unattended operation, human review/action, or human execution with agent support. | The repository defines procedures and responsibility boundaries appropriate to the operation. These are workflow definitions; their existence alone does not prove successful execution of every variant. |
| Patent lifecycle | The local workflow represents idea, optional provisional, candidate and granted-utility stages. Domain fields record the case's facts. Separate local scripts inspect those fields, detect changes and identify items needing attention; stage advancement is assigned to human confirmation by the written method. | A task can represent a case maintained over years. A workflow stage can describe the condition of that case, with several kinds of work occurring within it. |
| Proposed invention disclosures | A skill combines a deterministic source gatherer, agent screening and drafting, a human selection step and creation of approved candidate tasks. The gatherer's pending state is separate from its accepted scan state. | Domain judgment, ordinary scripts, human decisions and durable follow-up work can be composed into a repository-owned method. This inspection did not run the scanner or assess its output quality. |

Local evidence locations: `admin/coga/workflows/{human-gated,surface-due-and-notify}.md`,
`admin/coga/workflows/browser/`, the supplier-reminder and payroll-reconciliation
scripts beside their tasks; `patents/coga/workflows/patent/lifecycle-v2.md`,
the sweep/sync scripts under `patents/coga/tasks/repo/`, and
`patents/coga/skills/coga/auto-disclosure/{SKILL.md,gather.py}`. These paths
are relative to the owner's local directory of checkouts, not public links.
Task frontmatter includes completed admin reminder instances and active
patent lifecycle records; that is persisted usage evidence, not independent
verification of the underlying business outcomes.

The current Coga source supports the architectural explanation. Its
[configuration parser](../../src/coga/config.py) accepts declared extension
fields and repository-owned extension tables. The generic
[workflow parser](../../src/coga/workflow.py), [composer](../../src/coga/compose.py)
and [launcher](../../src/coga/commands/launch.py) operate on task state and
selected instructions. The inspected domain calculations live in repository
scripts using files and CLI calls; the core has no special dispatcher for
these administrative or patent procedures. Coga still ships coding workflows
and package commands such as PR handling. The supported claim is flexibility
of the shared task/workflow machinery, not that the package contains no
domain-oriented facilities.

**Version boundary:** some patent recurring templates still use older inline
script syntax. Current core instead recognizes the reserved sibling
`ticket.py` for a deterministic launch phase. The examples establish actual
authored methods and local implementations; this review does not certify that
every checkout is migrated or runnable unchanged against current Coga.

**Comparison with Compound Engineering:** its
[published default loop](https://github.com/EveryInc/compound-engineering-plugin)
centres on building and reviewing software. However, its explicit
[non-code execution route](https://github.com/EveryInc/compound-engineering-plugin/blob/main/skills/ce-work/references/non-code-execution.md)
produces knowledge-work deliverables while bypassing the coding/shipping
stages. Our earlier CE trial also executed a non-code plan. “Engineering
only” is therefore inaccurate. The defensible distinction is that CE supplies
an engineering-centred method with broader routes, while Coga's common task
runtime supports independently authored methods for recurring operations,
ongoing cases and deliverables. This is a concrete product-scope distinction;
it does not establish that CE cannot be extended to reproduce the examples.

Together with the moving-frontier thesis, these examples supply two forms of
adaptability: the method can vary with the domain of work and can be revised
as the available agents become more capable. The interface for human
direction remains useful across both changes. Neither future capability gains
nor a matched cross-domain superiority claim was tested here.

## What counts as a substantial difference

A different filename, command or launch button is a small difference. A
substantial difference changes what the operator maintains, how work waits
for decisions, or how the next session and next job acquire their instructions.
The comparison therefore follows five actions: define the work, execute it,
correct it, return to it, and reuse what was learned.

The relevant baseline includes normal configuration and documented extensions.
A person using Pi with a workflow package, or VS Code with custom agents,
does not have the experience of an empty installation. Conversely, a documented
pattern that requires assembling a queue and its policies is not evidence
that a complete application already supplies those choices. Both facts matter;
neither alone establishes extra human effort.

The judgments below concern the magnitude of the work-model difference for
the stated need. They are not product-quality scores or measured reasons to
switch. Setup and review common to both alternatives are not differential
costs. No comparative attention saving or penalty has been demonstrated.

## The Coga experience, grounded in its own use

A job has a maintained brief, selected contexts, a workflow and a blackboard.
The workflow records agent and human responsibilities; the ticket saves its
current step independently of its lifecycle status. A new launch composes
supported sections of these files. Chat can help prepare and revise them,
and agents can do most of the writing. A human can also edit, copy or script
the same source material directly.[^1][^2]

There are real distinctions between jobs. The packaged code design workflow
progresses through design, independent evaluation, owner design review,
implementation, PR preparation and owner review. The marketing audit uses
`draft-for-human`, whose current saved step is `human-owns-and-finishes`.
The latter remains an ongoing human-owned job while research and revisions
continue; it need not be converted into a code-delivery pipeline.[^3][^4]

Megalaunch services eligible work within a selected scope. Its dependency
drain can revisit blocked tickets after named task dependencies finish;
unresolved human questions retain their own treatment. This is saved job
state that directs subsequent execution. The ordinary sweep is sequential;
it should not be sold as a faster parallel-workspace manager.[^2]

Dream reads completed work and operating documents to propose improvements.
The audited September batch produced 13 proposal PRs, all subsequently merged,
with agent-generated findings and repairs. This establishes a functioning
maintenance process. It does not establish reliable improvement: an accepted
warning about launch side effects failed to prevent a later relevant mistake.
The correction's delivery into the next task matters as much as its existence.[^5]

The implementation also limits the prompt-control claim. Coga composes
`Description`, `Context` and blackboard content, alongside selected contexts
and step instructions; an arbitrary top-level section can be omitted. Base
and session-conduct prompts are packaged resources, and the host supplies
additional instructions. Workflow step metadata is frozen for an existing
ticket, so changing a template does not silently replace that ticket's stages.
The useful promise is control over supported work instructions and methods,
not immediate project-file control over every instruction seen by the model.[^2][^6]

## Comparison at a glance

These are analytical judgments from the detailed usage comparisons below.

| Alternative | What the operator normally returns to | Magnitude and location of Coga's difference |
|---|---|---|
| [Zed](#zed) | Agent thread and project/worktree | **Substantial addition** when the need is a standing job process; small benefit for session persistence alone. |
| [Superset](#superset) | Task, workspace and agent/coordinator session | **Moderate:** canonical job/workflow files and a supplied knowledge-maintenance process; heavy overlap in delegation. |
| [Pi](#pi) | Agent session plus chosen files and packages | **Substantial supplied structure relative to core Pi; small prompt-control distinction.** Configured packages can narrow the gap. |
| [Compound Engineering](#compound-engineering) | Plan, execution evidence, skills and reusable lessons | **Small to moderate:** Coga's standard standing-job runtime. The closest exercised alternative. |
| [Backlog.md](#backlogmd) | Editable task, plan, acceptance criteria and board | **Small in authoring; moderate in operation:** Coga supplies execution, per-job stages and knowledge upkeep around the task. |
| [Kiro](#kiro) | Spec artifacts, execution sessions and steering | **Small for a coding feature; moderate for broader job operations** and the explicit knowledge-acceptance policy. |
| [GitHub Spec Kit](#github-spec-kit) | Specification, plan and implementation task list | **Small in document-directed work; moderate for a standing collection of independently staged jobs.** |
| [GitHub Agentic Workflows](#github-agentic-workflows) | Workflow file, Actions run and GitHub work records | **Moderate interaction difference; strong conceptual overlap.** Coga serves local attended work through the same job model. |
| [Agent Orchestrator](#agent-orchestrator) | Worker session or persistent project coordinator | **Moderate:** authored job/workflow authority and reviewed shared knowledge; ongoing orchestration is already present. |
| [VS Code](#vs-code) | Agent session plus prompt/skill/agent files | **Moderate as an added task system; small for reusable instructions and guided handoffs alone.** |

## Zed

The documented sequence is to open an agent thread, choose the agent, write
the request and attach relevant context. The operator watches edits, reviews
diffs and sends corrections. Messages are editable. Several threads can run
independently, optionally in separate worktrees. The operator can restore
history, refer to another thread, or start a new thread from a summary;
availability varies with external-agent integrations.[^7]

Instructions are not confined to that conversation. Project and personal
instruction files supply persistent guidance; named skills carry reusable
procedures. Files, directories and other context can be explicitly attached
to a request. A Zed user can therefore work from a maintained brief and
correct shared instructions without adopting Coga.[^7][^8]

**What changes with Coga:** the return point becomes a job whose brief,
responsibility, stage and selected knowledge are maintained independently of
the thread. The operator can resume the job by launching its saved definition,
and can manage other jobs and knowledge proposals using the same conventions.
That is a substantial addition when thread management has become insufficient.

**When the difference is small:** the work consists of independent coding
conversations and the main problem was restoring workspaces after restarting.
Zed already addresses that reported need. Coga has not demonstrated a better
editor or conversation experience; adoption can leave Zed in place.

## Superset

Superset's Tasks view accepts native tasks and imported issues. The operator
edits the description and properties, selects one or several tasks, then runs
them in workspaces with a chosen agent. Task content becomes the prompt
through an editable per-agent template; automatic submission can be disabled
to inspect the prepared command. Results proceed to branch/PR review.[^9]

The shipped orchestration skill lets the current agent coordinate workers:
create isolated workspaces, send bounded assignments, monitor terminals,
deliver follow-ups and collect completion or blocker reports. This already
automates substantial coordination.[^10]

For recurring work, the operator saves an automation prompt, project or
session mode, target device and schedule. Each run creates a workspace that
can be inspected and continued. The documented automation success state
means workspace creation succeeded; it does not attest that the agent
completed its task. Outcome inspection remains in the workspace.[^11]

**What changes with Coga:** maintained repo files become the authoritative
job and workflow records, and knowledge maintenance has a supplied proposal
process. A job's stage and human responsibility can continue across launches.
This is a moderate change in how operations are represented and maintained.

**When the difference is small:** the person wants task delegation, parallel
branches and consolidated review. Superset already provides that process.
Editable prompts and recurring execution are not missing. Using Coga's
instructions within a Superset workspace is a possible combination, not a
verified integration or a reason to replace the workspace application.

## Pi

Pi's ordinary interface is an agent session with a message editor. The
operator can use an external editor, expand Markdown prompt templates, load
skills, steer ongoing work and resume or branch persisted sessions. Files
can be supplied as input. Project-level `SYSTEM.md` can replace the default
system prompt; separate append and resource-loading controls are available.[^12]

Pi deliberately leaves workflow choices to extensions, skills and packages.
Its extension API covers tool-call interception, context injection,
compaction, commands, custom interfaces and persisted state. The documentation
includes working examples and explicitly supports agent-assisted extension
creation. A usable configured Pi system need not be manually built from
scratch by its human operator.[^13]

**What changes with Coga:** the operator chooses an existing task/context/
workflow/knowledge system, with a job lifecycle already implemented. Relative
to core Pi that is a substantial amount of supplied structure. It is not
superior prompt ownership: Pi's documented project-level system-prompt
override is more direct than changing Coga's packaged base resource.

**When the difference is small:** existing Pi files and packages already
provide the desired method. CE also lists Pi among its supported targets,
making Pi plus CE a concrete documented stack to consider, although that
combination was not exercised here.[^14] The adoption case is choosing
Coga's particular working system; hackability alone gives little reason to
change. Pi and Coga also occupy potentially complementary layers, subject
to validating an integration.

## Compound Engineering

CE takes work through planning, execution, review and knowledge capture,
passing durable artifacts between stages. Its execution skill accepts a
plan/spec path, checks readiness and prerequisites, then operates the plan.
Recovery instructions can identify an existing external run and resume its
recorded state. The plan is an operating input even when its invocation
comes from chat.[^14][^15]

Knowledge work has an explicit execution path: read the production plan and
named sources, synthesize the deliverable, then save it durably. It omits
inapplicable code-shipping machinery. Mixed code and document work is
therefore real overlap, not an imagined future extension.[^16]

Reusable knowledge is more than an archive of task summaries. `ce-compound`
captures qualifying verified reasoning and updates a stale existing lesson
when appropriate. Experimental Compound Packs supply prescriptive domain rules
to planning and review. The refresh protocol supports branch-and-PR proposals
on the default branch; feature-branch handling differs. Human-reviewed
knowledge is supported, although acceptance isolation must be deliberately
maintained for the required policy.[^14][^17][^18][^44]

**What changes with Coga:** a standing collection of independently staged
jobs, role resolution, blocker handling and maintenance is the supplied
runtime. CE's work protocol already supports a caller owning later stages,
so the boundary is not an immutable CE pipeline versus an editable Coga
workflow.[^19]

**Magnitude: small to moderate, with the strongest evidence of a usable
alternative.** The [actual trial](adoption-trial.md) added a 26-line queue
instruction file and Git isolation, then exercised code and non-code work,
a held human decision, restart from an edited task, a knowledge proposal and
fresh preview reuse. These were Coga-inspired conventions added around
unmodified CE skills. The result limits a claim of a large missing capability;
it does not measure whether maintaining that setup is better or worse than
Coga. A feature-oriented CE user already satisfied with their process has a
weak switching reason. The trial's actual human merge remains pending.

### CE refresh, Dream and the communication angle

The loops have a more concrete distinction than the existence of a memory
feature. CE's standard sequence develops a change and captures reasoning
for subsequent work. Its separate refresh skill audits the captured
`solutions/` corpus. When a lesson conflicts with a named skill, runbook or
instruction file, refresh reports the conflict and explicitly leaves that
guidance unchanged. This is the scope of this skill, not a claim that the
whole CE plugin cannot edit working methods.[^42][^44]

Coga's recurring Dream pass scans the operating corpus, extracts completed
work, and checks knowledge and contracts. Stale contexts or skills become
proposal PRs; a missing context, skill or workflow becomes a draft ticket
for human design judgment. Knowledge changes require human acceptance.
The work definition and the method governing work are therefore explicit
subjects of its maintenance cycle. Adding a missing workflow is a design
decision, not an automatic rewrite of all running tickets.[^45]

For communication, emphasize what the person controls and what the loop
improves: define the work and its method, run agents from those instructions,
then review proposed improvements to the shared operating material. “Human
driven” means ownership of intent and accepted changes; it does not mean
manually initiating every phase. CE also offers an autonomous `/lfg` path
and non-interactive upkeep, so a manual-CE/automatic-Coga distinction would
misrepresent it.[^42][^44]

Claude Code's own help lists `/dream` and auto-dream terminology; these should
not be conflated with Coga's Dream or the third-party CE refresh skill.
The inspected help entry alone does not establish the same operating-corpus
scope or human-merge contract.[^43] A candidate communication direction is
**running and improving your own way of working, with human control over
the instructions**. This describes an emphasis supported by Coga's design;
it does not require claiming that competing tools cannot be configured
similarly, and it does not imply guaranteed improvement.

## Backlog.md

The usage guide makes the written task central. An idea becomes small tasks
with acceptance criteria; the human reviews them. For a selected task the
agent writes an implementation plan into the task, the human reviews the
plan, and execution follows. If the result is inadequate, the documented
remedy is to refine the task and criteria, clear obsolete implementation
material, and rerun in a fresh session.[^20]

This is not a chat-only task-authoring system. The CLI supports editing the
description, plan, criteria and notes, opening a task in an editor, and
linking documentation. Dependencies and readiness are represented. Markdown
documents have their own create/update/search commands; JSON listings and
watching provide integration surfaces.[^21]

**What changes with Coga:** task state participates in an existing execution
runtime, with independently selected workflow steps, assigned roles,
composed context and knowledge-maintenance jobs. Backlog's documented path
leaves the surrounding agent execution process to the chosen agent and
integration. Coga's addition is moderate when that surrounding process is
the missing piece.

**When the difference is small:** authoring, refining and restarting one
task. That part of the proposed Coga experience is already directly present.
A Backlog user with satisfactory execution and lesson maintenance may have
little reason to migrate. The presence of Backlog documentation and task
references also rules out selling Coga simply as “tasks plus knowledge.”

## Kiro

Feature work produces requirements, design and task Markdown files. The
operator chooses a requirements-first or design-first path, reviews and
refines the artifacts, then runs individual tasks or the task set. Parallel
execution can derive dependency waves. Quick Spec is a separate choice
that omits intermediate approval gates.[^22][^23]

Reusable steering files carry domain and project guidance. Inclusion can be
always-on, selected by files, requested manually or matched automatically.
The operator can write the files directly or ask AI to refine them. Hooks
add event-triggered commands or prompts, including context injection and
validation, with capabilities varying by surface and trigger.[^24][^25]

Kiro Web also has recurring automations: save a prompt and schedule against
repositories, inspect the resulting session, review generated PRs and merge.
Its automatic memory learns from the task creator's PR feedback. That memory
can be inspected and deleted, whereas steering remains explicitly editable.
These are different knowledge mechanisms inside the same product.[^26][^27]

**What changes with Coga:** a shared job model across varied work, chosen
agent CLIs, explicit per-ticket workflows and proposed shared-knowledge
changes subject to human acceptance. The required acceptance step is a
meaningful difference from Kiro Web's automatic memory, but Kiro's reviewed
steering and PR-producing automations already provide relevant controls.

**Magnitude:** small for defining and delivering a software feature; moderate
for someone seeking Coga's broader repo-owned job system. A general claim
that Kiro lacks editable context, learning, human review or recurring work
would be false. Preference for Coga's arrangement must outweigh leaving a
specification environment that already fits the person's work.

## GitHub Spec Kit

The operator establishes a constitution, specifies the feature, develops a
plan, generates tasks and executes them. The specification, plan and task
list persist as project artifacts. Implementation reads those documents,
checks review checklists, respects ordering/dependencies, reports failures
and marks completed tasks in the task file.[^28][^29]

The method is editable too. Project overrides, presets and extensions can
change templates, add commands and hooks, or introduce domain-specific
phases. The published examples include non-code idea assessment. Coga
therefore cannot differentiate by saying Spec Kit hard-codes an unchangeable
method or cannot handle any work beyond implementation.[^28]

**What changes with Coga:** the same operating collection holds independent
jobs at different human/agent stages and with different selected workflows;
maintenance of reusable operating knowledge is part of that system. Spec
Kit's core task execution organizes units within a specified feature. Those
are different scopes of coordination, even though both use durable documents.

**Magnitude:** small at the level of making written intent govern execution;
moderate when the need extends to a standing collection of mixed jobs and
its knowledge upkeep. Existing presets and extensions must be included in
the person's comparison. Coga has not established better requirements,
design or software-delivery discipline; those needs alone do not justify
switching from Spec Kit.

## GitHub Agentic Workflows

The operator maintains a Markdown workflow with natural-language work
instructions and structured triggers, permissions and tools. Compilation
produces the Actions configuration. A schedule, event or manual dispatch
starts execution; the operator inspects Actions and resulting issues or PRs,
edits the instructions and reruns. The quickstart distinguishes instruction
edits from frontmatter changes that require recompilation.[^30][^31]

Its documented WorkQueueOps patterns already cover durable queues in issue
checklists, sub-issues, cache memory or Discussions. Work can continue across
runs and days. These are patterns to configure, with explicit idempotency
and concurrency considerations, rather than a single installed Coga-style
ticket application.[^32]

The experimental CorrectionOps pattern is a particularly strong precedent.
It retains predictions, compares them with later trusted human decisions,
and proposes instruction updates through draft PRs when evidence warrants.
The worked examples include the intake, comparison and adaptation stages.
This overlaps directly with improving editable instructions from human
corrections; it is broader evidence than a generic ability to open PRs.
Its experimental status limits maturity claims, not its conceptual relevance.[^33]

**What changes with Coga:** a local attended job can use the same maintained
ticket model as queued work and return to a saved human-owned step. GH-AW's
normal cycle remains an Actions execution with GitHub work records; running
Actions on one's own machine does not by itself provide that attended
interaction. For GitHub-centered background work, its existing execution
environment may be the better fit.

**Magnitude:** moderate interaction and packaging difference, strong overlap
in the underlying approach. Coga has a weak full-switch argument for someone
whose work already fits these automations. Queues plus reviewed instruction
learning are not a Coga-exclusive combination. Whether a particular GH-AW
configuration equals the complete local job system has not been tested.

## Agent Orchestrator

AO's quickstart adds a project, creates a task with a prompt and chosen
harness, then follows its worker in chat or a native terminal. The worker
gets a workspace; the operator sends corrections and reviews PR/CI state
in the same application. A project coordinator can also retain the larger
goal and delegate to workers, select context and redirect ongoing work.[^34][^35]

The board derives attention and delivery states from session activity and
PR/review facts. Scratch projects are available, so every worker need not
produce a code branch. Current AO state is managed by a local daemon,
including its database and workspaces under `~/.ao`; current built-in
capabilities should not be confused with the older npm plugin model.[^35][^36][^37]

**What changes with Coga:** explicit authored workflow stages, role
assignments and current work instructions govern the job record, with
reviewed shared-knowledge maintenance alongside it. AO already supplies
ongoing coordination and human attention routing. Coga's distinction is the
authority and maintenance of the operating files, not discovering that
multiple agents need a supervisor.

**Magnitude:** moderate, conditional on valuing that file-based operating
model. A user who prefers a persistent coordinator and live session board
already has a coherent system. The reviewed standard AO usage does not
establish the same canonical Markdown ticket lifecycle and Dream process;
it also does not establish that these cannot be added through the agents.
No throughput or supervision advantage for Coga has been demonstrated.

## VS Code

Prompt files are a direct precedent: author a Markdown prompt with references
and optional agent/tool settings, then invoke it. Current documentation
limits these files to the Local agent and directs Agent Host users toward
skills. The migration changes the mechanism, not the availability of
file-authored reusable instructions.[^38]

The surrounding product matters. Custom agents are editable Markdown files
with instructions, tools and optional handoffs. A planning agent can offer
an implementation handoff after the operator reviews its output. Custom
agents can also coordinate subagents. This already supplies editable methods
and guided human review steps.[^39]

The Agents window tracks sessions across workspaces and documents preview
automations from saved prompts and schedules. Preview memory retains user
and repository notes locally; its session-scoped plans have a different
lifetime. These features prevent a fair comparison from treating VS Code
as a single reusable-prompt button.[^40][^41]

**What changes with Coga:** independent tickets hold the current brief,
selected knowledge, workflow position and human responsibility, while shared
knowledge changes follow a defined proposal process. The supported VS Code
handoff is a transition between agent roles in the interaction; it is not
by itself a standing collection of those ticket records.

**Magnitude:** moderate as an added operating system for tasks; small if
reusable prompts, role handoffs and ordinary sessions solve the problem.
VS Code can remain the editor. The current previews and harness differences
also mean a person's actual enabled configuration must be compared, without
assuming all documented features run together in every harness.

## Where the difference becomes useful

Consider a hypothetical small launch: fix an installer defect, prepare an
article, obtain a publishing decision, then reuse a corrected product fact
in a later job. Coga can represent these as independent tickets with different
workflows and shared contexts. The article can wait for its owner while
other eligible work proceeds. A reviewed correction can later become part
of the selected context for a new task.

The differentiating experience is visible in three operations:

1. **Revise current intent.** Edit the article's maintained brief; the next
   launch reads that definition. Backlog, CE, Kiro and Spec Kit already
   support closely related document-directed work.
2. **Return to the right responsibility.** The job retains its stage,
   assignee, blocker and working notes while other jobs follow different
   methods. Coga supplies this arrangement. AO, Superset and GH-AW already
   supply substantial alternative coordination, and the CE trial reproduced
   a small file-directed queue.
3. **Maintain the rules across jobs.** Inspect a proposed change to shared
   knowledge, accept or reject it, then check that later work actually uses
   the accepted rule. CE refresh and GH-AW CorrectionOps are close precedents;
   Coga's own audit shows why successful reuse must be demonstrated.

Together these can be a significant change for an operator currently
stitching together conversations and remembered obligations. Each separate
operation has competition. The value comes from wanting this particular
maintainable system and finding it useful in daily work.

## Product and switching judgment

**Fundamental originality: limited. Product differentiation: moderate overall,
potentially substantial for the standing-job use case. Comparative advantage:
not yet established.** Coga is recognizably part of the document-driven agent
tool family, with a specific emphasis on operating varied ongoing work through
the same editable task/context/workflow structure.

The narrow “edit your prompt” claim understates Coga's scope while inviting
comparisons it cannot win through uniqueness. A more useful proposition to
demonstrate is: **maintain the work, its working method and its reusable
knowledge together, and run agents through that maintained system.** This
is a description of the product choice, not approved headline copy.

The strongest prospective adopter already delegates several jobs, has
repeated context or method corrections, and wants the work to remain
inspectable across sessions and responsibilities. The weak adopter is
someone whose only problem is parallel coding, saved worktrees or better
specification. The tool they currently use does not identify which of those
people they are.

The available evidence does not justify replacing Coga now, nor does it
justify telling a satisfied CE or GH-AW user that a major missing capability
requires Coga. The CE trial is a real alternative for the exercised slice;
it leaves production coverage and comparative usefulness open. Coga can earn
adoption through its supplied process without technical exclusivity. Evidence
that someone returns to it for another real job would be more decisive than
another broad prompt-control claim.

## Sources

External sources below are first-party documentation or source, accessed
September 12, 2026. Unversioned documentation and `main` links describe the
retrieved state, not a pinned release. Feature-preview labels are retained
in the assessment. Local sources refer to the inspected Coga workspace;
the CE trial separately records its pinned revision and verification receipts.

[^1]: Coga, [principles](../contexts/coga/principles/SKILL.md), especially agents/humans, legibility and human-reviewed memory.
[^2]: Coga, [architecture](../contexts/coga/architecture/SKILL.md), ticket state machines, launch, dependency drain, step gates and prompt composition.
[^3]: Coga, [packaged design workflow](../../src/coga/resources/templates/coga/bootstrap/workflows/code/design-then-implement.md).
[^4]: Coga, [draft-for-human workflow](../../coga/workflows/draft-for-human.md) and [marketing audit ticket](../archive/launch-programs/phase-0-audit/audit-ticket.md), historical human-step snapshot archived on 2026-09-21.
[^5]: Coga, [upkeep audit](upkeep-audit.md), September 11, 2026; [Dream run record](https://github.com/FastJVM/coga/blob/9cb722546/coga/tasks/recurring/dream/ticket.md#dream-run-summary), September 9, 2026 (the 2026-W37 period ticket as frozen at commit `9cb722546`; the live path is rewritten every period).
[^6]: Coga, [prompt composer](../../src/coga/compose.py) and [composition probe](build-vs-adopt.md#coga-must-meet-the-same-standard).
[^7]: Zed, [Agent Panel](https://zed.dev/docs/ai/agent-panel).
[^8]: Zed, [Instructions](https://zed.dev/docs/ai/instructions).
[^9]: Superset, [Tasks](https://docs.superset.sh/tasks).
[^10]: Superset, [Agent Orchestration](https://docs.superset.sh/orchestration).
[^11]: Superset, [Automations](https://docs.superset.sh/automations).
[^12]: Pi, [Usage](https://pi.dev/docs/latest/usage).
[^13]: Pi, [Extensions](https://pi.dev/docs/latest/extensions).
[^14]: EveryInc, Compound Engineering, [Concepts](https://github.com/EveryInc/compound-engineering-plugin/blob/main/CONCEPTS.md), pipeline, packs, guidance, handoffs and supported targets.
[^15]: EveryInc, Compound Engineering, [input triage](https://github.com/EveryInc/compound-engineering-plugin/blob/main/skills/ce-work/references/input-triage.md).
[^16]: EveryInc, Compound Engineering, [non-code execution](https://github.com/EveryInc/compound-engineering-plugin/blob/main/skills/ce-work/references/non-code-execution.md).
[^17]: EveryInc, Compound Engineering, [ce-compound protocol](https://github.com/EveryInc/compound-engineering-plugin/blob/main/skills/ce-compound/SKILL.md).
[^18]: EveryInc, Compound Engineering, [committing a knowledge refresh](https://github.com/EveryInc/compound-engineering-plugin/blob/main/skills/ce-compound-refresh/references/commit.md).
[^19]: EveryInc, Compound Engineering, [ce-work protocol](https://github.com/EveryInc/compound-engineering-plugin/blob/main/skills/ce-work/SKILL.md).
[^20]: MrLesk, [Backlog.md README: working with AI agents](https://github.com/MrLesk/Backlog.md#working-with-ai-agents).
[^21]: MrLesk, Backlog.md, [CLI instructions](https://github.com/MrLesk/Backlog.md/blob/main/CLI-INSTRUCTIONS.md).
[^22]: Kiro, [Specs](https://kiro.dev/docs/specs/), page updated August 27, 2026.
[^23]: Kiro, [Feature Specs](https://kiro.dev/docs/specs/feature-specs/).
[^24]: Kiro, [Steering](https://kiro.dev/docs/steering/), page updated September 2, 2026.
[^25]: Kiro, [Hooks](https://kiro.dev/docs/hooks/), IDE/CLI/Web support varies by trigger.
[^26]: Kiro, [Web Automations](https://kiro.dev/docs/web/automations/), page updated August 4, 2026.
[^27]: Kiro, [Web Memory](https://kiro.dev/docs/web/memory/).
[^28]: GitHub, [Spec Kit README](https://github.com/github/spec-kit), standard sequence, templates, presets, extensions and non-code assessment.
[^29]: GitHub, Spec Kit, [implementation command](https://github.com/github/spec-kit/blob/main/templates/commands/implement.md).
[^30]: GitHub Next / Microsoft Research, GH-AW, [Overview](https://github.github.com/gh-aw/introduction/overview/).
[^31]: GitHub Next / Microsoft Research, GH-AW, [Quick Start](https://github.github.com/gh-aw/setup/quick-start/).
[^32]: GitHub Next / Microsoft Research, GH-AW, [WorkQueueOps](https://github.github.com/gh-aw/patterns/workqueue-ops/).
[^33]: GitHub Next / Microsoft Research, GH-AW, [CorrectionOps](https://github.github.com/gh-aw/experimental/correction-ops/), explicitly experimental.
[^34]: Agent Orchestrator, [Quickstart](https://useao.dev/docs/quickstart/).
[^35]: Untrivial-ai, [Agent Orchestrator README](https://github.com/Untrivial-ai/agent-orchestrator).
[^36]: Agent Orchestrator, [Installation and state location](https://useao.dev/docs/installation/).
[^37]: Agent Orchestrator, [Built-in capabilities](https://useao.dev/docs/plugins/), current daemon-backed model.
[^38]: Microsoft, VS Code, [Prompt files](https://code.visualstudio.com/docs/agent-customization/prompt-files), Local-agent support and Agent Host migration.
[^39]: Microsoft, VS Code, [Custom agents](https://code.visualstudio.com/docs/agent-customization/custom-agents), including handoffs and orchestration examples.
[^40]: Microsoft, VS Code, [Agents window](https://code.visualstudio.com/docs/agents/run/agents-window), preview; includes the documented recurring-automation entry point. The dedicated automations page was not retrievable; no additional behavior is inferred from it.
[^41]: Microsoft, VS Code, [Memory](https://code.visualstudio.com/docs/agents/run/memory), preview; page dated September 9, 2026.
[^42]: EveryInc, Compound Engineering, [refresh protocol](https://github.com/EveryInc/compound-engineering-plugin/blob/main/skills/ce-compound-refresh/SKILL.md), especially Scope, Investigate and Classify; [mode behavior](https://github.com/EveryInc/compound-engineering-plugin/blob/main/skills/ce-compound-refresh/references/modes.md).
[^43]: Anthropic, [Claude Code power user tips](https://support.claude.com/en/articles/14554000-claude-code-power-user-tips), contents and command appendix name auto-dream and `/dream`; the main memory section describes auto-memory. These references do not establish equivalence with Coga's Dream.
[^44]: EveryInc, [Compound Engineering README](https://github.com/EveryInc/compound-engineering-plugin), standard loop, autonomous `/lfg`, separate plugin installation and experimental Compound Packs.
[^45]: Coga, [recurring Dream template](../../coga/recurring/dream/ticket.md), run order and disposition rules for extraction, stale knowledge, contract drift and missing operating material.
