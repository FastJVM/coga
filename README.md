# Coga

 **Agents work in sessions. Humans work on tasks. Coga connects the two.**

Claude Code and Codex can turn an idea into a plan and start implementing it. But plans change, assumptions turn out to be wrong, and sessions end. What happens then?

**Coga turns those plans into Markdown tickets you can inspect, edit, and run with your agent.** Run multiple projects in parallel, each in its own Git repo. Choose how involved you want to be: guide sessions interactively, add human review gates, or queue work to run unattended.

Coga is a local CLI, not another coding agent.

[Browse real project tickets](https://github.com/FastJVM/thinkpick/tree/main/coga/tasks)

## See the workflow

In an existing Git repository, after installing Coga:

```sh
coga init --user <your-name>
coga ticket "Add a health-check endpoint"                 # discuss and draft a ticket
coga show add-a-health-check-endpoint                    # inspect the ticket and history
coga launch add-a-health-check-endpoint --prompt-report  # inspect the prompt layers
coga launch add-a-health-check-endpoint                  # start the agent in your terminal
```

The ticket is an ordinary Markdown file under `coga/tasks/`. Here's the essential part of a [real Thinkpick ticket](https://github.com/FastJVM/thinkpick/blob/main/coga/tasks/classifier/state-of-the-art-review.md):

```md
## Description

Survey the state of the art: is predicting how much reasoning effort a model
needs, from the task description alone, already a solved problem?

## Context

- **Core unknown:** we have no ground truth.
- Out of scope: writing code, running experiments, picking providers.
```

Its workflow is **agent researches → human reviews and decides which follow-up tasks are needed → agent records the outcome**. You can edit the ticket directly or refine it with an agent. At launch, Coga assembles the ticket, its attached contexts, and its current workflow step into a fresh prompt.

## Why use Coga instead of just the agent?

You keep using Claude Code or Codex. Coga gives each task durable context, a workflow, and a history that survives individual agent sessions:

- **Change the plan.** Split a vague task, test an assumption first, cancel work, or change the next step after seeing new evidence.
- **Give each task the right context.** Attach relevant facts, constraints, and decisions instead of making every session rediscover them.
- **Put reviews where they matter.** Use a lightweight workflow for a simple change or require design, peer review, and human approval for more substantial work.
- **Keep what you learn.** Record decisions in project contexts so later tasks inherit them, even when a different agent does the work.

## When the first plan was wrong: Thinkpick

We used Coga to build [Thinkpick](https://github.com/FastJVM/thinkpick), a tool for choosing a model's reasoning level for a task. After ten minutes of discussion, `coga build` produced plausible tickets—but the plan assumed we already knew how to choose the right level.

We didn't. Instead of implementing that assumption, we changed the tickets to [review existing approaches](https://github.com/FastJVM/thinkpick/blob/main/coga/tasks/classifier/state-of-the-art-review.md), [establish ground truth](https://github.com/FastJVM/thinkpick/blob/main/coga/tasks/classifier/head-to-head-ground-truth.md), [evaluate an existing candidate](https://github.com/FastJVM/thinkpick/blob/main/coga/tasks/classifier/evaluate-jev.md), [compare candidates](https://github.com/FastJVM/thinkpick/blob/main/coga/tasks/classifier/score-candidates.md), and finally [make a decision](https://github.com/FastJVM/thinkpick/blob/main/coga/tasks/decide-classifier-approach.md).

The tickets were written with Claude and worked on with Codex. The decision became project knowledge for later work.

**The win wasn't a flawless initial plan. It was being able to challenge it, change it, and carry the result forward.**

Coga is [built with Coga](coga/tasks/), too. Its task history lives in [`coga/log.md`](coga/log.md).

## Get started

You'll need Git and an authenticated [Claude Code](https://claude.com/claude-code) or [Codex](https://github.com/openai/codex) CLI to run agent sessions. Coga requires Python 3.11+, but the recommended `uv` installer can obtain a compatible Python for you.

```sh
uv tool install coga
coga --version
cd <your-git-repository>
coga init --user <your-name>
```

Then choose how to begin:

```sh
# New, otherwise empty Git repo: discuss the idea and draft a first plan
coga build

# Existing project: discuss what's next
coga chat

# Check the current work
coga status
```

You can edit any ticket directly in Markdown or run `coga ticket <slug>` to refine it with an agent. For a walkthrough from a draft to a reviewed PR, see [Your first task](docs/contexts/coga/first-task/SKILL.md).

## What lives in your repo?

Everything Coga manages is visible under `coga/`:

- **Tickets** (`coga/tasks/`) — specific outcomes, attached context, workflow, and working notes. [How tickets work](docs/contexts/coga/tickets/SKILL.md).
- **Contexts** — durable facts, constraints, and decisions you choose to attach to tasks. [How knowledge works](docs/contexts/coga/knowledge/SKILL.md).
- **Workflows** — agent steps and human review gates. [How workflows work](docs/contexts/coga/workflows/SKILL.md).
- **History** (`coga/log.md`) — task transitions kept separately from the prompt sent to an agent.

## Principles

Coga is built around a few deliberate choices:

**Text above code.** In most coding repos, code is the source of truth. In a Coga repo, the truth lives in the text. Code is an artifact "compiled" from it—and yes, we can regenerate it.

**Keep everything at human scale.** Coga stays small enough to understand and change. The tool should fit the way you work, not make you fit its process.

**Amplify agents, don't duplicate them.** Don't build another planner, researcher, coder, or reviewer. Use what coding agents already know. As they improve, Coga benefits.

**Coga encoded in Coga.** The same tickets, contexts, and workflows used for other projects should describe and evolve Coga itself.

## Learn more

- [Documentation](docs/README.md) — installation, concepts, operation, and development.
- [Design principles](docs/contexts/coga-dev/principles/SKILL.md) — the reasoning behind the workbench approach.
- [Contributing](CONTRIBUTING.md) — how to work on Coga.

Licensed under [Apache-2.0](LICENSE).
