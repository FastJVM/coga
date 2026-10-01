## Coga

Coga is a work system for humans and AI agents. Humans focus on the parts of a problem that are still unclear, and agents automate the parts that have become known. What both learn along the way becomes part of how future work gets done.

### Why I built it

A big part of my work is inventing new things: making judgment calls, figuring things out, and learning what works along the way. I wanted a system where what we learn through the work changes how the next piece of work gets done. I tried a lot of agent tools and couldn't find one built around that idea, so I built Coga.

### The problem: scattered context

When you delegate work to an agent, you need to give it context: the task, how the system works, and how the work should be done. Today that context is spread across a ticket tracker, `AGENTS.md`, documentation, and whatever the agent finds by exploring the codebase.

That holds up for a while. But different work needs different context, so you start pasting task-specific instructions into the chat box and explaining the same things over and over. Agents can rediscover some of it themselves, but discovery costs time and tokens, and you never quite know what they found or what they missed.

### The work system as files

Coga makes the work system itself explicit. Tickets, knowledge, instructions, workflows, and working state live in Markdown files in Git that humans and agents can both read and change.

Because tickets and instructions live in the same place, context becomes declarative. A ticket and its workflow declare the knowledge and skills the work needs — skills are reusable procedures an agent can follow — and Coga assembles the prompt from those pieces deterministically. You can see exactly what the agent is given and why. The foundation isn't left to the agent's judgment. Agents still discover things on top of it, but you know where they start.

### A system you can reshape

When you're building something new, you don't yet know the right architecture, the right process, or even the right way to describe the work. As you learn, you change the knowledge, workflows, and instructions the same way you change the product.

Shared pieces carry a risk: changing one affects future work across the project. That's why they're ordinary versioned files. Every change can be inspected, reviewed, reverted, or rejected in a pull request, just like code.

### Agents work on the system too

Because humans and agents work on the same material, agents can improve the system used to build the product, not only the product itself. When an agent makes a useful discovery, notices a repeated procedure, or gets corrected, it can propose a change to the project's knowledge or workflows. A human reviews the change, and once it's merged, it shapes how similar work gets done next time.

Coga also runs recurring maintenance over that knowledge. Its Dream process looks for knowledge that has become stale, drift between the documented system and the real one, missing knowledge, and useful lessons buried in completed work. It proposes changes as pull requests or durable tickets rather than silently rewriting the team's memory.

### Why not automated memory?

Automated memory is useful, but it still gets things wrong, misses context, and holds on to conclusions that no longer apply. Files can go stale too. The difference is that Coga's knowledge is visible and attributable: you can see what an agent was told, trace where it came from, review proposed changes, and fix or remove it when reality changes.

This knowledge belongs to the team, not to an agent or a hidden memory store, and different agents can use it over time.

### The loop

Humans work on what is still unknown and make the judgments that matter. Agents automate what has become known. The work captures what both learn, and that knowledge improves the next round.

The goal isn't just more autonomous agents. It's humans and agents learning faster together.

## Getting Started

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
[AGPL-3.0-or-later](LICENSE).

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
