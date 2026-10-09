# Coga: Stop Repeating to Agents

Coga is a CLI that runs any agent from Markdown files in your Git
repo. Every launch rebuilds the agent's prompt from those files, never from
chat history. When an agent gets something wrong, you fix the file once, and
every later run starts from the fix.

Coga is built with Coga: see the tickets in [`coga/tasks/`](coga/tasks) and
the full history in [`coga/log.md`](coga/log.md).

## Key Ideas
When you use coding agents a lot, they forget instructions, skip steps and
drift off course. You end up babysitting them. Coga turns the instructions
you keep repeating into a way of working that lives in your repo.

It is built around three ideas:

- **Built for work you discover by doing.** Work is small tickets you can
  reshape at any time. When a premise turns out wrong, rewind the ticket:
  what was learned stays, and abandoned designs stay on disk but out of the
  agent's prompt.
- **Improvements compound.** Coga is full of feedback loops, at every step:
  - **Within a ticket**, the blackboard carries what each step learned into
    the next one, and a second agent can review the first one's work.
  - **Across tickets**, what a finished ticket taught is folded into the
    contexts and skills that future tickets start from.
  - **Across the system**, recurring jobs such as Dream check docs against
    the code, flag drift and keep skills up to date.
  - **From you**, any correction to a ticket, context or skill takes effect
    on the next launch.
  
- **Everything is inspectable and hackable.** The base prompt, workflows,
  docs and skills are plain files, and you can change any of them.
  `coga launch --prompt-report` shows the exact prompt before anything runs.
  You and your agents change the system as your ways of working evolve. 
  Changes to the shared rules arrive as pull requests: nothing changes how
  agents work until you merge it.


The trade-off: you specify more up front, and you stay the one who decides. In exchange, you stop babysitting your agents.

## Example

I wanted a plugin that picks the model and reasoning level per task, instead
of running Astra at max reasoning for everything. `coga build` turned ten
minutes of conversation into a plan of tickets, but the plan assumed routing
was a solved problem. It isn't.

Asked directly, Claude would say routing isn't a solved problem. But it's easy for Claude to amplify your hidden biases and assumptions which is what happened here. Building a plan makes them visible, so you can question and correct them. Together.

So we think harder, backtrack and build a research plan in tickets (written with Claude, run
by Codex): [state of the art](https://github.com/FastJVM/thinkpick/blob/main/coga/tasks/classifier/state-of-the-art-review.md),
[head-to-head ground truth](https://github.com/FastJVM/thinkpick/blob/main/coga/tasks/classifier/head-to-head-ground-truth.md),
[Jev](https://github.com/FastJVM/thinkpick/blob/main/coga/tasks/classifier/evaluate-jev.md),
[candidate scoring](https://github.com/FastJVM/thinkpick/blob/main/coga/tasks/classifier/score-candidates.md), then the
[decision](https://github.com/FastJVM/thinkpick/blob/main/coga/tasks/decide-classifier-approach.md). The answer becomes a context
every later ticket starts from. Browse the whole example in
[thinkpick's tasks](https://github.com/FastJVM/thinkpick/tree/main/coga/tasks).

## Install

## Quick Start 
### Existing repo

### New repo

## Development & Community

## Donors and Sponsors
## Licnence

```sh
coga build
```

`coga build` is a guided discussion about your project and your goals. It turns that discussion into tickets, contexts and workflows.

Everything it creates is just files in your repo. Edit them directly with any text editor, or use coga ticket <name> when you want to work through a ticket with an agent.

What it creates is far from perfect — that's the point. It gives you a structure to work from, exposes how agents understand your project and how they would approach it, and gives you something concrete to correct as your own understanding changes.

```sh
coga status
```
lists all the tickets

```sh
coga ticket my-first-ticket
``` will start another conversation to complete the ticket. You can edit it yourself.


```sh
coga launch my-first-ticket
```
coga launch <ticket> works through the ticket by launching an agent. It assembles the prompt from the ticket, relevant context, workflow instructions and working state.

When the work teaches you something worth keeping, you decide what should change. Edit it yourself, ask an agent to propagate that new understanding through the project, or let Coga surface and carry it forward through its recurring work.

## Install

Coga needs Python 3.11+, Git, and an authenticated
[Claude Code](https://claude.com/claude-code) or
[Codex](https://github.com/openai/codex) CLI; in a terminal, `coga init`
offers to install and log in whichever agent CLI you pick.

```sh
uv tool install coga            # or: python -m pip install coga
cd <your git repository>
coga init --user <your-name>
coga ticket "<what you want done>"
coga launch <ticket>
```

[Install](docs/contexts/coga/install/SKILL.md) covers setup, joining a
repository that already uses Coga, and troubleshooting.
[First task](docs/contexts/coga/first-task/SKILL.md) walks one ticket from
draft to reviewed result. A [95-second demo](https://www.youtube.com/watch?v=iwnewxJvRPc)
was recorded in July 2026; some command names may have changed since.

## Who it is for, and its limits

Coga is for small technical teams who already use CLI agents, are comfortable
with Git and the shell, and want to understand and correct the material their
agents work from. It fits when writing down how work should be done costs less
than supervising the same work indefinitely.

It is local, self-hosted and self-supported: no managed service, SLA, hosted
dashboard or zero-setup path. Workflows are linear sequences of steps; dynamic
orchestration belongs in an agent framework. Coga does not replace judgment: it
makes the points where you decide and correct explicit.

This is a field report. Coga runs the work that builds Coga at FastJVM, a
two-person company, and we build it around a thesis — that a two-person
technical team can produce the output of a ten-person team when agents do the
mechanizable work and humans specify, evaluate and correct — which is
[a bet, not a measured result](docs/contexts/product/vision/SKILL.md). One
dated observation: in the week ending 2026-07-05 the repository recorded
31 distinct agent-operated workstreams, counted per week rather than as
simultaneous processes ([method and limits](docs/evidence/velocity.md)).
Human time per shipped task has not been measured.

Managing prompts and instructions as files has close precedents. For dated
comparisons with other tools, see the [evidence pages](docs/evidence/) and the
[market landscape](docs/archive/market-landscape.md) record.

## Learn more

- [Documentation index](docs/README.md): start, understand, operate and
  develop.
- [Principles](docs/contexts/coga/principles/SKILL.md): the design
  constraints.
- [Contributing](CONTRIBUTING.md).

Coga is free software licensed under
[Apache-2.0](LICENSE).

## Weekly telemetry

By default, operator recurring sweeps attempt a weekly aggregate usage snapshot
(counts, movement, bounded version/platform fields) to FastJVM’s US PostHog
project, shared with Multiply. This measures repos with active sweeps, not
installs: Coga installs no scheduler, and download/init send nothing. An opaque
repo ID is committed and shared by synced clones. No task content is sent.
The network peer sees source IP; project settings discard it and disable GeoIP.
Editable/source installations do not report.

Set `[telemetry] enabled = false` in shared or local config to stop sending and
its Slack receipt. Disabling stops sending; movement from the gap may appear in
the first count after re-enabling. See the [contract](docs/contexts/coga/telemetry/SKILL.md)
and [operator runbook](docs/contexts/coga/telemetry/operations/SKILL.md) for the boundary, verification and deletion.
