# Coga

**A company OS for small teams in the agentic era.**

## Agents do. Humans think. In your repo, on a machine you own.

You already know how to run several agent sessions in parallel: open more
terminal tabs, paste more prompts, and keep the state of each job in your head.
Coga turns those tabs into an operation. Every session gets a ticket, a
blackboard that survives crashes, a queue for questions that need judgment, and
a git-backed record of what shipped. `coga megalaunch` schedules the queue: when
one task blocks, it parks the question and starts the next. You move from
piloting every session to air-traffic control—answering batched interrupts
instead of acting as the CPU.

## See the loop

<!-- The 60-second morning-ritual demo from marketing/add-killer-demo will replace this slot. -->

https://github.com/user-attachments/assets/b310bb0f-2312-4e19-98d4-cc65548b01c1

**[Watch the current 95-second demo →](https://www.youtube.com/watch?v=iwnewxJvRPc)**

## The bet

We are building Coga around a bet: a two-person technical team can produce the
output of a ten-person team when frontier agents do the mechanizable work and
the humans concentrate on specification, evaluation, and correction.

That is a thesis, not a measured productivity multiplier. The full argument,
including the conditions and failure modes, is in [the vision](docs/vision.md).

## Measured on itself

Coga runs the work that builds Coga. Its repository records a few categorical
facts we can defend without pretending they prove the bet:

- agents carry work through implementation steps after a human or scheduler
  selects the task;
- shipped development work receives a separate agent peer-review step;
- the operation reached **31 agent-operated workstreams in one week** at the
  peak of its initial reporting window;
- the operating model kept shipping while one of its two founders was working
  half-time.

These are observations about how the operation ran, not a benchmark against a
counterfactual team. [Read the counting rules, source paths, and caveats in the
velocity report](docs/velocity-report.md). The launch experiment will add the
more useful number—human-minutes per shipped task—after it has been measured.

## What it replaces

| Before | Coga |
|---|---|
| Notion or Linear as the work ledger | Markdown tickets in your git history |
| Zapier for recurring glue | Scheduled, inspectable skills and scripts |
| An ops coordinator moving work between people | Script tasks and `megalaunch` |
| A wiki agents may or may not find | Contexts composed into the task prompt |
| Slack as fragile company memory | Per-task blackboards plus an append-only log |

Coga does not replace the systems where the underlying work happens. It gives
the work one legible control plane.

## The correction loop

The important demo is not an agent succeeding. It is an agent being wrong in a
way you can fix permanently:

```sh
$ $EDITOR coga/contexts/payments/refunds/SKILL.md  # correct the missing rule
$ git add coga/contexts/payments/refunds/SKILL.md && git commit -m "Clarify refund approval"
$ coga launch payments/reconcile-refunds           # the prompt is rebuilt from disk
# this run—and every later task using that context—gets the correction
```

No hidden memory was retrained. You changed a file you own, reviewed the diff,
and the next stateless session used it.

## Six primitives

- **Tickets** make each unit of work durable and directable.
- **Blackboards** preserve working state and blockers between sessions.
- **Contexts** hold facts about your company and domain.
- **Skills** hold procedures for agents or deterministic scripts.
- **Workflows** define ordered handoffs and human gates.
- **The log** records launches, transitions, usage, and outcomes in append-only text.

## Who it is for

Coga is for small, technical teams that already use CLI agents, enjoy rigor,
and want to understand and correct their own operational machinery. It is a
good fit when the cost of writing down how work should happen is lower than the
cost of supervising the same work forever.

It is not for teams that want a managed service, an SLA, zero setup, or a
delegate-and-forget employee substitute. Its workflows are linear state
machines; use an agent framework for dynamic orchestration. Coga is local,
self-hosted, and self-supported by design.

## How it differs

**Plain Claude Code or Codex** is the engine, not the competitor. A session is
ephemeral, forgets the last ticket, and leaves you scheduling tabs. Coga gives
those engines persistent, vendor-neutral operating state.

**Backlog.md** stores work as markdown. Coga adds the execution loop: composed
facts and procedures, step handoffs, blockers, review gates, and a scheduler.

**OpenAI Symphony** has the same broad skeleton—tickets as a state machine,
stateless agents, isolated workspaces, respawning workers—but takes the human
out of the loop, keeps board state in cloud software, and is Codex- and
code-specific. Coga keeps the gate and state in your git and can drive either
vendor across operational domains.

**CompanyOS** shares the owned-markdown instinct. It is a collection of context
and skills, without Coga's task state machine, resumable blackboard, or gated
correction loop.

**Autonomy platforms** sell “no human between stages.” There is no such thing
as full autonomy: autonomy is a function of specification quality and how
reliably the result can be evaluated. Hide the human and the specification,
review, and babysitting work still lands somewhere—or the mistakes do. Coga
makes that irreducible judgment work explicit and batches it.

## Install

Coga requires Python 3.11+ and Git. Install the isolated CLI with `uv`:

```sh
uv tool install coga
```

Or install it in an activated virtual environment:

```sh
python -m pip install coga
```

Then, from the root of the git repository you want Coga to operate:

```sh
coga init --user <your-name>
coga build
```

`coga init` installs the markdown OS into that repository. `coga build` starts
the first-run interview and creates an initial batch of tickets. You need an
authenticated [Claude Code](https://claude.com/claude-code) or
[Codex](https://github.com/openai/codex) CLI before `coga build` launches its
agent. Installation troubleshooting and adopting an existing Coga repository
are covered in [Getting started](docs/getting-started.md).

## Docs

- **Why:** [Vision](docs/vision.md)
- **Start:** [Getting started](docs/getting-started.md)
- **Reference:** [CLI commands](docs/cli.md)
- **Evidence:** [Velocity report](docs/velocity-report.md)

## Values

**Own the system.** Coga is markdown, Python, Git, and the shell. There is no
hosted state, hidden database, telemetry, or plugin fence around the rules.

**Make judgment scarce.** Agents and scripts do the mechanizable work. Humans
choose what matters, evaluate results, and correct the substrate.

**Compound corrections.** Knowledge changes through readable diffs and human
gates, not opaque automatic memory.

**Fail loud.** Missing context, broken references, script failures, and blocked
decisions surface instead of silently producing a plausible wrong answer.

**Keep vendors replaceable.** Claude Code and Codex work today; the company
memory belongs to neither.

Coga is free software licensed under
[AGPL-3.0-or-later](LICENSE).
