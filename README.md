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
`relay-os/relay.local.toml`. Then create your first ticket:

```sh
relay create "First task"
```

Multi-surface companies (e.g. an admin repo + a code repo) run multiple
relay-os/ side by side — coordinate them by pointing each repo's
`$SLACK_WEBHOOK_URL` at the same channel.

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

### `relay create "<title>"`

Scaffold a new `draft` ticket under `relay-os/tasks/<slug>/` (slug derived
from the title) and launch the `bootstrap/ticket` skill on it. The skill
interviews you, scans the inventory, and fills in workflow, contexts,
assignee, and description directly in the ticket. If the slug already
exists, the new task gets `-2`, `-3`, … appended.

```sh
relay create "Add retry to webhook handler"
```

`relay create` is shipped as a default alias for
`relay launch bootstrap/ticket` — see [Aliases](#aliases). Programmatic
callers (e.g. the recurring scaffolder) call `scaffold_task()` in
`relay.scaffold` directly with the full keyword surface.

### `relay recurring check`

Scan `relay-os/recurring/` and scaffold any due tasks. Called from
`scripts/cron.sh`; safe to run by hand. Recurring scaffolding goes through
`scaffold_task()` in `relay.scaffold` directly with the template's full
frontmatter.

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
                                                    # factory: scaffold a draft task
                                                    # with that title and launch the
                                                    # bootstrap/ticket skill on it
```

Tasks are addressed by slug — there is no numeric ID. Pass any unique prefix
(git-short-SHA-style) and ambiguous prefixes error out with the matches listed.

The agent type comes from the ticket's `assignee` (e.g. `claude1`) resolved
through `[assignees.<user>]` and `[agents.<type>]` in `relay.toml`.

A task is launchable in `draft` (agent is authoring) or `active` (agent is
executing) status. `paused` and `done` require a flip first.

`bootstrap/<name>` tickets are stateless re-entry points for skills. Without
a title arg they run as authoring sessions and don't acquire a lock —
concurrent launches are safe. With a title, they act as factories: scaffold
a new task seeded from the shim's frontmatter (mode, assignee, skill),
status=draft, then launch the agent on the new task to fill in the details.

Init ships `bootstrap/ticket` (authoring flow); the `relay-os/bootstrap/`
tree is upstream-managed and refreshed wholesale by `relay init --update`,
so don't add custom shims there — write your own launch wrappers elsewhere.

### `relay status`

Show every task in the repo — `draft`, `active`, `paused`, and `done`.
One line per task. Bootstrap shims have no status and don't appear.

```sh
relay status
```

### `relay bump <slug> [--message "..."]`

Advance a workflow-bound task one step. Updates the ticket's `step:`
field and appends a log entry. Bumping past the last step marks the task
`done`. The workflow itself is frozen into the ticket at create time, so
step semantics don't drift mid-task.

`--message` piggy-backs an FYI onto the state-transition Slack
broadcast — useful for "advanced to (pr) — PR opened: <link>" or
"finished — talked to marc, scope ok" without firing a second message.

```sh
relay bump add-retry                         # advance one step
relay bump add-retry --message "PR: https://example/142"
relay bump add-retry                         # again, until past the last → done
```

### `relay automerge`

Walk active tickets, find ones on their final workflow step (or with no
workflow) whose blackboard `## Dev` section names a merged PR, and
auto-bump them to `done`. Looks the PR up via `gh pr view`. Posts to
Slack with a distinct `auto-bumped on merge of PR #<N>` line.

`relay init` symlinks this into `.git/hooks/post-merge`, so a normal
`git pull` after a teammate merges runs it for you. `relay status` also
calls it opportunistically so the long tail (you didn't pull, but you
checked status) gets caught. No `gh`? The `status` path silently skips;
the explicit command surfaces the error.

```sh
relay automerge   # one-shot. Safe to run by hand.
```

### `relay panic --task <slug> --reason "..."`

The agent gives up. Writes a blocker entry to the ticket, posts to the
Slack channel naming the owner, and releases the task lock so a human
(or another agent) can pick it up. Intended for the agent to call when
it's truly stuck — not for routine handoffs.

```sh
relay panic --task add-retry --reason "Auth flow needs prod creds I don't have"
```

### `relay slack --task <slug> --message "..."`

Manual broadcast escape hatch. Posts a short FYI to the team Slack
channel without changing task state — for events that don't coincide
with a `bump`/`panic`/launch transition (e.g. a human announcing they
hand-edited a ticket, or "tests still flaky" mid-step). For FYIs that
*do* fire alongside a state change, prefer `bump --message`.

```sh
relay slack --task add-retry --message "Reassigned to pierre"
```

### Slack — the team sync point

Slack is required by default. Every state change posts to the channel
pointed at by `$SLACK_WEBHOOK_URL`: ticket created, draft → active,
`bump`, `panic`, `slack`, script-mode failure, and each recurring
scaffold. Opening a session on an already-active ticket does *not*
post — that isn't a state change. Failures are loud: if Slack is
unreachable or the webhook isn't set, the command exits non-zero
rather than silently dropping the message — a missed FYI becomes a
stale mental model on the human side, and that's worse than a noisy
retry.

**Setup (solo or team).** Create a Slack incoming webhook for the
channel and export the URL in your shell rc:

```sh
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
```

The URL is a bearer token — anyone holding it can post to that channel
as the app. Don't commit it; don't paste it in tickets or logs. Rotate
via the Slack app's webhook page if it ever leaks. For multi-user
setups, each member exports the same URL locally; the `relay.toml` does
not carry the webhook.

Run `relay validate --check-slack` to probe the webhook (POSTs an
empty-text payload that Slack rejects without posting to the channel)
so a dead URL surfaces at config time, not at first `bump`. Failures
during runtime posts also append a line to the task's `log.md` so
daemon / cron / launched-script runs leave a recoverable trace.

**Opt out (solo dev / CI / dry runs).** Set in `relay.local.toml`:

```toml
[slack]
enabled = false
```

With `enabled = false`, every Slack call is suppressed to stderr and
nothing crashes. Treat this as an exit from the sync loop, not a
default — once you're working with another person, turn it back on.

### `relay --version`

Print the relay package version, plus — when run from inside a `relay-os/` —
the upstream commit SHA `.relay/` was vendored from. Useful for "is this
fixed in your copy?" questions.

```sh
$ relay --version
relay 0.2.0
vendored from upstream 61fa3ddb6571 (full: 61fa3ddb6571339237c701424c5675c2c615bdba)
```

### Aliases

Sugar for the often-used commands. The `[aliases]` table in `relay.toml`
maps a one-word name to an expanded `relay` command; positional args after
the alias name forward to the expansion. Default aliases shipped by
`relay init`:

```toml
[aliases]
chat = "launch bootstrap/orient"
create = "launch bootstrap/ticket"
```

So `relay create "Add retry"` runs as
`relay launch bootstrap/ticket "Add retry"` (and prints the expansion to
stderr — `→ relay launch bootstrap/ticket "Add retry"` — so the
indirection is visible). Add your own for shims or skills you launch
often.

Rules, checked at config load — fail loud, not silent:
- Alias names cannot collide with built-in commands.
- The first token of the expansion must be a known built-in.
- Aliases are positional pass-through only — they don't accept their own
  flags.

## Development

```sh
git clone https://github.com/FastJVM/relay
cd relay
python -m pip install -e .
python -m pytest                    # 83 tests
relay validate --json               # validate the bundled example/ fixture
```

The dogfood relay-os/ for this very repo lives at `relay-os/`. Tasks tracked
under `relay-os/tasks/` are real — they're how we drive work on relay itself.
