# Coga

 **Agents work in sessions. Humans make things. Coga connects the two.**

Claude Code and Codex can turn an idea into a plan and start implementing it. But plans change, assumptions turn out to be wrong, and sessions end. That's where Coga comes in.

**Coga keeps plans, decisions, and project knowledge in ordinary Markdown, organized in Git.** Humans and agents can browse, question, and improve that knowledge directly—even outside Coga sessions.

For a specific task, `coga launch` brings its ticket, selected contexts, and current workflow step into your agent's prompt. This reduces repeated discovery and gives each session a more consistent starting point. Guide sessions interactively, add human review gates, or queue work to run unattended. Work across multiple projects, each in its own Git repo.

Coga is a local CLI, not another coding agent.

[Browse real project tickets](https://github.com/FastJVM/thinkpick/tree/main/coga/tasks)

## See the workflow

In an existing Git repository, after installing Coga (replace `YOUR_NAME`
with the name you want Coga to use for you):

```sh
coga init --user YOUR_NAME
coga ticket "Add a health-check endpoint"                 # discuss and draft a ticket
coga show add-a-health-check-endpoint                    # inspect the ticket and history
coga launch add-a-health-check-endpoint --prompt-report  # inspect the prompt layers
coga launch add-a-health-check-endpoint                  # start the agent in your terminal
```

The ticket is an ordinary Markdown file under `coga/tasks/`. Here's the essential part of a [real Thinkpick ticket](https://github.com/FastJVM/thinkpick/blob/a980f5822c876776361b9709b9f6b2ad4b57e9bc/coga/tasks/classifier/state-of-the-art-review.md):

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
- **Give each task the right context.** Keep facts, constraints, and decisions discoverable as Markdown; select what a focused launch needs instead of making each session rediscover it.
- **Put reviews where they matter.** Use a lightweight workflow for a simple change or require design, peer review, and human approval for more substantial work.
- **Keep what you learn.** Record decisions in project contexts so later tasks inherit them, even when a different agent does the work.

## When the first plan was wrong: Thinkpick

We asked `coga build` to plan [Thinkpick](https://github.com/FastJVM/thinkpick), a tool for recommending how much reasoning effort a model should use for a task.

The agent produced a concrete plan: [a library](https://github.com/FastJVM/thinkpick/blob/5bb87f87c9103fb94ce956cd8ed29bd7dcc16aa1/coga/tasks/recommendation-core-library.md) that takes a task description and returns an effort level with a reason, a CLI to expose it, a feedback log, and a ticket to choose between heuristics, a cheap LLM, or a hybrid.

The plan was reasonable given our prompt. **But the prompt itself assumed the hard problem was solved:** that the right reasoning effort could be predicted reliably from a task description. We hadn't established that.

So we parked the implementation tickets and [changed the plan](https://github.com/FastJVM/thinkpick/commit/6b32d453d6e0cf684f13d2cdc4484f8e51527b64) to investigate existing approaches and establish ground truth first. We eventually [paused Thinkpick](https://github.com/FastJVM/thinkpick/blob/main/coga/contexts/product/vision/SKILL.md#decision-2026-10-28-paused-not-abandoned) because validating the benefit in real coding-agent workflows would require more investment than we could justify.

**The agent followed the original plan. The human questioned its premise. Coga made it possible to change course without losing the work.**

Coga is [built with Coga](https://github.com/FastJVM/coga/tree/main/coga/tasks), too. Its task history lives in [`coga/log.md`](https://github.com/FastJVM/coga/blob/main/coga/log.md).

## Get started

Agent sessions run on Linux or macOS. You'll need working Git and an installed,
authenticated [Claude Code CLI](https://code.claude.com/docs/en/quickstart) or
[Codex CLI](https://developers.openai.com/codex/cli/). Follow the chosen CLI's
installation instructions, then run `claude` or `codex login` to sign in.
Coga does not include either agent. Coga requires Python 3.11+, but the
recommended `uv` installer can obtain a compatible Python for you.

**Native Windows is not ready for a first task.** PyPI release 0.4.1
does not run there. The development version runs deterministic commands but
still refuses agent sessions; see the [launch platform boundary](https://github.com/FastJVM/coga/blob/main/docs/contexts/coga/launch/SKILL.md#phases-and-routing).
WSL has not been verified as an alternative. The steps below are for macOS
and Linux.

On macOS, check that `git --version` works. If it prompts for developer
tools, run `xcode-select --install`; Git installed another way works too.
Full Xcode is not required. On Linux, install Git with your distribution's
package manager if `git --version` fails.

If `uv` isn't installed yet, get it first (macOS/Linux):

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

See [other uv installation methods](https://docs.astral.sh/uv/getting-started/installation/).
Open a new terminal if `uv` isn't on your `PATH` after installation.

```sh
uv tool install coga
coga --version
```

For an existing project, change into its Git repository. For a new project,
create the repository first:

```sh
mkdir myproject
cd myproject
git init -b main
```

Check `git var GIT_AUTHOR_IDENT` before init. If Git asks for an identity,
set `git config user.name "Your Name"` and
`git config user.email "you@example.com"` with your own details in this repo.
Then run:

```sh
coga init --user YOUR_NAME
```

In a repo new to Coga, init commits the Coga files. In a clone that already
uses Coga, it sets up your local identity and agent links without a commit
([init details](https://github.com/FastJVM/coga/blob/main/docs/contexts/coga/init/SKILL.md)).
In an interactive terminal, it offers agent CLI installation and login when
neither supported CLI is installed and a supported installer is available;
an already-installed CLI still needs authentication. It seeds the onboarding
ticket only for an otherwise empty repo; a short starter README, LICENSE or
`.gitattributes` still counts as empty. Choose how to begin:

```sh
# New, otherwise empty Git repo: discuss the idea and draft a first plan
coga build

# Existing project: discuss what's next
coga chat

# Check the current work
coga status
```

To use Codex explicitly, run `coga build --agent codex`,
`coga chat --agent codex`, or `coga ticket "Your task title" --agent codex`.
In the shipped setup, chat and ticket interviews default to Claude even when
new tasks use Codex.
You can also edit any ticket directly in Markdown.

For a walkthrough to a reviewed PR, follow [Your first task](https://github.com/FastJVM/coga/blob/main/docs/contexts/coga/first-task/SKILL.md).
That PR path needs a GitHub remote you can push to and [GitHub CLI](https://cli.github.com/)
authentication (`gh auth login`). The guide explains the choice between a
peer review using both agent CLIs and a workflow using one agent.
GitHub CLI is optional for init and work that does not use GitHub;
[1Password CLI](https://github.com/FastJVM/coga/blob/main/docs/contexts/coga/secrets/SKILL.md)
is needed only for tickets that declare `op://` secrets.

Upgrade with `uv tool upgrade coga`. To remove Coga from a repo, run
`coga uninstall`; the [uninstall guide](https://github.com/FastJVM/coga/blob/main/docs/contexts/coga/uninstall/SKILL.md)
explains what it removes and how to remove the global package too.

## What lives in your repo?

Everything Coga manages is visible under `coga/`:

- **Tickets** (`coga/tasks/`) — specific outcomes, attached context, workflow, and working notes. [How tickets work](https://github.com/FastJVM/coga/blob/main/docs/contexts/coga/tickets/SKILL.md).
- **Contexts** — durable facts, constraints, and decisions you choose to attach to tasks. [How knowledge works](https://github.com/FastJVM/coga/blob/main/docs/contexts/coga/knowledge/SKILL.md).
- **Workflows** — agent steps and human review gates. [How workflows work](https://github.com/FastJVM/coga/blob/main/docs/contexts/coga/workflows/SKILL.md).
- **History** (`coga/log.md`) — task transitions kept separately from the prompt sent to an agent.

## Principles

Coga is built around a few deliberate choices:

**Text above code.** In most coding repos, code is the source of truth. In a Coga repo, the truth lives in the text. Code is an artifact "compiled" from it—and yes, we can regenerate it.

**Keep everything at human scale.** Coga stays small enough to understand and change. The tool should fit the way you work, not make you fit its process.

**Amplify agents, don't duplicate them.** Don't build another planner, researcher, coder, or reviewer. Use what coding agents already know. As they improve, Coga benefits.

**Coga encoded in Coga.** The same tickets, contexts, and workflows used for other projects should describe and evolve Coga itself.

## Learn more

- [Documentation](https://github.com/FastJVM/coga/blob/main/docs/README.md) — installation, concepts, operation, and development.
- [Design principles](https://github.com/FastJVM/coga/blob/main/docs/contexts/coga-dev/principles/SKILL.md) — the reasoning behind the workbench approach.
- [Contributing](https://github.com/FastJVM/coga/blob/main/CONTRIBUTING.md) — how to work on Coga.

Licensed under [Apache-2.0](https://github.com/FastJVM/coga/blob/main/LICENSE).
