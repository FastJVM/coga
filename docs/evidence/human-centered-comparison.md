# Human control in practice: Coga and the alternatives

**2026-09-15.** Follow-up to [who operates the agents in practice](pitch-evaluation.md#who-operates-the-agents-in-practice--2026-09-15).
The question is whether Coga changes the person's working relationship with
agents: define useful work, leave it progressing, and return to results and
decisions. This checks the implementation behind that promise.

**Finding:** Coga has a substantial difference from Zed's standard thread
workflow. Prepared tasks, recorded handoffs and explicit human steps drive
execution. The owner's clarified criterion is **who controls the timing of
human attention**: prepare work together, let each eligible task reach its
next human handoff or blocker, then review the gathered decisions when the
person chooses. Merely launching in the background or notifying a person
does not establish this whole-batch behavior. Neither does the presence of a
human question prove that all other work must stop. Superset supplies agent
coordination; AO has a durable coordination path; Kortix supports deferred
work; CE can run without a human present. Coga's case is the supplied method
for managing the whole set of tasks and its directly editable local state.

Evidence here combines source inspection, 18 passing Coga checks, a separate
pure prompt-composition probe, existing Coga work records and the previously
recorded CE trial. It is not a new live trial of every product or a measurement
of comparative attention. The owner's current Zed test is useful qualitative
feedback: the UI is pleasant and the working experience feels different. It
does not by itself establish the behavior of every Zed agent or extension.

## What Coga actually does after delegation

An illustrative batch has a research task, an implementation task and a
drafting task. The research needs a new human decision; implementation reaches
an owner review step; drafting remains executable. In unattended megalaunch:

1. The runtime reads eligible tasks and their current workflow steps. An
   owner step stays with the human, including when an agent override is given.
2. The agent's conduct instructions say that an available terminal does not
   mean a person is waiting. A genuinely unavailable decision must become a
   recorded blocker through `coga block`.
3. That command records the ask and emits the completion marker. The
   supervisor ends the worker session, and the sweep can advance another
   eligible task. Printing a question or a prose “blocked” message is not the
   same transition.
4. Subsequent agent steps can proceed until a blocker, human step, completion
   or failure ends that task's run. Eligible unrelated work can continue.
5. The human returns to an explicit question or review step. A later launch
   composes instructions from the current files, including recorded answers
   and work state; it does not require restoring the old model conversation.

These are maintained runtime and protocol behaviors, rather than a hope that
one long conversation will remember the arrangement. See the
[sweep and routing](../src/coga/megalaunch.py),
[unattended conduct](../src/coga/resources/prompt-megalaunch.md),
[block command](../src/coga/commands/block.py),
[supervisor](../src/coga/repl_supervisor.py) and
[prompt composition](../src/coga/compose.py).

The boundaries matter. The local supervisor must remain running. Work needs
an eligible next task. The model must report substantive blockers correctly;
timeouts end stalled sessions but do not manufacture a useful explanation.
The service order is oldest first with numbered subtrees in sequence, not
an intelligent planner that discovers and optimizes every dependency. A
dependency-drain pass can revisit recorded blockers naming completed tasks;
it does not decide unanswered human questions. Explicitly selecting a blocked
task is a separate attended resolution path.

This also concerns a particular Coga mode: ordinary attended launches support
conversation and clarification. Human control means choosing the boundary,
not making every task unattended. The shipped
[design/implementation workflow](../src/coga/resources/templates/coga/bootstrap/workflows/code/design-then-implement.md)
makes this concrete: design and evaluation lead to owner approval, then
implementation and a PR, then owner review. Workflow steps are snapshotted
for a task; later template edits do not silently change its route. Selected
skill and context content is read again for later launches.

## Where the alternatives differ

### Zed: a substantial difference in the supplied working method

Zed's [parallel-agent procedure](https://zed.dev/docs/ai/parallel-agents)
organizes agent threads and isolated workspaces. The person can launch work,
leave it running and return to a notification. That is useful, and continuous
attendance is not required. The inspected procedure does not supply Coga's
policy for advancing a prepared batch past human gates and recorded blockers.

The practical distinction is **working alongside agents in a workspace**
versus **preparing work that advances through recorded handoffs**. Neither
precludes the other: Zed can be a pleasant editor for Coga's files and results.
The reason to add or switch to Coga is repeatedly needing that delegation
method, not disliking Zed's UI.

Keep native Zed agents, external ACP agents and terminal agents separate.
External agents bring their own execution methods and authentication. Zed
supports paid ChatGPT subscriptions through its ChatGPT Subscription provider
or Codex, and Claude Pro/Max through Claude Agent or Claude Code. Confusing
API-key setup is not evidence that subscriptions are unsupported.
[Subscription paths](https://zed.dev/docs/ai/use-an-existing-subscription),
[external agents](https://zed.dev/docs/ai/external-agents).

### Superset: coordination belongs to an agent's working context

Its shipped orchestration skill assigns launching workers, monitoring,
forwarding dependency results and verifying completion to an agent. Its own
repository instructions explicitly tell development agents to use that CLI
for isolated workspaces and long-running jobs. It is inaccurate to count
every orchestration command as human labor.
[Shipped skill](https://github.com/superset-sh/superset/blob/855adfc7d450d900cf5e9fdcceb7fb0e63b26b07/plugins/superset/skills/orchestrate/SKILL.md),
[development instructions](https://github.com/superset-sh/superset/blob/855adfc7d450d900cf5e9fdcceb7fb0e63b26b07/AGENTS.md).

The distinctive implementation choice is that the skill keeps the semantic
task map in the coordinator's working context. Organization tasks are issue
records, not orchestration dependency nodes. Worker completion and blocker
markers are conventions read from terminal output. Recovering terminal IDs
is not itself reconstruction of the task map. Coga puts task state and routing
in files the runtime rereads. That supports a concrete preference for Coga
when inspecting, editing and resuming the definition of work matters. It
does not establish that Superset cannot finish a delegated batch.
[Coordinator procedure](https://github.com/superset-sh/superset/blob/855adfc7d450d900cf5e9fdcceb7fb0e63b26b07/plugins/superset/skills/orchestrate/SKILL.md).

**On “agents ask me when they need me”: yes, the user promise overlaps.**
The worker reports to its coordinator, which can resolve the need itself or
ask the person. The skill says to launch all ready independent workers and
monitor all running workers. Its blocker rule does not expressly stop the
whole batch when one task needs an answer. The inspected text also does not
establish how dispatch proceeds while an unanswered human question is
pending. No live comparison here demonstrates that Coga needs fewer human
interruptions in that situation. Superset's orchestration skill is itself
Markdown, so editable instructions alone are not an exclusive distinction.

### Agent Orchestrator: delegation is real, including durable reports

The injected coordinator instructions assign planning, spawning workers and
routing feedback to the agent. The cloud source goes further: a worker report
is delivered to its parent coordinator through a transaction. The message
path records terminal input or a queued turn and wakes a waiting worker;
the durable queue remains authoritative if a notification is lost. This is
more than asking a person to read a notification and type “continue.”
[Coordinator instructions](https://github.com/Untrivial-ai/agent-orchestrator/blob/d6c7d601890638088e76b3528e8bc6b9ef72624a/backend/internal/session_manager/prompt.go),
[worker report delivery](https://github.com/Untrivial-ai/agent-orchestrator/blob/d6c7d601890638088e76b3528e8bc6b9ef72624a/cloud/internal/postgres/orchestrator_store.go),
[durable message path](https://github.com/Untrivial-ai/agent-orchestrator/blob/d6c7d601890638088e76b3528e8bc6b9ef72624a/cloud/internal/postgres/event_store.go).

This establishes an implemented cloud path, not that the same behavior is
available in every desktop release. Coga's stronger comparative angle is
direct ownership of task definitions, routing and reusable context. “AO
cannot continue without the human” is not supported by this inspection.

### Kortix: a close alternative, with a different boundary for ownership

Kortix stores project prompts, skills and memory in Git. Its agent can operate
sessions, project configuration and scheduled work through commands. Trigger
dispatch uses durable execution records; delivery into an existing session
uses a queued command with retry and failure handling. Its reflection process
reviews session histories and proposes changes through change requests.
These are substantial overlaps with the Coga thesis.
[Operational instructions](https://github.com/kortix-ai/suna/blob/05c2901f6d510da70500fc5c3ef207bfc233d8cc/packages/starter/templates/managed/.kortix/opencode/skills/kortix-system/SKILL.md),
[trigger implementation](https://github.com/kortix-ai/suna/blob/05c2901f6d510da70500fc5c3ef207bfc233d8cc/apps/api/src/projects/lib/triggers.ts).

Session-local instruction edits take effect immediately. Shared changes
require review, and the refinement procedure permits a human **or another
agent with merge rights**. The September 16 follow-up traced the actual merge
route: it checks the person's merge capability, calls the agent-scope check,
and rejects the originating session's self-merge. Human-only acceptance can
be configured through the agent grants; the presence of an optional reviewer
agent is not evidence that human control is missing. Managed `kortix-*`
skills are platform-owned and overwritten at session boot; extensions use
separate project skills.
[Refinement protocol](https://github.com/kortix-ai/suna/blob/05c2901f6d510da70500fc5c3ef207bfc233d8cc/packages/starter/templates/managed/.kortix/opencode/skills/kortix-harness-refinement/SKILL.md),
[change-request policy](https://github.com/kortix-ai/suna/blob/05c2901f6d510da70500fc5c3ef207bfc233d8cc/apps/api/src/projects/change-request-policy.ts),
[merge route](https://github.com/kortix-ai/suna/blob/05c2901f6d510da70500fc5c3ef207bfc233d8cc/apps/api/src/projects/routes/r9.ts#L42),
[managed skill implementation](https://github.com/kortix-ai/suna/blob/05c2901f6d510da70500fc5c3ef207bfc233d8cc/apps/api/src/runtime-assets/managed-skills.ts).

Coga explicitly puts acceptance of accumulated shared knowledge with the
human and keeps its method in locally owned files and tooling. Dream's
substantive knowledge changes are proposal PRs for human review; safe
deterministic maintenance is a separate category. That is Coga's explicit
policy, not an exclusive capability or a security boundary against an
unrestricted agent. The stronger distinction here is local ownership of the
coordination method and runtime.
[Coga principles](../coga/contexts/coga/principles/SKILL.md),
[Dream procedure](../coga/recurring/dream/ticket.md).

### Compound Engineering: a method can supply much of the behavior

Stock LFG advances one job through stages and stops at a real blocker. Its
current interaction rule explicitly accounts for human absence: questions
through brainstorming are reserved for when a person is present; other work
proceeds within authorization, and unresolved blockers end the run with a
report. It is designed to run under schedulers and outer coordinators too.
Claiming that CE inherently requires the person to stay available is wrong.
The missing stock behavior in this comparison is Coga's independent-task
sweep and its handling of human handoffs across the whole prepared set. The
previous [local adoption trial](adoption-trial.md) added a 26-line coordinator
instruction file and observed a code task, dependent non-code brief, declared
human gate and restart from edited plans without manual routing during
execution. No newly discovered blocker occurred in its first batch. This is
evidence that the behavior can be assembled with CE, not that CE ships Coga's
queue or that unexpected blocker recovery was tested. Ordinary setup and
review are not automatically extra attention compared with Coga.
[Current stock LFG](https://github.com/EveryInc/compound-engineering-plugin/blob/main/skills/lfg/SKILL.md).

### Kiro: autonomous work and dependency-aware spec execution

The current web procedure asks clarifying questions up front, plans the
work, delegates execution and can produce a PR without step-by-step human
direction. If new clarification is needed, that task enters Needs attention
and waits. This overlaps with preparing work before leaving. The documented
procedure does not establish megalaunch's sweep over separate prepared tasks
and their successive human handoffs. A waiting Kiro task also does not prove
that every other Kiro session stops. Coga's difference is the supplied batch
method, not the mere possibility of leaving during execution.
[Kiro autonomous mode](https://kiro.dev/docs/web/autonomous-mode/).

**Additional path checked:** Kiro Specs can run all tasks in a prepared spec.
It builds a dependency graph and executes independent tasks in successive
waves. Describing Kiro generally as only a single independently launched task
would therefore be incomplete. Its supplied spec structure is requirements or
bug analysis, design, then implementation tasks. For open-ended research, the
comparison concerns how hypotheses, admissible evidence and later decisions
change that structure, not whether Kiro can schedule dependencies.
[Kiro Specs](https://kiro.dev/docs/specs/).

### GitHub Agentic Workflows: the broad schedule promise is shared

WorkQueueOps supplies persistent queues processed over scheduled runs. Its
cache-memory example processes a batch, records each item as completed or
failed with an error note, saves the remaining queue and reports the result.
Its discussion example is explicitly for asynchronous collaboration where
people inspect work before or after processing. These are supplied patterns
for a workflow author, not proof of an identical general-purpose human-blocker
policy. They do show that durable batch progress and later human review are
not exclusive to Coga. Coga offers a local task/context/workflow method around
agent CLIs; this alternative uses GitHub workflow execution and its queue
backends. Which surface better fits the operator is the relevant choice.
[WorkQueueOps](https://github.github.com/gh-aw/patterns/workqueue-ops/).

## Strength of the schedule-based differentiation

| Compared with | Assessment on the owner's criterion |
|---|---|
| Zed's standard thread workflow | **Strong supplied-method difference:** Coga advances the prepared task collection to recorded handoffs. Zed already permits independent background threads. |
| Superset's orchestration skill | **A more explicit Coga policy; comparative advantage unresolved:** the coordinator manages workers, but its behavior while a human question is unanswered is not fully specified. No finding here shows that all Superset dispatch necessarily stops. |
| AO's coordinator | **Close alternative:** durable worker reports can wake coordination without a person. That is not proof of the exact Coga batch policy, nor evidence that Coga requires less human attention. The inspected durable report path is cloud source, not a verified desktop release feature. |
| Stock CE LFG | **Meaningful batch difference, weaker absence claim:** CE handles a delegated job without a present human. The recorded custom integration reproduced a small task queue with a declared human gate. |
| Kiro | **Overlap in both preparation and task scheduling:** autonomous mode clarifies up front, and Specs executes a prepared dependency graph in waves. Coga's comparison must concern human handoffs across the evolving task collection, not an alleged absence of dependency scheduling. |
| Kortix | **Substantial overlap in deferred work:** its scheduling playbook includes recording state and scheduling a continuation after an approval or reply. This does not demonstrate an identical unattended sweep over arbitrary tickets. Local ownership and explicit workflow boundaries matter more to Coga's case here. |
| GitHub Agentic Workflows | **Weak distinction in the broad promise:** persistent scheduled batches and asynchronous review already exist as supplied patterns. The implementation surface and working method differ. |

The pitch is strong for a person whose day is repeatedly interrupted to feed
or restart agent sessions. It does not establish a universal reason to leave
an existing coordinator that already lets that person batch decisions.
Describe **“Coga works on your schedule”** through the observable prepared-work
cycle; do not silently substitute “can run unattended” when assessing it.

Kortix source for the approval-wait case:
[scheduling playbook](https://github.com/kortix-ai/suna/blob/05c2901f6d510da70500fc5c3ef207bfc233d8cc/packages/starter/templates/managed/.kortix/opencode/skills/kortix-system/references/scheduling.md).
The same playbook distinguishes long waits from an ordinary clarification
that the agent should ask directly. General deferred execution is therefore
evidence of overlap, not proof that every question is automatically parked
while another ready task is dispatched.

## Coga's own usage and a limitation found in this check

### Scope note for the research-use follow-up

The [September 16 research comparison](research-work-comparison.md) develops
the CE and Kortix replacements concretely and gives the keep-or-switch
judgment. It also checks CE's experiment loop and Kortix's connected-computer
path, which prevents treating research or access to local hardware as Coga
exclusives.

The owner subsequently asked about open-ended human/agent research rather
than routine operations. The comparison criterion expands: can a person
delegate a bounded investigation, receive evidence and critique, revise the
question or stop a research line, and preserve the accepted reasoning for
later work? A reusable investigation method does not require knowing the
eventual result or predefining every future task.

This is not an exclusive capability claim. CE explicitly supplies
[brainstorming](https://github.com/EveryInc/compound-engineering-plugin/blob/main/skills/ce-brainstorm/SKILL.md),
[evidence-grounded judgments](https://github.com/EveryInc/compound-engineering-plugin/blob/main/skills/ce-pov/SKILL.md)
and [planning](https://github.com/EveryInc/compound-engineering-plugin/blob/main/skills/ce-plan/SKILL.md),
including non-software paths and a pipeline return when a settled decision
is invalidated. GitHub Agentic Workflows also documents a
[research/plan/assign/review pattern](https://github.github.com/gh-aw/patterns/research-plan-assign-ops/)
with artifacts and human checkpoints; its example is software maintenance,
not evidence that it supplies a scientific experiment protocol unchanged.

A proposed research demonstration should make the ordinary output of an
agent phase be **evidence for a human decision**, then show that decision
changing the next task and reusable context. The comparison should identify
which tool supplies the coordination and which domain-specific methods the
operator supplies. Research rules, hypotheses and experimental checkers do
not become Coga-exclusive merely because they live in a Coga project.

### Existing public Coga records

The method is used to maintain Coga itself. The completed
[megalaunch activation ticket](../coga/tasks/megalaunch-activates-picks-before-preflight.md)
records implementation, peer evaluation, PR preparation and owner review.
Its fix also illustrates why runtime details matter: a task must not be
marked active before the promised preparation has actually succeeded.

The [existing upkeep audit](upkeep-audit.md) records a Dream batch producing
13 merged proposal PRs and 18 draft tickets. Generation needed no additional
genuine human instructions in the inspected transcript; merge counts and
transcript turns do not measure human review time. The history also records
[Dream scan agents returning without findings](../coga/tasks/dream-phases-2-3-cannot-complete-scan-subagents-re.md)
and [findings being lost between routing paths](../coga/tasks/dream-findings-have-three-routing-holes-that-lose.md).
Those are completed repair records, not claims that the old bugs remain.
They show both real use and the maintenance needed to keep delegation useful.

**A present prompt-delivery limit was reproduced.** A temporary ticket with
separate level-two `Description`, `Acceptance Criteria`, `Proposed Shape`
and `Context` sections, plus a blackboard, was passed directly to
`compose_prompt(..., launch_context="megalaunch")`. Description, Context and
blackboard markers appeared in the result. Acceptance Criteria and Proposed
Shape markers did not. The [composer](../src/coga/compose.py) extracts named
sections and stops at the next level-two heading.

The agent can still read the full original ticket, and relevant implementation
instructions tell it to do so. This probe establishes omission from the
initial composed prompt, not that the material is inaccessible or always
ignored. It qualifies an overly broad “everything you edit is directly in the
prompt” claim. No agent was launched and no source behavior was changed.

## What this supports saying

**Candidate explanation, not a newly approved campaign:**

> Define the work. Let agents carry it forward. Come back where you're needed.

Coga makes that concrete with tasks, reusable context and workflows you can
read and edit. You choose which steps agents own and where a human decision
belongs; megalaunch advances prepared work and records the points that need
you. That combination is a substantial reason to try it when managing agent
threads has become work in itself. For someone already using a coordinator,
the reason is preferring this explicit, locally owned working method—not an
exclusive claim to unattended execution or human control.

## Verification record

Coga inspected at `ffb0e361ae0ed8b77cbe5eaaea39c7d1e7bc5e1f`. Competitor
implementation links above are pinned to the inspected commits; current
product documentation and stock CE LFG links are mutable.

The following existing checks passed: **18 passed in 1.27s**. Parametrization
accounts for more cases than selectors. They exercise test agents and process
supervision, not a new live model benchmark. `tomlkit` was installed only in
the temporary dependency directory; repository dependencies were unchanged.

```bash
PYTHONPATH=/tmp/coga-human-center-deps python -m pytest -q \
  tests/test_megalaunch.py::test_megalaunch_agent_override_keeps_human_gate \
  tests/test_megalaunch.py::test_megalaunch_skips_open_blocker \
  tests/test_megalaunch.py::test_megalaunch_redrains_ticket_that_blocked_during_main_sweep \
  tests/test_megalaunch.py::test_megalaunch_drains_blocker_after_dependency_finishes \
  tests/test_megalaunch.py::test_megalaunch_selection_resumes_blocked_and_reblocks_unresolved \
  tests/test_megalaunch.py::test_megalaunch_reapplies_sweep_gates_to_exact_ticket_bytes \
  tests/test_megalaunch.py::test_megalaunch_chains_agent_owned_steps \
  tests/test_megalaunch.py::test_megalaunch_missing_packaged_prompt_fails_task_not_sweep \
  tests/test_compose.py::test_stock_step_prompt_escalates_per_launch_mode \
  tests/test_compose.py::test_compose_open_blockers_add_resolution_preamble \
  tests/test_repl_supervisor.py::test_sentinel_file_terminates_child \
  tests/test_repl_supervisor.py::test_idle_timeout_terminates_silent_child
```
