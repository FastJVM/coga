# Coga

Most tools say *don't think* — delegate the work and forget it. Coga's bet is the opposite:

> ## Don't don't think. Think better.

**Coga is git-backed Markdown + a small CLI that turns your intent into
executable tickets and runs them on the coding agents you already use** —
Claude Code and Codex today, or any CLI agent (Gemini CLI, Goose, OpenHands,
Devin, your own) in a few lines of config. **It is not another autonomous
agent** — it sits *above* the agents you have and coordinates them across
code, research, and operations alike.

The difference you feel: your context and corrections **compound**. Instead of
a flat `CLAUDE.md` that bloats and a session that forgets, Coga's prose is
decomposed, scoped, versioned, and reused — and every correction lands as a
pull request you merge, not a note that evaporates when the session ends. The
agent acts; you judge what's worth doing and what was wrong, and grant autonomy
one step at a time. It's all Markdown and Git on your disk — nothing hidden, no
lock-in — so you always see *why* an agent did what it did.

It's the substrate FastJVM uses to run the company. **Try it now ↓** — then read
[the principles](#principles) for why it's shaped this way.

## Getting Started

**1. Install the CLI (once).**

```sh
git clone https://github.com/FastJVM/coga
cd coga
python -m pip install -e .
```

That puts `coga` on your PATH against the source. Keep it current later with a
periodic `git pull && pip install -e .`.

To reinstall a packaged build from GitHub instead of using a source checkout
(useful for testing a PR branch before it lands), use `pipx`:

```sh
pipx install --force "git+https://github.com/FastJVM/coga.git@<branch-or-tag>"
```

Use `main` after a PR lands, or the PR branch name while testing it.

**2. Set up a project.** One `coga/` per repo — the repo *is* the project.
For a fresh project:

```sh
mkdir ~/work/myproject && cd ~/work/myproject
git init
coga init --user "<your name>"        # creates coga/ and records you as the owner
```

`--user` is required on a fresh init; it stamps who owns the work and seeds a
`coga-build` onboarding ticket.

**3. Bootstrap with `coga build`.**

```sh
coga build
```

`coga build` opens an onboarding chat: it asks one question, talks through what
you're building, writes a product-vision context, and drafts a starter batch of
tickets.

**4. Launch your first ticket.**

```sh
coga status                 # see the drafted tickets
coga launch <slug>          # activate + start work on one
```

**What you end up with:** a `coga/` in your repo, a product-vision context,
a handful of draft tickets, and one of them in progress with an agent.

From there:

- `coga chat` — drop into an agent already oriented in your repo, no ticket.
- `coga create <new-slug>` — create a placeholder ticket you can come back to later.
- `coga ticket` — create a new ticket or edit an existing one and immediately begin authoring.
- `coga ticket <new-slug>` — create a new task and begin ticket authoring.
- `coga ticket <existing-slug>` — begin editing an existing ticket.
- `coga status` — every task and its state.
- `coga --help` — the full command surface.

> **First run vs. ongoing authoring.** `coga build` is the one-time greenfield
> path (onboarding chat → a batch of draft tickets). Day-to-day you author tasks
> one at a time — `coga ticket` for guided authoring, `coga create` for a
> quick stub — see **Task lifecycle** and **`coga ticket`** below.

## Principles

Everything in Coga is a **consequence** of that one idea, and every consequence
has a **receipt** — the feature that proves it.

| Principle | What it means | The feature that proves it |
|---|---|---|
| **1. Hackable** | change anything, directly — no plugin fence | edit any markdown under `coga/` → next `coga launch` uses it; the ~2-min correction loop (edit → commit → fixed) |
| **2. Agents do, humans think** | offload everything mechanizable; humans spend attention on judgment | no webUI — the CLI + files are the whole surface; modes (`interactive`/`auto` vs `script`) and per-step `assignee` route each step to agent, script, or human |
| **3. Obvious** | boring, standard, immediately understandable | the substrate is just markdown + Python + `SKILL.md` (the Claude Code / Codex format); no DB, no DSL |
| **4. Memory via PR** | thinking compounds, human-gated, never opaque | **Dream** reads execution history and opens *proposal PRs* — propose, human disposes; the blackboard region (in `ticket.md`) = working memory, `contexts/` = long-term |
| **5. Yours** | own the substrate, swap the vendors | git-backed markdown, local, no cloud; `claude` ↔ `codex` interchangeable; `SKILL.md` is an open standard |
| **6. Fail loud** | surface every failure | missing context/skill → raise; `coga validate` errors; failures never swallowed; `coga panic` hands back to a human |

The full canon is [`coga/contexts/coga/principles/SKILL.md`](coga/contexts/coga/principles/SKILL.md);
the *why* essay is [`docs/vision.md`](docs/vision.md); the market/strategy
read is [`docs/market-thesis.md`](docs/market-thesis.md). The rest of this
README is the **reference** for the features above — layout, task lifecycle, and
a one-screen entry per CLI command.

## Operating notes

A few things worth knowing once you run more than one project:

- **One `coga/` per repo.** The repo is the project, so run `coga init` in
  each operational repo.

- **Vendored CLI.** Each `coga init` also vendors a self-contained copy of the
  CLI into that repo's `coga/.coga/` (its own venv) — there for bootstrap
  (a fresh clone runs without `pip install`) and as a known-good copy agents can
  target.

- **Your global `coga` runs day-to-day.** Coga deliberately doesn't
  auto-activate the vendored copy per-repo (no PATH munging, no rbenv-style
  re-exec) — with several repos that turns into a "which `.coga/.venv/bin/coga`
  won the PATH race?" mess. The tradeoff: keep your global install reasonably
  current with that periodic `git pull && pip install -e .`.

## External CLI Tools

`requirements.txt` is only for Python packages. Coga also shells out to a few
human-installed command line tools. The canonical list — name, purpose, and
whether it's required — lives in [`src/coga/dependencies.py`](src/coga/dependencies.py),
which is what `coga init` checks; this section mirrors it:

- `git` — **required (checked at `coga init`)**. Coga stores state in the
  current git repo, vendors its CLI via a clone, and uses working-tree diffs as
  the review surface.
- `python` 3.11+ — **required** for the Coga CLI and the vendored `.coga/` copy.
- `gh` — **required (checked at `coga init`)** for GitHub PR workflows such as
  opening PRs and the merged-ticket autoclose sweep. Run `gh auth login` once
  installed.
- `gh` 2.90.0+ with `gh skill` — **optional**, used by Coga-managed skill
  install/update. `gh skill` ships as a public preview in recent `gh`; a fresh
  `coga init` on an older `gh` skips managed skills with a warning rather than
  failing.
- `op` — the [1Password CLI](https://developer.1password.com/docs/cli/get-started/).
  **Optional, checked at launch — not at init.** Needed only when a ticket's
  `secrets:` entry has an `op://vault/item/field` reference: Coga resolves it
  live with `op read` at launch / `coga secret get` (run `op signin` first),
  failing loud naming the reference (never the value) if `op` is missing when an
  `op://` secret is actually needed. Tickets that use only `env:VAR` references
  never invoke it.

So `coga init` **fails loud** (with install hints) if `git` or `gh` is missing,
surfacing a broken setup up front rather than at PR time. `op` is deliberately
left out of that check — forcing the 1Password CLI on everyone would be too
much — and is enforced at the point a ticket actually needs it.

### Git/GitHub auth readiness

Coga does not run its own account system or store a GitHub token — it uses the
standard tools you already have. PR and git-sync paths need:

- A configured git remote. Coga uses the remote named in `[git].remote`
  (default `origin`), not a hardcoded `origin` — if yours is named differently,
  set that key in `coga.toml`.
- Push access to that remote through your normal git setup. Transport is your
  choice:
- For SSH, keep your key loaded in `ssh-agent` (`ssh-add -l`) and authorized on GitHub.
- For HTTPS, let a git credential helper hold valid credentials. Coga never reads `GITHUB_TOKEN` or stores a PAT.
- `gh` installed and authenticated for the same GitHub host as the remote:
  run `gh auth login` once, or `gh auth login --hostname <host>` for GitHub
  Enterprise.

Check all of this before launching work with the opt-in preflight:

```sh
coga validate --check-github
```

It verifies the configured remote exists, probes push access with a
non-mutating `git push --dry-run`, and confirms `gh` is installed and
authenticated for the remote host - turning each failure into a direct setup
hint (set/fix the remote, load your SSH key or credential helper, run
`gh auth login`) instead of a surprise at PR time. Like `--check-slack`, it is
the only thing that makes `coga validate` touch the network; plain
`coga validate`, `coga status`, and `coga show` stay offline and read-only.

Multi-surface companies (e.g. an admin repo + a code repo) run multiple
coga/ side by side — coordinate them by giving each repo a
`[notification.slack].webhook = "env:SLACK_WEBHOOK_URL"` entry whose env var
resolves to the same channel webhook.

## Layout

```
mycompany/
├── .git/
└── coga/
    ├── coga.toml              # shared config (committed)
    ├── coga.local.toml        # per-machine: user, paths, secrets (gitignored)
    ├── context.md              # company context shared by every task
    ├── skills/                 # reusable process knowledge
    ├── contexts/               # reusable domain knowledge
    ├── workflows/              # multi-step recipes
    ├── recurring/              # cron-like recurring task templates
    ├── log.md                  # repo-global append-only audit log (merge=union)
    ├── tasks/                  # one dir per task (named by slug): a single ticket.md (body + blackboard region)
    ├── bootstrap/              # persistent bootstrap tickets (e.g. bootstrap/ticket)
    └── .coga/                 # vendored CLI + venv (gitignored)
        ├── src/coga/          # CLI source
        ├── .venv/              # self-contained venv
        ├── bin/coga           # wrapper symlink
        └── COGA_PIN           # upstream commit SHA this .coga/ was vendored from
```

## Task lifecycle

Coga now separates ticket authoring, queue approval, and launched work:

```text
draft -> active -> in_progress -> done
             \          /
              -> paused
```

- `draft` is unapproved work. Use `coga ticket "<title>"` for the guided
  authoring interview, or `coga create "<title>"` when you only want the raw
  files. You can also run `coga ticket "<new-slug>"` to create a ticket and
  begin authoring, or `coga ticket "<existing-slug>"` to edit a ticket.
- `active` is approved and queued. Humans can still refine active tickets with
  `coga ticket <slug>` before work starts.
- `in_progress` is launched work. `coga launch <slug>` moves an active ticket
  into this state, and `coga bump <slug>` only moves workflow steps from here.
- `paused` preserves the current workflow step while taking the task out of
  execution.
- `done` clears the workflow step and closes the task.

The normal path for a new ticket is:

```sh
# Opens a guided authoring chat — the agent greets first and writes the draft.
coga ticket "Add retry to webhook handler"

# After you finish authoring and exit, start the work:
coga launch add-retry-to-webhook-handler

# The agent works, writes the blackboard, and bumps workflow steps.
coga mark done add-retry-to-webhook-handler   # finish on the final step
```

## Commands

### `coga init [PATH] [--user <name>]`

Create `coga/` inside `PATH` (default: the current dir). A fresh init
requires `--user <name>` (the name tickets and agents refer to you by), and
`PATH` must already be a git repo — coga is git-backed, so init commits the
new create into your repo; run `git init` there first if it isn't one. Copies
templates from the installed Coga package, vendors the CLI into `.coga/`,
creates a self-contained venv, writes a starter `coga.local.toml`, and
auto-stages and commits the new create (push is left to you).

```sh
coga init --user marc             # fresh init in the current dir (PATH defaults to .)
coga init mycompany --user marc   # or: create + init a new mycompany/ dir
```

If `~/.local/bin` is on your `PATH`, init also drops a `~/.local/bin/coga`
symlink so the vendored copy is usable from any cwd in a new shell.

### `coga uninstall [--yes] [--purge]`

Remove the Coga footprint from the current repo: `coga/`, the agent skill
symlinks in `.claude/` and `.codex/`, unmodified Coga orientation guides
(`CLAUDE.md` / `AGENTS.md`), the coga-managed `.gitignore` block, and the
`~/.local/bin/coga` shim if it points back into this repo.

Uninstall prints a removal plan and asks for confirmation; `--yes` skips the
prompt for scripts. Edited `CLAUDE.md` / `AGENTS.md` files are renamed to
`<name>.coga-bak` rather than deleted. By default the global `coga`
package is left installed and the command prints the exact `pipx uninstall
coga` / `pip uninstall coga` commands. Add `--purge` to run the global
uninstall too.

**Batteries and skill discovery.** The installed Coga package carries bundled
skills, contexts, hooks, and bootstrap tickets as package resources. `pip install`
puts those resources in the wheel; `coga init` does not
materialize a repo-local `coga/bootstrap/` mirror. Runtime resolution reads
the package resources directly after checking project-local `coga/skills/`,
`coga/contexts/`, and `coga/workflows/`, so local overrides still win when
they define the same ref.

Init also builds an ignored `coga/.agent-skills/` view that merges
project-local skills with bundled bootstrap skills, then wires that view into
the project-level skill dirs of the agents that follow the `SKILL.md` standard:

- **Claude Code** — symlinked into `.claude/skills/coga/`.
- **Codex** — symlinked into `.codex/skills/coga/`.

That covers our two daily drivers. Other agents (e.g. OpenCode) don't have a
matching project-level skill convention yet — point them at
`coga/.agent-skills/` yourself if you use them. If init finds something
non-directory in the way (e.g. an empty `.codex` sentinel file from an older
setup), it skips that agent and prints what to clear.

### `coga create "<title>"`

Create a new raw `draft` ticket under `coga/tasks/<slug>/` (slug
derived from the title). Does **not** spawn an agent
and does **not** run the guided authoring interview. The new ticket is empty
— title, owner, mode, and timestamp set; workflow, contexts, assignee, and
description still need to be filled in. If the slug already exists, the new
task gets `-2`, `-3`, … appended.

```sh
coga create "Add retry to webhook handler"
coga create "Nightly cleanup" --mode auto
```

### `coga ticket [<title-or-slug>] [--agent <type>]`

Run the guided ticket-authoring skill. This is the normal path when you want
Coga to ask clarifying questions, choose a workflow/context/assignee shape,
and create or edit the ticket before work starts.

```sh
coga ticket                                  # no target — agent greets and asks: new ticket, or edit an existing one?
coga ticket "Add retry to webhook handler"   # new draft, then a guided authoring chat (agent greets first)
coga ticket add-retry                        # edit an existing ticket (any status)
coga ticket add-retry --agent codex          # same, but pick the authoring agent
```

`coga ticket` edits a ticket at any lifecycle status. Editing leaves the
status unchanged; for an `in_progress` (in flight) or `done` (finished)
ticket it prints a heads-up first, since revising those is unusual.

For the standard `claude` and `codex` CLIs, `coga ticket` passes the
composed authoring prompt as system/developer context. That keeps the first
human exchange available for the agent session title, which makes later
resume lists easier to scan. Set `[agents.<type>].discussion` to override
the argv template for another agent.

The usual boot sequence is:

1. `coga ticket "<title>"` — create and fill the draft.
2. Review or edit the ticket.
3. `coga launch <slug>` — approve, mark it `in_progress`, and spawn the
   agent. Launching a `draft` activates it inline, so there is no separate
   `coga mark active` step.

Programmatic callers (e.g. `coga recurring`) call `create_task()` in
`coga.create` directly with the full keyword surface.

### `coga mark <state> <slug> [--message "..."]`

Change a ticket's `status`. Three subcommands:

```sh
coga mark active add-retry         # draft / paused → active.
coga mark paused add-retry         # active / in_progress → paused. Preserves step.
coga mark done   add-retry         # active / in_progress → done. Clears step.
```

`coga mark active` refuses a ticket with no workflow — a workflow-less
ticket has no steps and can't be moved by `coga bump`. A bare-string
`workflow:` ref is frozen into its snapshot on activation. `coga validate`
backs the same rule, erroring on a workflow-less `active`/`in_progress`/`paused`
ticket: a workflow is mandatory everywhere except `draft`. (Recurring and
retire tasks create straight to `active`, but they are *not* workflow-less:
a template that declares no workflow, and every retire task, creates with
the one-step `direct/body` workflow that runs the ticket body directly.)

`coga launch` owns the `active` → `in_progress` start transition, and
activates a `draft` inline as it starts — so `coga mark active` is **not** a
required pre-launch step. Reach for it only to approve or queue a ticket you
don't want to launch yet. `coga bump` no longer marks final-step tickets done.

`--message` piggy-backs an FYI onto the state-transition Slack
broadcast — one post instead of two.

### `coga recurring`

Scan `coga/recurring/` and launch the templates that are due. Coga keeps
**one live task per template**: a generated task is identified by the stable
group-qualified ref `recurring/<name>` (`coga/tasks/recurring/<name>/`),
and if it is already `active` or orphaned `in_progress`, that one is
launched/resumed and no duplicate is created. Only when none is live does
`coga recurring` get-or-create the current run at that stable path and update
the template blackboard's `last_serviced_period` high-water mark. It prints a
scan table, then launches the due ones sequentially: orphaned `in_progress`
resumes first (a dead sweep's frozen run, picked back up from its step), then
fresh launches, each group most-overdue first. `done` and `paused` tasks are
left alone. A stuck `in_progress` run therefore **defers** the next period
until it reaches `done`/`paused` — finish the in-flight run before piling
another on, and it stays visible in `coga status` meanwhile. During a bare
recurring sweep, if a launched task returns still `active`, `in_progress`, or
otherwise unfinished, the sweep stops before launching the next due task.

Only the current period is considered; `coga recurring` never chases missed
periods, so a template runs at most once per period no matter how long since
the last invocation. Dedup after a completed run is deleted comes from
`last_serviced_period >= current period_key` in the template blackboard. The
the repo-global `coga/log.md` stays append-only human history; it is not parsed for dedup.

Recurring creating goes through `create_task()` in `coga.create`
directly with the template's full frontmatter. Recurring tasks are created
straight to `active` — they can't go through the `coga mark active` gate — so
they must carry a workflow to be valid and bumpable: a template that declares
its own keeps it, and a workflow-less one (e.g. Dream) creates with the
one-step `direct/body` workflow, which runs the template body's ordered phases
directly.

Coga does not ship a scheduler entry point in v1. Naming a command
`recurring` does not install or schedule anything — `coga recurring` only
runs when you invoke it directly.

`--interactive` launches every due task in interactive mode for that run,
even ones whose template says `mode: auto` — the debug knob for stepping
through a recurring run in an attended terminal. It threads `coga launch
--mode interactive` through and rewrites no ticket files.

### `coga recurring launch <name>`

Create one named recurring template now, ignoring its schedule, and launch
it. The task ref is `recurring/<name>`, so a manual `launch` and a bare
`coga recurring` run converge on one stable task directory; an orphaned
`in_progress` run is resumed rather than duplicated. This is the on-demand
entry point behind aliases like `coga dream`. `--interactive` runs it in
interactive mode even if the template says `mode: auto` — handy for debugging
one template by hand.

### `coga dream`

Run Coga's generic cleanup pass now. `dream` is an alias for
`coga recurring launch dream`: it creates the `recurring/dream/`
recurring task and launches it. The instantiated task ref is
`recurring/dream`, shared with the scheduled run — running `coga dream`
mid-week reuses that task rather than creating a second one.

### Dream and REM

Dream is Coga's generic ticket cleanup pass for one `coga/`. It ships as a
recurring task template, `coga/recurring/dream/`: a weekly `coga
recurring` run creates and launches it when its schedule is due, and the
`coga dream` alias creates and launches it on demand. A Dream task scans all tickets, runs fixed Coga
housekeeping skills such as `validate-drift` and `retro/done-ticket`, proposes
cleanup, writes results to that run's blackboard, and leaves a human-reviewable
trail. Retro work is batched for done tickets: Dream loads the context/skill
corpus once, processes every eligible done ticket in a single run with a
running knowledge delta, and opens one small PR per coherent theme (at most
five source tickets each) only when durable knowledge changed.

REM is repo/user-specific recurring maintenance. It is opt-in user space: copy
the inert `coga/recurring/_rem/` template, give it a schedule and
workflow, and define the operational checks that matter to that repo. Stale
branch cleanup belongs in a dev maintenance loop, not in Dream's generic ticket
cleanup pass.

### `coga skill`

Manage project-local skills under `coga/skills/` without inventing a second
package manager. GitHub-backed installs and updates delegate to GitHub CLI's
public preview `gh skill` command; Coga adds exact removal, URL-backed
provenance, local-adaptation checks, and a PR-ready update summary for Dream.
Bundled bootstrap skills are package-backed batteries: `coga skill status`
shows them, but `coga skill update --all` skips them and points you at the
package update path (`pip install --upgrade coga`).

```sh
coga skill install owner/repo skill-name
coga skill install-url https://example.com/skill.zip
coga skill install-local ./downloaded-skill
coga skill update skill-name
coga skill update --all
coga skill update --all --pr --verify "coga validate --json"
coga skill remove skill-name
coga skill status --check
```

URL-backed installs are downloaded into a temporary directory, validated for a
`SKILL.md`, installed through `gh skill install --from-local`, then recorded in
`coga/skills/<name>/.coga-source.json` with the original URL and content
digests. URL-backed updates re-fetch that source and skip locally adapted
skills instead of overwriting them. Removal is exact-name only and leaves a
normal git delete for review. To customize a bundled skill, copy it to the same
ref under `coga/skills/`; the local copy shadows the bundled one and becomes
your repo-owned skill.

### `coga launch <target>`

Compose every relevant file for a task — rules, project context, ticket,
attached contexts, current workflow step, frozen skills — into a single
prompt and start the configured agent against it.

`launch` accepts `status: active` or `status: in_progress` directly. A
`draft` / `paused` / `done` ticket is activated inline first — typing `coga
launch` is the readiness signal, so it activates the ticket for you
(re-activating a `done` ticket restarts its workflow at step 1) rather
than refusing. A ticket that can't be activated — no workflow, or an empty
`required` extension field — fails loud with the same remedy `mark active`
gives. Launching an active ticket then marks it `in_progress`; launching an
already-`in_progress` ticket resumes it.

```sh
coga launch add-retry-to-webhook-handler           # full slug
coga launch add-retry                              # any unique prefix works
coga launch add-retry --agent codex                # one-off agent override
coga launch add-retry --mode interactive           # debug: run an auto ticket interactively
coga launch add-retry --prompt-report              # show prompt layer sizes, no launch
coga launch bootstrap/orient                       # stateless launch target → run a skill
coga launch bootstrap/orient --agent codex         # choose a bootstrap agent
```

Tasks are addressed by slug — there is no numeric ID. Pass any unique prefix
(git-short-SHA-style) and ambiguous prefixes error out with the matches listed.

The agent type comes from the ticket's `assignee` (e.g. `claude`), which
names an `[agents.<type>]` block in `coga.toml` directly. Pass
`--agent <type>` to override for this launch only; normal task launches do
not rewrite the ticket's `assignee`. Bootstrap tickets use the same flag for
one-off sessions, so `coga chat --agent codex` can open the orient ticket
with Codex while `coga chat --agent claude` opens it with Claude.

Discussion tickets (`bootstrap/orient`, `bootstrap/ticket`) use built-in
discussion templates for the standard `claude` and `codex` CLIs, or the
selected agent's optional `discussion = "...{prompt}..."` override. In
interactive mode the Coga prompt is context and the first human ask can name
the session. Ordinary task launches keep passing the composed prompt
positionally.

For workflow-bound interactive/auto tasks, one `coga launch` can run multiple
agent-owned steps. After each clean agent exit, Coga re-reads the ticket and
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
compose no agent prompt. **`auto` is temporarily disabled** (until streaming
lands): `coga launch --mode auto` is refused, so today the override is only
useful for running an `auto` ticket `interactive`ly.

`bootstrap/<name>` tickets are stateless re-entry points for skills.
Concurrent launches are safe — they have no status, no log of state changes,
and no lock. They are package-backed resources, not files materialized into
the repo. Don't add custom bootstrap tickets under `coga/bootstrap/`; write
your own launch wrappers elsewhere.

For autonomous runs, an operator can opt an agent into skipping its CLI's
per-command permission/approval prompts with a partial `[agents.<name>]`
table in `coga.local.toml`:

```toml
[agents.claude]
skip_permissions = "auto"
skip_permissions_argv = "--dangerously-skip-permissions"
```

The policy is machine-local by design — committing either key to shared
`coga.toml` fails config load, so a repo can never set a dangerous default
for everyone. It applies only to normal task tickets in effective
`mode: auto`: interactive launches, bootstrap/discussion tickets (`coga chat`,
`coga ticket`), and script tasks keep today's behavior. The argv is one
string (`shlex`-split) inserted between the session-name argv and the auto
argv/prompt — e.g. `codex --dangerously-bypass-approvals-and-sandbox exec
<prompt>` — and supervised chains re-resolve it per step for whichever agent
the step rotated to. `skip_permissions = "auto"` with no configured
`skip_permissions_argv` fails the launch loud before any agent spawns.
Verify the flags against your installed CLIs before enabling.

### `coga status`

Show the live tasks in the repo — `draft`, `active`, `in_progress`, and `paused`.
One line per task. Bootstrap tickets have no status and don't appear. `done`
tickets are hidden by default (the listing ends with a `(N done tasks hidden —
use --all to show)` note); add `--all` (`-a`) to include them.

```sh
coga status
coga status --all
```

### `coga show <slug>`

Print a task's `ticket.md` (body + blackboard region) and its history from the repo-global `coga/log.md` to the
terminal, rendered as markdown. Same prefix matching as `bump`/`launch`.
Bootstrap tickets show only `ticket.md`. For grep/pipe use, read the
files directly — `show` is for human eyes.

```sh
coga show add-retry
coga show bootstrap/orient
```

### `coga bump <slug> [--message "..."] [--to N | --backward]`

Move a workflow-bound task step. By default this advances one step. A human
outside a supervised launch may rewind to an earlier step number with
`--to <step-number>` or one step back with `--backward`. Each move updates
the ticket's `step:` field and appends a log entry. The workflow itself is
frozen into the ticket at create time, so step semantics don't drift mid-task.

`bump` no longer finishes tickets. Bumping past the last step is an
error pointing you at `coga mark done <slug>`. Bumping a ticket
without a workflow is the same error — `mark done` is how you finish
those.

`--message` piggy-backs an FYI onto the state-transition Slack
broadcast — useful for "advanced to (pr) — PR opened: <link>" without
firing a second message.

```sh
coga bump add-retry                         # advance one step
coga bump add-retry --to 1                  # human rewind to step 1
coga bump add-retry --backward              # human rewind one step
coga bump add-retry --message "PR: https://example/142"
coga mark done add-retry                    # finish (on final step, or no workflow)
```

### Auto-closing merged tickets

The `autoclose-merged` recurring sweep walks active/in-progress tickets,
finds ones on their final workflow step (or with no workflow) whose
blackboard `## Dev` section names a merged PR, and auto-bumps them to
`done`. It looks the PR up via `gh pr view` and posts to Slack with a
distinct `auto-bumped on merge of PR #<N>` line.

This daily sweep is the **sole** trigger. There is no manual `automerge`
command and no post-merge git hook, and `coga status` does **not** trigger
it (status stays a strictly read-only view — no network, no state mutation
as a side effect of rendering). Tradeoff: a ticket merged today auto-closes
on the next sweep (≤24h). To close one immediately, run `coga mark done`.

### `coga delete <slug>`

Throw away an abandoned ticket. Removes the whole task directory —
ticket, blackboard, log. Recovery is via `git restore`; the git
history is the audit trail, no Slack broadcast.

Bootstrap tickets aren't user-deletable — they're package-backed batteries
managed by the installed Coga package.

```sh
coga delete add-retry
```

### `coga retire <slug>`

Wrap up a `done` ticket: create a one-shot `retire-<slug>` task whose
body invokes the `retro/done-ticket` skill against the named ticket. `retire`
keeps the single-ticket path; Dream owns batched Retro runs. The retro skill
always deletes the processed source task in a reviewable PR. When it extracts
new durable knowledge, that PR records the `## Retro` marker, edits the
knowledge base, and deletes the source task directory together. When no new
durable knowledge exists, Retro records `result: no-new-durable-knowledge` and
deletes the ticket in a delete-only prune PR. The retire task creates
straight to `active` carrying the one-step `direct/body` workflow (which runs
its body directly) and is launched unless `--no-launch` is passed.

Refuses if the target task is not `status: done`. Use `coga delete`
for an abandoned ticket where retro has nothing to extract. Branch
hygiene (pruning the merged feature branch, sweeping stale branches)
belongs in a Dream worker, not here.

```sh
coga retire add-retry                       # interactive mode (the default)
coga retire add-retry --mode auto           # one-shot autonomous Retro run
coga retire add-retry --no-launch           # create without launching
```

`retire` runs interactively by default so the Retro pass writes live
console output. **`--mode auto` is temporarily disabled** (until streaming
lands) and is currently refused; it is intended to run the pass as a one-shot
headless `claude -p` session whose output is buffered to the task log.

### `coga panic --task <slug> --reason "..."`

The agent gives up. Writes a blocker entry to the ticket and posts a
notification naming the owner so a human (or another agent) can pick it up.
Coga has no task lock to release — the ticket's `status` is the only signal.
Intended for the agent to call when it's truly stuck — not for routine
handoffs.

```sh
coga panic --task add-retry --reason "Auth flow needs prod creds I don't have"
```

### `coga slack --task <slug> --message "..."`

Manual broadcast escape hatch. Posts a short FYI through the configured
notification channel without changing task state — for events that don't
coincide with a `bump`/`panic`/launch transition (e.g. a human announcing they
hand-edited a ticket, or "tests still flaky" mid-step). For FYIs that *do*
fire alongside a state change, prefer `bump --message`.

```sh
coga slack --task add-retry --message "Reassigned to pierre"
```

### Notifications — the team sync point

**Notifications are optional on first run.** A fresh `coga init` selects no
channels (`[notification] channels = []`), so you can `draft`, `launch`, and
`bump` your first task without configuring anything. Turn them on when you
start coordinating with other people.

Slack is the first backend. Once selected, urgent and manual events post to the
channel configured by `[notification.slack].webhook`; outcome events may spool
into the daily digest before posting. Relaunching an already-`in_progress`
ticket does *not* post — that isn't a new state change. Once Slack is selected,
failures are loud: if Slack is unreachable or the webhook isn't set, the
command exits non-zero rather than silently dropping the message — a missed FYI
becomes a stale mental model on the human side, and that's worse than a noisy
retry.

**Opt in (team).** Create a Slack incoming webhook for the channel, select the
Slack channel, keep the shared config pointed at an env var, and export the URL
locally; older or minimal repos add the same block:

```toml
[notification]
channels = ["slack"]

[notification.slack]
webhook = "env:SLACK_WEBHOOK_URL"
```

Then set the env var in your shell rc:

```sh
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
```

Coga reads the canonical webhook from `[notification.slack].webhook`. Legacy
`[slack].webhook` and a bare `SLACK_WEBHOOK_URL` remain deprecated
compatibility fallbacks. The URL is a bearer token — anyone holding it can post
to that channel as the app. Don't commit a literal URL; don't paste it in
tickets or logs. Rotate via the Slack app's webhook page if it ever leaks. For
multi-user setups, commit the safe `env:` reference and have each member export
the same URL locally; `coga.local.toml` may override
`[notification.slack].webhook` for a machine-specific channel.

Run `coga validate --check-slack` to probe the webhook (POSTs an
empty-text payload that Slack rejects without posting to the channel)
so a dead URL surfaces at config time, not at first `bump`. Failures
during runtime posts also append a line (tagged by task ref) to the repo-global `coga/log.md` so
daemon / cron / launched-script runs leave a recoverable trace.

**Temporarily silence a repo that already opted in (solo dev / CI / dry
runs).** To run without posts but keep the Slack channel selected, set in
`coga.local.toml`:

```toml
[notification.slack]
enabled = false
```

With `enabled = false`, every Slack-channel call is suppressed to stderr and
nothing crashes. Treat this as an exit from the sync loop, not a
default — once you're working with another person, turn it back on. (If you
never opted in, you don't need this — a fresh repo posts nothing already.)

### `coga digest`

Post the spooled outcome events — `done` tickets and other merged commits — to
the notification channel, then advance the digest state so the same events
aren't posted twice. This is the batch counterpart to the urgent events that
post immediately: outcome events spool here and go out together (a recurring
`digest` template drives it on a schedule).

```sh
coga digest                    # post the spool; stay silent if it's empty (default)
coga digest --announce-empty   # post a one-line "nothing to report" note instead
```

### `coga telemetry [show | send]`

Anonymous, **opt-out** install telemetry — a once-a-day product-market-fit
signal sent by the `recurring/telemetry/` task. The complete wire payload is
three fields and **nothing else**:

```json
{"instance_id": "<uuid4>", "tickets_total": 12, "last_run": "2026-06-19"}
```

`instance_id` is a random UUID in machine-local state (`$XDG_STATE_HOME/coga`),
`tickets_total` is a bare count of `ticket.md` files, and `last_run` is a coarse
UTC date. No repo, path, cwd, hostname, username, git remote, or ticket
slug/title/content is ever sent. See [docs/telemetry.md](docs/telemetry.md) for
the full design and the GCP relay that drops the client IP.

```sh
coga telemetry show    # print status, instance id, endpoint, and the exact payload — sends nothing
coga telemetry send    # build + send one ping (what the recurring task runs); no-op if disabled
```

**On by default; disable any of three ways** — `[telemetry] enabled = false` in
`coga.toml`/`coga.local.toml`, `COGA_TELEMETRY_DISABLE=1`, or the cross-tool
standard `DO_NOT_TRACK=1`. Any one results in zero network calls; env beats
config.

### `coga validate`

Static diagnostic for the repo and config: it checks task files, frontmatter
schema, workflow refs, and config, and exits non-zero if anything is an error.
Read-only and offline by default — the two `--check-*` probes are the only
options that touch the network.

```sh
coga validate                       # validate the whole repo
coga validate --json                # machine-readable output
coga validate --task add-retry      # validate one task (skips Slack + idle checks)
coga validate --fix                 # conservative safe repairs (add a missing blackboard fence)
coga validate --check-slack         # probe the Slack webhook
coga validate --check-github        # probe git/GitHub auth readiness
```

`--idle-hours` and `--max-blackboard-kb` tune the thresholds for the idle-task
and blackboard-bloat warnings.

### `coga --version`

Print the coga package version, plus — when run from inside a `coga/` —
the upstream commit SHA `.coga/` was vendored from. Useful for "is this
fixed in your copy?" questions.

```sh
$ coga --version
coga 0.2.0
vendored from upstream 61fa3ddb6571 (full: 61fa3ddb6571339237c701424c5675c2c615bdba)
```

### Aliases

Sugar for the often-used commands. The `[aliases]` table in `coga.toml`
maps a one-word name to an expanded `coga` command; positional args after
the alias name forward to the expansion. Default aliases shipped by
`coga init`:

```toml
[aliases]
chat = "launch bootstrap/orient"
dream = "recurring launch dream"
build = "launch coga-build"
# Add per-agent shortcuts once those types are declared in `[agents.*]`:
# claude = "launch bootstrap/orient --agent claude"
# codex = "launch bootstrap/orient --agent codex"
```

`draft`, `ticket`, and `create` are built-in commands, not aliases. Add your
own aliases for bootstrap tickets or skills you launch often; running an alias prints the
expansion to stderr —
`→ coga launch bootstrap/orient` — so the indirection is visible.

Rules, checked at config load — fail loud, not silent:
- Alias names cannot collide with built-in commands.
- The first token of the expansion must be a known built-in.
- Aliases are pass-through only. Arguments and flags after the alias name
  are forwarded to the expanded command.

## Development

Install from source as in [Getting Started](#getting-started), then:

```sh
python -m pytest                    # run the test suite
coga validate --json               # validate the bundled example/ fixture
coga validate --fix                # add a missing blackboard fence only
```

The dogfood coga/ for this very repo lives at `coga/`. Tasks tracked
under `coga/tasks/` are real — they're how we drive work on coga itself.

## License

Coga is open source under AGPL-3.0-or-later. See [`LICENSE`](LICENSE).
