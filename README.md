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
agent types, and set `user = "<you>"` in `relay-os/relay.local.toml`.
Then draft your first ticket:

```sh
relay ticket "First task"
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

## Task lifecycle

Relay now separates ticket authoring, queue approval, and launched work:

```text
draft -> active -> in_progress -> done
             \          /
              -> paused
```

- `draft` is unapproved work. Use `relay ticket "<title>"` for the guided
  authoring interview, or `relay draft "<title>"` when you only want the raw
  files.
- `active` is approved and queued. Humans can still refine active tickets with
  `relay ticket <slug>` before work starts.
- `in_progress` is launched work. `relay launch <slug>` moves an active ticket
  into this state, and `relay bump <slug>` only advances workflow steps from
  here.
- `paused` preserves the current workflow step while taking the task out of
  execution.
- `done` clears the workflow step and closes the task.

The normal path for a new ticket is:

```sh
relay ticket "Add retry to webhook handler"
relay mark active add-retry
relay launch add-retry
# agent works, writes blackboard, and bumps workflow steps
relay mark done add-retry
```

For old scripts or muscle memory, `relay create "<title>"` still works as a
compatibility spelling for `relay draft "<title>"`; it does not run the
authoring interview.

## Commands

### `relay init [PATH] [--update] [--all]`

Scaffold `relay-os/` inside `PATH` (default: `.`). Copies templates from the
installed Relay package, vendors the CLI into `.relay/`, creates a
self-contained venv, writes a starter `relay.local.toml`, and — if `PATH` is a
git repo — auto-stages and commits the new scaffold (push is left to you).

```sh
relay init mycompany           # fresh scaffold; refuses if relay-os/ exists
relay init --update            # refresh .relay/ + package templates in current repo
                               # (never touches your relay.toml, rules.md, custom skills, etc.)
relay init --update --all      # sweep: refresh every relay repo under the current dir
relay init --update --all ~/work   # ...or under the given dir
```

Because each repo vendors its own batteries, picking up a new Relay release
means `pip install -U relay-os` once, then `relay init --update` per repo. The
`--all` sweep does that last step in bulk — it scans `PATH` for every
`relay-os/relay.toml`, refreshes each (sharing one upstream clone), reports
per-repo results, and exits non-zero if any repo failed.

If `~/.local/bin` is on your `PATH`, init also drops a `~/.local/bin/relay`
symlink so the vendored copy is usable from any cwd in a new shell.

**Batteries and skill discovery.** The installed Relay package carries bundled
skills, contexts, hooks, and bootstrap shims as package resources. `pip install`
puts those resources in the wheel; `relay init` / `relay init --update`
materializes them into `relay-os/bootstrap/`. Project-local
`relay-os/skills/` and `relay-os/contexts/` still win when they define the same
ref.

Init also builds an ignored `relay-os/.agent-skills/` view that merges
project-local skills with bundled bootstrap skills, then wires that view into
the project-level skill dirs of the agents that follow the `SKILL.md` standard:

- **Claude Code** — symlinked into `.claude/skills/relay/`.
- **Codex** — symlinked into `.codex/skills/relay/`.

That covers our two daily drivers. Other agents (e.g. OpenCode) don't have a
matching project-level skill convention yet — point them at
`relay-os/.agent-skills/` yourself if you use them. If init finds something
non-directory in the way (e.g. an empty `.codex` sentinel file from an older
setup), it skips that agent and prints what to clear.

### `relay draft "<title>"`

Scaffold a new raw `draft` ticket under `relay-os/tasks/<slug>/` (slug
derived from the title) and post `✨` to Slack. Does **not** spawn an agent
and does **not** run the guided authoring interview. The new ticket is empty
— title, owner, mode, and timestamp set; workflow, contexts, assignee, and
description still need to be filled in. If the slug already exists, the new
task gets `-2`, `-3`, … appended.

```sh
relay draft "Add retry to webhook handler"
relay draft "Nightly cleanup" --mode auto
```

`relay create "<title>"` remains as a compatibility spelling for this raw
draft operation.

### `relay ticket [<title-or-slug>] [--agent <type>]`

Run the guided ticket-authoring skill. This is the normal path when you want
Relay to ask clarifying questions, choose a workflow/context/assignee shape,
and edit the ticket before work starts.

```sh
relay ticket                                  # ask for title, then fill a draft
relay ticket "Add retry to webhook handler"  # create draft, then interview
relay ticket add-retry                        # edit existing draft/active/paused
relay ticket add-retry --agent codex          # choose authoring agent
```

`relay ticket` refuses `in_progress` and `done` tickets by default. Editing a
draft/active/paused ticket leaves its status unchanged.

The usual boot sequence is:

1. `relay ticket "<title>"` — scaffold and fill the draft.
2. Review or edit the ticket.
3. `relay mark active <slug>` — approve it into the queue.
4. `relay launch <slug>` — mark it `in_progress` and spawn the agent.

Programmatic callers (e.g. `relay recurring`) call `scaffold_task()` in
`relay.scaffold` directly with the full keyword surface.

### `relay mark <state> <slug> [--message "..."]`

Change a ticket's `status`. Three subcommands:

```sh
relay mark active add-retry         # draft / paused → active. Posts 🚀.
relay mark paused add-retry         # active / in_progress → paused. Preserves step.
relay mark done   add-retry         # active / in_progress → done. Clears step.
```

`relay mark active` refuses a ticket with no workflow — a workflow-less
ticket has no steps and can't be advanced by `relay bump`. A bare-string
`workflow:` ref is frozen into its snapshot on activation. (Recurring and
retire tasks are intentionally workflow-less and are scaffolded straight to
`active`, bypassing this gate.)

`relay launch` owns the `active` → `in_progress` start transition. `relay
bump` no longer marks final-step tickets done.

`--message` piggy-backs an FYI onto the state-transition Slack
broadcast — one post instead of two.

### `relay recurring`

Scan `relay-os/recurring/` and launch the templates that are due. For each
template (excluding `_`-prefixed inert templates), `relay recurring`
get-or-creates the **current period's** task, prints a scan table, then
launches the still-`active` ones sequentially, most-overdue first. Tasks
already `done`, `in_progress`, or `paused` are left alone — no auto-resume.

Only the current period is considered; `relay recurring` never chases missed
periods, so a template runs at most once per period no matter how long since
the last invocation. The task slug is the schedule-derived period key
(`dream-2026-W21`), which makes the get-or-create idempotent.

Recurring scaffolding goes through `scaffold_task()` in `relay.scaffold`
directly with the template's full frontmatter. Recurring tasks are
workflow-less, so they are scaffolded straight to `active` — they can't go
through the `relay mark active` gate.

`scripts/cron.sh` calls `relay recurring` directly. Naming a command
`recurring` does not install or schedule anything — `relay recurring` only
runs when you (or a cron entry you set up yourself) invoke it.

`--interactive` launches every due task in interactive mode for that run,
even ones whose template says `mode: auto` — the debug knob for stepping
through a recurring run in an attended terminal. It threads `relay launch
--mode interactive` through and rewrites no ticket files.

### `relay recurring launch <name>`

Scaffold one named recurring template now, ignoring its schedule, and launch
it. The task slug still uses the template's schedule-derived period key, so a
manual `launch` and a bare `relay recurring` run converge on one task
directory per period. This is the on-demand entry point behind aliases like
`relay dream`. `--interactive` runs it in interactive mode even if the
template says `mode: auto` — handy for debugging one template by hand.

### `relay dream`

Run Relay's generic cleanup pass now. `dream` is an alias for
`relay recurring launch dream`: it scaffolds the `recurring/dream.md`
recurring task and launches it. The slug is the recurring period key
(`dream-2026-W21`), shared with the scheduled run — running `relay dream`
mid-week reuses that week's task rather than creating a second one.

### Dream and REM

Dream is Relay's generic ticket cleanup pass for one `relay-os/`. It ships as a
recurring task template, `relay-os/recurring/dream.md`: a weekly `relay
recurring` run scaffolds and launches it when its schedule is due, and the
`relay dream` alias scaffolds and launches it on demand. A Dream task scans all tickets, runs fixed Relay
housekeeping skills such as `validate-drift` and `retro/done-ticket`, proposes
cleanup, writes results to that run's blackboard, and leaves a human-reviewable
trail. Retro work is batched for done tickets: Dream loads the context/skill
corpus once, processes up to five coherent tickets with a running knowledge
delta, and opens one small PR only when durable knowledge changed.

REM is repo/user-specific recurring maintenance. It is opt-in user space: copy
the inert `relay-os/recurring/_rem.md` template, give it a schedule and
workflow, and define the operational checks that matter to that repo. Stale
branch cleanup belongs in a dev maintenance loop, not in Dream's generic ticket
cleanup pass.

### `relay skill`

Manage project-local skills under `relay-os/skills/` without inventing a second
package manager. GitHub-backed installs and updates delegate to GitHub CLI's
public preview `gh skill` command; Relay adds exact removal, URL-backed
provenance, local-adaptation checks, and a PR-ready update summary for Dream.
Bundled bootstrap skills are package-backed batteries: `relay skill status`
shows them, but `relay skill update --all` skips them and points you at the
package update path (`pip install --upgrade relay-os`, then
`relay init --update`).

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
normal git delete for review. To customize a bundled skill, copy it to the same
ref under `relay-os/skills/`; the local copy shadows the bundled one and becomes
your repo-owned skill.

### `relay launch <target>`

Compose every relevant file for a task — rules, project context, ticket,
attached contexts, current workflow step, frozen skills — into a single
prompt and start the configured agent against it.

`launch` accepts `status: active` or `status: in_progress`. Drafts must be
activated with `relay mark active <slug>` first; paused / done tickets must
be marked back to active before they can be launched. Launching an active
ticket marks it `in_progress`; launching an already-`in_progress` ticket
resumes it.

```sh
relay launch add-retry-to-webhook-handler          # full slug
relay launch add-retry                              # any unique prefix works
relay launch add-retry --agent codex                # one-off agent override
relay launch add-retry --mode interactive           # debug: run an auto ticket interactively
relay launch add-retry --prompt-report              # show prompt layer sizes, no launch
relay launch bootstrap/orient                       # stateless shim → run a skill
relay launch bootstrap/orient --agent codex         # choose a bootstrap agent
```

Tasks are addressed by slug — there is no numeric ID. Pass any unique prefix
(git-short-SHA-style) and ambiguous prefixes error out with the matches listed.

The agent type comes from the ticket's `assignee` (e.g. `claude`), which
names an `[agents.<type>]` block in `relay.toml` directly. Pass
`--agent <type>` to override for this launch only; normal task launches do
not rewrite the ticket's `assignee`. Bootstrap shims use the same flag for
one-off sessions, so `relay chat --agent codex` can open the orient shim
with Codex while `relay chat --agent claude` opens it with Claude.

For workflow-bound interactive/auto tasks, one `relay launch` can run multiple
agent-owned steps. After each clean agent exit, Relay re-reads the ticket and
continues in a fresh agent process only when the task is still `in_progress`, the step
advanced, the new current step has a `skill:`, and the concrete `assignee:`
did not change. It stops at human/no-skill steps, assignee handoffs, done or
paused tasks, no-progress exits, and panic/non-zero exits.

Use `--prompt-report` to inspect the composed prompt without checking for a
TTY or spawning an agent. The report lists each included layer, exact
context/skill refs, bytes, and approximate token counts. The token estimate is
intentionally dependency-light (`characters / 4`), so use it to catch prompt
bloat and compare tasks, not to predict exact provider billing.

`--mode <interactive|auto>` overrides the ticket's `mode:` for one launch —
the debug knob for stepping through a `mode: auto` ticket in an attended
terminal (and vice versa). It is ephemeral: the ticket file is never
rewritten, and both the spawned command and the composed mode-specific prompt
block follow the override. It is rejected for `mode: script` tasks, which
compose no agent prompt.

`bootstrap/<name>` tickets are stateless re-entry points for skills.
Concurrent launches are safe — they have no status, no log of state changes,
and no lock. The `relay-os/bootstrap/` tree is upstream-managed and refreshed
wholesale by `relay init --update`, so don't add custom shims there — write
your own launch wrappers elsewhere.

### `relay status`

Show every task in the repo — `draft`, `active`, `in_progress`, `paused`, and `done`.
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

Walk active/in-progress tickets, find ones on their final workflow step (or with no
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
body invokes the `retro/done-ticket` skill against the named ticket. `retire`
keeps the single-ticket path; Dream owns batched Retro runs. The retro skill
always deletes the processed source task in a reviewable PR. When it extracts
new durable knowledge, that PR records the `## Retro` marker, edits the
knowledge base, and deletes the source task directory together. When no new
durable knowledge exists, Retro records `result: no-new-durable-knowledge` and
deletes the ticket in a delete-only prune PR. The retire task is workflow-less,
so it is scaffolded straight to `active` and launched unless `--no-launch` is
passed.

Refuses if the target task is not `status: done`. Use `relay delete`
for an abandoned ticket where retro has nothing to extract. Branch
hygiene (pruning the merged feature branch, sweeping stale branches)
belongs in a Dream worker, not here.

```sh
relay retire add-retry                       # interactive mode (the default)
relay retire add-retry --mode auto           # one-shot autonomous Retro run
relay retire add-retry --no-launch           # scaffold without launching
```

`retire` runs interactively by default so the Retro pass writes live
console output; `--mode auto` runs it as a one-shot headless `claude -p`
session whose output is buffered to the task log.

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
active → in_progress, `bump`, `panic`, `slack`, script-mode failure, and each
recurring scaffold. Relaunching an already-`in_progress` ticket does *not*
post — that isn't a new state change. Failures are loud: if Slack is
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
# Add per-agent shortcuts once those types are declared in `[agents.*]`:
# claude = "launch bootstrap/orient --agent claude"
# codex = "launch bootstrap/orient --agent codex"
```

`draft`, `ticket`, and `create` are built-in commands, not aliases. Add your
own aliases for shims or skills you launch often; running an alias prints the
expansion to stderr —
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
