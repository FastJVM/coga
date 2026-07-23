# Command reference

Every public `coga` command, grouped by what you use it for. This mirrors the
CLI's own `--help` — run `coga <command> --help` for the authoritative, current
detail; the help output is the source of truth if anything here drifts.

`coga --version` prints the Coga package and vendored CLI versions.

Throughout, a `<task>` argument accepts a task's slug or id-slug (and, where
noted, a `bootstrap/<name>` target).

## Setup

### `coga init [PATH]`
Create `coga/` from the package templates. `PATH` is the target directory
(created if missing) — a Git repo root, or any subdirectory inside one (e.g.
`coga init tools/ops` in a monorepo). Defaults to the current directory.

- `--user <name>` — your name, written as `user` in `coga.local.toml`; the name
  tickets and agents refer to you by.

### `coga uninstall`
Remove this repo's Coga footprint (and optionally the global package).

- `-y`, `--yes` — skip the confirmation prompt (for scripts).
- `--purge` — also uninstall the global `coga` package from the machine (affects
  every repo, not just this one). Without it, the command prints the uninstall
  command for you to run.

## Creating work

### `coga create TITLE`
Create a raw **draft** ticket. Prefix the title with a sub-directory path to
place it there: `coga create "marketing/social/relaunch"` nests under
`tasks/marketing/social/`; no slash means top level.

- `--workflow <name>` — attach a workflow (a name under `coga/workflows/`).
  Optional, but a workflow-less draft can't be activated until one is added.

### `coga ticket [TARGET]`
Run the guided authoring interview (the `bootstrap/ticket` skill). `TARGET` is an
existing task slug to edit, or a new title to draft (sub-directory prefix works
like `create`). Omit it to start an empty interview.

- `--agent <nickname>` — agent to run the interview.

### `coga project [SEED]`
Interview about a project, then create an ordered set of draft tickets. `SEED` is
an optional one-line description or a path/link to a vision doc to seed the
interview.

- `--agent <nickname>` — agent to run the planning interview.

## Running work

### `coga launch TASK [ARGS...]`
Compose context and start work on a task. Accepts a task slug, id-slug, or a
`bootstrap/<name>` ticket (resolved local-first: a repo-local
`coga/bootstrap/<name>/ticket.md` overrides the packaged one). Activates a
`draft`/`paused` ticket inline, flips `active → in_progress`, composes the
prompt, and spawns the assignee's agent (or runs a script step directly). A
`done` ticket is refused and left untouched. Trailing `ARGS` follow the target's
execution medium: *script* launches receive `COGA_ARG_1..N` plus `COGA_ARGC`
env vars, while *agent* launches receive the ordered values in an appended
`## Launch arguments` prompt block.

- `--agent <nickname>` — use this agent for the launch instead of the ticket
  assignee.
- `--prompt-report` — print the composed prompt layers and approximate token
  counts, then exit **without** launching.
- `--idle-timeout <seconds>` — tear down a stalled interactive REPL after this
  many seconds with no output or input. Off by default (an attended launch waits
  indefinitely).
- `--max-session <seconds>` — tear down an interactive REPL after this much
  wall-clock even while it's still producing output (the runaway-loop case idle
  timeout misses). Off by default.

### `coga launch bootstrap/browser-automation`
A stateless setup session that turns a concrete browser task into durable,
reviewable work. Describe the target site, desired outcome, and success check
when the agent asks. The bundled `browser/build-automation` skill first checks
whether an API or an ordinary script is a better fit, then picks a workflow
whose handoffs match the requested action and creates and launches a ticket for
the actual task. Launching it creates no standing task of its own, and
installing Coga does not seed a generic browser-automation draft in your task
list.

The two browser skills split by role.
`browser/build-automation` is the orchestration skill: it routes the request and
authors the concrete ticket.
`browser/playwright` is the lower-level execution skill: it drives a real
browser from the terminal, and is attached to a ticket only when the chosen
implementation actually needs one.

### `coga megalaunch [DIR]`
Run the shared megalaunch engine once — a sweep that launches every launchable
task (optionally scoped to `tasks/<DIR>/`).

- `--pick` — choose interactively from an arrow-key list of every launchable task
  (any owner, any non-terminal status, drafts included); the confirmed set is
  prepared, activated, launched, and saved for `--relaunch`. Also available as
  the `coga pick` alias.
- `--relaunch` — re-run the last confirmed picker selection.
- `--max-tasks <n>` — stop after this many launchable tasks have been attempted.
- `--agent <type>` — launch swept tasks with this agent regardless of each
  ticket's assignee (human-assigned tickets still skip).

If a launched task cancels itself, the run summary reports it as `canceled`,
separately from successfully `completed` work.

### `coga recurring [COMMAND]`
Scan recurring task templates under `coga/recurring/` and launch any that are
due. With no subcommand it runs the sweep.

- `--interactive` — launch due agent tasks as a human-stepped run, leaving REPL
  liveness backstops unarmed; ticket files aren't modified.
- `--all <PATH>` — discover every Coga repo below `PATH` and run each repo's due
  sweep once (one scheduler entry can serve several repos). Combines with
  `--force`.
- `--force` — force a full run of **every** template, bypassing the schedule and
  the already-serviced/done/paused filter. A canceled period task is not
  reactivated: its refusal is reported, later templates still run, and the
  sweep exits non-zero after finishing. Delete the canceled task before
  starting a fresh run.
- `--agent <type>` — agent to use for agent-backed recurring tasks in this sweep.

Subcommands:

- **`coga recurring launch NAME`** — create a named recurring template now and
  launch it (the directory under `coga/recurring/`). This is what the `coga
  dream`, `coga skill-update`, and `coga autoclose` aliases wrap.
  - `--interactive` — launch as a human-stepped run, leaving REPL liveness
    backstops unarmed; ticket files aren't modified.
  - `--agent <type>` — agent to use for an agent-backed launch (script tasks
    still run as scripts; the ticket assignee isn't rewritten).
- **`coga recurring list`** — list recurring templates with their schedules, plus
  instantiated tasks.

## Task state

### `coga mark <status> TASK`
Change a ticket's status. Subcommands:

- **`coga mark active TASK`** — set `active` (allowed from `draft` or `paused`).
- **`coga mark paused TASK`** — set `paused` (allowed from `active` or
  `in_progress`).
- **`coga mark done TASK`** — set `done` (allowed from `active` or
  `in_progress`). `--force` finishes a `direct/body` ticket even when it
  committed product code that won't reach the control branch (the code stays
  stranded — the flag just acknowledges that).
- **`coga mark canceled TASK --message "<reason>"`** — intentionally abandon a
  ticket from any non-terminal status, including `draft` and `blocked`. The
  required non-empty reason is appended to the audit log; cancellation clears
  `step:` but keeps body and blackboard history (including blocker text).

The other mark commands accept optional `--message <text>` to piggy-back an FYI
on the state-transition broadcast. `done` and `canceled` are distinct terminal
outcomes; neither appears in the default status view, and canceled tickets
cannot be reactivated.

### `coga bump TASK`
Advance one workflow step. Bumping past the last step is an error — use `coga
mark done` to finish. Tickets without a workflow can't be bumped.

- `--message <text>` — FYI to piggy-back on the transition broadcast (e.g. a PR
  link when bumping into a review step).
- `--to <n>` — **human-only**: rewind to an earlier 1-based step number.
- `--backward` — **human-only**: rewind one step.

The rewind flags are refused for an agent inside a supervised launch — a human
runs them.

### `coga block --task TASK --reason "<ask>"`
Record an unresolved blocker and set the ticket to `blocked`. Both flags are
required; `--reason` must be a specific, answerable question — it's written to
the blackboard, notified to the owner, and ends the session.

### `coga unblock [TASK]`
Resolve open blockers. Moves `blocked → active` (an `in_progress` ticket stays
put), preserving the step.

- `--answer <text>` — the resolution to record for all open asks.
- `--all` — walk every blocked task, show its cause, and prompt for an answer per
  ticket (blank to skip). Omit the `TASK` argument when using `--all`.

## Pull requests and finishing

### `coga open-pr TASK`
Push the branch recorded under `## Dev` on the blackboard and open (or ready) its
PR. A default alias for `coga launch bootstrap/open-pr TASK` — a stateless
script launch of the packaged open-pr command ticket. Run it from the primary
control checkout when `worktree:` is a separate linked checkout; when it records
the primary checkout itself, run it there on the feature branch from the task's
active launch session (the seam matches `COGA_EXPECTED_TASK`, which that outer
launch pins and no nested launch rewrites, to prove the checkout owns the live
ticket). The command reads `branch:`/`worktree:`, commits the pending generated
launch-log append, confirms the recorded checkout is clean and ahead of `main`,
accepts only byte-identical generated task/log overlaps, and rejects a
single-checkout branch whose only commits are generated task/log state. It
pushes the branch by name, opens the PR (or marks an existing draft ready), and
writes `pr: <url>` back under `## Dev`. In the single-checkout layout it syncs
that generated ticket write to the feature branch *and* the control branch, so
the checkout stays clean and both tips keep identical ticket bytes — a retry
stays idempotent instead of tripping the overlap gate on the command's own
record. That sync is reported but not fatal: the PR is already open by then, so
a failed push must not fail the command. The subsequent `requires: pr` bump
republishes its post-transition ticket state, and launch teardown publishes the
trailing usage record, keeping the PR branch mergeable with control and aligned
with the local tip. Independent fallback clones keep using the primary control
checkout for this command.

### `coga resolve-conflicts [PR]`

Rebase stale open-PR branches onto `origin/main`, resolve conflicts with agent
judgment, verify the resulting diff (`python -m pytest` when `src/` or `tests/`
changed), and push only with an explicit force-with-lease. Omit `PR` to sweep
the repository's open PRs; pass one PR number or URL to scope the run. Each PR
is reported as `rebased-pushed`, `up-to-date`, `conflict`, `skipped-dirty`, or
`verify-failed`, followed by a one-line Slack roll-up. Unsafe or ambiguous
resolutions are aborted and never pushed.

This is a default alias for the stateless, agent-backed
`coga launch bootstrap/resolve-conflicts [PR]` command ticket. It intentionally
sees open PRs only; stale branches with no PR are outside its scope.

### `coga retire TASK`
Wrap up a **done** task: prune its Git branch (local and its merged `origin`
counterpart, read from `## Dev`), then launch a `retro/done-ticket` pass. The
retro opens a PR when it extracts durable knowledge (recording a `## Retro`
marker, editing the knowledge base, and deleting the source task in the same PR);
otherwise it direct-deletes the task (recover with `git restore`).

- `--agent <nickname>` — agent to assign (defaults to your first configured
  agent).
- `--no-launch` — create the retire task but don't launch it.

### `coga delete TASK`
Remove a task directory. Recovery is via `git restore`.

## Inspecting

### `coga status [DIR]`
Show tasks in the repo. `DIR` scopes to `tasks/<DIR>/` (nested tasks included).

- `--no-recurse` — list only tasks directly in the directory, not sub-directories.
- `-o`, `--order-by <col>` — sort by `slug`, `status`, `owner`, `assignee`,
  `step`, `updated`, or `created` (default `updated`).
- `-r`, `--reverse` — reverse the sort.
- `-a`, `--all` — include terminal `done` and `canceled` tasks (hidden by
  default). The totals report the two outcomes separately.
- `-d`, `--dirs` — list the plain (non-task) directories under `tasks/` instead
  of the tasks.
- `--blocked` — show only blocked tickets, expanding every open ask.

### `coga show TASK`
Print a task's contents — its ticket (frontmatter + body + blackboard) and, for a
real task, its history reconstructed from the repo-global log. Accepts a
`bootstrap/<name>` target.

### `coga validate`
Validate the repo and config; exits 1 if any errors are found.

- `--json` — emit JSON instead of text.
- `--task <slug>` — validate exactly one task (skips Slack and idle-stuck
  checks).
- `--fix` — apply conservative safe repairs before reporting.
- `--idle-hours <n>` — active-task idle threshold (default 72).
- `--max-blackboard-kb <n>` — blackboard size above which to warn about prompt
  bloat (default 32).
- `--check-slack` — probe the Slack webhook (network call).
- `--check-github` — probe git/`gh` auth readiness (network call).

### `coga usage`
Show agent token usage recorded in `coga/log.md`.

- `--by <field>` — group by `task` (default), `model`, `agent`, or `step`.
- `--since <ts>` / `--until <ts>` — bound by ISO timestamp or `YYYY-MM-DD`.
- `--task <slug>` — one task only.
- `--json` — structured output.

## Notifications

### `coga slack --task TARGET --message "<text>"`
Post an FYI through the configured notification channel(s). `TARGET` may be a
durable task or a stateless `bootstrap/<name>` command ticket. Both flags are
required. A successful bootstrap-target FYI is also that stateless agent
command's completion signal to its launch supervisor; durable-task FYIs do not
advance or end their workflow.

- `--important` — route to the important notification destination (the
  human-action channel) instead of the default.

### `coga digest`
Post Done tickets and other merged commits, then update digest state.

- `--announce-empty` / `--quiet-empty` — on an empty spool, print a one-line note
  or stay silent (default quiet).

## Skills and secrets

### `coga skill <command>`
Install, update, remove, and inspect Coga-managed skills. Subcommands:

- **`install SOURCE [SKILL]`** — install a GitHub-backed skill through `gh skill`
  (`SOURCE` is `owner/repo` or a GitHub URL; optional `SKILL` names a path in the
  repo).
- **`install-local PATH [SKILL]`** — install an already-downloaded local skill
  via `gh skill --from-local`. `PATH` is the local skill directory or bundle;
  optional `SKILL` names a skill path inside it.
- **`install-url URL [SKILL_OR_PATH]`** — download a non-GitHub URL, install
  locally, and preserve Coga metadata. `SKILL_OR_PATH` selects the skill
  directory inside an archive that holds more than one. `--force` overwrites a
  locally adapted URL skill and resets Coga provenance notes.
- **`update [SKILL]`** — update one named skill, or use `--all` for every managed
  skill. `--json` emits a structured summary; `--pr` opens or updates a single
  draft PR with the update summary (`--pr-title <text>` sets its title);
  `--verify <cmd>` runs a verification command before creating the PR
  (repeatable).
- **`remove SKILL`** — remove one exact installed skill path, leaving a
  git-visible delete.
- **`status`** — summarize installed skills and their recorded source metadata.
  `--check` fetches URL-backed sources to report update availability; `--json`
  emits structured output.

### `coga secret get <ref>`
Resolve one `op://…` or `env:VAR` reference and print its value to stdout. Under
`coga secret`.

## Aliases

Thin sugar over common commands, defined in `coga.toml` under `[aliases]`.
Positional args after the alias name forward to the expanded form.

| Alias | Expands to |
| --- | --- |
| `coga chat` | `coga launch bootstrap/orient` |
| `coga claude` | `coga launch bootstrap/orient --agent claude` |
| `coga codex` | `coga launch bootstrap/orient --agent codex` |
| `coga build` | `coga launch coga-build` |
| `coga dream` | `coga recurring launch dream` |
| `coga skill-update` | `coga recurring launch skill-update` |
| `coga autoclose` | `coga recurring launch autoclose-merged` |
| `coga pick` | `coga megalaunch --pick` |
| `coga open-pr` | `coga launch bootstrap/open-pr` |
| `coga resolve-conflicts` | `coga launch bootstrap/resolve-conflicts` |

Aliases are just config — edit or add your own in `coga.toml`.
