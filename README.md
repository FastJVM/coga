# Coga

> Most tools are building infrastructure for agents. Coga is an instrument
> for the human using them.

Coga is a CLI that runs your coding agent from Markdown files in your Git
repo. Claude Code and Codex work out of the box; any other CLI agent takes a
few lines of config. Every launch rebuilds the agent's prompt from those
files. When an agent gets something wrong, you fix the file once, and every
later run starts from the fix. It doesn't replace Claude Code or Codex; it
handles the part they can't do for you.

Coga is built with Coga: see the tickets in [`coga/tasks/`](coga/tasks) and
the full history in [`coga/log.md`](coga/log.md).

## The problem

On a real project, `CLAUDE.md` or `AGENTS.md` keeps growing until the agent
only skims it. You repeat the same instructions in chat, and sometimes open a
fresh session just to make the agent forget a bad idea. Worse, the same fact
ends up written in several places that slowly disagree, including memories the
tool keeps outside your repo. Nobody knows which version is true, so the agent
acts on whichever copy it read, or falls back on its defaults.

Tool memories store what was said; they can't tell which of it mattered or
what changed along the way. On simple tasks that's fine. On work you have to
argue through, with wrong turns and reversals, what survives is what got
written down.

Vibe coding explores fast but forgets what it found. Spec-driven tools keep
what they know, but they're built around writing the spec before the code.
A lot of real work is neither: you find out what you want by building it,
and you backtrack when a premise breaks. Code is now cheap enough to throw
away; what's expensive is the right idea, a clear spec, and proof that it
works.

## Key ideas

Each of these follows from one premise: you find out what you want while
building it. So what has to last is what you learned, kept in files you can
read, change and redo from, not the code and not the chat.

- **The unit is the task, not the session.** Each launch builds a fresh
  prompt from what that task needs: the ticket, the contexts it attaches, the
  current workflow step. Contexts are chosen by what the task is, not by where
  the code is; they go into the prompt as truth, and the agent can still look
  up the rest. Nothing carries over from an earlier chat, so a bad idea
  doesn't outlive the session that had it.
- **Knowledge moves out of code and chat, into files.** Code says what the
  system does; contexts and tickets say what it should do, why, and what
  didn't work, with one owning file per fact. Every loop feeds them: each
  step's findings go to the next, a retired ticket's lessons go to the
  contexts, Dream, a weekly recurring job, checks contexts against the code,
  and your corrections apply on the next launch. When a premise turns out
  wrong, cancel the ticket with the reason, fix the context that owns the
  fact, and start a new one.
- **Each kind of work gets its own process.** A workflow lists the steps and
  says which ones need you. A routine fix goes straight to a pull request you
  review. Risky work first stops for you to approve a written design that a
  second agent has already reviewed. Think plan mode, except the plan is a file
  that's still there when implementation starts. Changes to workflows and
  other shared rules arrive as pull requests, so nothing changes how agents
  work until you merge it. You decide how closely to read each pull request;
  the agent that prepares one recommends a review depth in its title (merge,
  skim or deep), and Coga marks it deep when its recorded evidence is
  incomplete.
- **Hackable, and mostly automated.** Everything is a plain file you can
  change, and contexts and skills use the same `SKILL.md` convention as agent
  skills, but you rarely start from a blank page. After a short chat,
  `coga build` drafts a vision and starter tickets, and `coga ticket` drafts a
  ticket and picks its workflow and contexts with you; you edit the result,
  rewrite it, or chat again. `coga launch <slug> --prompt-report` lists the
  prompt layers a launch would compose, with their sizes, without launching an
  agent.

**The trade-off:** you write things down instead of saying them in chat, and
you decide where you're needed; agents do most of the drafting. In exchange,
you stop repeating yourself, and what you and your agents learn stays in your
repo.

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
agents work from. It fits when writing down how work should be done costs less
than supervising the same work indefinitely.

It pays off most on work you have to argue through; for routine tasks, the
agents' own memory is usually enough.

It is local, self-hosted and self-supported: no managed service, SLA, hosted
dashboard or zero-setup path. Workflows are linear sequences of steps; dynamic
orchestration belongs in an agent framework. Coga does not replace judgment: it
makes the points where you decide and correct explicit.

If you already separate what you know from what you are still discovering,
Coga gives that separation a place in your repo. If you plan unknown work as
if it were known, with fixed specs and throughput goals, it will feel like
overhead. Coga assumes you know what you are merging: it makes changes
visible; it doesn't stop you.

Contexts go into the prompt as truth, so a stale one misleads. The retro on a
retired ticket updates the contexts that ticket touched; changes made outside
Coga, or that affect contexts a ticket didn't load, wait for Dream's next
scan. One owner per fact is an authoring rule, not something a test enforces.

The same task and workflow core also runs FastJVM's administrative routines
and patent work, which have nothing to do with pull requests
([usage comparison](docs/evidence/usage-comparison.md#core-flexibility-across-administrative-and-patent-work)).

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

## Install

Coga runs on Linux or macOS and needs Python 3.11+, Git, and an authenticated
[Claude Code](https://claude.com/claude-code) or
[Codex](https://github.com/openai/codex) CLI; in a terminal, `coga init`
offers to install and log in whichever agent CLI you pick.

```sh
uv tool install coga            # or: python -m pip install coga
coga --version                  # check the install
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
