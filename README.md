# Coga

> Most tools are building infrastructure for agents. Coga is an instrument
> for the human using them.

Coga is a CLI that runs your coding agent from Markdown files in your Git
repo. Every launch assembles those files into the agent's opening task
prompt. When an agent gets something wrong, you correct the relevant file,
and future work starts from the updated instructions.

**Text above code.** The text is the source of truth for intent, knowledge,
and decisions. Code implements that understanding and can be rewritten as
we learn.

Think of it as a workbench, not an assembly line: it's what you build with
while you're still working out what to build. 

Coga is a small overlay on top of what agents already provide, so it gets better when they do.

Coga is built with Coga: see the tickets in [`coga/tasks/`](coga/tasks) and
the full history in [`coga/log.md`](coga/log.md).

## The problem

On a real project, `CLAUDE.md` or `AGENTS.md` keeps growing until the agent only skims it. There are various techniques to mitigate this problem: auto-memories, scoped `AGENTS.md` files, MCP servers. Coga's solution is to make all this explicit while keeping intact the search capabilities of the agent. Each launch injects what you decided the task needs. In our use, the skimming problem never came up.

## Key ideas

Treating an agent as a person who remembers is a convenient abstraction.
Under heavy use, it can get in the way: you need to know what was kept,
where it applies, and how to correct it. Even editable memory isn't
necessarily organized for that work.

Coga drops that abstraction. You maintain the knowledge and
instructions explicitly, and choose what each task needs. Each launch
assembles that material into its opening prompt. It's like writing SQL
instead of going through an ORM: more of the work is in your hands, and you
see what goes in. For intensive use, we find that easier to manage.

- **The unit is the task, not the session.** Each launch builds a fresh
  prompt from what that task needs: the ticket, the contexts it attaches, the
  current workflow step.

- **Knowledge moves out of code and chat, into files.** Coga treats the text as a first-class citizen. It creates PRs to update the documentation and takes great care to be right. The code is the agent's job. Coga's job is to make sure the text reflects your work and your learning.

- **Hackable and automated.** You want a feature in Coga? Start `coga chat` and build it from there. It's built on known agent conventions, so it can build itself and you can understand what's being built.


## Key concepts

- **Ticket**: one piece of work as a Markdown file: what to do, the context
  blocks it needs, the workflow it follows.
  ([tickets](docs/contexts/coga/tickets/SKILL.md))
- **Context block** (context for short): a durable fact about the project,
  such as a behavior, a decision or an intent.
  ([knowledge](docs/contexts/coga/knowledge/SKILL.md))
- **Workflow**: the steps for one kind of work, and which of them need you.
  ([workflows](docs/contexts/coga/workflows/SKILL.md))
- **Recurring work**: reusable task templates with a schedule. When you run
  `coga recurring`, due templates become tasks and run through the ordinary
  task lifecycle — for maintenance, reviews, or other work worth repeating.
  ([recurring](docs/contexts/coga/recurring/SKILL.md))

## Philosophy

Coga helps people direct work, question assumptions, and carry what they learn
into the next task. The [manifesto](docs/contexts/product/vision/SKILL.md)
describes the philosophy and design principles behind Coga.

## Example

I wanted a plugin that picks the model and reasoning level for each task, so
a subscription's usage limits cover more work instead of spending top
reasoning on everything. `coga build` turned ten minutes of conversation
into a plan of tickets, and the plan treated routing as a solved problem.
It isn't. The agent had followed my assumption instead of questioning it;
having the plan written down is what made the assumption visible. So we
replaced it with a research plan in tickets, written with Claude and run by
Codex: [state of the art](https://github.com/FastJVM/thinkpick/blob/main/coga/tasks/classifier/state-of-the-art-review.md),
[head-to-head ground truth](https://github.com/FastJVM/thinkpick/blob/main/coga/tasks/classifier/head-to-head-ground-truth.md),
[Jev](https://github.com/FastJVM/thinkpick/blob/main/coga/tasks/classifier/evaluate-jev.md),
[candidate scoring](https://github.com/FastJVM/thinkpick/blob/main/coga/tasks/classifier/score-candidates.md), then the
[decision](https://github.com/FastJVM/thinkpick/blob/main/coga/tasks/decide-classifier-approach.md). The decision became a
context that every later ticket starts from. Browse the whole example in
[thinkpick's tasks](https://github.com/FastJVM/thinkpick/tree/main/coga/tasks).

## Who it is for, and its limits

Coga is for small technical teams who already use CLI agents, are comfortable
with Git and the shell, and want to understand and correct the material their
agents work from.

It is built for work you learn by doing, where you are still working out
what to build while you build it. For trivial tasks, the agent's own defaults
are usually enough. For work you can fully specify up front, or that has
settled into a routine, tools built for that are a better fit.

It runs locally, in your repository's `coga/` directory: no hosted service.

## Install

Coga runs on Linux, Windows or macOS and needs Python 3.11+, Git, and an authenticated
[Claude Code](https://claude.com/claude-code) or
[Codex](https://github.com/openai/codex) CLI; in a terminal, `coga init`
offers to install and log in whichever agent CLI you pick.

```sh
uv tool install coga            # or: python -m pip install coga
coga --version                  # check the install
cd <your git repository>
coga init --user <your-name>
```

[Install](docs/contexts/coga/install/SKILL.md) covers setup, joining a
repository that already uses Coga, and troubleshooting.
[First task](docs/contexts/coga/first-task/SKILL.md) walks one ticket from
draft to reviewed result. A [95-second demo](https://www.youtube.com/watch?v=iwnewxJvRPc)
was recorded in July 2026; some command names may have changed since.

## First steps

After `coga init`:

- **Empty repo:** run `coga build`, a guided discussion that turns your
  project and goals into a short vision context and a batch of starter
  tickets. A stock README, LICENSE or `.gitattributes` from your hosting
  provider still counts as empty; any other project file does not.
- **Existing project:** init skips that step. Create your first ticket with
  `coga ticket "<title>"`.

Either way, everything is plain files in your repo: edit them with any text
editor, or use `coga ticket <slug>` to revise a ticket with an agent. What
the agents draft is far from perfect, and that's the point: it shows how
they understand your project and how they would approach it, and gives you
something concrete to correct.

```sh
coga status                 # list the tickets
coga ticket my-first-ticket # refine a ticket with an agent, or edit it yourself
coga launch my-first-ticket # launch an agent on it
```

`coga launch` assembles the prompt from the ticket, its contexts, the workflow
step and the working state. When the work teaches you something worth
keeping, decide what should change: edit it yourself, ask an agent to carry
the new understanding through the project, or let Coga's recurring work
surface it.

## Learn more

- [Documentation index](docs/README.md): start, understand, operate and
  develop.
- [Manifesto](docs/contexts/product/vision/SKILL.md): the philosophy and design
  principles behind Coga.
- [Contributing](CONTRIBUTING.md).
- Limits: contexts go into the prompt as truth, so a stale one misleads.
  Managing prompts and instructions as files has close precedents; see the
  [evidence pages](docs/archive/evidence/) for dated comparisons.

Coga is free software licensed under
[Apache-2.0](LICENSE).
