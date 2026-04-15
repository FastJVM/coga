# Relay

**A blackboard for humans and agents.** CLI-first, git-backed,
agent-agnostic. No server, no database, no UI.

This repo is a Relay CompanyOS — a single source of truth for the
tasks, skills, contexts, and workflows a small team runs on. Everything
is markdown you can read, edit, and diff.

## Status

**Demonstration scaffold. Nothing here touches live operations.**

The CLI works end-to-end for the basics (`create`, `status`, `launch`,
`step`, `panic`, `feed`) and the `relay/` knowledge tree is stocked
with example skills, contexts, workflows, and recurring templates so
the shape is legible.

But:

- The four existing automations (RD tax, Brex, Xero, SF forms)
  continue to run under their current launchd jobs, untouched. The
  matching files under `recurring/` and `skills/admin/` document the
  shape a migration would take — they do not execute the real scripts.
- The only script-mode skill that exists, `skills/admin/xero-reconcile/
  run.sh`, is a **dry-run demo** that prints what it would do and
  exits. Instructions for wiring it to the real automation are in
  comments at the top of that file.
- The example project paths in `relay.local.toml.example` point only
  at directories inside this repo. No smoke test can accidentally
  write into a real automation directory.
- There is no Slack webhook configured by default, so `relay feed`,
  `relay panic`, and `relay step` silently no-op on the Slack side.
  Set `SLACK_WEBHOOK_URL` in your shell environment to enable it.

Everything in this repo is Python, markdown, and shell. There is no
TypeScript, no Node, no server, no database.

## Repo layout

```
relay.toml                Shared, committed config (projects, agents, team)
relay.local.toml          Per-machine config — paths and secret refs (gitignored)
rules.md                  Global rules inlined in every task prompt
protocol.md               Relay protocol system prompt (base)
protocol-interactive.md   Mode block — human is present
protocol-auto.md          Mode block — agent is alone

skills/                   Process knowledge (how to do things)
  <path>/SKILL.md         name + description frontmatter, markdown body
  <path>/<script>         Optional bundled script (e.g. run.sh, post.py)

contexts/                 Domain knowledge (what's true about the world)
  <path>/SKILL.md         Attached to tickets via ticket.md frontmatter

workflows/                Step sequences frozen into tickets at creation
  <path>.md               YAML frontmatter lists steps; each step may
                          reference a skill or use inline instruction

recurring/                Templates that create tasks on a cron schedule
  <name>.md               Schedule + full ticket template

projects/                 Local-type projects live here (optional).
  demo/relay-os/          Repo-type projects live anywhere on disk and
    context.md            are pointed to from relay.local.toml.
    counter               Per-project task ID counter (auto-incremented
                          by `relay create`, atomic via fcntl).
    tasks/                Each task is a directory with ticket.md,
                          blackboard.md, log.md, and task.lock.

cli/                      The Relay CLI (Python)
  relay                   Entry point (add cli/ to PATH or symlink)
  relay_cli/              Package

scripts/                  Shell entry points
  cron.sh                 Called by the user's crontab; runs
                          `relay create --check-recurring`.
```

## Install

Requires Python 3.11+ and `pyyaml`.

```bash
cd ~/Desktop/ticketing-system
pip install -r requirements.txt
cp relay.local.toml.example relay.local.toml
# edit relay.local.toml — set `user`, project paths, and secret env vars

# Add the CLI to your PATH (or symlink `cli/relay` into ~/bin):
export PATH="$PWD/cli:$PATH"
chmod +x cli/relay

relay status   # should print "no active tasks" on a fresh repo
```

## First task

```bash
# Create a demo task with a workflow
relay create \
  --project demo \
  --title "Check demo pipeline" \
  --workflow code/with-review \
  --assignee claude1

# See it listed
relay status

# When you're ready to work on it (must be `active`):
# - edit ticket.md frontmatter: change `status` from `ready` to `active`
# - then launch
relay launch --task 001
```

## CLI commands

| Command | Purpose |
|---|---|
| `relay create` | Scaffold a new task directory in a project |
| `relay status` | One-line-per-task view across all projects |
| `relay launch` | Compose prompt, inject secrets, spawn agent or run script |
| `relay step` | Advance the task to the next workflow step (or mark done) |
| `relay panic` | Record a blocker and notify the task owner in Slack |
| `relay feed` | Post an FYI to the shared Slack feed |

See `protocol.md` for how agents are taught to use these.

## The four automations

Four proof-of-concept automations already exist on this machine and are
stubbed as recurring templates under `recurring/`:

- `recurring/rd-tax-weekly.md` — weekly Slack scrape + Claude
  classification for the IRC §41 R&D tax credit running doc.
- `recurring/brex-unmapped-monthly.md` — monthly Brex unmapped
  transaction count, posts to Slack.
- `recurring/xero-reconciliation-monthly.md` — monthly Xero click-OK
  reconciliation, flags manual-attention items.
- `recurring/sf-forms-annual.md` — annual download of DE-9/940/941 from
  Gusto to Google Drive.

These templates document the intended shape. Migrating the existing
scripts into `mode: script` skills under `skills/admin/` is a follow-up
task — the templates reference the skill paths they will use.

## Design principles

- **No magic, everything exposed.** Markdown files in a git repo. Every
  CLI command is callable by a human. No hidden internals.
- **Files over databases.** Tasks are directories, not rows. You can
  read them with `cat`, edit them with `vim`, diff them with `git`.
- **Agent-agnostic.** Knowledge lives in portable markdown, not any
  one agent's memory or config format.
- **Git as sync.** No server. `git pull` is how teammates see each
  other's tasks.
- **Human in the loop at the highest-leverage point.** The human picks
  which context belongs with which task. Everything else — generation,
  execution, reporting — is automated.

See the full spec for the long form. See `protocol.md` for how agents
are taught to operate inside this system.
