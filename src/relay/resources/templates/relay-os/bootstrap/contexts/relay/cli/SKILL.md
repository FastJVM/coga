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

## relay draft "\<title\>" [--mode interactive|auto|script]

Scaffold a new raw `draft` ticket and post `✨` to Slack. Does not launch an
agent and does not choose workflow, contexts, or assignee beyond defaults. Use
this when you already want bytes on disk and will author the ticket yourself.

`relay create "<title>"` is a compatibility spelling for the same raw draft
operation.

## relay ticket [\<title-or-slug\>] [--agent <nickname>]

Run the guided ticket-authoring interview (`bootstrap/ticket`).

- `relay ticket` — ask for a title, create a draft, and fill it.
- `relay ticket "Add retry to webhook handler"` — create that draft, then
  launch the authoring skill against it.
- `relay ticket add-retry` — edit an existing `draft`, `active`, or `paused`
  ticket. Refuses `in_progress` and `done` tickets by default.

The guided authoring flow chooses workflow/context/assignee with the human,
edits the ticket, and leaves status unchanged. For a new draft, the boot
sequence is: `relay ticket "<title>"` → review/edit → `relay mark active
<slug>` → `relay launch <slug>`.

## relay mark \<state\> \<slug\> [--message "..."]

Change a ticket's `status`. Three subcommands: `mark active`,
`mark paused`, `mark done`. The verb mirrors the frontmatter field, so
the command shape is `<status field value> on disk` = `<mark
subcommand>`.

- `mark active <slug>` — allowed from `draft` or `paused`. Posts `🚀`.
- `mark paused <slug>` — allowed from `active` or `in_progress`. Preserves `step:`.
  Posts `⏸️`.
- `mark done <slug>` — allowed from `active` or `in_progress`. Clears `step:`. Posts
  `🎉`. Use this to finish a workflow on its final step, or to finish
  any ticket without a workflow.

`--message` piggy-backs an FYI onto the Slack broadcast.

`relay launch` owns the `active` → `in_progress` transition. `relay bump` no
longer marks final-step tickets done.

## relay launch \<target\>

Compose every relevant file (rules + repo context + ticket contexts +
current step's skill + blackboard + ticket body) into one prompt and
start the configured agent. Requires `status: active` or `in_progress`:
drafts must be activated via `relay mark active <slug>` first; paused / done
tickets must be marked back to active before they can be launched. Launching
an active ticket marks it `in_progress` before spawning the agent; launching
an already-`in_progress` ticket resumes it without another status flip.
Interactive launches require stdin and stdout to both be terminals; use
`mode: auto` or `mode: script` for non-interactive wrappers and CI.
Script launches inject task metadata env vars including `RELAY_TASK_SLUG`,
`RELAY_TASK_DIR`, and `RELAY_TASK_BLACKBOARD`.

- `relay launch <slug>` — accepts any unique prefix (git-short-SHA-style).
- `relay launch <slug> --agent <nickname>` — one-off agent override;
  does not rewrite the ticket's `assignee:`.
- `relay launch <slug> --prompt-report` — print composed prompt layers,
  exact context/skill refs, bytes, and approximate token counts without
  spawning an agent.
- `relay launch bootstrap/<name>` — stateless shim; concurrent launches
  safe.

Agent type comes from the ticket's `assignee`, resolved through
`[assignees.<user>]` and `[agents.<type>]` in `relay.toml`.

For workflow-bound interactive/auto tasks, `launch` can continue through
consecutive agent-owned steps in fresh processes. After a clean agent exit,
it re-reads the ticket and continues only if the task is still `in_progress`, the
step advanced, the new current step has `skill:`, and the concrete assignee
did not change. It stops at human/no-skill steps, assignee handoffs, done or
paused tasks, no-progress exits, and panic/non-zero exits.

That supervisor loop only exists when a live `relay launch` process is
running around the agent. API/manual sessions still follow the base prompt:
after `relay bump`, inspect the new ticket state and continue any still
`in_progress`, same-assignee next step with a `skill:` directly instead of
stopping after the first bump.

`--prompt-report` is for prompt-scope inspection. Its token counts use a
dependency-light `characters / 4` estimate, so treat them as a prompt-bloat
guardrail and task-to-task comparison, not exact provider billing.

## relay status

List every task in the repo — `draft`, `active`, `in_progress`, `paused`, and `done`.
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

Walk active/in-progress tickets; bump any whose blackboard `## Dev` section names a
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

## relay retire \<slug\> [--mode auto|interactive] [--agent <nickname>] [--no-launch]

Wrap up a `done` ticket: scaffold a one-shot `retire-<slug>` task whose body
invokes the `retro/done-ticket` skill against the named ticket. The retro
skill opens the PR that records the `## Retro` marker, edits the knowledge
base if warranted, and deletes the source task directory in the same PR.
`relay retire` is the launcher.

- `relay retire <slug>` — scaffold and launch in `auto` mode.
- `relay retire <slug> --mode interactive` — supervise the run.
- `relay retire <slug> --no-launch` — scaffold the retire task and print the
  explicit `relay launch <slug>` command.

Refuses if the target task is not `status: done`. Use `relay delete` for an
abandoned ticket where retro has nothing to extract. Branch hygiene (pruning
the merged feature branch, sweeping stale branches) belongs in a Dream
worker, not here.

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

## relay dream [--agent <nickname>] [--no-launch]

Create an ad-hoc Dream cleanup task for the current Relay repo. The task slug
is plain slug allocation (`dream`, `dream-2`, etc.), not a schedule or time
bucket. By default the command immediately launches the new task in `auto`
mode using the current user's first configured agent nickname.

- `relay dream` — create and launch a Dream cleanup run now.
- `relay dream --agent codex1` — assign the run to a specific agent nickname.
- `relay dream --no-launch` — scaffold the run and print the explicit
  `relay launch <slug>` command.

Dream scans current task state, runs the known Relay housekeeping pass, writes
its results to that run's blackboard, and should finish with `relay bump`.
It is not the recurring scheduler and does not use `relay-os/recurring/`.

## relay recurring check

Scan `relay-os/recurring/` and scaffold any due tasks. Cron entry point;
called from `relay-os/scripts/cron.sh`.

REM and other user-defined recurring maintenance loops use this surface.
Dream currently uses `relay dream` directly so manual cleanup runs do not
depend on a schedule-derived slug.

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

- Scaffolding a raw new draft → `relay draft "<title>"`.
- Guided ticket authoring → `relay ticket` or `relay ticket "<title-or-slug>"`.
- Activating a draft to start work → `relay mark active <slug>`.
- Pausing a task → `relay mark paused <slug>`.
- Finishing a task (final step, or no workflow) → `relay mark done <slug>`.
- Ticket-less chat session → `relay chat` (alias for
  `launch bootstrap/orient`).
- Running Relay cleanup now → `relay dream`.
- Starting or resuming agent work → `relay launch <slug>`.
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
