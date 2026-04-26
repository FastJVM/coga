# Relay

A blackboard for humans and agents. Markdown files in a git repo, a small CLI on
top, no database. The substrate FastJVM uses to run the company.

For the why, read [`docs/vision.md`](docs/vision.md). For the full data model
and config reference, read [`docs/spec.md`](docs/spec.md). This README is the
quickstart + a one-screen reference for each CLI command.

## Install

```sh
pip install relay-os                # global install
relay init mycompany                # scaffolds mycompany/relay-os/
cd mycompany
# edit relay-os/relay.toml + relay-os/relay.local.toml
relay create --project mycompany --title "First task"
```

`relay init` also vendors a self-contained copy of the CLI into
`relay-os/.relay/`, so even if your global install drifts, every contributor
runs the same version. Refresh it with `relay init --update`.

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
    ├── tasks/                  # one dir per task: ticket.md, blackboard.md, log.md
    ├── counter                 # monotonic task ID counter
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

### `relay create`

Scaffold a new task directory under `relay-os/tasks/<NNN>-<slug>/`, allocating
the next ID from the counter and writing `ticket.md`, `blackboard.md`, and
`log.md`. The ticket frontmatter encodes who owns it, who's assigned, what
workflow it follows, and what contexts it pulls in.

```sh
relay create --project mycompany --title "Add retry to webhook handler"
relay create --project email --title "Investigate bounce rate" \
             --workflow code/with-review --context email/payment-flow \
             --assignee claude1 --mode auto
```

Key flags:
- `--workflow NAME` — freeze a workflow into the ticket so steps + skills are pinned.
- `--context REF` (repeatable) — attach domain knowledge files; validated to exist.
- `--mode interactive | auto | script` — how the launcher should run it.
- `--check-recurring` — scan `relay-os/recurring/` and create any tasks that are due.

### `relay launch --task <id>`

Compose every relevant file for a task — rules, project context, ticket,
attached contexts, current workflow step, frozen skills — into a single
prompt and start the configured agent against it. Acquires a `task.lock`
so two agents don't grab the same ticket.

```sh
relay launch --task mycompany/001-add-retry          # use full ref
relay launch --task 001                              # short, when unambiguous
relay launch --task mycompany/001 --force            # break a stale lock
```

The agent type comes from the ticket's `assignee` (e.g. `claude1`) resolved
through `[assignees.<user>]` and `[agents.<type>]` in `relay.toml`.

### `relay status`

Show what's in flight across every project. Defaults to non-terminal tasks
(`design`, `ready`, `active`, `paused`); use `--all` to include `done`,
`canceled`, `failed`.

```sh
relay status                              # active work, all projects
relay status --project mycompany          # filter to one project
relay status --all                        # include closed tasks
```

### `relay step <NEXT> --task <id>`

Advance a workflow-bound task to the next step (1-indexed), or finish it.
Updates the ticket's `step:` field and appends a log entry. The workflow
itself is frozen into the ticket at create time, so step semantics don't
drift mid-task.

```sh
relay step 2 --task mycompany/001-add-retry         # move to step 2
relay step done --task mycompany/001-add-retry      # mark workflow complete
```

### `relay panic --task <id> --reason "..."`

The agent gives up. Writes a blocker entry to the ticket, @-mentions the
owner in Slack, and releases the task lock so a human (or another agent)
can pick it up. Intended for the agent to call when it's truly stuck —
not for routine handoffs.

```sh
relay panic --task mycompany/001 --reason "Auth flow needs prod creds I don't have"
```

### `relay feed --task <id> --message "..."`

Post a short FYI to the team Slack channel without changing task state.
Use it for "heads up, deploy started", "tests still flaky", non-blocker
context that the team should see but doesn't need to react to. Posts to
stderr if `[slack].webhook` isn't configured.

```sh
relay feed --task mycompany/001 --message "Pushed branch, waiting on CI"
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
