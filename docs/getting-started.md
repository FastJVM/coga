# Getting started

This guide takes you from nothing to a first task that ends in a real pull
request — and, along the way, gives you enough of the mental model to understand
what just happened. Budget twenty minutes. When you're done, read
[Concepts](concepts.md) to make the model precise.

Coga is **adopted into an existing project**, not set up in a separate
workspace. Its whole point is to live in the same Git repo as the work it
organizes, so everything an agent reads and writes is versioned alongside your
code.

## Prerequisites

- **Python 3.11+.** Coga uses the standard-library `tomllib`, so 3.11 is the
  floor.
- **Git.** `coga init` requires it, and Git is Coga's sync layer — every state
  change is a commit.
- **An agent CLI**, installed and authenticated: either
  [Claude Code](https://claude.com/claude-code) or
  [Codex](https://github.com/openai/codex). You need one before anything that
  launches an agent (`coga launch`, `coga ticket`, `coga build`). `coga init`
  itself works without one.
- **The GitHub CLI** ([`gh`](https://cli.github.com), then `gh auth login`) is
  recommended but not required at init. PR workflows, the merged-ticket autoclose
  sweep, and managed-skill installs need it and will tell you clearly when it's
  missing.

Coga does not own your identity. It uses the tools you already authenticate —
`git`, your credential helper, `gh` — and fails with an actionable hint when one
isn't ready, rather than storing tokens of its own.

## Install

Coga is published on PyPI as `coga`. The cleanest install is an isolated CLI
with [`uv`](https://docs.astral.sh/uv/):

```sh
uv tool install coga
```

That puts `coga` on your `PATH` in a virtualenv of its own, without touching your
system Python.

No `uv`? Use a virtualenv:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install coga
```

If you explicitly want Coga in the current environment — no virtualenv, no
isolation — opt out with `python3 -m pip install coga` (or `uv pip install
--system coga`).

**If `pip` aborts** with `Hashes are required in --require-hashes mode`, your
machine has pip's hash-checking mode on globally (common on managed work
laptops). Two escape hatches: install with `uv tool install coga` (uv ignores
pip's config), or disable checking for the one command —
`PIP_REQUIRE_HASHES=0 pip install coga`.

Confirm it's there:

```sh
coga --help
```

## Adopt Coga into your repo

Run `init` from the root of the Git repository you want Coga to manage:

```sh
cd /path/to/your/project
coga init --user <your-name>
```

`--user` is the name tickets and agents will refer to you by — pick something
short, like `marc`. This creates the markdown OS under `coga/` in that same
repository: contexts, workflows, a `tasks/` directory, `coga.toml`, and a
gitignored `coga.local.toml` holding your name.

A few things worth knowing about init:

- **It belongs in your real project, not an empty scratch directory.** If you
  ran it somewhere empty by mistake, `cd` back to your project's Git root and run
  it there. Starting a brand-new project? `git init` first, then `coga init`.
- **You can nest it.** In a monorepo, `coga init tools/ops` puts the `coga/` tree
  under `tools/ops/` and manages that subtree.

`coga init` commits the new `coga/` directory for you (it prints the commit
SHA); push it when you're ready, like any other project change.

### Joining a repo that already uses Coga

`coga init` is only for repos that don't have a `coga/` yet. If you cloned a repo
that already uses Coga, the shared `coga.toml` came with the clone, but
`coga.local.toml` — the machine-local file holding **your** name — is gitignored,
so every clone makes its own. Create it next to `coga.toml`:

```sh
echo 'user = "<your-name>"' > coga/coga.local.toml
```

Coga never guesses your name from Git or `$USER`: tickets reference people by
these names, and a wrong guess fails quietly. Read-only commands (`coga status`,
`coga show`, `coga validate`, `--help`) work without it; anything that creates or
moves work needs it. `coga validate` nags with a warning until it's set.

## Your first task

A **ticket** is one unit of work: a markdown file under `coga/tasks/` with
frontmatter, a body, and a blackboard. There are two ways to create one.

### The quick way: `coga create`

```sh
coga create "Add a health-check endpoint" --workflow code/with-review
```

This scaffolds a **draft** ticket at `coga/tasks/add-a-health-check-endpoint.md`.
Open it and fill in the `## Description` and `## Context` sections — this is plain
markdown, edit it however you like. `--workflow` attaches a workflow now; you can
also add one later, but a ticket can't be *activated* without one.

### The guided way: `coga ticket`

```sh
coga ticket "Add a health-check endpoint"
```

This launches an authoring interview: an agent asks what you're building, what
"done" means, which contexts apply, and which workflow fits, then writes a
well-formed draft for you. Use it when you'd rather talk the ticket into shape
than fill in a template. Planning a whole batch of related tickets at once? See
`coga project`.

Either way you now have a **draft**. Drafts are intentionally cheap: they capture
intent before the shape is settled and don't have to commit to a workflow yet.

### Launch it

```sh
coga launch add-a-health-check-endpoint
```

`coga launch` is where the system comes alive. It:

1. **Activates the draft** — launching *is* the "yes, do this" signal, so a draft
   or paused ticket is marked active inline, then flipped to `in_progress`.
2. **Composes the prompt** — base instructions, this repo's context, the ticket's
   attached contexts, the current step's skill, the blackboard, and the ticket
   body, assembled into one prompt. (Run `coga launch <task> --prompt-report` to
   see the layers and their token counts without launching.)
3. **Spawns the agent** in a live REPL and supervises it.

You watch, and you talk to the agent — an attended launch is a conversation, not
a fire-and-forget. The agent does the step's work (here, `implement`: write the
code on a feature branch), records findings and decisions on the blackboard, and
finishes the step by running `coga bump`. Under the launch supervisor, that bump
tears down the session and — for a multi-step workflow like `code/with-review` —
spawns the next step automatically, rotating to the peer agent for the review
step.

You'll land at the final `review` step with an open PR, which is a human gate:
Coga hands control back to you to review and merge on GitHub. Close the ticket
with `coga mark done <task>` once it's merged. If your repo runs the
`autoclose-merged` recurring sweep on a schedule, that sweep will also mark a
merged ticket `done` on its next run — but that's opt-in maintenance, not
something that happens on its own (see [Operations](operations.md#recurring-maintenance)).

That's the whole loop: **create → launch → the agent works and bumps → you
review and merge.**

## What just happened

You touched five ideas. Here they are in one paragraph each — [Concepts](concepts.md)
goes deeper.

- **Ticket.** The durable unit of work. Everything about the task — its state,
  its history pointer, its scratch memory — lives in files under `coga/tasks/`,
  not in a session that vanishes when the process exits.
- **Workflow.** The ordered steps a ticket moves through (`implement →
  peer-review → open-pr → review`). It's frozen into the ticket at creation, so
  editing a workflow never disturbs tasks already in flight.
- **Blackboard.** The free-form region at the bottom of the ticket where the
  agent writes what it's doing and learns. It's the persistence layer between
  otherwise-stateless sessions: the first thing a resumed agent reads, and how
  work survives a torn-down REPL.
- **Composition.** Coga builds each prompt fresh from the files on disk *right
  now*. There's no carried-over session state, which is exactly why editing a
  context between runs takes effect completely and inspectably.
- **The correction loop.** When the agent gets something wrong, you don't argue
  with it — you open the context or workflow that misled it, fix the file, and
  commit. The next launch composes the corrected version. Your fixes compound.

## Check your work

`coga validate` checks repo and task structure and exits non-zero on errors —
run it after config, workflow, or ticket changes:

```sh
coga validate
coga validate --json      # machine-readable
```

`coga status` shows the tasks in your repo; `coga show <task>` prints one
ticket in full, history included.

## Where to go next

- **[Concepts](concepts.md)** — make the mental model precise.
- **[Command reference](reference.md)** — the full CLI surface.
- **[Operations](operations.md)** — notifications, aliases, recurring
  maintenance, and secrets, once you're running Coga for real.
