# Coga
Coga is a tool built to amplify your thinking and learning.

It is a work system for humans and AI agents. It helps you focus on the parts of a problem that are still unclear, while agents automate the known parts.

As you learn, you update the work. Coga carries those changes into future agent sessions.

A big part of my work is inventing new things — making judgment calls, figuring things out, and learning what works along the way. I needed a system where what we learn along the way becomes part of how the work gets done. I tried a lot of agent tools and couldn't find one built around that idea, so I built Coga.

For humans and agents to create, inspect, and change knowledge together, it has to exist as something they can both work on. In Coga, it lives in Markdown, is versioned in Git, and can be reviewed in a pull request. The knowledge belongs to the team, not to an agent or a hidden memory system. Humans can inspect it, change it, reject it, or remove it, and different agents can use it over time.

Automated memory is useful, but today it still gets things wrong, misses important context, and preserves conclusions that no longer hold. When that memory shapes future work, those errors compound. Coga keeps that learning loop visible so humans can correct it.

This creates a learning loop between humans and AI: humans work on what is still unknown and make the judgments that matter; agents automate what has become known; the work captures what both learn; and that knowledge improves the next round of work.

Coga is built for collaboration, not human replacement. The goal is not just to make agents more autonomous. It is to make humans and agents together learn faster over time.

## Getting Started

```sh
coga build
coga ticket my_first_ticket
coga launch init
```

`coga build` is a guided discussion about your project and your goals. It turns that discussion into tickets, contexts and workflows.

Everything it creates is just files in your repo. Edit them directly with any text editor, or use coga ticket <name> when you want to work through a ticket with an agent.

What it creates is far from perfect — that's the point. It gives you a structure to work from, exposes how agents understand your project and how they would approach it, and gives you something concrete to correct as your own understanding changes.

coga launch <ticket> works through the ticket by launching an agent. It assembles the prompt from the ticket, relevant context, workflow instructions and working state.

When the work teaches you something worth keeping, you decide what should change. Edit it yourself, ask an agent to propagate that new understanding through the project, or let Coga surface and carry it forward through its recurring work.

## Install

## Getting Started

## Concepts

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
