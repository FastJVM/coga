---
name: relay/cli
description: The relay CLI surface — what each command does, the flags that matter, and which command to reach for when. Loaded by ticket-less bootstrap shims so an oriented agent doesn't have to discover commands by trial.
---

# Relay CLI

Built-in commands plus a config-driven alias mechanism. Everything
else is a flag or subcommand. The model beneath them lives in
`relay/architecture` — read that for primitives and prompt composition.
This context is just the operator's reference.

## relay init [PATH] [--update] [--all]

Scaffold `relay-os/` in `PATH` (default `.`), or with `--update` refresh
the relay-managed bits in the current repo.

- `relay init mycompany` — fresh scaffold; refuses if `relay-os/` exists.
- `relay init --update` — refresh the vendored CLI from upstream and
  package-owned `_*` templates, `bootstrap/`, and relay-owned recurring
  batteries (`recurring/dream/`) from the installed Relay package. Leaves
  `relay.toml`, `rules.md`, user contexts, user skills, and repo-specific
  recurring loops (REM) untouched.
- `relay init --update --all [PATH]` — sweep mode. Scan `PATH` (default the
  current dir) for every relay repo below it — directories holding a
  `relay-os/relay.toml` — and run the `--update` refresh in each. One
  upstream clone is shared across all repos; a failure in one repo is
  reported and the sweep continues; the `relay` on PATH is upgraded once at
  the end. Exits non-zero if any repo failed. `--all` without `--update` is
  an error — there is no bulk fresh-scaffold. Search roots are passed on the
  command line, not stored: a multi-repo sweep can't read per-repo config,
  so it stays stateless by design.

`pip install relay-os` installs bundled batteries into the wheel as package
resources. It does not modify a repo. `relay init` and `relay init --update`
materialize those package resources into `relay-os/bootstrap/`, where Relay
resolves them after project-local `relay-os/skills` and `relay-os/contexts`.

## relay draft "\<title\>" [--workflow \<name\>] [--mode interactive|auto|script]

Scaffold a new raw `draft` ticket and post `✨` to Slack. Does not launch
an agent. Step one of the three-step boot: `draft` → edit the body /
workflow / contexts as needed → `relay mark active <slug>` →
`relay launch <slug>`. `relay create` is a compatibility spelling for
`relay draft` — identical behavior, no guided interview.

`--workflow <name>` (path under `relay-os/workflows/`) is optional. A
workflow-less draft is a valid authoring state; the workflow can be added
to the ticket any time before activation. The bumpability gate lives at
activation, not here: `relay mark active` refuses a workflow-less ticket
with an error pointing at `--workflow` or `relay ticket`. For guided
authoring that fills the workflow in for you, use `relay ticket`.

The deliberate separation keeps the moment of authorship distinct from
the moment of starting work. Tickets you mean to draft now and start
later get the same call; nothing fires the agent until you choose to.

## relay ticket [\<title-or-slug\>] [--agent <type>]

Run the guided ticket-authoring interview (`bootstrap/ticket`).

- `relay ticket` — ask for a title, create a draft, and fill it.
- `relay ticket "Add retry to webhook handler"` — create that draft, then
  launch the authoring skill against it.
- `relay ticket add-retry` — edit an existing `draft`, `active`, or `paused`
  ticket. Refuses `in_progress` and `done` tickets.

The guided authoring flow chooses workflow/context/assignee with the human,
edits the ticket, and leaves status unchanged. After the session it
validates the task; a draft handed back with no workflow is rejected at the
terminal rather than later at activation. For a new draft, the boot sequence
is: `relay ticket "<title>"` → review/edit → `relay mark active <slug>` →
`relay launch <slug>`.

For the standard `claude` and `codex` CLIs, `relay ticket` passes the
composed authoring prompt as system/developer context instead of as the first
user message. That lets the first real human exchange set the agent session
title for later resume. Set `[agents.<type>].discussion` to override the argv
template for another agent.

## relay mark \<state\> \<slug\> [--message "..."]

Change a ticket's `status`. Three subcommands: `mark active`,
`mark paused`, `mark done`. The verb mirrors the frontmatter field, so
the command shape is `<status field value> on disk` = `<mark
subcommand>`.

- `mark active <slug>` — allowed from `draft` or `paused`. Posts `🚀`.
  Refuses a workflow-less ticket — set `workflow:` or run `relay ticket`
  first.
- `mark paused <slug>` — allowed from `active` or `in_progress`. Preserves
  `step:`. Posts `⏸️`.
- `mark done <slug>` — allowed from `active` or `in_progress`. Clears
  `step:`. Posts `🎉`. Use this to finish a workflow on its final step, or
  to finish any ticket without a workflow.

`--message` piggy-backs an FYI onto the Slack broadcast.

`relay launch` owns the `active` → `in_progress` start transition. `relay
bump` no longer marks final-step tickets done. The status state machine and
the step state machine are separate.

## relay launch \<target\>

Compose every relevant file (rules + repo context + ticket contexts +
current step's skill + blackboard + ticket body) into one prompt and
start the configured agent. Requires `status: active` or `in_progress` —
drafts must be activated via `relay mark active <slug>` first; paused / done
tickets must be marked back to active before they can be launched. Launching
an `active` ticket marks it `in_progress` (posting `▶️`) before spawning the
agent; launching an already-`in_progress` ticket resumes it without another
status flip. Interactive launches require stdin and stdout to both be
terminals. **`mode: auto` is temporarily disabled** — auto runs (claude
`-p`, codex `exec`) buffer stdout until completion, leaving the operator
with no live console signal. Use `mode: script` for unattended wrappers
and CI until streaming lands. `mode: script` runs the step's skill script
directly. Script launches inject task metadata env vars including
`RELAY_TASK_SLUG`, `RELAY_TASK_DIR`, and `RELAY_TASK_BLACKBOARD`.

- `relay launch <slug>` — accepts any unique prefix (git-short-SHA-style).
- `relay launch <slug> --agent <type>` — one-off agent-type override
  (e.g. `--agent claude`); does not rewrite the ticket's `assignee:`.
- `relay launch <slug> --prompt-report` — print composed prompt layers,
  exact context/skill refs, bytes, and approximate token counts without
  spawning an agent.
- `relay launch <slug> --no-verify` — skip the pre-launch freshness check
  (below). For offline runs, or when you know the ticket is stale and want
  to launch anyway.
- `relay launch <slug> --mode <interactive|auto>` — override the ticket's
  `mode:` for this launch only. The debug knob for stepping through a
  `mode: auto` ticket in an attended terminal. Ephemeral: the ticket file is
  never rewritten, and both the spawned command and the composed
  mode-specific prompt block follow the override. Rejected for `mode: script`
  tickets, which compose no agent prompt. `--mode auto` is rejected while
  the auto-launch policy is in force.
- `relay launch bootstrap/<name>` — stateless shim; concurrent launches
  safe.

Discussion bootstrap shims (`bootstrap/orient`, `bootstrap/ticket`) use
built-in templates for the standard `claude` and `codex` CLIs, or the selected
agent's optional `discussion = "...{prompt}..."` override. In interactive mode
the Relay prompt is context and the first human ask can name the session.
Other task launches keep passing the composed prompt positionally.

Before composing the prompt, `launch` verifies the ticket is still where
disk says it is: for an `active`/`in_progress` ticket on its final step (or
with no workflow) that names a merged PR under `## Dev`, it auto-bumps to
done first. If the bump finished the ticket it prints a line and exits 0
without spawning an agent. A missing or unauthed `gh` is a loud warning
(with a `gh auth login` hint), not a hard failure — the launch continues
unverified. Bootstrap shims, `--prompt-report`, and `--no-verify` skip the
check entirely.

Agent type comes from the ticket's `assignee` directly — it names an
`[agents.<type>]` block in `relay.toml`. Human assignees aren't
launchable; reassign to an agent type first.

For workflow-bound interactive tasks, `launch` can continue through
consecutive agent-owned steps in fresh processes. After a clean agent exit,
it re-reads the ticket and continues only if the task is still
`in_progress`, the step advanced, the new current step has `skill:`, and the
concrete assignee did not change. It stops at human/no-skill steps, assignee
handoffs, done or paused tasks, no-progress exits, and panic/non-zero exits.

That supervisor loop only exists when a live `relay launch` process is
running around the agent. API/manual sessions still follow the base prompt:
after `relay bump`, inspect the new ticket state and continue any still
`in_progress`, same-assignee next step with a `skill:` directly instead of
stopping after the first bump.

`--prompt-report` is for prompt-scope inspection. Its token counts use a
dependency-light `characters / 4` estimate, so treat them as a prompt-bloat
guardrail and task-to-task comparison, not exact provider billing.

## relay status

List every task in the repo — `draft`, `active`, `in_progress`, `paused`,
and `done`. Bootstrap shims have no status and don't appear here. No
filtering flags yet; pipe through `grep` if you want to slice the output.

## relay show \<slug\>

Print a task's `ticket.md`, `blackboard.md`, and `log.md` to the
terminal, rendered as markdown via Rich. Same prefix matching as
`launch`/`bump`. Bootstrap shims show only `ticket.md` (they have no
blackboard or log). For grep/pipe use, read the files directly — `show`
is for human eyes.

## relay bump \<slug\> [--message "..."]

Advance a workflow-bound task one step. Updates `step:`, appends a log
entry. Requires `status: in_progress`. The workflow is frozen into the
ticket at create time, so step semantics don't drift mid-task.

`bump` no longer finishes tickets. Bumping past the last step is an
error pointing you at `relay mark done <slug>`. Bumping a ticket
without a workflow is the same error — those tickets only have one
"step" (the whole ticket), and `mark done` is how you finish them.

`--message` piggy-backs an FYI onto the state-transition Slack
broadcast — one post instead of two. Use it for transition-tied notes
like "PR opened: <link>" or "shipped, watching error rate". For FYIs
that don't fit a transition, reach for `relay slack` instead.

## relay automerge

Walk active / in-progress tickets; bump any whose blackboard `## Dev`
section names a PR that has merged on GitHub. Looks each PR up via
`gh pr view`. Scope: tickets on their final workflow step, or with no
workflow at all. Mid-workflow merges stay alone — those need a human eye.

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
git history is the audit trail, no Slack broadcast. The removal itself
runs through the `bootstrap/delete-task` skill, so the command is a thin
resolver and the same deletion is reachable as a `mode: script` step.

Bootstrap shims aren't user-deletable — they're managed by
`relay init --update`.

## relay retire \<slug\> [--mode interactive] [--agent <type>] [--no-launch]

Wrap up a `done` ticket: scaffold a one-shot `retire-<slug>` task whose body
invokes the `retro/done-ticket` skill against the named ticket. The retro
skill opens the PR that records the `## Retro` marker, edits the knowledge
base if warranted, and deletes the source task directory in the same PR.
The retire task is scaffolded straight to `active`; `relay retire` launches
it unless `--no-launch` is passed.

- `relay retire <slug>` — scaffold and launch in `interactive` mode (auto
  is temporarily disabled).
- `relay retire <slug> --no-launch` — scaffold the retire task (already
  `active`) and print the explicit `relay launch <slug>` command.

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

The subcommands cover three source types: `install <owner/repo-or-url> [skill]`
for GitHub, `install-url <url>` for an arbitrary URL downloaded locally first,
and `install-local <path>` for an already-downloaded directory. `update <skill>`
/ `update --all` (with optional `--pr` to open one draft skill-update PR) and
`remove <skill>` (exact-name only, shown as a normal git delete) round out the
surface.

`relay skill` is a thin wrapper around GitHub CLI's `gh skill`, not a new
package manager. GitHub-backed installs and updates delegate straight to
`gh skill ... --dir relay-os/skills`. Constraints that come with that
substrate:

- `gh skill` is a GitHub CLI public-preview feature and needs `gh` **2.90.0+**.
  When `gh skill` is unavailable Relay fails loud with an actionable upgrade
  hint rather than degrading silently.
- `gh skill` writes source metadata into a GitHub/local install. For an
  arbitrary-URL install that provenance would only remember the temporary
  download path, so Relay writes its own `.relay-source.json` next to the
  installed skill — original URL, selector, timestamp, and content/tree
  digests. URL-backed updates compare that digest and skip a skill that has
  been locally adapted instead of overwriting it.
- `gh skill update --dir` has a known bug that relocates or deletes skills in
  nested custom directories. Keep Relay-managed skills at a flat
  `relay-os/skills/<ns>/<name>/` layout so `--dir` updates stay safe.

`gh` is an external CLI dependency, not a pip package — it belongs in the
README `External CLI Tools` list, never in `requirements.txt`.

## relay panic --task \<slug\> --reason "..."

Agent gives up. Writes a panic marker on the blackboard and posts a
Slack notification naming the task owner. Exits non-zero. Reserved for
genuinely stuck states, not routine handoffs.

## relay slack --task \<slug\> --message "..."

Manual broadcast escape hatch — posts a short FYI to the team Slack
channel without changing task state. Use for events that don't
coincide with a state transition (e.g. announcing a hand-edit to a
ticket, or surfacing a non-blocker mid-step). For FYIs that *do*
coincide with a `bump`, use `bump --message` instead — one post,
not two. Slack is required (see `relay/sync`); commands crash if
`$SLACK_WEBHOOK_URL` is unset and the user hasn't opted out via
`[slack].enabled = false`.

## relay dream

Run Relay's generic cleanup pass now. `dream` is not a built-in command — it
is a default alias for `recurring launch dream`. It scaffolds the
`relay-os/recurring/dream/` recurring task and launches it interactively.

The task slug is the recurring period key (`dream-2026-W21`): running
`relay dream` mid-week reuses that week's task instead of creating a second
one. Dream scans current task state, runs the known Relay housekeeping pass,
writes results to that run's blackboard, and finishes with `relay mark done`.

## relay recurring

Scan `relay-os/recurring/`, then scaffold and launch every task that is due.

For each template (skipping `_`-prefixed files) `relay recurring`
get-or-creates the **current period's** task and launches the ones still
`active`, **sequentially** — most-overdue first, one finishing before the
next starts. It prints a scan table (`ready` vs `overdue Nd`) before
launching. Already-`done`/`in_progress`/`paused` tasks are skipped — never
relaunched.

Current period only: it does not chase missed periods. Running `relay
recurring` once a month for a weekly template produces one run (this
period's), not a backlog. It does not install or manage system cron —
nothing runs unless you invoke it. `relay-os/scripts/cron.sh` is the
optional entry point if you later wire it into a scheduler yourself.

`relay recurring --interactive` launches every due task in interactive mode
for that run, even ones whose template says `mode: auto` — the debug knob
for stepping through a recurring run by hand. It threads `relay launch
--mode interactive` through and rewrites no ticket files.

**`mode: auto` templates are temporarily skipped** with a stderr line and
a Slack scan-error summary. The auto-launch path produces no live console
output, so scheduled runs would sit silently. Templates should use
`mode: script` (or `mode: interactive` if they can run from a TTY) until
streaming lands.

Dream, REM, and other recurring maintenance loops all use this surface.

## relay recurring launch \<name\>

Scaffold one named recurring template now and launch it, ignoring its
schedule. `name` is the directory name under `relay-os/recurring/`. The task slug
still uses the template's schedule-derived period key, so a manual `launch`
and a bare `relay recurring` converge on one task directory per period
(idempotent — a second `launch` in the same period reuses the existing
task). A task already past `active` (a finished or paused run) is left
alone. This is exactly what the `relay dream` alias expands to.
`--interactive` runs it in interactive mode even if the template says
`mode: auto`, for debugging one template by hand.

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
dream = "recurring launch dream"
```

`chat` and `dream` are also registered as built-in default aliases, so they
dispatch even in repos whose `relay.toml` predates the line. `create` is a
built-in command, not an alias (it has its own scaffolding behavior beyond
what a `launch bootstrap/...` expansion would give it).

Rules: alias names can't collide with built-in commands; the first
token of the expansion must be a known built-in. Both checked at
config load — fail loud, not silent. Aliases are positional pass-through
only; they don't accept their own flags.

## Pick which command

- Scaffolding a raw new draft → `relay draft "<title>"`.
- Guided ticket authoring → `relay ticket` or `relay ticket "<title-or-slug>"`.
- Activating a draft to start work → `relay mark active <slug>`.
- Pausing a task → `relay mark paused <slug>`.
- Finishing a task (final step, or no workflow) → `relay mark done <slug>`.
- Ticket-less chat session → `relay chat` (alias for
  `launch bootstrap/orient`).
- Running Relay cleanup now → `relay dream`.
- Launching every due recurring task → `relay recurring`.
- Launching one named recurring task now → `relay recurring launch <name>`.
- Starting or resuming agent work on a task → `relay launch <slug>`.
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

There's also `relay validate [--task <slug>] [--json] [--fix] [--check-slack]`,
a static repo + config diagnostic. By default it scans every task; `--task
<slug>` validates exactly one task directory (files plus strict frontmatter
schema) and is what a human or agent runs after a direct hand-edit to a single
ticket. Relay-owned commands that mutate a task — draft, ticket-authoring exit,
mark, bump, launch-time transitions, recurring/retire scaffolding — run that
same task-scoped check after the write and before reporting success, so
malformed frontmatter fails at the edge of the edit instead of drifting until
launch. `--fix` is deliberately narrow: it creates missing `blackboard.md` and
empty `log.md` files, then reports the remaining issues. It does not rewrite
existing files, freeze workflows, delete locks, or push git state. Reach for
validation when a command is misbehaving or slack/webhook setup looks broken;
Dream's validate-drift skill is the normal place to apply safe fixes and
broadcast a summary during a Dream run.

## What this context does NOT cover

- The mental model behind these commands (primitives, planes, prompt
  composition, locking) — see `relay/architecture`.
- Where source lives + how to test changes — see `relay/codebase`.
- Reference contracts — frontmatter shapes and primitives are in
  `relay/architecture`; config schemas live in `src/relay/config.py`.
