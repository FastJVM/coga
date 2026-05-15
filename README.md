# Relay

A blackboard for humans and agents. Markdown files in a git repo, a small CLI on
top, no database. The substrate FastJVM uses to run the company.

For the why, read [`docs/vision.md`](docs/vision.md). For the working mental
model — primitives, prompt composition, command surface — read the contexts
under [`relay-os/contexts/relay/`](relay-os/contexts/relay/). This README is
the quickstart + a one-screen reference for each CLI command.

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

## External CLI Tools

`requirements.txt` is only for Python packages. Relay also shells out to a few
human-installed command line tools:

- `git` — required. Relay stores state in the current git repo and uses normal
  working-tree diffs as the review surface.
- `python` 3.11+ — required for the Relay CLI and the vendored `.relay/` copy.
- `gh` — required for GitHub-backed PR workflows such as opening PRs,
  checking merged PRs, and automerge. Run `gh auth login` before relying on
  those paths.
- `gh` 2.90.0+ with `gh skill` — required for Relay-managed skill install and
  update workflows once those commands land. Older `gh` versions should fail
  loud with an upgrade hint.

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
from the title) and post `✨` to Slack. Does **not** spawn an agent.
The new ticket is empty — title, owner, mode, and timestamp set; workflow,
contexts, assignee, and description still need to be filled in. If the
slug already exists, the new task gets `-2`, `-3`, … appended.

```sh
relay create "Add retry to webhook handler"
relay create "Nightly cleanup" --mode auto
```

`create` is one third of the boot sequence:

1. `relay create "<title>"` — scaffold the draft.
2. Edit the ticket body (workflow, contexts, description).
3. `relay mark active <slug>` — flip status to active.
4. `relay launch <slug>` — spawn the agent.

The split keeps the moment of authoring distinct from the moment of
starting work. Tickets you mean to draft now and start later get the
same `create` call; nothing fires until you choose to.

Programmatic callers (e.g. the recurring scaffolder) call
`scaffold_task()` in `relay.scaffold` directly with the full keyword
surface.

### `relay mark <state> <slug> [--message "..."]`

Change a ticket's `status`. Three subcommands:

```sh
relay mark active add-retry         # draft / paused → active. Posts 🚀.
relay mark paused add-retry         # active → paused. Posts ⏸️. Preserves step.
relay mark done   add-retry         # active → done.   Posts 🎉. Clears step.
```

`relay mark` is the only command that writes `status:`. `relay launch`
no longer activates drafts; `relay bump` no longer marks final-step
tickets done. The two state machines are entirely separated.

`--message` piggy-backs an FYI onto the state-transition Slack
broadcast — one post instead of two.

### `relay recurring check`

Scan `relay-os/recurring/` and scaffold any due tasks. Called from
`scripts/cron.sh`; safe to run by hand. Recurring scaffolding goes through
`scaffold_task()` in `relay.scaffold` directly with the template's full
frontmatter.

### `relay dream`

Create an ad-hoc Dream cleanup task for this Relay repo, activate it, and
launch it. The slug is allocated like any other task (`dream`, `dream-2`,
etc.); it is not derived from a schedule or timestamp. With `--no-launch`,
Relay only scaffolds the draft and prints the `relay mark active` /
`relay launch` sequence.

### Dream and REM

Dream is Relay's generic ticket cleanup pass for one `relay-os/`. A Dream task
scans all tickets, runs fixed Relay housekeeping skills such as
`validate-drift` and `retro/done-ticket`, proposes cleanup, writes results to
that run's blackboard, and leaves a human-reviewable trail.

REM is repo/user-specific recurring maintenance. It is opt-in user space: copy
the inert `relay-os/recurring/_rem.md` template, give it a schedule and
workflow, and define the operational checks that matter to that repo. Stale
branch cleanup belongs in a dev maintenance loop, not in Dream's generic ticket
cleanup pass.

### `relay skill`

Manage skills under `relay-os/skills/` without inventing a second package
manager. GitHub-backed installs and updates delegate to GitHub CLI's public
preview `gh skill` command; Relay adds exact removal, URL-backed provenance,
local-adaptation checks, and a PR-ready update summary for Dream.

```sh
relay skill install owner/repo skill-name
relay skill install-url https://example.com/skill.zip
relay skill install-local ./downloaded-skill
relay skill update skill-name
relay skill update --all
relay skill update --all --pr --verify "relay validate --json"
relay skill remove skill-name
relay skill status --check
```

URL-backed installs are downloaded into a temporary directory, validated for a
`SKILL.md`, installed through `gh skill install --from-local`, then recorded in
`relay-os/skills/<name>/.relay-source.json` with the original URL and content
digests. URL-backed updates re-fetch that source and skip locally adapted
skills instead of overwriting them. Removal is exact-name only and leaves a
normal git delete for review.

### `relay launch <target>`

Compose every relevant file for a task — rules, project context, ticket,
attached contexts, current workflow step, frozen skills — into a single
prompt and start the configured agent against it.

`launch` requires `status: active`. Drafts must be activated with
`relay mark active <slug>` first; paused / done tickets must be marked
back to active before they can be launched. `launch` no longer mutates
status itself.

```sh
relay launch add-retry-to-webhook-handler          # full slug
relay launch add-retry                              # any unique prefix works
relay launch add-retry --agent codex1               # one-off agent override
relay launch add-retry --prompt-report              # show prompt layer sizes, no launch
relay launch bootstrap/orient                       # stateless shim → run a skill
relay launch bootstrap/orient --agent codex1        # choose a bootstrap agent
```

Tasks are addressed by slug — there is no numeric ID. Pass any unique prefix
(git-short-SHA-style) and ambiguous prefixes error out with the matches listed.

The agent type comes from the ticket's `assignee` (e.g. `claude1`) resolved
through `[assignees.<user>]` and `[agents.<type>]` in `relay.toml`. Pass
`--agent <nickname>` to use one of your configured agent nicknames for this
launch only; normal task launches do not rewrite the ticket's `assignee`.
Bootstrap shims use the same flag for one-off sessions, so `relay chat --agent
codex1` can open the orient shim with Codex while `relay chat --agent claude1`
opens it with Claude.

For workflow-bound interactive/auto tasks, one `relay launch` can run multiple
agent-owned steps. After each clean agent exit, Relay re-reads the ticket and
continues in a fresh agent process only when the task is still active, the step
advanced, the new current step has a `skill:`, and the concrete `assignee:`
did not change. It stops at human/no-skill steps, assignee handoffs, done or
paused tasks, no-progress exits, and panic/non-zero exits.

Use `--prompt-report` to inspect the composed prompt without checking for a
TTY or spawning an agent. The report lists each included layer, exact
context/skill refs, bytes, and approximate token counts. The token estimate is
intentionally dependency-light (`characters / 4`), so use it to catch prompt
bloat and compare tasks, not to predict exact provider billing.

`bootstrap/<name>` tickets are stateless re-entry points for skills.
Concurrent launches are safe — they have no status, no log of state changes,
and no lock. The `relay-os/bootstrap/` tree is upstream-managed and refreshed
wholesale by `relay init --update`, so don't add custom shims there — write
your own launch wrappers elsewhere.

### `relay status`

Show every task in the repo — `draft`, `active`, `paused`, and `done`.
One line per task. Bootstrap shims have no status and don't appear.

```sh
relay status
```

### `relay show <slug>`

Print a task's `ticket.md`, `blackboard.md`, and `log.md` to the
terminal, rendered as markdown. Same prefix matching as `bump`/`launch`.
Bootstrap shims show only `ticket.md`. For grep/pipe use, read the
files directly — `show` is for human eyes.

```sh
relay show add-retry
relay show bootstrap/orient
```

### `relay bump <slug> [--message "..."]`

Advance a workflow-bound task one step. Updates the ticket's `step:`
field and appends a log entry. The workflow itself is frozen into the
ticket at create time, so step semantics don't drift mid-task.

`bump` no longer finishes tickets. Bumping past the last step is an
error pointing you at `relay mark done <slug>`. Bumping a ticket
without a workflow is the same error — `mark done` is how you finish
those.

`--message` piggy-backs an FYI onto the state-transition Slack
broadcast — useful for "advanced to (pr) — PR opened: <link>" without
firing a second message.

```sh
relay bump add-retry                         # advance one step
relay bump add-retry --message "PR: https://example/142"
relay mark done add-retry                    # finish (on final step, or no workflow)
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

### `relay delete <slug>`

Throw away an abandoned ticket. Removes the whole task directory —
ticket, blackboard, log. Recovery is via `git restore`; the git
history is the audit trail, no Slack broadcast.

Bootstrap shims aren't user-deletable — they're managed by
`relay init --update`.

```sh
relay delete add-retry
```

### `relay retire <slug>`

Wrap up a `done` ticket: scaffold a one-shot `retire-<slug>` task whose
body invokes the `retro/done-ticket` skill against the named ticket. The
retro skill opens a PR only when it extracts new durable knowledge; that PR
records the `## Retro` marker, edits the knowledge base, and deletes the source
task directory in the same PR. If no new durable knowledge exists, Retro
records `result: no-new-durable-knowledge` on the source blackboard and opens
no PR. This command activates and launches the retire task unless `--no-launch`
is passed.

Refuses if the target task is not `status: done`. Use `relay delete`
for an abandoned ticket where retro has nothing to extract. Branch
hygiene (pruning the merged feature branch, sweeping stale branches)
belongs in a Dream worker, not here.

```sh
relay retire add-retry                       # auto mode by default
relay retire add-retry --mode interactive    # supervise the run
relay retire add-retry --no-launch           # scaffold without launching
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
# Optional once those nicknames exist for the current user:
# claude = "launch bootstrap/orient --agent claude1"
# codex = "launch bootstrap/orient --agent codex1"
```

`create` is a built-in command, not an alias — it has its own
scaffolding behavior. Add your own aliases for shims or skills you
launch often; running an alias prints the expansion to stderr —
`→ relay launch bootstrap/orient` — so the indirection is visible.

Rules, checked at config load — fail loud, not silent:
- Alias names cannot collide with built-in commands.
- The first token of the expansion must be a known built-in.
- Aliases are pass-through only. Arguments and flags after the alias name
  are forwarded to the expanded command.

## Development

```sh
git clone https://github.com/FastJVM/relay
cd relay
python -m pip install -e .
python -m pytest                    # 83 tests
relay validate --json               # validate the bundled example/ fixture
relay validate --fix                # repair missing blackboard.md/log.md only
```

The dogfood relay-os/ for this very repo lives at `relay-os/`. Tasks tracked
under `relay-os/tasks/` are real — they're how we drive work on relay itself.
