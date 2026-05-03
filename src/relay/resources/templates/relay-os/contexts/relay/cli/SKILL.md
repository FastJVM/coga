---
name: relay/cli
description: The relay CLI surface — what each command does, the flags that matter, and which command to reach for when. Loaded by ticket-less bootstrap shims so an oriented agent doesn't have to discover commands by trial.
---

# Relay CLI

Eight built-in commands plus a config-driven alias mechanism. Everything
else is a flag or subcommand. The model beneath them lives in
`relay/architecture` — read that for primitives and prompt composition.
This context is just the operator's reference.

## relay init [PATH] [--update]

Scaffold `relay-os/` in `PATH` (default `.`), or with `--update` refresh
the relay-managed bits in the current repo.

- `relay init mycompany` — fresh scaffold; refuses if `relay-os/` exists.
- `relay init --update` — pull latest CLI + `_*` templates + `bootstrap/`
  + `skills/bootstrap/` from upstream. Leaves `relay.toml`, `rules.md`,
  user contexts, and user skills untouched.

## relay launch \<target\> [title]

Compose every relevant file (rules + repo context + ticket contexts +
current step's skill + blackboard + ticket body) into one prompt and
start the configured agent. Acquires `task.lock`.

- `relay launch <slug>` — accepts any unique prefix (git-short-SHA-style).
- `relay launch <slug> --force` — break a stale lock.
- `relay launch <slug> --agent <nickname>` — one-off agent override;
  does not rewrite the ticket's `assignee:`.
- `relay launch bootstrap/<name>` — stateless shim; no lock, concurrent
  launches safe. With a title arg, acts as a factory: scaffolds a new
  ticket from the shim's frontmatter and launches on it.

Agent type comes from the ticket's `assignee`, resolved through
`[assignees.<user>]` and `[agents.<type>]` in `relay.toml`.

For workflow-bound interactive/auto tasks, `launch` can continue through
consecutive agent-owned steps in fresh processes. After a clean agent exit,
it re-reads the ticket and continues only if the task is still active, the
step advanced, the new current step has `skill:`, and the concrete assignee
did not change. It stops at human/no-skill steps, assignee handoffs, done or
paused tasks, no-progress exits, and panic/non-zero exits.

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
entry. Bumping past the last step marks the task `done`. The workflow
is frozen into the ticket at create time, so step semantics don't drift
mid-task. On a ticket without a workflow, `bump` marks it `done`
directly — the whole ticket is the only "step".

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

## relay recurring check

Scan `relay-os/recurring/` and scaffold any due tasks. Cron entry point;
called from `relay-os/scripts/cron.sh`.

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
create = "launch bootstrap/ticket"
```

So `relay create "Investigate flaky tests"` runs as
`relay launch bootstrap/ticket "Investigate flaky tests"` (and prints
the expansion to stderr so the indirection is visible).

Rules: alias names can't collide with built-in commands; the first
token of the expansion must be a known built-in. Both checked at
config load — fail loud, not silent. Aliases are positional pass-through
only; they don't accept their own flags.

## Pick which command

- Starting a fresh task → `relay create "<title>"` (alias for
  `launch bootstrap/ticket`).
- Ticket-less chat session → `relay chat` (alias for
  `launch bootstrap/orient`).
- Continuing a known task → `relay launch <slug>`.
- Other bootstrap shim → `relay launch bootstrap/<name>`.
- Advancing a workflow-bound task → `relay bump`.
- Catching up tickets after a teammate merged a PR → `relay automerge`
  (also fires automatically on `git pull` and from `relay status`).
- Triage view → `relay status`.
- Reading a single task without opening the file → `relay show <slug>`.
- Surfacing a non-blocker note tied to a step transition → `relay bump --message`.
- Surfacing a non-blocker note that doesn't fit a transition → `relay slack`.
- Surfacing a blocker → `relay panic`.

There's also `relay validate [--json] [--fix] [--check-slack]`, a static
repo + config diagnostic. `--fix` is deliberately narrow: it creates missing
`blackboard.md` and empty `log.md` files, then reports the remaining issues.
It does not rewrite existing files, freeze workflows, delete locks, or push
git state. Reach for validation when a command is misbehaving or
slack/webhook setup looks broken; Dream's validate-drift worker is the normal
place to apply safe fixes and broadcast a summary during maintenance.

## What this context does NOT cover

- The mental model behind these commands (primitives, planes, prompt
  composition, locking) — see `relay/architecture`.
- Where source lives + how to test changes — see `relay/codebase`.
- Reference contracts (config schemas, frontmatter shapes, error
  tables) — see `docs/spec.md`.
