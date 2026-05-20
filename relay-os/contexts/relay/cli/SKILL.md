---
name: relay/cli
description: The relay CLI surface — what each command does, the flags that matter, and which command to reach for when. Loaded by ticket-less bootstrap shims so an oriented agent doesn't have to discover commands by trial.
---

# Relay CLI

Built-in commands plus a config-driven alias mechanism. Everything
else is a flag or subcommand. The model beneath them lives in
`relay/architecture` — read that for primitives and prompt composition.
This context is just the operator's reference.

## relay init [PATH] [--update]

Scaffold `relay-os/` in `PATH` (default `.`), or with `--update` refresh
the relay-managed bits in the current repo.

- `relay init mycompany` — fresh scaffold; refuses if `relay-os/` exists.
- `relay init --update` — refresh the vendored CLI from upstream and
  package-owned `_*` templates + `bootstrap/` from the installed Relay
  package. Leaves `relay.toml`, `rules.md`, user contexts, and user skills
  untouched.

`pip install relay-os` installs bundled batteries into the wheel as package
resources. It does not modify a repo. `relay init` and `relay init --update`
materialize those package resources into `relay-os/bootstrap/`, where Relay
resolves them after project-local `relay-os/skills` and `relay-os/contexts`.

## relay create "\<title\>" --workflow \<name\> [--mode interactive|auto|script]

Scaffold a new `draft` ticket and post `✨` to Slack. Does not launch an
agent. Use this as step one of the three-step boot: `create` → edit the
draft body / workflow / contexts as needed → `relay mark active <slug>`
→ `relay launch <slug>`.

`--workflow <name>` (path under `relay-os/workflows/`) is required.
Workflow-less drafts are rejected with an actionable error pointing at
either the flag or `relay ticket` for guided authoring. The gate is
unconditional and closes the failure mode where an agent scaffolds a
dead-end ticket no `relay bump` can advance.

The deliberate separation keeps the moment of authorship distinct from
the moment of starting work. Tickets you mean to draft now and start
later get the same `create` call; nothing fires the agent until you
choose to.

## relay mark \<state\> \<slug\> [--message "..."]

Change a ticket's `status`. Three subcommands: `mark active`,
`mark paused`, `mark done`. The verb mirrors the frontmatter field, so
the command shape is `<status field value> on disk` = `<mark
subcommand>`.

- `mark active <slug>` — allowed from `draft` or `paused`. Posts `🚀`.
- `mark paused <slug>` — allowed from `active`. Preserves `step:`.
  Posts `⏸️`.
- `mark done <slug>` — allowed from `active`. Clears `step:`. Posts
  `🎉`. Use this to finish a workflow on its final step, or to finish
  any ticket without a workflow.

`--message` piggy-backs an FYI onto the Slack broadcast.

Status transitions live nowhere else. `relay launch` no longer activates
drafts; `relay bump` no longer marks final-step tickets done. The two
state machines are completely separated.

## relay launch \<target\>

Compose every relevant file (rules + repo context + ticket contexts +
current step's skill + blackboard + ticket body) into one prompt and
start the configured agent. Requires `status: active` — drafts must be
activated via `relay mark active <slug>` first; paused / done tickets
must be marked back to active before they can be launched.
Interactive launches require stdin and stdout to both be terminals.
**`mode: auto` is temporarily disabled** — auto runs (claude `-p`, codex
`exec`) buffer stdout until completion, leaving the operator with no
live console signal. Use `mode: script` for unattended wrappers and CI
until streaming lands. Script launches inject task metadata env vars
including `RELAY_TASK_SLUG`, `RELAY_TASK_DIR`, and `RELAY_TASK_BLACKBOARD`.

- `relay launch <slug>` — accepts any unique prefix (git-short-SHA-style).
- `relay launch <slug> --agent <type>` — one-off agent-type override
  (e.g. `--agent claude`); does not rewrite the ticket's `assignee:`.
- `relay launch <slug> --prompt-report` — print composed prompt layers,
  exact context/skill refs, bytes, and approximate token counts without
  spawning an agent.
- `relay launch bootstrap/<name>` — stateless shim; concurrent launches
  safe.

Agent type comes from the ticket's `assignee` directly — it names an
`[agents.<type>]` block in `relay.toml`. Human assignees aren't
launchable; reassign to an agent type first.

For workflow-bound interactive/auto tasks, `launch` can continue through
consecutive agent-owned steps in fresh processes. After a clean agent exit,
it re-reads the ticket and continues only if the task is still active, the
step advanced, the new current step has `skill:`, and the concrete assignee
did not change. It stops at human/no-skill steps, assignee handoffs, done or
paused tasks, no-progress exits, and panic/non-zero exits.

That supervisor loop only exists when a live `relay launch` process is
running around the agent. API/manual sessions still follow the base prompt:
after `relay bump`, inspect the new ticket state and continue any still-active,
same-assignee next step with a `skill:` directly instead of stopping after the
first bump.

`--prompt-report` is for prompt-scope inspection. Its token counts use a
dependency-light `characters / 4` estimate, so treat them as a prompt-bloat
guardrail and task-to-task comparison, not exact provider billing.

## relay status

List every task in the repo — `draft`, `active`, `paused`, and `done`.
Bootstrap shims have no status and don't appear here. No filtering
flags yet; pipe through `grep` if you want to slice the output.

## relay show \<slug\>

Print a task's `ticket.md`, `blackboard.md`, and `log.md` to the
terminal, rendered as markdown via Rich. Same prefix matching as
`launch`/`bump`. Bootstrap shims show only `ticket.md` (they have no
blackboard or log). For grep/pipe use, read the files directly — `show`
is for human eyes.

## relay bump \<slug\> [--message "..."]

Advance a workflow-bound task one step. Updates `step:`, appends a log
entry. The workflow is frozen into the ticket at create time, so step
semantics don't drift mid-task.

`bump` no longer finishes tickets. Bumping past the last step is an
error pointing you at `relay mark done <slug>`. Bumping a ticket
without a workflow is the same error — those tickets only have one
"step" (the whole ticket), and `mark done` is how you finish them.

`--message` piggy-backs an FYI onto the state-transition Slack
broadcast — one post instead of two. Use it for transition-tied notes
like "PR opened: <link>" or "shipped, watching error rate". For FYIs
that don't fit a transition, reach for `relay slack` instead.

## relay automerge

Walk active tickets; bump any whose blackboard `## Dev` section names a
PR that has merged on GitHub. Looks each PR up via `gh pr view`. Scope:
tickets on their final workflow step, or with no workflow at all.
Mid-workflow merges stay alone — those need a human eye.

`relay init` symlinks this into `.git/hooks/post-merge` so a normal
`git pull` after a teammate's merge runs it for you. `relay status`
also calls it opportunistically (quietly) so the long tail still gets
caught even when nobody pulled. The explicit command surfaces `gh`
errors (missing, unauthed); the status path silently skips.

Posts a distinct Slack line — `🎉 *<slug>* "<title>" auto-bumped on
merge of PR #<N>` — so the team can tell auto-bumps apart from manual
ones.

## relay delete \<slug\>

Remove a task directory from the working tree — ticket, blackboard,
log, and the directory itself. Recovery is via `git restore`; the
git history is the audit trail, no Slack broadcast.

Bootstrap shims aren't user-deletable — they're managed by
`relay init --update`.

## relay retire \<slug\> [--mode interactive] [--agent <type>] [--no-launch]

Wrap up a `done` ticket: scaffold a one-shot `retire-<slug>` task whose body
invokes the `retro/done-ticket` skill against the named ticket. The retro
skill opens the PR that records the `## Retro` marker, edits the knowledge
base if warranted, and deletes the source task directory in the same PR.
`relay retire` activates and launches the retire task unless `--no-launch` is
passed.

- `relay retire <slug>` — scaffold and launch in `interactive` mode (auto is
  temporarily disabled).
- `relay retire <slug> --no-launch` — scaffold the retire task and print the
  explicit `relay mark active` / `relay launch` sequence.

Refuses if the target task is not `status: done`. Use `relay delete` for an
abandoned ticket where retro has nothing to extract. Branch hygiene (pruning
the merged feature branch, sweeping stale branches) belongs in a Dream
worker, not here.

## relay skill

Manage project-local skills under `relay-os/skills/`. `relay skill install`
and `relay skill install-*` never write into `relay-os/bootstrap/`; bootstrap
skills are package-backed batteries. `relay skill status` reports bundled
bootstrap skills as `package-backed`, and reports a project-local skill with
the same ref as a `local-override`. `relay skill update --all` updates
project-local managed skills and skips bundled skills with the package update
path: upgrade `relay-os`, then run `relay init --update`.

## relay panic --task \<slug\> --reason "..."

Agent gives up. Writes a blocker to the ticket, posts to Slack naming
the owner, releases the lock. Exits non-zero. Reserved for genuinely
stuck states, not routine handoffs.

## relay slack --task \<slug\> --message "..."

Manual broadcast escape hatch — posts a short FYI to the team Slack
channel without changing task state. Use for events that don't
coincide with a state transition (e.g. announcing a hand-edit to a
ticket, or surfacing a non-blocker mid-step). For FYIs that *do*
coincide with a `bump`, use `bump --message` instead — one post,
not two. Slack is required (see `relay/sync`); commands crash if
`$SLACK_WEBHOOK_URL` is unset and the user hasn't opted out via
`[slack].enabled = false`.

## relay dream [--agent <type>] [--no-launch]

Create an ad-hoc Dream cleanup task for the current Relay repo. The task slug
is plain slug allocation (`dream`, `dream-2`, etc.), not a schedule or time
bucket. By default the command activates and launches the new task in
`interactive` mode using the first-declared `[agents.<type>]` block in
`relay.toml`. (Auto mode is temporarily disabled — see `relay launch` above.)

- `relay dream` — create and launch a Dream cleanup run now.
- `relay dream --agent codex` — assign the run to a specific agent type.
- `relay dream --no-launch` — scaffold the run and print the explicit
  `relay mark active` / `relay launch` sequence.

Dream scans current task state, runs the known Relay housekeeping pass, writes
its results to that run's blackboard, and should finish with `relay mark done`.
It is not the recurring scheduler and does not use `relay-os/recurring/`.

## relay recurring check

Scan `relay-os/recurring/` and scaffold any due tasks. Cron entry point;
called from `relay-os/scripts/cron.sh`.

REM and other user-defined recurring maintenance loops use this surface.
Dream currently uses `relay dream` directly so manual cleanup runs do not
depend on a schedule-derived slug.

**`mode: auto` templates are temporarily skipped** with a stderr/Slack note.
The auto-launch path produces no live console output, so scheduled runs
would sit silently. Templates should use `mode: script` for unattended
runs until streaming lands.

## relay --version

Package version + the upstream commit SHA `.relay/` was vendored from.
Useful for "is this fixed in your copy?" questions.

## Aliases

`[aliases]` in `relay.toml` maps a one-word name to an expanded relay
command. Positional args after the alias name forward to the expansion.
Default aliases shipped by `relay init`:

```toml
[aliases]
chat = "launch bootstrap/orient"
```

`create` is a built-in command, not an alias (it has its own
scaffolding behavior beyond what a `launch bootstrap/...` expansion
would give it).

Rules: alias names can't collide with built-in commands; the first
token of the expansion must be a known built-in. Both checked at
config load — fail loud, not silent. Aliases are positional pass-through
only; they don't accept their own flags.

## Pick which command

- Scaffolding a new draft → `relay create "<title>"`.
- Activating a draft to start work → `relay mark active <slug>`.
- Pausing a task → `relay mark paused <slug>`.
- Finishing a task (final step, or no workflow) → `relay mark done <slug>`.
- Ticket-less chat session → `relay chat` (alias for
  `launch bootstrap/orient`).
- Running Relay cleanup now → `relay dream`.
- Spawning the agent on an active task → `relay launch <slug>`.
- Other bootstrap shim → `relay launch bootstrap/<name>`.
- Advancing a workflow-bound task → `relay bump`.
- Catching up tickets after a teammate merged a PR → `relay automerge`
  (also fires automatically on `git pull` and from `relay status`).
- Triage view → `relay status`.
- Reading a single task without opening the file → `relay show <slug>`.
- Surfacing a non-blocker note tied to a step transition → `relay bump --message`.
- Surfacing a non-blocker note tied to a status transition → `relay mark <state> --message`.
- Surfacing a non-blocker note that doesn't fit a transition → `relay slack`.
- Surfacing a blocker → `relay panic`.
- Throwing away an abandoned ticket → `relay delete <slug>`.
- Wrapping up a finished ticket (retro + source-dir delete via retro PR) →
  `relay retire <slug>`.

There's also `relay validate [--json] [--fix] [--check-slack]`, a static
repo + config diagnostic. `--fix` is deliberately narrow: it creates missing
`blackboard.md` and empty `log.md` files, then reports the remaining issues.
It does not rewrite existing files, freeze workflows, delete locks, or push
git state. Reach for validation when a command is misbehaving or
slack/webhook setup looks broken; Dream's validate-drift skill is the normal
place to apply safe fixes and broadcast a summary during a Dream run.

## What this context does NOT cover

- The mental model behind these commands (primitives, planes, prompt
  composition, locking) — see `relay/architecture`.
- Where source lives + how to test changes — see `relay/codebase`.
- Reference contracts (config schemas, frontmatter shapes, error
  tables) — see `docs/spec.md`.
