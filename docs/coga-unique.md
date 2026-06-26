# Where Coga Is Unique

> **Scope.** This doc isolates Coga's uniqueness. It is not a full product
> thesis; see [`vision.md`](vision.md) and [`market-thesis.md`](market-thesis.md)
> for the larger argument.

## The Short Version

Coga is unique in the combination, not in any single primitive.

Tickets, agents, skills, markdown, recurring jobs, and task state machines all
exist elsewhere. Coga's claim is the way those pieces are held together:

> Durable company work lives in git-backed markdown, agents operate from that
> substrate, autonomy is chosen per task or step, and knowledge compounds only
> through inspectable human-gated changes.

The product is not "an agent dashboard." It is a repo-native operating substrate
for small technical teams.

## 1. The Repo Is The System Of Record

Coga's most important architectural choice is that durable state is not hidden
in an app database.

Tasks are directories. Knowledge is context files. Process is skill files.
Workflow definitions are files. The blackboard is a file. State transitions are
logs and git history.

This matters because the correction loop is direct:

1. An agent gets something wrong.
2. The operator identifies the missing rule or fact.
3. The operator edits the context, skill, workflow, or ticket.
4. The next launch reads the changed file.

No vendor support ticket, migration, opaque memory store, or platform config
layer is needed. The operator can inspect and change the same material the agent
will consume.

## 2. Workflow Means Handoff, Not "Automation Pipeline"

Coga's workflow primitive is not just a sequence of automated steps. It is an
ordered set of operator handoffs.

A task can move from:

- human design
- agent implementation
- peer-agent review
- agent PR publication
- human review
- script-mode maintenance

The assignee can change at each step. That means Coga can encode not only what
happens, but who has authority at each point.

This is why the planned rename from `workflow` to `playbook` matters: the shape
is closer to "ordered plays with handoffs" than to a background automation flow.

## 3. Autonomy Is A Per-Task And Per-Step Choice

Coga is not manual-first and not autonomy-first. It is judgment-first.

Coga has several autonomy levels:

- `interactive`: human-attended agent work for ambiguous or high-context tasks.
- `auto`: autonomous agent work where the agent should panic or hand off when
  stuck.
- `script`: deterministic automation with no agent judgment.
- workflows: mixed human, agent, peer-agent, and script steps in one task.
- recurring templates: stable work that runs repeatedly as normal Coga tasks.
- Dream/REM: maintenance loops that inspect tasks and propose or perform bounded
  work.

The point is not to keep humans in every loop. The point is to put the right
amount of autonomy in the right place and keep the resulting work legible.

## 4. Knowledge Compounds Through Files And PRs

Coga treats context as the appreciating asset.

If a task reveals durable knowledge, that knowledge belongs in a context or
skill, not in chat history. If the system can infer a correction from recent
work, Dream/Retro can propose it. But durable knowledge should land through a
reviewed diff, not silent auto-memory.

This gives Coga a specific memory stance:

- blackboard = task-local working memory
- log = state-transition history
- contexts = durable facts about the world
- skills = durable procedures for doing work
- PRs = human gate for long-term memory changes

That is different from session persistence. A resumed session may remember what
it was doing; Coga's context library changes what future agents know.

## 5. Skills Are Bound To Work, Not Just Agents

Coga uses the standard `SKILL.md` shape, but the product semantics are
work-bound.

In agent mode, a workflow step's skill is composed into the launch prompt. In
script mode, a skill can carry an executable script. Coga injects task metadata
through env vars, so the script runs inside the same task model as agent work:
ticket, blackboard, log, repo root, Coga root, and skill directory.

That means a skill is not merely an optional capability an agent may discover.
It is a process contract for a specific step of work.

## 6. Recurring Work Produces Normal Work Artifacts

Coga recurring tasks are not just cron jobs.

A recurring template creates a period-keyed task. That task has the same
ticket, blackboard, log, contexts, skills, launch path, and review gates as any
other Coga task.

This makes recurring operations inspectable:

- what was launched
- what context it used
- what the agent/script wrote down
- whether it panicked, bumped, paused, or finished
- what should be corrected before the next period

That is the difference between "a job ran" and "an operation happened and left
evidence."

## 7. The Blackboard Is Recoverable Working Memory

The blackboard is deliberately plain and task-local. Agents write plans,
findings, blockers, test results, PR links, and decisions there.

That gives Coga a simple but powerful recovery path:

- an agent can crash and another can resume
- Claude can hand off to Codex
- a human can inspect why a decision was made
- a future Dream/Retro pass can mine the task for durable knowledge

The blackboard is not long-term memory. It is the working surface that lets
long-term memory be extracted deliberately.

## 8. UI Is Allowed, But It Must Not Become The Source Of Truth

Coga's no-UI posture is not "we did not get to it yet." It is part of the
architecture.

A future UI can be useful:

- status view
- task browser
- launch remote
- approval surface
- cost/status dashboard
- recurring run monitor

But it should remain a view or remote over repo state. The durable source of
truth should stay in files, because that is what keeps Coga inspectable,
scriptable, git-diffable, and agent-operable.

The wedge user is the person who says: "Thank you, it has a CLI and no UI."

## 9. What Is Not Unique

Coga should not overclaim.

These are not unique by themselves:

- agents doing tasks
- markdown files
- skills
- recurring jobs
- ticket state machines
- Slack notifications
- multi-agent review
- local-first tooling

The unique claim is the disciplined combination:

> operations-as-code, executed by agents and scripts, with human-gated memory and
> repo-native state.

## 10. The Buyer It Is For

Coga's first users are probably not generic business operators.

The likely wedge:

- founder-engineers
- tiny technical companies
- research labs
- AI-native dev shops
- open-source maintainers
- people already running many Claude/Codex sessions manually
- operators who distrust opaque agent platforms

They already understand git, terminals, diffs, PRs, and repo conventions. Coga
turns those instincts into a company operating substrate.

## Positioning Line

Coga is for operators who want agents to run company work without moving the
company into an agent platform.

Or, more concretely:

> Coga gives your repo workflows, recurring operations, agent handoffs,
> blackboard memory, and compounding knowledge as files.
