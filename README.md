# Relay

Most tools say *don't think* — delegate the work and forget it. Relay's bet is the opposite:

> ## Don't don't think. Think better.

The substrate FastJVM uses to run the company: markdown files in a git repo, a
small CLI on top, no database. It exists to make your judgment *sharper, not
absent* — and to keep the system **yours**.

Relay is an open-source, hackable **programming layer for agent work**: you turn
intent into executable Markdown — tickets that compose context blocks, skills,
workflows, and autonomy rules — and run them on the agents you already use:
Claude Code and Codex today, or any CLI agent (Gemini CLI, Goose, OpenHands,
Devin, your own) in a few lines of config. It is **not another autonomous agent**: it
sits *above* your agents and coordinates them — across **code, research, and
operations alike** (the same substrate runs a refactor, a research experiment,
or a deadline-driven workflow).

You author it by *talking*: `relay chat` drops you into an agent already
oriented in your repo, and `relay ticket` runs a guided interview where the
agent drafts the structured ticket and workflow while you supply the spec and
the judgment. And unlike a flat `CLAUDE.md` — one file that *bloats* as you add
to it, re-read whole on every prompt — Relay's prose is decomposed, scoped,
versioned, and reused: your knowledge **compounds** instead of piling up.

**What "think better" means.** Relay is simple on purpose — Markdown, scripts,
and Git, nothing hidden — because you can only think clearly about what you can
read. You stay in control: the agent acts, you judge what's worth doing and what
was wrong, and you grant autonomy one step at a time. Everything is inspectable,
so you always see *why* an agent did what it did; and your context, skills, and
corrections compound through pull requests you merge, instead of evaporating each
session. It runs on your disk, in your Git, driving the agents you already pay
for. The point isn't a tool that thinks *for* you — it's one that makes your own
thinking sharper, reusable, and legible.

Everything in Relay is a **consequence** of that one idea, and every consequence
has a **receipt** — the feature that proves it. Read the principles first; the
features are downstream.

| Principle | What it means | The feature that proves it |
|---|---|---|
| **1. Hackable** | change anything, directly — no plugin fence | edit any markdown under `relay-os/` → next `relay launch` uses it; the ~2-min correction loop (edit → commit → fixed) |
| **2. Agents do, humans think** | offload everything mechanizable; humans spend attention on judgment | no webUI — the CLI + files are the whole surface; modes (`interactive`/`auto` vs `script`) and per-step `assignee` route each step to agent, script, or human |
| **3. Obvious** | boring, standard, immediately understandable | the substrate is just markdown + Python + `SKILL.md` (the Claude Code / Codex format); no DB, no DSL |
| **4. Memory via PR** | thinking compounds, human-gated, never opaque | **Dream** reads execution history and opens *proposal PRs* — propose, human disposes; `blackboard.md` = working memory, `contexts/` = long-term |
| **5. Yours** | own the substrate, swap the vendors | git-backed markdown, local, no cloud; `claude` ↔ `codex` interchangeable; `SKILL.md` is an open standard |
| **6. Fail loud** | surface every failure | missing context/skill → raise; `relay validate` errors; failures never swallowed; `relay panic` hands back to a human |

The full canon is [`relay-os/contexts/relay/principles/SKILL.md`](relay-os/contexts/relay/principles/SKILL.md);
the *why* essay is [`docs/vision.md`](docs/vision.md); the market/strategy
read is [`docs/market-thesis.md`](docs/market-thesis.md). The rest of this
README is the **reference** for the features above — install, layout, and a
one-screen entry per CLI command.

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
relay-os/ side by side — coordinate them by giving each repo a
`[slack].webhook = "env:SLACK_WEBHOOK_URL"` entry whose env var resolves to
the same channel webhook.

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
  into this state, and `relay bump <slug>` only moves workflow steps from here.
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
relay init --update --all ~/work   # sweep: refresh every relay repo under ~/work
```

Because each repo vendors its own batteries, picking up a new Relay release
means `pip install -U relay-os` once, then `relay init --update` per repo. The
`--all` sweep does that last step in bulk — it requires an explicit scan root,
then scans that path for every `relay-os/relay.toml`, refreshes each (sharing
one upstream clone), reports per-repo results, and exits non-zero if any repo
failed.

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

For the standard `claude` and `codex` CLIs, `relay ticket` passes the
composed authoring prompt as system/developer context. That keeps the first
human exchange available for the agent session title, which makes later
resume lists easier to scan. Set `[agents.<type>].discussion` to override
the argv template for another agent.

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
ticket has no steps and can't be moved by `relay bump`. A bare-string
`workflow:` ref is frozen into its snapshot on activation. `relay validate`
backs the same rule, erroring on a workflow-less `active`/`in_progress`/`paused`
ticket: a workflow is mandatory everywhere except `draft`. (Recurring and
retire tasks scaffold straight to `active`, but they are *not* workflow-less:
a template that declares no workflow, and every retire task, scaffolds with
the one-step `direct/body` workflow that runs the ticket body directly.)

`relay launch` owns the `active` → `in_progress` start transition. `relay
bump` no longer marks final-step tickets done.

`--message` piggy-backs an FYI onto the state-transition Slack
broadcast — one post instead of two.

### `relay recurring`

Scan `relay-os/recurring/` and launch the templates that are due. Relay keeps
**one live task per template**: a generated task is identified by its slug
prefix `recurring-<name>-`, and if one is already `active` or orphaned
`in_progress` — even from a *prior* period — that one is launched/resumed and
no new period is scaffolded. Only when none is live does `relay recurring`
get-or-create the **current period's** task. It prints a scan table, then
launches the due ones sequentially: orphaned `in_progress` resumes first
(a dead sweep's frozen run, picked back up from its step), then fresh
launches, each group most-overdue first. `done` and `paused` tasks are left
alone. A stuck `in_progress` run therefore **defers** the next period until it
reaches `done`/`paused` — finish the in-flight run before piling another on,
and it stays visible in `relay status` meanwhile. During a bare recurring
sweep, if a launched task returns still `active`, `in_progress`, or otherwise
unfinished, the sweep stops before launching the next due task.

Only the current period is considered; `relay recurring` never chases missed
periods, so a template runs at most once per period no matter how long since
the last invocation. The task slug is `recurring-<name>-<period>`
(`recurring-dream-2026-W21`) — the `recurring-` prefix is the identity marker
and the schedule-derived period disambiguates, which makes the get-or-create
idempotent.

Recurring scaffolding goes through `scaffold_task()` in `relay.scaffold`
directly with the template's full frontmatter. Recurring tasks are scaffolded
straight to `active` — they can't go through the `relay mark active` gate — so
they must carry a workflow to be valid and bumpable: a template that declares
its own keeps it, and a workflow-less one (e.g. Dream) scaffolds with the
one-step `direct/body` workflow, which runs the template body's ordered phases
directly.

`scripts/cron.sh` calls `relay recurring` directly. Naming a command
`recurring` does not install or schedule anything — `relay recurring` only
runs when you (or a cron entry you set up yourself) invoke it.

`--interactive` launches every due task in interactive mode for that run,
even ones whose template says `mode: auto` — the debug knob for stepping
through a recurring run in an attended terminal. It threads `relay launch
--mode interactive` through and rewrites no ticket files.

### `relay recurring launch <name>`

Scaffold one named recurring template now, ignoring its schedule, and launch
it. The task slug is `recurring-<name>-<period>`, so a manual `launch` and a
bare `relay recurring` run converge on one task directory per period; an
orphaned `in_progress` run (even a prior period's) is resumed rather than
duplicated. This is the on-demand entry point behind aliases like
`relay dream`. `--interactive` runs it in interactive mode even if the
template says `mode: auto` — handy for debugging one template by hand.

### `relay dream`

Run Relay's generic cleanup pass now. `dream` is an alias for
`relay recurring launch dream`: it scaffolds the `recurring/dream/`
recurring task and launches it. The slug is `recurring-<name>-<period>`
(`recurring-dream-2026-W21`), shared with the scheduled run — running
`relay dream` mid-week reuses that week's task rather than creating a second
one (and resumes a still-running prior week's Dream instead of starting a
new one).

### Dream and REM

Dream is Relay's generic ticket cleanup pass for one `relay-os/`. It ships as a
recurring task template, `relay-os/recurring/dream/`: a weekly `relay
recurring` run scaffolds and launches it when its schedule is due, and the
`relay dream` alias scaffolds and launches it on demand. A Dream task scans all tickets, runs fixed Relay
housekeeping skills such as `validate-drift` and `retro/done-ticket`, proposes
cleanup, writes results to that run's blackboard, and leaves a human-reviewable
trail. Retro work is batched for done tickets: Dream loads the context/skill
corpus once, processes every eligible done ticket in a single run with a
running knowledge delta, and opens one small PR per coherent theme (at most
five source tickets each) only when durable knowledge changed.

REM is repo/user-specific recurring maintenance. It is opt-in user space: copy
the inert `relay-os/recurring/_rem/` template, give it a schedule and
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

`launch` accepts `status: active` or `status: in_progress` directly. A
`draft` / `paused` / `done` ticket is activated inline first — typing `relay
launch` is the readiness signal, so it runs the `relay mark active` step for
you (re-activating a `done` ticket restarts its workflow at step 1) rather
than refusing. A ticket that can't be activated — no workflow, or an empty
`required` extension field — fails loud with the same remedy `mark active`
gives. Launching an active ticket then marks it `in_progress`; launching an
already-`in_progress` ticket resumes it.

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

Discussion shims (`bootstrap/orient`, `bootstrap/ticket`) use built-in
discussion templates for the standard `claude` and `codex` CLIs, or the
selected agent's optional `discussion = "...{prompt}..."` override. In
interactive mode the Relay prompt is context and the first human ask can name
the session. Ordinary task launches keep passing the composed prompt
positionally.

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
compose no agent prompt. **`auto` is temporarily disabled** (until streaming
lands): `relay launch --mode auto` is refused, so today the override is only
useful for running an `auto` ticket `interactive`ly.

`bootstrap/<name>` tickets are stateless re-entry points for skills.
Concurrent launches are safe — they have no status, no log of state changes,
and no lock. The `relay-os/bootstrap/` tree is upstream-managed and refreshed
wholesale by `relay init --update`, so don't add custom shims there — write
your own launch wrappers elsewhere.

For autonomous runs, an operator can opt an agent into skipping its CLI's
per-command permission/approval prompts with a partial `[agents.<name>]`
table in `relay.local.toml`:

```toml
[agents.claude]
skip_permissions = "auto"
skip_permissions_argv = "--dangerously-skip-permissions"
```

The policy is machine-local by design — committing either key to shared
`relay.toml` fails config load, so a repo can never set a dangerous default
for everyone. It applies only to normal task tickets in effective
`mode: auto`: interactive launches, bootstrap/discussion shims (`relay chat`,
`relay ticket`), and script tasks keep today's behavior. The argv is one
string (`shlex`-split) inserted between the session-name argv and the auto
argv/prompt — e.g. `codex --dangerously-bypass-approvals-and-sandbox exec
<prompt>` — and supervised chains re-resolve it per step for whichever agent
the step rotated to. `skip_permissions = "auto"` with no configured
`skip_permissions_argv` fails the launch loud before any agent spawns.
Verify the flags against your installed CLIs before enabling.

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

### `relay bump <slug> [--message "..."] [--to N | --backward]`

Move a workflow-bound task step. By default this advances one step. A human
outside a supervised launch may rewind to an earlier step number with
`--to <step-number>` or one step back with `--backward`. Each move updates
the ticket's `step:` field and appends a log entry. The workflow itself is
frozen into the ticket at create time, so step semantics don't drift mid-task.

`bump` no longer finishes tickets. Bumping past the last step is an
error pointing you at `relay mark done <slug>`. Bumping a ticket
without a workflow is the same error — `mark done` is how you finish
those.

`--message` piggy-backs an FYI onto the state-transition Slack
broadcast — useful for "advanced to (pr) — PR opened: <link>" without
firing a second message.

```sh
relay bump add-retry                         # advance one step
relay bump add-retry --to 1                  # human rewind to step 1
relay bump add-retry --backward              # human rewind one step
relay bump add-retry --message "PR: https://example/142"
relay mark done add-retry                    # finish (on final step, or no workflow)
```

### `relay automerge`

Walk active/in-progress tickets, find ones on their final workflow step (or with no
workflow) whose blackboard `## Dev` section names a merged PR, and
auto-bump them to `done`. Looks the PR up via `gh pr view`. Posts to
Slack with a distinct `auto-bumped on merge of PR #<N>` line.

`relay automerge` is explicit-only — run it by hand to catch the long
tail. It is no longer wired into any implicit trigger: `relay status` does
**not** trigger automerge (it stays a strictly read-only view — no
network, no state mutation as a side effect of rendering), and there is no
post-merge git hook. No `gh`? The explicit command surfaces the error.

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
deletes the ticket in a delete-only prune PR. The retire task scaffolds
straight to `active` carrying the one-step `direct/body` workflow (which runs
its body directly) and is launched unless `--no-launch` is passed.

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
console output. **`--mode auto` is temporarily disabled** (until streaming
lands) and is currently refused; it is intended to run the pass as a one-shot
headless `claude -p` session whose output is buffered to the task log.

### `relay panic --task <slug> --reason "..."`

The agent gives up. Writes a blocker entry to the ticket and posts to the
Slack channel naming the owner so a human (or another agent) can pick it up.
Relay has no task lock to release — the ticket's `status` is the only signal.
Intended for the agent to call when it's truly stuck — not for routine
handoffs.

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
configured by `[slack].webhook`: ticket created, draft → active, active →
in_progress, `bump`, `panic`, `slack`, script-mode failure, and each
recurring scaffold. Relaunching an already-`in_progress` ticket does *not*
post — that isn't a new state change. Failures are loud: if Slack is
unreachable or the webhook isn't set, the command exits non-zero
rather than silently dropping the message — a missed FYI becomes a
stale mental model on the human side, and that's worse than a noisy
retry.

**Setup (solo or team).** Create a Slack incoming webhook for the
channel, keep the shared config pointed at an env var, and export the URL
locally. Fresh `relay.toml` files include this entry; older or minimal repos
should add it:

```toml
[slack]
webhook = "env:SLACK_WEBHOOK_URL"
```

Then set the env var in your shell rc:

```sh
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
```

Relay reads the webhook from `[slack].webhook`, not directly from the bare
process environment. `SLACK_WEBHOOK_URL` only counts when referenced with
`env:` as above. The URL is a bearer token — anyone holding it can post to
that channel as the app. Don't commit a literal URL; don't paste it in tickets
or logs. Rotate via the Slack app's webhook page if it ever leaks. For
multi-user setups, commit the safe `env:` reference and have each member export
the same URL locally; `relay.local.toml` may override `[slack].webhook` for a
machine-specific channel.

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
python -m pytest                    # run the test suite
relay validate --json               # validate the bundled example/ fixture
relay validate --fix                # repair missing blackboard.md/log.md only
```

The dogfood relay-os/ for this very repo lives at `relay-os/`. Tasks tracked
under `relay-os/tasks/` are real — they're how we drive work on relay itself.
