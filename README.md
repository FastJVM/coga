# Relay

A blackboard for humans and agents. Markdown files in a git repo, a small CLI on
top, no database. The substrate FastJVM uses to run the company.

For the why, read [`docs/vision.md`](docs/vision.md). For the full data model
and config reference, read [`docs/spec.md`](docs/spec.md). This README is the
quickstart + a one-screen reference for each CLI command.

## Install

Not yet on PyPI. Bootstrap from the source repo:

```sh
git clone https://github.com/FastJVM/relay
cd relay
python -m pip install -e .
```

That puts `relay` on your PATH against the source. Once it's there, the
normal flow is to **`relay init` each operational repo** — one `relay-os/`
per repo, since the repo *is* the project:

```sh
relay init ~/work/admin                # scaffolds ~/work/admin/relay-os/
relay init ~/work/code                 # ditto for the code repo
```

Each `relay init` also vendors a self-contained copy of the CLI into that
repo's `relay-os/.relay/` (with its own venv). It exists for two things:
**bootstrap** — a fresh contributor who clones the repo can run it without
`pip install`-ing anything — and as a known-good copy that agents can
target. Refresh it later with `relay init --update`.

Day-to-day, your *global* `relay` is what runs. We deliberately don't
auto-activate the vendored copy per-repo (no PATH munging, no rbenv-style
re-exec): with multiple operational repos that quickly turns into a mess of
"which `.relay/.venv/bin/relay` won the PATH race?". The tradeoff is that
relay assumes everyone keeps their global install reasonably current — a
periodic `git pull && pip install -e .` in the source repo is enough.

After init, edit the freshly-written `relay-os/relay.toml` to declare your
agents and assignees, and set `user = "<you>"` in
`relay-os/relay.local.toml`. Then create your first task:

```sh
relay create --title "First task"
```

Multi-surface companies (e.g. an admin repo + a code repo) run multiple
relay-os/ side by side — coordinate them by pointing each repo's `[slack]
webhook` at the same channel.

## Layout

```
mycompany/
├── .git/
└── relay-os/
    ├── relay.toml              # shared config (committed)
    ├── relay.local.toml        # per-machine: user, paths, secrets (gitignored)
    ├── rules.md                # project-wide agent rules
    ├── context.md              # company context shared by every task
    ├── skills/                 # reusable process knowledge
    ├── contexts/               # reusable domain knowledge
    ├── workflows/              # multi-step recipes
    ├── recurring/              # cron-like recurring task templates
    ├── tasks/                  # one dir per task (named by slug): ticket.md, blackboard.md, log.md
    ├── bootstrap/              # persistent launch shims (e.g. bootstrap/ticket)
    └── .relay/                 # vendored CLI + venv (gitignored)
        ├── src/relay/          # CLI source
        ├── .venv/              # self-contained venv
        ├── bin/relay           # wrapper symlink
        └── RELAY_PIN           # upstream commit SHA this .relay/ was vendored from
```

## Commands

### `relay init [PATH] [--update]`

Scaffold `relay-os/` inside `PATH` (default: `.`). Copies templates from
upstream, vendors the CLI into `.relay/`, creates a self-contained venv,
writes a starter `relay.local.toml`, and — if `PATH` is a git repo — auto-stages
and commits the new scaffold (push is left to you).

```sh
relay init mycompany           # fresh scaffold; refuses if relay-os/ exists
relay init --update            # refresh .relay/ + _* templates in current repo
                               # (never touches your relay.toml, rules.md, skills/, etc.)
```

If `~/.local/bin` is on your `PATH`, init also drops a `~/.local/bin/relay`
symlink so the vendored copy is usable from any cwd in a new shell.

**Skill discovery.** Init also wires `relay-os/skills/` into the project-level
skill dirs of the agents that follow the `SKILL.md` standard, so they
auto-discover relay's skills when you start a session in the repo:

- **Claude Code** — symlinked into `.claude/skills/relay/`.
- **Codex** — symlinked into `.codex/skills/relay/`.

That covers our two daily drivers. Other agents (e.g. OpenCode) don't have a
matching project-level skill convention yet — point them at `relay-os/skills/`
yourself if you use them. If init finds something non-directory in the way
(e.g. an empty `.codex` sentinel file from an older setup), it skips that
agent and prints what to clear.

### `relay create`

Scaffold a new task directory under `relay-os/tasks/<slug>/` (slug derived
from the title) and write `ticket.md`, `blackboard.md`, and `log.md`. If the
slug already exists, the new task gets `-2`, `-3`, … appended. The ticket
frontmatter encodes who owns it, who's assigned, what workflow it follows,
and what contexts it pulls in.

```sh
relay create --title "Add retry to webhook handler"
relay create --title "Investigate bounce rate" \
             --workflow code/with-review --context email/payment-flow \
             --assignee claude1 --mode auto
```

Key flags:
- `--workflow NAME` — freeze a workflow into the ticket so steps + skills are pinned.
- `--context REF` (repeatable) — attach domain knowledge files; validated to exist.
- `--mode interactive | auto | script` — how the launcher should run it.
- `--check-recurring` — scan `relay-os/recurring/` and create any tasks that are due.

`relay create` is intentionally mechanical — it lays bytes on disk. The
*authoring* flow (interview, pick a workflow, attach the right contexts,
fill in the assignee) lives in the `bootstrap/ticket` skill. Run that via
the persistent shim — bare for an empty session, or with a title to
scaffold a design-status task and have the agent fill in the rest:

```sh
relay launch bootstrap/ticket
relay launch bootstrap/ticket "Investigate bounce rate"
```

### `relay launch <target> [title]`

Compose every relevant file for a task — rules, project context, ticket,
attached contexts, current workflow step, frozen skills — into a single
prompt and start the configured agent against it. Acquires a `task.lock`
so two agents don't grab the same ticket.

```sh
relay launch add-retry-to-webhook-handler          # full slug
relay launch add-retry                              # any unique prefix works
relay launch add-retry --force                      # break a stale lock
relay launch bootstrap/ticket                       # stateless shim → run a skill
relay launch bootstrap/ticket "Add retry to webhook handler"
                                                    # factory: scaffold a design-status
                                                    # task with that title and launch
                                                    # the bootstrap/ticket skill on it
```

Tasks are addressed by slug — there is no numeric ID. Pass any unique prefix
(git-short-SHA-style) and ambiguous prefixes error out with the matches listed.

The agent type comes from the ticket's `assignee` (e.g. `claude1`) resolved
through `[assignees.<user>]` and `[agents.<type>]` in `relay.toml`.

A task is launchable in `design` (agent is authoring) or `active` (agent is
executing) status. `paused`, `done`, etc. require a flip first.

`bootstrap/<name>` tickets are stateless re-entry points for skills. Without
a title arg they run as authoring sessions and don't acquire a lock —
concurrent launches are safe. With a title, they act as factories: scaffold
a new task seeded from the shim's frontmatter (mode, assignee, skill),
status=design, then launch the agent on the new task to fill in the details.

Init ships `bootstrap/ticket` (authoring flow); the `relay-os/bootstrap/`
tree is upstream-managed and refreshed wholesale by `relay init --update`,
so don't add custom shims there — write your own launch wrappers elsewhere.

### `relay status`

Show what's in flight in the repo. Defaults to non-terminal tasks
(`design`, `ready`, `active`, `paused`); use `--all` to include `done`,
`canceled`, `failed`.

```sh
relay status                              # active work
relay status --all                        # include closed tasks
```

### `relay step <NEXT> --task <slug>`

Advance a workflow-bound task to the next step (1-indexed), or finish it.
Updates the ticket's `step:` field and appends a log entry. The workflow
itself is frozen into the ticket at create time, so step semantics don't
drift mid-task.

```sh
relay step 2 --task add-retry                       # move to step 2
relay step done --task add-retry                    # mark workflow complete
```

### `relay panic --task <slug> --reason "..."`

The agent gives up. Writes a blocker entry to the ticket, @-mentions the
owner in Slack, and releases the task lock so a human (or another agent)
can pick it up. Intended for the agent to call when it's truly stuck —
not for routine handoffs.

```sh
relay panic --task add-retry --reason "Auth flow needs prod creds I don't have"
```

### `relay feed --task <slug> --message "..."`

Post a short FYI to the team Slack channel without changing task state.
Use it for "heads up, deploy started", "tests still flaky", non-blocker
context that the team should see but doesn't need to react to. Posts to
stderr if `[slack].webhook` isn't configured.

```sh
relay feed --task add-retry --message "Pushed branch, waiting on CI"
```

### `relay --version`

Print the relay package version, plus — when run from inside a `relay-os/` —
the upstream commit SHA `.relay/` was vendored from. Useful for "is this
fixed in your copy?" questions.

```sh
$ relay --version
relay 0.2.0
vendored from upstream 61fa3ddb6571 (full: 61fa3ddb6571339237c701424c5675c2c615bdba)
```

## Development

```sh
git clone https://github.com/FastJVM/relay
cd relay
python -m pip install -e .
python -m pytest                    # 83 tests
python -m relay.validate --json     # validate the bundled example/ fixture
```

The dogfood relay-os/ for this very repo lives at `relay-os/`. Tasks tracked
under `relay-os/tasks/` are real — they're how we drive work on relay itself.
