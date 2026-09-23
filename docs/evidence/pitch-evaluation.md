# Evaluating the current Coga pitch

**September 13, 2026.** Evaluation of the pair the owner liked, with a draft
explanatory paragraph for the Bookface/newsletter writing work:

**Coga — even AGI needs direction.**

**Define, run and evolve how your agents work—in files you control.**

**Owner's further clarification, September 13:** the two central ideas are
choosing the level and manner of delegated responsibility, and owning a
system one can understand and change. Read the
[maintained statement](../contexts/marketing/positioning/SKILL.md).
Legible instructions, knowledge, state and tooling make control over
delegation practical. Preserve this connection when developing the endorsed
explanation below; the competitive findings remain evidence about its
distinctiveness, not a replacement for the product promise.

## Research-work comparison — 2026-09-16

**Live follow-up:** [CE replacement test, Kortix implementation and traction](research-replacement-trial.md).
CE plus a 35-line operator discovered a research-premise conflict, parked the
decision, completed independent work and resumed from owner-revised files in
a fresh session. The decision was staged test input; the scientific draft
still needs review. Kortix exposes concrete dispatch, pending-question and
artifact-transfer primitives for a similar coordinator. These findings
further narrow an exclusivity claim: Coga supplies the working method and
small runtime directly, while the method itself is portable. No comparative
attention or reliability advantage has been measured.

The [serious CE/Kortix comparison](research-work-comparison.md) examines a
programme whose next tasks emerge from evidence and human decisions. Its
recommendation is to keep Coga for that existing use, while treating CE as
a useful method library and Kortix as a credible platform alternative.
Human-led exploration, editable instructions, reviewed knowledge and local
hardware access are not Coga exclusives. The defensible difference is the
supplied task/context/workflow method, human handoffs across a standing set
of work, and its small local runtime. This is research for the next message,
not approval of new campaign copy.

## Work on the human's schedule — owner clarification, 2026-09-15

**The owner's meaning of “human at the center” is control over the timing
of human attention.** A tool can delegate to agents and still make the
person follow the machine's schedule if progress repeatedly requires an
immediate answer. Coga's intended rhythm is to prepare work together, let
eligible tasks advance to their next human handoff or blocker, and return
to the gathered results and decisions when the human chooses. A stop for
one task does not become a demand to stop the person's other work.

This is more specific than the presence of a human review gate or a
completion notification. The comparison must ask what continues while the
human is unavailable, and when preparation and decision work demand them.
The concise expression of the intended benefit is **“Coga works on your
schedule.”** This records the clarification, not approval of a final campaign.

Implementation receipts: the selected-draft path groups authoring before
execution in [`_run_selection`](../../src/coga/megalaunch.py); agent steps chain
to a human handoff, terminal outcome or blocker; the unattended sweep advances
other eligible tickets. Dependency handling includes
[planned service order](../../src/coga/service_order.py) and a
[dependency drain](../contexts/coga/megalaunch/SKILL.md)
that automatically resumes work after a named prerequisite finishes.
The earlier assessment should not reduce this to merely launching jobs in
order. These mechanisms support the Coga promise; they do not establish that
every competitor necessarily requires an immediate human response.

## Who operates the agents in practice? — 2026-09-15

**Implementation follow-up:** [Human control in practice](human-centered-comparison.md)
traces Coga's handoffs and the closest alternatives, checks actual maintenance
records, and records 18 passing Coga checks plus a reproduced prompt-delivery
limitation. The difference from Zed's standard thread workflow is substantial;
Superset, AO and Kortix supply real delegated coordination too. The strongest
case is Coga's directly editable method for defining work and human handoffs,
not exclusive ownership of “human-centered” delegation. The owner's current
Zed test also reports a pleasant UI and a noticeably different working
experience; it is qualitative feedback, not a comparative benchmark.

**The owner's question is about the working relationship:** after defining
useful work, can the person leave, or must they keep launching sessions,
passing results between them and restarting progress? Defining the work,
making a substantive decision and reviewing its result are human judgment;
repeated dispatch and message forwarding are coordination that can be
delegated. The existence of setup or review does not establish extra human
attention, and a command shown in an agent's instructions is not necessarily
an action the person performs.

**Finding:** the concern fits several standard session-by-session workflows.
It does not describe every competitor or every supplied mode. Some products
already assign coordination to an agent. This check read current usage
procedures, shipped agent instructions and selected implementation, and
re-examined the saved CE trial. It did not conduct new live sessions in Zed,
Superset, AO or Kortix, or measure comparative human effort.

| Product and actual path | Who does the coordination after the initial request? |
|---|---|
| **Zed: standard parallel-thread workflow** | The documented procedure has the person start threads, switch between them and review results. Launched work can run in the background. That procedure does not supply Coga's policy for selecting another prepared job when one needs a human. It supports the narrower observation that managing a collection of sessions can leave the person as dispatcher; it does not prove continuous attendance is required. [Parallel agents](https://zed.dev/docs/ai/parallel-agents). |
| **Backlog.md: documented task implementation flow** | Its example separates task definition, plan approval and implementation of one named task. It supplies durable task management, not an unattended executor for the whole backlog. Some interactions are useful decisions; moving execution from task to task needs an execution method around it. [Usage](https://github.com/MrLesk/Backlog.md). |
| **Superset: shipped orchestration skill** | An agent coordinator launches ready workers, monitors them, passes dependency results and gathers outcomes. These are explicitly agent responsibilities. The skill ships with Desktop; the user does not have to invent the coordinator. Its recommended scope is clear, verifiable parallel slices. Semantic queue state remains in the coordinator's context, and a worker's blocked marker tells it to resolve the need or ask the user before redispatching. This is evidence of delegated coordination, not a live demonstration that an unexpected unanswered question leaves every other job progressing. [Orchestration procedure](https://github.com/superset-sh/superset/blob/main/apps/docs/content/docs/orchestration.mdx), [shipped skill](https://github.com/superset-sh/superset/blob/main/plugins/superset/skills/orchestrate/SKILL.md). |
| **Agent Orchestrator: coordinator session** | The actual injected prompt assigns spawning, monitoring, clarification and routing CI/review feedback to the coordinator agent. Workers send it true blockers. The ordinary quickstart also offers a more manual worker/reviewer flow, so the mode matters. Source inspection establishes who is instructed to coordinate; it does not establish reliability through every stalled or ended coordinator session. [Prompt assembly](https://github.com/Untrivial-ai/agent-orchestrator/blob/main/backend/internal/session_manager/prompt.go), [quickstart](https://github.com/Untrivial-ai/agent-orchestrator/blob/main/frontend/src/landing/content/docs/quickstart.mdx). |
| **Compound Engineering: stock LFG versus the local adoption trial** | Stock LFG advances a delegated job through its stages but stops on a reported blocker; this is not an independent-job queue. In the earlier live trial, a custom 26-line coordinator instruction file did run a code task and its dependent non-code brief, preserve a human decision and resume from edited plans without manual routing during execution. That is an observed alternative for this small scenario, not a shipped CE queue. [Current LFG](https://github.com/EveryInc/compound-engineering-plugin/blob/main/skills/lfg/SKILL.md), [trial and receipts](adoption-trial.md). |
| **Kortix: scheduled and deferred work** | Its shipped operational instructions explicitly tell the agent to save pending work, end the turn and schedule another run when a long wait is needed. Scheduled runs can start fresh or reuse a session; the agent is told to notify only for useful findings. This supplies a way to leave work running or deferred without manually restarting each turn. It does not establish megalaunch's particular cross-ticket selection policy. [Scheduling playbook](https://github.com/kortix-ai/suna/blob/main/packages/starter/templates/managed/.kortix/opencode/skills/kortix-system/references/scheduling.md). |

Superset also supplies an [overnight audit recipe](https://github.com/superset-sh/superset/blob/main/apps/docs/content/docs/recipes/nightly-audit.mdx)
that leaves unresolved decisions in `AUDIT.md` for morning review. Its
[automation documentation](https://github.com/superset-sh/superset/blob/main/apps/docs/content/docs/automations.mdx)
identifies remaining operating work: inspecting the workspace to learn the
agent's outcome and manually retrying a run missed while its host was
offline. The [dispatcher](https://github.com/superset-sh/superset/blob/main/packages/trpc/src/router/automation/dispatch.ts)
records dispatch success after starting the session, rather than tracking
completion of the requested work. These are concrete limits, not evidence
that its coordinator needs the person to relay every result.

Other inspected counterexamples include [Kiro autonomous mode](https://kiro.dev/docs/web/autonomous-mode/)
for a delegated job (opt-in; a later question can still require attention)
and [GitHub Agentic Workflows queues](https://github.github.com/gh-aw/patterns/workqueue-ops/)
for persistent scheduled batches. Background jobs alone do not establish
Coga's blocker behavior, but neither should supplied coordination be
dismissed as merely a notification feature.

**The CE trial's exact limit matters here:** its human gate was declared in
advance. The saved first run recorded no newly blocked task. It demonstrates
execution without task-by-task human routing, not recovery from an
unexpected question inside a running worker. The saved nine initial checks
and eight restart/proposal checks are checks of one small fixture, not an
attention or reliability benchmark.

**What Coga demonstrably supplies:** megalaunch's
[conduct instructions](../../src/coga/resources/prompt-megalaunch.md) tell the
agent that a present terminal does not mean a human is available. On a new
unresolvable need, it records the ask with `coga block`; the
[runtime](../../src/coga/megalaunch.py) ends that session and advances eligible
prepared work. Simply asking a question or printing “blocked” is insufficient.
The local supervisor must remain running, and useful progress still needs
an eligible job. Coga makes that handoff a maintained part of the working
method; it does not establish that every other method requires babysitting.

The defensible product promise is to **let people define work and return to
results and decisions, with the coordination handled by their tool**.
Megalaunch makes that promise concrete. The comparison supports using this
benefit to explain Coga, and rejects “all the others make you the machine's
operator” as an exclusive claim. Superiority over the supplied coordinators
on unexpected blockers or human interruptions has not been demonstrated.

## Human attention and repeated steps — 2026-09-14

**The owner's correction improves the explanation:** Coga concentrates
human attention on defining, deciding and evaluating work, while agents
and scripts handle the repeatable doing and coordination. This is supported
by its [principles](../contexts/coga/principles/SKILL.md), and gives the
marketing ladder a clearer purpose than maximizing autonomy. The broad
benefit has substantial precedents; the product case is the concrete method
Coga supplies around the operator's existing agents.

Separate three kinds of effort:

- **Repeated explanation:** keep relevant knowledge and instructions in
  reusable contexts and skills, and compose them into the next job.
- **Repeated coordination:** let workflow transitions and megalaunch
  advance eligible work. A reported blocker ends that session and leaves
  its decision with the task while the queue continues elsewhere.
- **Necessary judgment:** choose worthwhile work, settle unresolved
  questions, assess the result and accept changes to the working method.
  Those remain useful human contributions. Agents can prepare them and
  author the files too; manual configuration is not the value proposition.

These mechanisms do not require a perfectly specified process before the
first task. They let useful direction survive a session and carry forward
when it applies again. The comparison below is a review of current primary
procedures and selected source, not a new product trial or an attention
benchmark. Ordinary setup and review also occur in competing methods;
their presence alone is not evidence of extra Coga attention cost.

### Claim verification

**“Kortix is a paid desktop app”: incomplete.** The repository documents
web, desktop and CLI surfaces, a self-host path and agent-operated project
commands. Its hosted pricing currently includes Free and a $40/seat/month
Team plan. Self-hosting does not remove infrastructure/model costs, and
some enterprise capabilities require a license. The relevant product
contrast is Coga's local layer around existing agent CLIs versus adopting
Kortix's session, sandbox and service infrastructure. [Kortix README](https://github.com/kortix-ai/suna),
[pricing](https://kortix.com/pricing), [self-host implementation](https://github.com/kortix-ai/suna/blob/main/apps/cli/src/commands/self-host.ts).

**The license difference is real.** Kortix's current root
[LICENSE](https://github.com/kortix-ai/suna/blob/main/LICENSE) is Elastic
License 2.0, which restricts offering substantial functionality as a hosted
service and bypassing license-key restrictions, among other terms. Elastic
identifies ELv2 as non-OSI-approved/source-available in its
[licensing FAQ](https://www.elastic.co/pricing/faq/licensing). Coga declares
AGPL-3.0-or-later in [its package metadata](../../pyproject.toml) and carries
the [AGPL license](../../LICENSE). Do not equate their licensing on the basis
of Kortix's README saying “open-source,” or conflate free access, readable
source and open-source licensing. Neither license distinction establishes
which working interface someone will prefer.

**“Coga delegates as much as possible to the agent”: supported as a design
direction, shared with close alternatives.** Coga exposes operations as
commands and file edits and assigns deterministic parts to scripts. The
agent can help create and revise the working system itself. Kortix's
[agent-facing CLI instructions](https://github.com/kortix-ai/suna/blob/main/packages/starter/templates/managed/.kortix/opencode/skills/kortix-system/references/kortix/kortix-cli.md)
also explicitly cover operating sessions, triggers, files and project
configuration. Pi asks its agent to extend its own harness. An app having a
GUI is not evidence that its operator must perform every action manually.

**“Zed requires staying at the PC”: false literally.** Its
[agent panel](https://zed.dev/docs/ai/agent-panel#get-notified) explicitly
supports putting Zed in the background and receiving completion
notifications. Its [skills](https://zed.dev/docs/ai/skills) store reusable
methods, and the agent can help create them. Coga's more specific supplied
behavior is advancing prepared jobs through recorded stages and past
blockers. The inspected Zed panel procedure does not establish that same
queue policy; it does establish that continuous human presence is optional.

**“Coga lets you think, then move on”: supported as a working rhythm.** The
[megalaunch conduct](../../src/coga/resources/prompt-megalaunch.md) instructs
the agent to continue authorized work or record a real blocker, without
assuming someone is waiting to answer. The [runtime](../../src/coga/megalaunch.py)
then progresses from task state. This is distinct from merely displaying
a waiting notification. It still requires a running local process, future
human decisions when needed, and an agent that reports the blocker through
the lifecycle command. It does not establish a universal “brief once,
never intervene” outcome or a measured lead over other products.

### All discussed tools under this criterion

Read the [continuation follow-up](#continuation-versus-conversation-thread--follow-up)
below when interpreting the thread/queue comparison. Background execution
and automatic dispatch of the next prepared job are different behaviors.

The last column is a fit judgment: what Coga should demonstrate to someone
already using that product. It does not presume the competitor lacks every
possible extension or custom workflow.

| Tool | How its documented method already avoids repeated human work | What Coga must make concrete |
|---|---|---|
| [Zed](https://zed.dev/docs/ai/skills) | Reusable skills, agent-assisted skill creation, background threads and notifications. | A prepared task queue that carries context and human stages and moves past a recorded blocker. Background execution alone is insufficient. |
| [Superset](https://github.com/superset-sh/skills/blob/main/skills/superset-orchestrate/SKILL.md) | An agent coordinator launches workers, follows dependencies and advances work. Its procedure keeps semantic task state in coordinator context and interprets worker reports. | Supplied lifecycle transitions and queue progression from durable task files. Do not describe coordinating the workers as necessarily the human's repeated job. |
| [Agent Orchestrator](https://github.com/Untrivial-ai/agent-orchestrator) | A persistent coordinator plans and delegates; a daemon tracks work and surfaces where attention is needed. | Individually authored methods and human responsibilities for varied jobs, operated from the task files. Generic “think, then delegate” already overlaps. |
| [Backlog.md](https://github.com/MrLesk/Backlog.md) | Agents draft tasks and plans; humans review them at checkpoints. Its current README explicitly identifies human attention as the bottleneck. Tasks and reusable completion criteria persist. | Execution/composition and workflow routing around the records. Human-centered Markdown tasks themselves are a direct precedent. |
| [Pi](https://pi.dev/) | Reusable Markdown prompts and skills; extensions can add workflow behavior, and the agent can build those extensions. | A supplied task/context/workflow and queue arrangement. “Own it, understand it, ask the agent to extend it” is already Pi territory. |
| [Compound Engineering](https://github.com/EveryInc/compound-engineering-plugin/blob/main/skills/lfg/SKILL.md) | Skills encode reusable procedures; LFG carries requests through the relevant method without waiting at each step. Its current routing includes non-code work. | The supplied queue across independently staged jobs, explicit context delivery and reviewed upkeep of broader operating instructions. Do not sell CE as requiring manual repetition of its full pipeline. |
| [Kiro](https://kiro.dev/docs/web/autonomous-mode/) | Upfront planning and background execution, plus [steering and memory](https://kiro.dev/docs/web/memory/) to avoid restating guidance. | A locally owned method around chosen agent CLIs and individually assigned stages. Dream's reviewed proposals differ from Web memory's automatic maintenance; Kiro's explicit steering remains editable. |
| [Spec Kit](https://github.com/github/spec-kit) | Specifications, templates, commands, presets and extensions retain and customize the working method. | A runtime over prepared jobs and human/agent stages. Editable reusable methods are already supplied there. |
| [VS Code agents](https://code.visualstudio.com/docs/agents/overview) | Background/remote work and session handoffs, with custom instructions, agents and other reusable methods. | The task records and queue as the operating surface for the work, potentially alongside the editor. Continuous PC attendance is not the dividing line. |
| [GitHub Agentic Workflows](https://github.github.com/gh-aw/patterns/workqueue-ops/) | Authored workflows repeatedly process durable queues. Experimental [CorrectionOps](https://github.github.com/gh-aw/experimental/correction-ops/) proposes instruction changes using human corrections. | Local one-off delegation and editable human stages outside an Actions-centered method. Reuse, queueing and reviewed improvement already overlap. |
| [Kortix](https://github.com/kortix-ai/suna) | Shared skills, scheduled triggers, retained project knowledge and an agent-facing CLI can delegate operation of the platform itself. | The AGPL license and local layer over existing agents, with a task queue and explicit method. Compare the actual infrastructure adopted; paid-only, GUI-only and agent-inoperable are inaccurate descriptions. |
| [LangGraph](https://docs.langchain.com/oss/python/langgraph/overview) | Developer-authored graphs combine deterministic and agent steps with durable state and human intervention. | A supplied way to operate existing agents through work files. Building an agent application is a different product need; repetition and human control are already supported. |
| [CrewAI](https://docs.crewai.com/en/concepts/flows) | Code-defined flows automate sequences, branching, state and agent work. | The same product distinction: operating existing agents with tasks versus building the application's execution flow. |

### Continuation versus conversation thread — follow-up

The owner proposes a continuation/thread analogy. **It is useful at the
workflow level:** Coga can preserve unfinished work independently of the
agent session and give execution back to the dispatcher. Treating this as
equivalent to a background thread with a notification misses the automatic
transition to other prepared work.

| Event | Zed's documented conversation-thread flow | Coga's megalaunch flow |
|---|---|---|
| Job A needs an unavailable answer | A waits in its conversation; other independently started threads can continue. | The agent records the ask with `coga block`; the supervised session ends. |
| Job B is ready but has not started | A completion/waiting notification does not itself select and launch B. Another thread, agent instruction or coordinator must start that work. | The sweep starts the next eligible prepared job, without the human having to answer A first. |
| Return to A | Continue the conversation; Zed also supports saved history and starting a fresh thread from a summary. | Launch again from the current task, workflow step, selected context and blackboard. The work can continue in a new agent process. |

The Coga code path is explicit: [block](../../src/coga/commands/block.py)
records the ask and blocked status, then emits the task-scoped done marker;
the [supervisor](../../src/coga/repl_supervisor.py) terminates the process group;
[`_launch_until_stop` and `_run_sweep`](../../src/coga/megalaunch.py) return the
blocked result and advance the queue. A later launch
[composes](../../src/coga/compose.py) the task's current instructions and
recorded work. [Agent launch](../../src/coga/commands/launch.py) builds a new
process invocation and, where configured, a new session identifier; Coga's
resume mechanism does not depend on keeping the old conversation running.

Three boundaries keep the analogy accurate:

- **A waiting Zed thread does not paralyse all work.** Its
  [parallel-thread documentation](https://zed.dev/docs/ai/parallel-agents)
  explicitly says other threads run independently. Its built-in
  [authorization loop](https://github.com/zed-industries/zed/blob/cbffa0f5e1fc4a05b43c3e29d0c759b5d24d0f8f/crates/agent/src/thread.rs#L6449)
  waits through an async task and response channel. “Thread” here names a
  conversation, not a claim that Zed blocks an OS thread or consumes model
  compute throughout the wait. No resource or throughput advantage was
  measured.
- **Coga preserves a task-level continuation, not a complete execution
  snapshot.** It reconstructs what to do from files; it does not restore
  the former model's full context or an exact suspended call stack.
  Unrecorded reasoning is not guaranteed to survive. Useful blackboard
  state and explicit handoffs therefore matter.
- **The yield is explicit.** The agent must use the lifecycle command;
  writing “I am blocked” or encountering an underlying CLI permission
  dialog does not automatically create that task handoff. The queue still
  needs other eligible work. Unanswered human blockers remain parked until
  resolved and relaunched; the special automatic dependency drain applies
  to named Coga tasks that have finished, not every kind of waiting event.

The practical benefit is that **an unanswered decision can remain pending
without occupying Coga's execution session or requiring the person to
dispatch the next ready job**. One execution slot can serve many tasks
whose human decisions happen at different times. This substantiates the
owner's “think, then move on” description more precisely than background
notifications do. It is a substantive operating distinction from a bare
thread manager, with no implication that queue-based orchestrators cannot
provide it. Superset's coordinator protocol and GH-AW's durable queues
remain relevant comparisons from the broader review.

This follow-up inspected Coga's block, supervisor, queue, composition and
launch paths, plus Zed's current thread procedures, sibling-thread tool and
built-in authorization loop. Zed main resolved to
`cbffa0f5e1fc4a05b43c3e29d0c759b5d24d0f8f`. It was a bounded source check,
not an executed comparative workload or an audit of every external agent.

### Implication for the ladder

Lead with **spend your attention on the decisions; let agents carry out the
working method you own**. Megalaunch demonstrates that benefit: prepare two
jobs, record a missing decision on one, and continue the other. Then show
how the brief, selected context or workflow is reused and changed, including
agent-assisted edits. Dream explains how proposed improvements can become
accepted instructions for later work.

This is a clearer purpose for Coga and a useful adoption argument where the
current setup leaves repeated direction or coordination to the person. It
is not an exclusive philosophy: Pi, CE, Backlog.md and Kortix are substantive
precedents, and coordinators already remove significant supervision. A
satisfied user of those tools needs the particular working arrangement,
license or deployment choice to matter. This clarification updates the
ladder's emphasis without replacing the owner's liked pitch or selecting
the campaign story.

**Source scope:** checked September 14. The additional Kortix review read
its root license, pricing, CLI and system-skill procedures, the self-host
command and the session prompt-queue command. The latter manages a durable
inbox within a session; its name alone does not establish megalaunch's
block-and-next-job policy. Main resolved to
`c6040c37ef3c17f7d81123a583e0c04014661800` during this pass. No Kortix
deployment or all-endpoint verification was performed. Earlier Coga source
checks and the bounded [CE trial](adoption-trial.md) retain their stated
limits.

## Marketing ladder assessment — 2026-09-14

The owner asks for the [whole message hierarchy](../contexts/marketing/positioning/SKILL.md)
to be evaluated against the discussed tools. **Keep this ladder. It is the
strongest marketing structure developed in this discussion:** a concrete
reason to try, an explanation of how the operator shapes the work, and a
reason to preserve and improve the method over time. Its competitive
strength is selective; it does not establish a globally exclusive category.

The [later clarification above](#human-attention-and-repeated-steps--2026-09-14)
sets the purpose of that hierarchy: remove repeated operational work while
preserving human judgment. Read the ratings below with that emphasis and
the corrected Kortix license/deployment facts.

These are editorial judgments about adoption appeal, informed by current
primary procedures, the Coga source inspection and the earlier CE trial.
This pass did not run new agent sessions or compare conversion rates. The
September 13 queue correction remains central: **record the blocker, end
that session, move to the next eligible job**. Background notifications
alone do not establish that behavior.

### How the ladder works

| Element | Commercial role | Evaluation |
|---|---|---|
| Megalaunch advances prepared work around blockers | An immediate reason to try | **Strongest opening.** Show that a missing answer is recorded with its task and execution moves to another job. Lead with this outcome before naming the command. A pair of simple one-off tasks can make it visible. |
| Editable tasks, context and workflows | A reason to choose this way of delegating | **Strong when concrete.** Show the operator changing the scope, relevant facts, method or human return point. “Flexible framework” alone overlaps with much of the market; the point is shaping the arrangement the queue actually executes. |
| Own and understand the system | Evidence that the operator can keep shaping it | **Supports every rung.** The brief, method, recorded state and tooling are available to inspect and change. Demonstrate one useful change in an ordinary file. File possession or an open-source license alone is a weaker claim. |
| Reuse and human-reviewed Dream proposals | A reason to keep and develop the method | **Useful depth after the first payoff.** Show a proposed instruction improvement and the human's disposition. Compounding is shared territory, and automatic improvement in subsequent outcomes is not established. |

The sequence holds together because each layer concerns the same work:
the queue advances a job, its files define the delegation, and accepted
knowledge can inform later jobs. “Framework of thinking” is an internal
description of making goals, assumptions and responsibilities explicit.
For a prospective user, “design how you and your agents work together”
is easier to connect to those actions. Start from the supplied simple
workflows; elaborate methods and recurring jobs are optional extensions.

### Competitive strength of the complete ladder

**Strong** means a clear supplied addition for someone who wants this
working style. **Moderate** means a concrete choice with substantial
overlap. **Close** means the broad ladder gives little switching pressure
without a more specific requirement. These rate Coga's adoption argument,
not the competing product's quality or tested performance.

| Tool | Where it competes with the ladder | Coga's complete adoption argument | Strength |
|---|---|---|---|
| [Zed](https://zed.dev/docs/ai/agent-panel) | Background threads, editable prompts, saved work and reusable instructions already exist. | A runtime that progresses through prepared jobs, parks blockers and carries each job's method and human stages in files. A reason to add Coga for queue-based work while keeping the editor. | **Strong for that need** |
| [Superset](https://github.com/superset-sh/skills/blob/main/skills/superset-orchestrate/SKILL.md) | Its coordinator owns task/dependency state in its working context and interprets worker result markers. It already coordinates work asynchronously. | Coga supplies durable task transitions and subsequent queue progression in code; editable work definitions are the dispatcher's input. This is a concrete operating choice beyond prompt editing, with no demonstrated overall reliability lead. | **Moderate, defensible** |
| [Agent Orchestrator](https://github.com/Untrivial-ai/agent-orchestrator) | A persistent project coordinator, supervised workers, local daemon and a view of work needing attention already cover much of the initial payoff. | Per-ticket methods and human responsibilities for varied jobs, directed through a common file-based queue. Its coding-session coordination is a close alternative; general autonomy is insufficient differentiation. | **Moderate, close on coordination** |
| [Backlog.md](https://github.com/MrLesk/Backlog.md#working-with-ai-agents) | Owned Markdown tasks and human review are already central; its documented agent flow uses one task per session. | Supply execution, selected-context composition, task stages and the queue around those work definitions, then reviewed upkeep. The concrete gain is operating the tasks; Markdown alone gives no switching reason. | **Strong if execution is the missing part** |
| [Pi](https://pi.dev/) | Ownership, prompt/context control and making the tool fit one's workflow are already its core message. Extensions and packages can add methods. | A supplied task-queue and knowledge method around existing agent CLIs. This offers a particular working arrangement, rather than superior hackability. No Coga/Pi integration was tested. | **Moderate relative to bare Pi; setup-dependent** |
| [Compound Engineering](https://github.com/EveryInc/compound-engineering-plugin/blob/main/skills/lfg/SKILL.md) | Autonomous execution, editable procedures, learning capture and maintenance overlap across the ladder. The current LFG protocol also routes non-code requests. | The supplied queue over independently staged jobs, explicit context delivery, human return points and broader reviewed instruction upkeep. The earlier actual CE trial reproduced several relevant transitions with added conventions. | **Close; moderate for the exact queue/method requirement** |
| [Kiro](https://kiro.dev/docs/web/autonomous-mode/) | Autonomous work, specs and steering already provide delegation and editable guidance. | A local queue over chosen agent CLIs and individually authored human/agent stages. Reviewed proposed knowledge is a clearer distinction from Kiro Web's automatically maintained, deletable [memory](https://kiro.dev/docs/web/memory/); editable steering also exists there. | **Moderate** |
| [Spec Kit](https://github.com/github/spec-kit) | Editable work definitions, customizable procedures, presets and non-code extensions already support designing a method. | Execute a collection of independently staged tasks with Coga's queue and reviewed upkeep. General flexibility or non-code applicability alone is insufficient. | **Moderate; stronger when a task runtime is wanted** |
| [VS Code](https://code.visualstudio.com/docs/agents/overview) | Background and remote sessions, multiple harnesses and session handoff already cover substantial agent operation; custom instructions and agents add methods. | Keep job stages and selected context in the task records the queue operates, independently of an editor session. This can complement VS Code; portraying it as a synchronous chat box would be inaccurate. | **Moderate** |
| [GitHub Agentic Workflows](https://github.github.com/gh-aw/patterns/workqueue-ops/) | Durable work queues and authored workflows already exist; experimental [CorrectionOps](https://github.github.com/gh-aw/experimental/correction-ops/) also proposes instruction changes from human corrections. | Locally operated one-off jobs with explicit human stages and a common task interface. GitHub Actions remains a strong fit for repository automation. WorkQueueOps alone does not establish the exact park-session-and-next-job policy. | **Close on the broad ladder** |
| [Kortix](https://kortix.com/blog/agi-ready-architecture) | Its published position spans delegation, owned operating files, human authority and reviewed evolution. Source inspection confirmed parts of its session/runtime and change-request machinery; its CLI also exposes platform operations to agents. | Coga's AGPL license, local layer over existing agent CLIs and explicit task queue, compared with Kortix's ELv2-licensed session/runtime platform. Kortix has self-hosting and a free hosted tier. Broad ownership and AGI claims overlap; the source review remains partial. | **Close in message; concrete license and architectural choice** |
| [LangGraph](https://docs.langchain.com/oss/python/langgraph/overview) | Fine-grained workflows, durable state and human intervention are capabilities it supplies to application developers. | Coga provides a working task system around existing agents. This is a clear product-category distinction, not evidence that LangGraph lacks control or flexibility. | **Different buying decision** |
| [CrewAI](https://docs.crewai.com/en/concepts/flows) | Developer-authored flows coordinate tasks, state and conditional execution. | Use Coga to direct existing agents through work files; use CrewAI to build the application flow itself. Calling Coga merely an agent framework obscures this distinction. | **Different buying decision** |

### What changes in the marketing judgment

The ladder provides a consequential operating choice for someone who has
prepared work and wants execution to keep progressing around their
unavailable decisions. Megalaunch makes that choice visible. The editable
division of responsibility and owned knowledge explain why Coga can remain
useful as the person's work changes. This is stronger than a list of shared
features or a promise of unrestricted customization.

The strongest initial case is an existing agent user who wants that queue
and whose current setup does not supply a satisfactory one. Superset and
AO users need the more specific operating distinction. Pi and CE users
already share much of the philosophy; show the supplied arrangement they
would gain. GH-AW and Kortix prevent claiming the broad ladder as Coga's
exclusive idea.

For first contact, show two prepared jobs: one records a missing decision
and ends, then the other starts. Show where the brief or responsibility is
changed, then a reviewed knowledge improvement if useful. This demonstrates
the message hierarchy without requiring a large initial process. Keep the
AGI line as the longer-term thesis in this proposed narrative order; final
campaign wording and story selection remain with the writing work.

**Source refresh:** current LFG handles non-code requests, so earlier
software-only descriptions of that entry point are superseded. Kiro is
assessed with its current autonomous mode and memory, and VS Code with its
broader agent interfaces. Neither is reduced to its old editor/chat entry
point. The [continuity assessment](continuity-comparison.md) and pending
human acceptance in the [CE trial](adoption-trial.md) still apply.

## Judgment

The following is the earlier September 13 pitch assessment; the September 14
ladder evaluation above adds the current message hierarchy.

**Owner clarification, later on September 13:** Coga is a lightweight tool
on top of an existing agent for delegating one-off tasks too. The initial
assessment below overemphasized collections of jobs, maintained workflows
and correction loops. Those explain how use can accumulate; they are not
prerequisites for understanding or benefiting from a single delegated job.

Keep the pair. The hook gives Coga a point of view: increasing capability
changes what we delegate and how we work, while objectives, knowledge and
decisions still need a place to be expressed. The supporting line explains
what the product lets someone do. Together they communicate more than
generic control or hackability, although the hook alone does not explain
the product or establish a reason to switch.

Start the explanation with **an editable brief for one job, handed to the
agent the operator already uses**. Coga assembles the task and selected
context, launches the configured agent, and carries task state, notes and
handoffs. The body can define the whole job in a single step. Its granularity
can vary from detailed instructions to a broader outcome the agent works
out how to achieve. Chat, direct editing and agent-assisted authoring all
operate on the same files.

Reusable context, additional workflow stages and Dream extend this starting
point. A task can be performed once while a lesson from it becomes useful
elsewhere. The wider thesis remains an editable working method that can
change with agent capability; it does not require a recurring process or
automatically redesign itself when a model changes.

“Lightweight” here describes the architectural relationship: Coga operates
an existing agent CLI from local work material. It is not a measured install,
runtime, configuration or attention advantage. The value of a single brief
already overlaps strongly with using an agent directly, Backlog.md and
Superset. These are more relevant adoption comparisons than a feature match
against a correction system or an application framework.

## Closest comparisons for delegating one job

### Is the complete approach unique?

**Owner feedback, September 13:** “that's a good explanation.” Retain the
single-task-first explanation below. The follow-up question is whether the
approach as a whole is unique.

**Assessment: a distinctive product design; uniqueness is not established.**
The subsequent [continuity check](continuity-comparison.md) resolves the
narrower question: continuity itself is not exclusive. CE supplies a
connected work/capture/retrieval path, with partial functional confirmation
from the actual trial. Coga has concrete advantages in supplied context
delivery, stage routing and upkeep scope; better overall outcomes remain
unestablished. Read that check for the current conclusion about continuity.

This judgment concerns the basic delegation experience, not merely shared
features in the upkeep loop. Backlog.md already makes editable local task
files a way to direct an existing agent. Superset already turns task content
and selected context into input for an existing agent. CE's work skill
accepts a direct work prompt within an editable instruction layer. The
primary sources and source checks below support these close precedents.

Coga's specific shape is the continuity between one-off delegation and
accumulated working knowledge: the task, selected context and method remain
editable material operated by humans and existing agents. The same approach
can carry more delegation, additional human decisions or reviewed proposed
improvements without requiring the first job to become a recurring process.
That continuity is a useful product distinction to demonstrate. We have not
shown it to be exclusive, substantially better than the closest alternatives,
or a new category. An exact combination of implementation details would not
by itself establish meaningful originality.

Use the concrete explanation to communicate the choice Coga offers. Do not
turn the lack of a verified full replacement into evidence that only Coga
can provide this experience.

### Alternatives

| Alternative | What the operator already gets | What Coga must add to justify using it |
|---|---|---|
| An existing agent plus a Markdown brief; [Pi](https://github.com/earendil-works/pi/tree/main/packages/coding-agent) is a concrete example | File tools, persistent sessions, prompt templates and extensibility already support work from written instructions. | A ready task record, selected context, composed launch, progress notes and any chosen handoff. If the brief and a single session suffice, adding Coga has little immediate benefit. Pi is an agent harness; this does not assert a tested Coga/Pi integration. |
| [Backlog.md](https://github.com/MrLesk/Backlog.md) | Local Markdown tasks, editable work definitions, agent-facing instructions and human review. | Task launch/composition and recorded execution stages around that task. This is a close comparison, including for one-off work; Markdown ownership is common ground. |
| [Superset](https://docs.superset.sh/tasks) | Editable task descriptions and configurable prompt templates for launching existing agents, with optional linked context. | The task and reusable context files as the maintained operating surface, with the task's method and handoffs carried alongside it. The source check below confirms that “layer over an agent” and prompt composition already overlap. |
| [Agent Orchestrator](https://github.com/Untrivial-ai/agent-orchestrator) | A worker can receive one task; ongoing project coordination is also supplied. | Directly authoring a job and its selected knowledge in Coga files, with a method suited to the job. One-off delegation and using existing agents are not exclusive to Coga. |
| [Compound Engineering](https://github.com/EveryInc/compound-engineering-plugin/blob/main/skills/ce-work/SKILL.md) | Its work skill accepts a concrete prompt as well as a plan, and includes a small-change route. It can support one-off work without first running a full compounding cycle. | A common task record and launch/handoff mechanism for individually authored methods across work kinds. CE is engineering-centred and has a non-code route; Coga should not be sold on an invented CE requirement to run a whole pipeline. |
| [Kortix](https://github.com/kortix-ai/suna) | One prompt can start a session; project files, permissions and reviewed changes surround it. | A local layer over the chosen agent CLI instead of adopting Kortix's session/runtime platform. The bounded source inspection now establishes that architectural difference; it is not a usability or performance comparison. |

For this use case, the most demanding comparisons are **agent plus brief,
Backlog.md, Superset and CE**. AO belongs in the comparison when worker/session
coordination matters. Kortix is relevant to the broader ownership/AGI pitch,
but its similar messaging should not make the two products interchangeable.

GH-AW remains a comparator for repository automation and maintained
instructions. Zed and VS Code are relevant to the editor interaction;
Kiro and Spec Kit to structured specification work; LangGraph and CrewAI to
building agent applications. Keep these in the wider landscape without
using their correction or orchestration features to define Coga's basic use.

## Follow-up source inspection

Read-only inspection on September 13; no upstream product was installed or
executed. Downloaded files were checked against Git blob hashes at the
following commits.

- **Coga:** [composition](../../src/coga/compose.py),
  [launch](../../src/coga/commands/launch.py), and the
  [single-step body workflow](../../coga/workflows/direct/body.md) support the
  brief-to-existing-agent path. A workflow is required at activation but can
  be one step; a task need not become a reusable multi-stage process. The
  [body skill](../../src/coga/resources/templates/coga/skills/direct/body/SKILL.md)
  has a product-code boundary: tracked product delivery uses the appropriate
  code workflow. This review does not propose changing those contracts.
- **Superset, `00efaec882ebd2d2220f29fdef8837a593cae6a0`:**
  [prompt composition](https://github.com/superset-sh/superset/blob/00efaec882ebd2d2220f29fdef8837a593cae6a0/apps/desktop/src/renderer/stores/new-workspace-prompt-context/buildSubmitPrompt.ts)
  returns the user prompt directly when there are no linked sections and
  otherwise appends task/issue/PR bodies.
  [Templates](https://github.com/superset-sh/superset/blob/00efaec882ebd2d2220f29fdef8837a593cae6a0/packages/shared/src/agent-prompt-template.ts)
  expose task and context variables, with per-agent overrides;
  [launch transport](https://github.com/superset-sh/superset/blob/00efaec882ebd2d2220f29fdef8837a593cae6a0/packages/shared/src/agent-prompt-launch.ts)
  hands the composed text to an external command. This is direct
  implementation evidence of overlap at the basic delegation layer.
- **Kortix, `aaa91b0d6b45ec331c4434440c4bfb4aecdb173e`:**
  the [session route](https://github.com/kortix-ai/suna/blob/aaa91b0d6b45ec331c4434440c4bfb4aecdb173e/apps/api/src/projects/routes/project-sessions.ts)
  invokes session lifecycle handling;
  [session creation](https://github.com/kortix-ai/suna/blob/aaa91b0d6b45ec331c4434440c4bfb4aecdb173e/apps/api/src/projects/lib/sessions.ts)
  accepts an initial prompt, persists session/inbox state and starts sandbox
  provisioning. The
  [runtime allocator](https://github.com/kortix-ai/suna/blob/aaa91b0d6b45ec331c4434440c4bfb4aecdb173e/apps/api/src/projects/lib/session-runtime-allocator.ts)
  resolves environment and project state and calls the sandbox provisioner.
  Its default OpenCode path also has a gated Pi-worker alternative, so do
  not call it an OpenCode-only system. The
  [change-request policy](https://github.com/kortix-ai/suna/blob/aaa91b0d6b45ec331c4434440c4bfb4aecdb173e/apps/api/src/projects/change-request-policy.ts)
  contains a session self-merge refusal and restrictions on agent retargeting.
  This goes beyond a marketing claim, while leaving end-to-end enforcement
  and usability untested. Kortix can be self-hosted; the distinction is the
  supplied platform, not whether local deployment is possible.

## Earlier broad pitch comparison

The original thirteen-tool pass below assessed the wider evolving-method
thesis. The focused comparison above corrects its overemphasis on ongoing
operations. Its ratings should not be treated as scores for one-off task
delegation. The Kortix row has been updated after source inspection.

“Contrast” rates how clearly the pitch describes a different provided way
of working, not product quality or how much control a tool can theoretically
offer. These are editorial judgments from primary documentation, the
[Coga source inspection](usage-comparison.md#source-code-distinction-from-langgraph-and-crewai)
and the [existing CE trial](adoption-trial.md). Primary pages below were
checked on September 13; this is not a new hands-on trial of all thirteen.

| Tool | Relevant overlap | Coga's angle and strength of contrast |
|---|---|---|
| [Zed](https://zed.dev/docs/ai/agent-panel) | Editable messages, saved agent threads, worktrees, explicit context and skills. | **Clear in the usual interaction.** Coga makes the maintained job definition, shared knowledge and human/agent workflow the continuing work surface. Useful when the work should outlive a thread; Zed can remain the editor. Persistence and prompt editing alone give no reason to switch. |
| [Superset](https://docs.superset.sh/tasks) | Editable task content becomes an agent prompt; task prompt templates are configurable. | **Moderate.** Emphasize maintaining the repository's tasks, methods and accepted guidance together. “The task is the prompt” already fits Superset and cannot carry the distinction. |
| [Agent Orchestrator](https://github.com/Untrivial-ai/agent-orchestrator) | A persistent project orchestrator retains goals and decisions, coordinates workers and exposes work needing human attention. | **Moderate.** Coga's angle is authoring methods for ongoing jobs, routines and cases across domains. Human direction and continuing coordination already belong to AO's documented coding experience. |
| [Backlog.md](https://github.com/MrLesk/Backlog.md) | Human-editable Markdown tasks, plans and acceptance criteria, with agent execution and review. Local non-code use is supported. | **Moderate.** Coga adds an operating method: per-job execution stages and responsibilities, reusable context and recurring upkeep. Owning and editing the work definition is shared ground. |
| [Kiro](https://kiro.dev/docs/steering/) | Editable Markdown steering captures persistent product, technical and project knowledge. | **Moderate.** Coga emphasizes authoring different workflows and operating them through chosen agent CLIs. Reusable knowledge and human-editable direction already exist in Kiro. |
| [Spec Kit](https://github.com/github/spec-kit) | An editable specification process with extensions, presets and a documented non-code extension. | **Moderate.** Coga carries ongoing jobs, handoffs and recurring obligations through a shared runtime. Customizing a working method or using files as authoritative instructions is already supported by Spec Kit. |
| [Compound Engineering](https://github.com/EveryInc/compound-engineering-plugin) | Editable methods, knowledge capture and maintenance; an explicit [non-code execution route](https://github.com/EveryInc/compound-engineering-plugin/blob/main/skills/ce-work/references/non-code-execution.md). | **Moderate, close overlap.** Coga supplies persistent tasks and varied human/agent workflows as a common operating environment. CE is engineering-centred, not engineering-only. The existing trial reproduced basic queue/resume behavior with 26 lines of added instructions; neither human review nor compounding is a unique Coga argument. |
| [Pi](https://pi.dev/) | Extensible agent harness, editable prompts and skills, context control, and agent-assisted modification of its own setup. | **Moderate, depending on setup.** Pi supplies a customizable agent; Coga supplies a particular task, workflow and knowledge-maintenance method around existing agents. Hackability and revisable methods overlap. This is not evidence of a tested Coga/Pi integration. |
| [VS Code custom agents](https://code.visualstudio.com/docs/agent-customization/custom-agents) | Markdown agent definitions, tools, instructions and human-initiated handoffs. | **Limited to moderate.** The supporting line could describe this too. Show Coga's saved responsibilities per job and shared upkeep process to explain the additional experience. |
| [GitHub Agentic Workflows](https://github.github.com/gh-aw/experimental/correction-ops/) | Experimental CorrectionOps uses observed human corrections to revise instructions and rollout decisions. [WorkQueueOps](https://github.github.com/gh-aw/patterns/workqueue-ops/) supplies durable issue-checklist queues. | **Limited for the broad thesis.** Even adapting delegation from evidence overlaps. Coga's angle is local, attended work and explicit human/agent ticket stages alongside recurring jobs. Human-reviewed learning alone is insufficient differentiation. |
| [LangGraph](https://docs.langchain.com/oss/python/langgraph/overview) | Developer-authored agent workflows, persistence and human intervention. | **Clear product-category difference.** LangGraph is an application execution framework. Coga runs existing agents from maintained work instructions. Coga is relevant to operating those agents; LangGraph remains relevant when building the application runtime. |
| [CrewAI](https://docs.crewai.com/en/concepts/flows) | Developer-authored flows combine state, events, conditions and agent work. | **Clear product-category difference.** Coga supplies an operator's task/workflow environment; CrewAI supplies application-building abstractions. Generality across domains and delegation are shared ambitions. |
| [Kortix](https://kortix.com/blog/agi-ready-architecture) | Published positioning already connects future agent capability with retained human authority, Git-backed operating files and reviewed learning. | **Limited messaging contrast; clearer architectural difference.** The follow-up source inspection above finds session/runtime provisioning and change-request policy. Coga's local layer over an existing agent is a concrete distinction; comparative usability and performance remain untested. |

## Draft explanatory paragraph

Coga is a lightweight layer for delegating work to the agents you already
use, starting with a single task. Write what you want done in a Markdown
brief, attach the context that matters, and let the agent work from it. Chat
can help shape the brief; you can also edit it directly. Coga assembles the
instructions, launches the agent and records progress and handoffs with the
task. You choose how much to spell out and how much to delegate.
As you take on more tasks, reuse the useful context and methods; Dream
proposes improvements for you to review and merge. Better agents can take
on more responsibility while you keep directing the work through files you
control.

The maintained copy is in
[positioning](../contexts/marketing/positioning/SKILL.md).
The owner also positively received this revised explanation on September 13.
It remains the leading working explanation for the writing ticket. It
describes editable work direction, not complete ownership of every underlying
provider prompt or a universal enforcement boundary.

## What makes the explanation credible

The [composition code](../../src/coga/compose.py) combines the brief, selected
context, current-step instructions and blackboard for an existing agent
CLI. [Workflow handling](../../src/coga/workflow.py) and the
[launcher](../../src/coga/commands/launch.py) carry task state and human handoffs.
The [Dream procedure](../../src/coga/resources/templates/coga/recurring/dream/ticket.md)
proposes maintenance through the same task machinery, with human acceptance
of changes to shared guidance. The thirteen earlier isolated Coga checks
exercise composition and routing; they do not certify that every agent
obeys instructions or that accepted knowledge is always applied correctly.

The [domain review](usage-comparison.md#core-flexibility-across-administrative-and-patent-work)
grounds the flexibility claim in different authored procedures using common
machinery. Private business records are not examples for publication.

For the launch explanation, first demonstrate one editable task and selected
context being handed to an existing agent. Show a clarification or correction
in the task and its recorded progress. Then show reuse or a reviewed proposed
improvement if it helps explain what carries forward. This makes the immediate
delegation benefit visible before expanding into methods that evolve with
capability. An agent may help author each revision; the operator chooses the
accepted method.
