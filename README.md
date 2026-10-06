# Coga: don't don't think.

**Stop repeating yourself to agents.**

Coga is a CLI that runs any agent from Markdown files in your Git
repo. Every launch rebuilds the agent's prompt from those files, never from
chat history. When an agent gets something wrong, you fix the file once, and
every later run starts from the fix.

Coga is built with Coga: see the tickets in [`coga/tasks/`](coga/tasks) and
the full history in [`coga/log.md`](coga/log.md).

## What is it

When you use coding agents a lot, they forget instructions, skip steps and
drift off course. You end up babysitting them. Coga turns the instructions
you keep repeating into a way of working that lives in your repo.

It is built around three ideas:

- **Built for work you discover by doing.** Work is small tickets you can
  reshape at any time. When a premise turns out wrong, rewind the ticket:
  what was learned stays, and abandoned designs stay on disk but out of the
  agent's prompt.
- **Improvements compound.** Coga is full of feedback loops, at every scale:
  - **Within a ticket**, the blackboard carries what each step learned into
    the next one, and a second agent can review the first one's work.
  - **Across tickets**, what a finished ticket taught is folded into the
    contexts and skills that future tickets start from.
  - **Across the system**, recurring jobs such as Dream check docs against
    the code, flag drift and keep skills up to date.
  - **From you**, any correction to a ticket, context or skill takes effect
    on the next launch.

  Changes to the shared rules arrive as pull requests: nothing changes how
  agents work until you merge it.
- **Everything is inspectable and hackable.** The base prompt, workflows,
  docs and skills are plain files, and you can change any of them.
  `coga launch --prompt-report` shows the exact prompt before anything runs.
  You and your agents change the system as your ways of working evolve.

The trade-off: you specify more up front, and you stay the one who decides. In exchange, you stop babysitting your agents.

## Sample Project
I want to add in Codex a plugin to pick the best model with the right "thinking" power (hard, etc.) asit would save quite a bit of money. 

Anyway, I typed

sh' coga build to explain my project. Coga built a first plan using Jev.  (I asked about it)
(screenshot of the plan + link to whole convo)

I read the first ticket and I realized that Codex used as assumption that this is an "solved problem"; in the sense that there were well-known solution. I asked to explain how and why. "Yes you're absolutely I don't know what I'm doing" was basically Claude's answer; I subsequently put it to work on building a research and parking his current plan for when we'll know what to build. I came up with the key idea: use double request to actually compute the drift and use this infrastructure to evaluate different strategies. It came out with the plan and the limitations (we can know only for a given repository and we'll need to redo this periodically).

(links to add: screnshot + comparison in video with Zed and Superset to show more autonomy/less work)
Then it concluded: planning are better with frontier model but implementation any model would do. This is for my repositories, it's not a general results and it's simple enough to not consider Jev further. All of the results are recorded in context blocks so agents have them handy AND the experiment is archived (so accessed on demands by agents but not by default to save tokens)

Altgoether competings tools were all able to build it but they built something different: it's only with Coga that we build this tesging infra, the other built direclty the ooling and I had to be more invovled in the day to day (because Coga forces you to specify more at the beginning)

On my side the time was maube 10 min (of deep concentration) and it was able to figure ou the rest + execute it and MOST importantly carry all of that into the implemtnation phase direclty

OPh and here's the plugin: do use it! 


## Why

To delegate work to agents, you need to give them context: the task, how the system works, and how the work should be done. Together, these make up the **whole context**. Today, that context is scattered across a ticket tracker, `AGENTS.md`, documentation, and code. This works—up to a point.

You start noticing the limits when you keep adding instructions in the chat box: "Push this one directly to main." "Run the full test suite." "Have another agent review this change before opening a PR." You are repeatedly supplying distinctions that your work system leaves implicit. Even a simple project contains several types of work: straightforward bug fixes, research, implementation, and maintenance. They each need different context, procedures, and human decisions.

I built Coga to make those differences explicit.

In Coga, tickets describe the work, workflows define its steps, context blocks hold the knowledge, and skills provide reusable procedures. These all live in Git as Markdown files. For instance, an investigation can have a workflow for running experiments and discussing results; an implementation task can have one for coding, testing, and review.

Coga uses agent conventions, including `SKILL.md`, so humans and agents can read and change the same material directly. The system is meant to be hacked by you and your agent: you can edit the instructions, reshape a workflow, or add a new way of working as the project evolves.



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
[Codex](https://github.com/openai/codex) CLI.

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
