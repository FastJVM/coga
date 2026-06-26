# Coga vs. Paperclip

> **Scope.** This is a focused comparison between Coga and Paperclip as of
> 2026-06-06, based on Coga's local product docs and Paperclip's public docs.
> Paperclip is moving quickly; re-check its README and docs before using this in
> external copy.

## The Short Version

Coga and Paperclip both live near "agent work operating systems," but they are
not trying to be the same thing.

**Paperclip manages agents as a workforce. Coga manages work as repo state.**

Paperclip asks: how do I coordinate an AI company with roles, goals, budgets,
heartbeats, approvals, and dashboards?

Coga asks: how do I make company work legible, repeatable, automatable, and
correctable through files the operator owns?

That difference shows up in features, working style, and philosophy.

## Status Difference

Paperclip is public and productized. Its public surface includes a Node.js
server, React UI, API docs, agent adapters, budget controls, approvals,
pre-built company templates, and a hosted Paperclip.inc offering.

Coga is earlier. It is an internal operating substrate being dogfooded in this
repo before release. That means a direct "who is winning" comparison is mostly
about public attention and product packaging, not proof that one architecture is
right.

Paperclip currently owns the clearer demo: dashboard, org chart, budgets,
heartbeats, "AI company." Coga currently owns a sharper substrate: files, git,
contexts, skills, blackboards, workflow handoffs, and human-reviewed knowledge.

## Philosophy

| Question | Paperclip | Coga |
|---|---|---|
| Primary metaphor | AI company / agent workforce | Company work as repo-native operations |
| Human role | Board/manager of agents | Operator whose judgment remains the authority |
| Agent role | Employee with title, manager, budget, status, heartbeat | Operator assigned to a workflow step |
| Desired feeling | Delegation at scale | Legibility, ownership, and correction speed |
| Default surface | Dashboard/API/server | CLI/files/git/Slack, with UI only as a possible view or remote |
| Risk | The management layer becomes the source of truth | The system feels austere or under-packaged before the loop is felt |

Paperclip's strongest story is "stop juggling agents; manage them like a
company." Coga's strongest story is "run agent work without moving your company
into an agent platform."

Coga is not anti-autonomy. It is anti-opaque autonomy and anti-defaulting every
task to the same autonomy level. Coga's model is to pick the right autonomy
level per task or step: human-attended, agent-run, script-run, recurring, or
review-gated.

## Feature Comparison

| Area | Paperclip | Coga |
|---|---|---|
| Source of truth | Server/API/database; local setup can use embedded Postgres and local storage | Markdown files under `coga-os/` plus git history |
| Work unit | Issue/task in Paperclip | Task directory with `ticket.md`, `blackboard.md`, and `log.md` |
| Agent coordination | Agent org chart, roles, reporting lines, statuses | Workflow handoffs across human, agent, other-agent, and script steps |
| Execution | Heartbeats wake agents on schedule, assignment, mention, or manual trigger | `coga launch`, `coga recurring`, `coga recurring launch`, and `mode: script` |
| Session continuity | Adapter-level session persistence, e.g. Claude session IDs or Codex response chaining | Recompose prompt from files each launch; preserve task-local reasoning in blackboard |
| Knowledge | Runtime skills and project/company context; broader memory/knowledge remains a moving area | Contexts and skills as durable markdown; Dream/Retro propose knowledge changes through PRs |
| Skills | Skills are discoverable runtime capabilities injected by adapters | Skills are process knowledge bound to workflow steps; script skills run with Coga task env vars |
| Recurring work | Routines and heartbeats create tracked issues and wake agents | Recurring templates create period-keyed Coga tasks with normal ticket/blackboard/log artifacts |
| Approvals | Board approvals, hire approvals, strategy approvals, pause/resume/terminate | Human workflow gates, `mark active`, PR review, and human-reviewed knowledge diffs |
| Cost control | First-class budgets, token/cost reporting, hard stops | Not first-class today |
| Locking | Atomic checkout and DB-backed execution locks | No hard mutex; status is the signal and divergence is recoverable through git |
| UI | Product dashboard and hosted/cloud story | CLI-first; UI should remain a view or remote over repo state |
| Multi-company | First-class multi-company isolation | Repo-scoped by default; multi-repo operation through git/Coga conventions |

## Working Style

Paperclip work feels like managing an organization:

1. Define a company or goal.
2. Hire/configure agents.
3. Assign or create issues.
4. Let heartbeats wake agents.
5. Monitor dashboard, budgets, approvals, and activity.

Coga work feels like operating a repo:

1. Draft or author a ticket.
2. Attach contexts and choose a workflow.
3. Launch the next operator.
4. Let the operator write to the blackboard and advance the workflow.
5. Correct missing knowledge in contexts or skills so the next run is better.

Paperclip tries to make autonomous delegation manageable. Coga tries to make
automated work inspectable, recoverable, and self-improving.

## Skill Runtime Injection

Both systems have skills, but the binding is different.

Paperclip injects capabilities into agents. Adapter docs describe making skills
discoverable to Claude/Codex so an agent can load the relevant module during a
heartbeat.

Coga binds process knowledge to work. A workflow step names a skill; `coga
launch` composes that skill into the prompt for that step. In `mode: script`,
Coga runs the skill's script directly and injects task metadata through env vars
such as `COGA_TASK_DIR`, `COGA_TASK_BLACKBOARD`, and `COGA_SKILL_DIR`.

The practical distinction:

- Paperclip: "this agent has these capabilities."
- Coga: "this step of this task is executed under this process contract."

That is one of the deepest product differences.

## What Coga Should Learn From Paperclip

Coga should take Paperclip seriously as category pressure. Paperclip shows that
people want:

- visible agent status
- easier remote operation
- cost/budget awareness
- recurring work that keeps moving
- approvals and high-stakes gates
- a clearer first-run demo
- a simple story for non-insiders

Coga can add those without copying Paperclip's architecture if every new surface
remains a view, adapter, or remote over repo state.

## What Coga Should Not Copy

Coga should not become a worse Paperclip. Avoid:

- making a database the durable source of truth
- making UI edits the canonical way state changes
- treating hidden session memory as durable company knowledge
- replacing workflow handoffs with agent-org theater
- turning skills into a plugin fence that makes direct file editing secondary
- selling "zero-human company" as the thesis

Coga's edge is that operators can read and change the exact files the agents
will read next time. Copying a platform control plane too literally would destroy
that edge.

## Positioning Takeaway

Paperclip is the more obvious product:

> Manage an AI workforce with org charts, goals, budgets, approvals, and
> heartbeats.

Coga is the more opinionated substrate:

> Run agent work from your repo: tickets, context, handoffs, recurring
> operations, and audit trail as markdown.

The right comparison is not "Coga lacks Paperclip's UI." The right comparison
is "Paperclip makes agent management a product; Coga makes company operations
repo-native."

## Sources

Coga:

- [`docs/vision.md`](vision.md)
- [`docs/market-thesis.md`](market-thesis.md)
- [`coga-os/contexts/coga/principles/SKILL.md`](../coga-os/contexts/coga/principles/SKILL.md)
- [`coga-os/contexts/coga/architecture/SKILL.md`](../coga-os/contexts/coga/architecture/SKILL.md)

Paperclip:

- [paperclipai/paperclip README](https://github.com/paperclipai/paperclip)
- [How Paperclip Agents Work](https://paperclip.inc/docs/guides/agent-developer/how-agents-work/)
- [Agent Task Workflow](https://paperclip.inc/docs/guides/agent-developer/task-workflow)
- [Writing an Agent Skill](https://paperclip.inc/docs/guides/agent-developer/writing-a-skill)
- [Costs and Budget Controls](https://paperclip.inc/docs/guides/board-operator/costs-and-budgets)
- [Handling Approvals](https://paperclip.inc/docs/guides/agent-developer/handling-approvals)
- [Paperclip.inc About](https://paperclip.inc/about)
