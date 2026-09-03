---
name: coga/cli
description: The coga CLI surface — what each command does, the flags that matter, and which command to reach for when. Loaded by ticket-less bootstrap tickets so an oriented agent doesn't have to discover commands by trial.
---

# Coga CLI

Built-in commands plus a config-driven alias mechanism. Everything
else is a flag or subcommand. The model beneath them lives in
`coga/architecture` — read that for primitives and prompt composition.
This context is just the operator's reference.

## coga init [PATH] [--user <name>]

Scaffold `coga/` in `PATH` (default `.`).

- `coga init mycompany` — fresh scaffold; refuses if `coga/` exists.
- `PATH` must be inside a git work tree, but doesn't have to be the git
  root: `coga init tools/ops` inside a monorepo scaffolds a nested
  `tools/ops/coga/` committed into the host repo. A nested coga repo is
  discovered only from inside its subtree (`tools/ops/…`) — commands run
  from the host repo's root won't see it. Nesting a `coga/` inside an
  existing coga repo is refused, as is a target the host repo gitignores
  (init must be able to commit `coga/`).

It copies the package's coga templates, builds the self-contained venv the
vendored CLI runs out of, writes a starter `coga.local.toml`, and commits the
new `coga/`. The venv's coga is pip-installed from the *running*
distribution — `coga==<running version>` from PyPI for wheel installs, the
source checkout itself for editable installs — never from a fresh upstream
clone, so the vendored copy is exactly the CLI that ran init. `COGA_REPO_URL`
overrides the source explicitly (a local checkout path or a git URL).
There is no in-place refresh command: bootstrap tickets, bundled skills,
bundled contexts, and bundled reusable workflows resolve directly from the
installed package, so picking up a new release uses the installer that owns the
CLI: `uv tool upgrade coga` for a uv tool install,
`pip install --upgrade coga` in the CLI's Python environment, or
`git pull && pip install -e .` against a source checkout — not a per-repo
refresh.

`pip install coga` installs bundled batteries into the wheel as package
resources. It does not modify a repo. `coga init`
does not materialize those package resources into `coga/bootstrap/`; Coga
resolves them directly from the installed package after checking project-local
`coga/skills`, the configured contexts directory (`coga/contexts` unless
`[layout] contexts` moves it), and `coga/workflows`.

## coga uninstall [--yes] [--purge]

Remove the Coga footprint from the current repo: `coga/`, the configured
contexts directory when it lives outside `coga/`, the agent skill symlinks in
`.claude/` and `.codex/`, unmodified Coga orientation guides (`CLAUDE.md` /
`AGENTS.md`), the coga-managed `.gitignore` block, and the `~/.local/bin/coga`
shim if it points back into this repo.

It prints the plan and asks for confirmation; `--yes` skips the prompt for
scripted runs. Edited `CLAUDE.md` / `AGENTS.md` files are renamed to
`<name>.coga-bak` rather than deleted. Without `--purge`, the global
`coga` package is left installed and the command prints the exact pipx/pip
uninstall commands. With `--purge`, it also uninstalls the global package; if
the running CLI is this repo's vendored copy, there is no separate global
package to remove.

## coga build

First-run onboarding entry point — the command to tell new users about. `build`
is not a built-in; it is a default alias for `launch coga-build`, so it
launches the packaged `coga-build` ticket through the normal `coga launch`
path (one question → agent-led chat → vision → starter tickets). Because it
dispatches through `coga launch` CLI parsing it requires an already-init'd
repo, and capturing your name is `coga init`'s job, not `build`'s. There is no
separate `coga setup` command — initialize the repo with `coga init`, then run
`coga build` with Claude Code or `coga build --agent codex` with Codex. The
explicit override follows the onboarding workflow's directly consecutive
`assignee: agent` steps, so both steps use Codex without rewriting the seeded
ticket.

## coga create "\<title\>" [--workflow \<name\>]

Scaffold a new raw `draft` ticket and post `✨` when a notification channel
is selected (a fresh repo selects none, so this is silent out of the box).
Does not launch an agent. Step one of the boot path: `coga create` → edit the
body / workflow / contexts as needed → `coga launch <slug>`. Launch activates
a draft inline; use `coga mark active <slug>` only when you want to
approve/queue without launching. This is the raw-create path — no guided
interview.

The positional reads like the task ref it becomes: a `/` separates an optional
sub-directory path from the title leaf, so `coga create "v2/Build the flow"`
lands the ticket at `tasks/v2/build-the-flow` (referenced as
`v2/build-the-flow`), and `marketing/social/relaunch` nests deeper. The leaf
is the human title (slugified for the slug, stored verbatim as the title); the
prefix is a plain sub-directory (the same kind you'd `mkdir`), created if
missing. No slash means a top-level create. Slug uniqueness is per-directory,
so a leaf may repeat across directories. It fails loud on a prefix that would
escape `tasks/` (`..`), name a `_`-prefixed (discovery-skipped) segment, nest
the task inside an existing task directory, or contain a non-slug-like
component (spaces or punctuation beyond `.`/`-`/`_`). That last guard is the
literal-slash-in-title case: because `/` means "sub-directory", a title like
`CI/CD pipeline` or `Populate coga/context.md` is read as a path, and the
prose prefix would land a mangled directory on disk — the error tells you to
drop the slash (create at the top level, then `mv` if needed) or pass a
slug-like prefix.

`--workflow <name>` (path under `coga/workflows/`) is optional *in
draft only*. A workflow-less draft is a valid authoring state; the workflow
can be added to the ticket any time before activation. The bumpability gate
lives at activation, not here: `coga mark active` refuses a workflow-less
ticket with an error pointing at `--workflow` or `coga ticket`, and
`coga validate` reports a workflow-less `active`/`in_progress`/`paused`
ticket as an `active-no-workflow` **error** (a stuck task no `coga bump` can
advance). Once a ticket leaves `draft`, a workflow is mandatory. For guided
authoring that fills the workflow in for you, use `coga ticket`.

The deliberate separation keeps the moment of authorship distinct from
the moment of starting work. Tickets you mean to draft now and start
later get the same call; nothing fires the agent until you choose to.

## coga ticket [\<title-or-slug\>] [--agent <type>]

Run the guided ticket-authoring interview (`bootstrap/ticket`).

- `coga ticket` — ask for a title, create a draft, and fill it.
- `coga ticket "Add retry to webhook handler"` — create that draft, then
  launch the authoring skill against it.
- `coga ticket add-retry` — edit an existing ticket at any status.

The guided authoring flow chooses workflow/context/assignee with the human,
edits the ticket, and preserves any valid lifecycle status. An
out-of-vocabulary status is malformed metadata: the interview confirms the
intended valid status and repairs its correlated workflow/step shape. After
the session it validates the task; a draft handed back with no workflow is
rejected at the terminal rather than later at activation. For a new draft,
the boot sequence is: `coga ticket "<title>"` → review/edit → `coga launch
<slug>`, which activates the draft inline as it starts work.

For the standard `claude` and `codex` CLIs, `coga ticket` passes the
composed authoring prompt as system/developer context instead of as the first
user message. That lets the first real human exchange set the agent session
title for later resume. Set `[agents.<type>].discussion` to override the argv
template for another agent.

## coga mark \<state\> \<slug\> [--message "..."]

Change a ticket's `status`. Four subcommands: `mark active`,
`mark paused`, `mark done`, and `mark canceled`. The verb mirrors the
frontmatter field, so the command shape is `<status field value> on disk` =
`<mark subcommand>`.

- `mark active <slug>` — allowed from `draft` or `paused`. Posts `🚀`.
  Refuses a workflow-less ticket — set `workflow:` or run `coga ticket`
  first.
- `mark paused <slug>` — allowed from `active` or `in_progress`. Preserves
  `step:`. Posts `⏸️`.
- `mark done <slug>` — allowed from `active` or `in_progress`. Clears
  `step:`. Posts `🎉`. Use this to finish a ticket without a workflow or to
  request an explicit status close without walking the remaining steps.
- `mark canceled <slug> --message "<reason>"` — allowed from every
  non-terminal status, including `draft` and `blocked`. Requires a non-empty
  reason, clears `step:`, and posts `🚫`. The reason is appended to the audit
  log; cancellation leaves body and blackboard content untouched, so a blocked
  ticket's open ask remains historical context.

For active, paused, and done, `--message` optionally piggy-backs an FYI onto
the transition. For canceled it is the required audit reason.

`coga launch` owns the `active` → `in_progress` start transition, and will
activate a `draft`/`paused` ticket inline first (launching is the readiness
signal). `blocked` is command-owned by `coga block` / `coga unblock`. `done`
and `canceled` are distinct terminal outcomes, and canceled has no transition
back to active.
On a workflow's final step, `coga bump` delegates to the same `mark_done`
finalizer, so the ordinary step-completion verb also closes the ticket.

## coga launch \<target\>

Resolve the target, then classify it by one fixed filename. A directory-form
ticket carrying `ticket.py` beside `ticket.md` runs that file headlessly first,
without composing a prompt or probing an agent CLI; the script owns its own
lifecycle transition. If the script leaves its step open, or the ticket has no
such sibling, launch composes every relevant file (rules + repo context + ticket
contexts + current step's skill + blackboard + ticket body) into one prompt and
starts the configured agent. Launch accepts `status: active` or `in_progress`
directly; a `draft` / `paused` ticket is activated inline first — typing
`coga launch` is the readiness signal, so it activates the ticket for you
rather than refusing. A `blocked` ticket resumes the same way when the launch
is interactive from a TTY: it reactivates inline (`blocked → active →
in_progress`, `step:` preserved) and the composed prompt gains a
resolve-or-re-block preamble listing the open asks verbatim, making them the
session's first job — the agent records the resolution with
`coga unblock <slug> --answer "..."` (which leaves an `in_progress` ticket's
status and step untouched) or re-blocks with a refined reason. If the resumed
session exits before recording an answer, launch returns the ticket to
`blocked` so blocker queues keep reporting it. TTY-less launches of a blocked
ticket are still refused until
`coga unblock` records the answer (the `coga megalaunch` *sweep* likewise
still skips it as `skipped-unresolved-blocker`; an explicit `--pick` of a
blocked ticket is the human act and resumes it the same interactive way); a
terminal `done` or `canceled` ticket is refused because it is closed. A ticket
that can't be activated — no workflow, or an empty `required` extension field
— still fails loud with the same remedy `mark active` gives. Launching an
`active` ticket then marks it `in_progress` (posting `▶️`) before its first
script or agent phase; launching an already-`in_progress` ticket resumes it
without another status flip. Only an agent phase requires stdin and stdout to
both be terminals. Trailing positional arguments arrive in an ordered
`## Launch arguments` block appended to an agent prompt; `ticket.py` receives
no operands. Repository-independent deterministic commands with stable argv /
stdout / exit contracts remain behind the registered `coga run` recipe surface.

- `coga launch <slug>` — accepts any unique prefix (git-short-SHA-style).
  A top-level task is its bare leaf slug; a nested task is referenced by its
  path under `tasks/` (`marketing/coga-crm`), matching what `coga status`
  prints — the bare leaf alone won't resolve.
- `coga launch <slug> --agent <type>` — explicit one-off agent-type override
  (e.g. `--agent claude`). Within that supervised launch, it follows directly
  consecutive workflow steps declared `assignee: agent`; another role ends the
  continuation. It may assist on a human-owned step, prints that unusual
  handoff in the launch banner, and never rewrites the ticket's `assignee:`;
  human-step assists never propagate. Without the flag, a human handoff is
  still refused.
- `coga launch <slug> --prompt-report` — print composed prompt layers,
  exact context/skill refs, bytes, and approximate token counts without
  spawning an agent. It refuses a `ticket.py` target because the deterministic
  phase runs before composition and prompt reporting never executes ticket code.
- `coga launch bootstrap/<name>` — stateless launch target; concurrent launches
  safe.
- `coga launch bootstrap/browser-automation` — stateless browser-automation
  setup. The bundled `browser/build-automation` orchestration skill checks for
  an API first, creates a concrete ticket with matching operator handoffs, and
  attaches the separate `browser/playwright` runner only when browser execution
  is needed.

Discussion bootstrap tickets (`bootstrap/orient`, `bootstrap/ticket`) use
built-in templates for the standard `claude` and `codex` CLIs, or the selected
agent's optional `discussion = "...{prompt}..."` override. In discussion
launches the Coga prompt is context and the first human ask can name the session.
Other task launches keep passing the composed prompt positionally.

Ordinary `launch` does not probe `gh` for PR state before composing the prompt —
auto-bumping a ticket whose final-step PR has merged is the job of
`coga autoclose` / the `autoclose-merged` recurring sweep, never launch. The
explicit human-step assist is the narrow exception: it verifies its recorded
open PR head before composing because that head authorizes generated writes to
the already-published branch. What that path must prove before every generated
write is in `coga/launch-internals`. Launch also **pre-flights git push access**:
before flipping status or spawning the agent, it runs a non-interactive
`git push --dry-run` against the configured remote (the same push-auth probe
`coga validate --check-github` uses) and refuses the launch if push auth is
broken. Coga drives the whole session through git/gh (branch push,
`gh pr create`, every `coga bump` syncs ticket state), so a dead remote means a
run guaranteed to fail at ship time — fail loud at the door, not after a long
run. The gate self-skips for bootstrap tickets, `[git].enabled = false`, and
non-git checkouts.

All of coga's git subprocesses run non-interactively (`GIT_TERMINAL_PROMPT=0`,
SSH `BatchMode=yes`), so a credential-less remote fails fast instead of hanging
on a prompt. Note the asymmetry: the launch-entry gate is **fatal** (refuse to
start), but a mid-workflow ticket-state sync miss (`coga bump` / `mark`) stays
**non-fatal** — reported to stderr + `log.md`, then continue — because the
on-disk markdown is the source of truth and aborting there would stall the
supervised chain.

Agent type normally comes from the ticket's `assignee` directly — it names an
effective `[agents.<type>]` block after `coga.local.toml` has layered individual
keys and local-only types over `coga.toml`. Human assignees are not launchable
by default. An explicit `--agent <type>` is the on-demand assist escape hatch: it
selects the agent in memory for that launch only, leaves the human assignee on
disk, and identifies the assist in the banner.

For workflow-bound interactive tasks, `launch` can continue through
consecutive agent-owned steps in fresh processes. After a clean agent exit,
it re-reads the ticket and continues only if the task is still
`in_progress`, the step advanced, the new current step has `skill:`, and the
concrete assignee did not change. It stops at human/no-skill steps, assignee
handoffs, terminal tasks, paused or blocked tasks, no-progress exits, and
non-zero exits.

That supervisor loop only exists when a live `coga launch` process is
running around the agent. API/manual sessions do not chain: after `coga bump`,
stop cleanly and let the human relaunch the next step. Only the launch
supervisor re-reads the ticket and starts a fresh step session.

### Releasing an interactive REPL

Interactive agent REPLs terminate through a session-scoped side channel:
`coga bump`, `coga mark done`, `coga mark canceled`, and `coga block` write the
launched task to `$COGA_DONE_SENTINEL`, and the PTY supervisor tears the REPL
down. PTY output is never a completion channel, so reading or printing prompt
text cannot end a session accidentally.

`--prompt-report` is for prompt-scope inspection. Its token counts use a
dependency-light `characters / 4` estimate, so treat them as a prompt-bloat
guardrail and task-to-task comparison, not exact provider billing.

## coga run \<recipe\> [args...]

Invoke one deterministic core recipe through Coga's fixed registry. The
registered names are `autoclose`, `digest`, `blocker-reminders`,
`branch-sweep`, `validate-drift`, `cleanup-orphan-markers`,
`recurring-scan`, `autofix-analyze`, `skill-update`, `open-pr`, and
`delete-task`. Unknown names
exit 2 and print that known set; recipes are not discovered from skills,
config, or entry points.

`coga run autofix-analyze [<run-log.md>] [--dry-run] [--agent <type>]` is the
hand-run half of the recurring autofix loop: it re-reads a recorded sweep (the
most recent under `.coga/recurring-runs/` when no path is given) and tickets
what it finds under `coga/tasks/autofix/`. Every `coga recurring` sweep already
runs the same analysis in-process when it finishes.

Two of them take a task ref as their single argument. `coga run open-pr
<task>` publishes a code ticket's recorded branch and prints the bare PR URL
(`coga open-pr <task>` is the default alias for it). `coga run delete-task
<task>` removes one task from the working tree without syncing the removal —
`coga delete` is the spelling that also lands it on the control branch.

Every token after the recipe name is forwarded as an ordinary Python
`list[str]`, so a value containing spaces stays one element and options such
as `--no-fix` reach the recipe parser unchanged. It preserves inherited
`COGA_TASK_*` metadata when an agent invokes it, passes stdout/stderr through,
and exits with the recipe's integer return code.

## coga status

List the live tasks in the repo — `draft`, `active`, `in_progress`, `blocked`,
and `paused`. Terminal `done` and `canceled` tasks are hidden by default; pass
`--all` (`-a`) to include them, with separate totals for each outcome.
Bootstrap tickets have no status and don't appear here. Pipe through
`grep` for ad-hoc slicing of any column. When terminal tasks are hidden the
output ends with a note that reports the hidden `done` / `canceled` counts and
points at `--all`.

The `updated` column reads `coga/log.md` first — the task's last recorded
workflow activity. The log only knows a task by its ref, so it goes silent for
a task that was moved (refs are path-qualified and log lines are append-only,
so a `mv` orphans the old ones) or one that reached disk without passing
through a logging command. Both cases fall back to the commit that last
touched the task's files, via one read-only `git log` pass. With `[git].enabled
= false` or outside a git checkout there is no fallback and the column shows
`-`. Nothing here mutates state or hits the network — `status` stays a pure
view.

An optional positional argument and the `--no-recurse` flag are two orthogonal
axes — *which* directory, and *how deep*. Tasks are directories (a `ticket.md`
directory at any depth), so the argument is just a directory path in the tree
and there is no Coga-invented vocabulary to learn:

- `coga status <dir>` — only tasks under `tasks/<dir>/`, nested ones
  included, so it reads like `ls -R <dir>`. The path can be nested
  (`coga status marketing` shows the whole sub-tree; `coga status
  marketing/social` narrows to that sub-directory).
- `coga status --no-recurse` — only tasks sitting directly under `tasks/`
  (none in a sub-directory), the way `ls` (without `-R`) lists one level.
  This is the top-level slice.
- `coga status <dir> --no-recurse` — combine the axes: only the tasks
  directly in `tasks/<dir>/`, excluding deeper sub-directories.
- An unknown directory fails loud, listing the directories that do exist,
  rather than printing a silently empty list. A *known* directory that
  currently holds no tasks is not an error — it prints `(no tasks in <dir>)`.

`coga status --dirs` (`-d`) flips the listing to the *directories* themselves
instead of the tasks: it prints every plain (non-task) directory under `tasks/`,
one path per line, and nothing else. It honors both axes — a `<dir>` argument
lists the sub-directories below that directory (the directory itself is the
query, not a result), and `--no-recurse` keeps only the immediate level. An
unknown `<dir>` fails loud the same way; an empty result prints a `(no
directories ...)` note. This is the read-only counterpart to the `mkdir` /
`mv` / `rm` you'd use to manage them.

There is no command to create, rename, or delete one of these directories —
they are plain directories, so you manage them with the shell: `mkdir
coga/tasks/<dir>` to make one (`mkdir -p` to nest), `mv` a task directory
to move it, `rm` to remove it. The filter only reads `tasks/`; like the rest of
`coga status` it mutates nothing and hits no network.

Generated recurring period tasks under `tasks/recurring/` (`recurring/<name>`)
are ordinary tasks and render as normal rows in the main table. The templates
in `coga/recurring/` are not tasks yet, so they get a **`Recurring` footer**
below the table instead — one row per template with its schedule, next fire,
and current-period state (`due — not created`, `ran this period — task
reaped` for a serviced period whose task Dream removed, or the live
instance's status) —
shown whenever the view's scope covers `tasks/recurring/` (the bare view or a
`recurring` directory filter), even when no period task is live. `coga
recurring list` remains the full schedule-aware view.

`coga status --blocked` is the focused human-answer queue. It shows only
blocked work and expands multi-blocker tasks to one row per open ask in a
single table (slug, step, owner, age, reason). The reason is ellipsized to keep
each ask on one line — the full text is one `coga show <slug>` away — and the
`coga unblock <slug> --answer "..."` command shape is a shared footer rather
than a repeated per-row column. Blocked-ness keys off `status: blocked` alone;
leftover asks on a non-blocked ticket are `coga validate`'s drift to catch, not
this view's. It is still read-only: it never resolves blockers, relaunches
work, or probes the network.

The script-backed `recurring/blocker-reminders` task uses the same blocked-task
contract to re-notify owners about unresolved blockers and records a
`## Blocker reminders` watermark on the blocked task after a live reminder
attempt.

## coga show \<slug\>

Print a task's `ticket.md` (frontmatter + body + blackboard region) and its
history from the repo-global `coga/log.md` to the
terminal, rendered as markdown via Rich. Same prefix matching as
`launch`/`bump`. Bootstrap tickets show only `ticket.md` (they have no
blackboard or log). For grep/pipe use, read the files directly — `show`
is for human eyes.

## coga usage [--by \<field\>] [--since \<ts\>] [--until \<ts\>] [--task \<slug\>] [--json]

Roll up agent token usage from the repo-global `coga/log.md`. There is no
separate usage store: when an agent session ends, `coga launch` reads that
CLI's own transcript and appends the result as an ordinary tagged log line
whose message is the record's JSON object. `usage` parses those lines back out
and skips every other line, so the ledger stays the same append-only,
union-merged file the rest of Coga already reads.

The default output is an `Overall:` line plus one row per group, with columns
for sessions, unknown, total, input, cache_create, cache_read, and output
tokens. `unknown` counts sessions whose transcript could not be read or parsed;
they still count as sessions but contribute zero tokens, so a high unknown
count means the totals are a floor rather than a measurement.

- `--by task|model|agent|step` — the group key (default `task`). A record with
  no value for that field groups under `(unknown)`. Any other value exits 2.
- `--since <ts>` / `--until <ts>` — bound the window by ISO timestamp or bare
  `YYYY-MM-DD` date; a bare date covers the whole day at both ends. An
  unparseable value exits 2.
- `--task <slug>` — one task only. This is an exact slug match, not the prefix
  matching `launch`/`show`/`bump` accept.
- `--json` — emit the same rollup as one JSON object instead of the table.

Read-only, like `status`, `show`, and `validate`: it mutates nothing, hits no
network, and does not trigger the end-of-command `coga/` state sweep. It is the
after-the-fact counterpart to `coga launch --prompt-report`, which estimates
the prompt side before a run; `usage` reports what the provider actually
recorded after one.

## coga bump \<slug\> [--message "..."] [--force]

Finish the current step of a workflow-bound task. It updates `step:` and
appends a log entry when another step follows; on the final step it marks the
ticket `done` through the same log, notification, digest, and sync path as
`coga mark done`. Requires `status: in_progress`. The workflow is frozen into
the ticket at create time, so step semantics don't drift mid-task.

Bumping a ticket without a workflow remains an error pointing you at
`coga mark done <slug>`: without a frozen step there is nothing for `bump` to
finish.

`--message` piggy-backs an FYI onto the state-transition Slack
broadcast — one post instead of two. Use it for transition-tied notes
like "PR opened: <link>" or "shipped, watching error rate". For FYIs
that don't fit a transition, reach for `coga slack` instead.

`--force` applies only when the current step is final. It allows a
`direct/body` ticket with committed product code off the control branch to
finish while acknowledging that the code will remain stranded, matching
`coga mark done --force`.

## coga autoclose

Walk active / in-progress tickets; bump any whose blackboard `## Dev`
section names a PR that has merged on GitHub. Looks each PR up via
`gh pr view`. Scope: tickets on their final workflow step, or with no
workflow at all. Mid-workflow merges stay alone — those need a human eye.

There is no `coga automerge` command; it was retired. The behavior lives in
`autoclose.sweep_merged`, reached either as the `coga autoclose` alias
(`recurring launch autoclose-merged`, whose period task runs the template's
`ticket.py`) or directly as the registered `coga run autoclose`.

It is not wired into any implicit trigger: `coga status` does **not** trigger
it (it is a strictly read-only view that never hits the network or mutates
ticket state as a side effect of rendering — principle 6, fail loud, names
`status`/`show`/`validate` as forbidden mutators), and there is no post-merge
git hook. It surfaces `gh` errors (missing, unauthed) loudly.

Posts a distinct Slack line with the ticket title, previous step, and linked
PR (`🎉 *<slug>* "<title>": <prev> → done — <pr-url|PR #<N>> merged`), so the
team can tell auto-bumps apart from manual ones.

## coga delete \<slug\>

Remove a task directory from the working tree — ticket, blackboard,
log, and the directory itself. Recovery is via `git restore`; the
git history is the audit trail, no Slack broadcast. The removal itself lives
in `coga.delete_task`, so the command is a thin resolver plus the sync, and
the same deletion is reachable as `coga run delete-task <slug>`.

Bootstrap tickets aren't user-deletable — they're package-backed batteries
managed by the installed Coga package.

`coga delete <slug> --keep-control-checkout` is the narrow Retro-only form. It
is accepted only from a linked git worktree and still pushes the deletion to the
remote control branch, but it does not fast-forward a different checkout that
has the local control branch checked out. A primary-checkout invocation fails
before deleting anything.

When a restricted sandbox cannot create that linked worktree, Retro may use an
independent clone and ordinary `coga delete` instead. The clone has separate Git
metadata, so the ordinary local-control-ref refresh cannot touch the operator's
checkout.

## coga retire \<slug\> [--agent <type>] [--no-launch]

Wrap up a `done` ticket. First it disposes of the ticket's feature checkout and
branch, read from `## Dev` while the ticket still exists: the recorded linked
worktree is removed only after proving it is a same-repository linked worktree
still holding the recorded branch, no live ticket in any sibling Coga workspace
shares it, no PR for that head remains open, and the branch is landed or still
equals the recorded merged PR head. Tracked, untracked, and ignored local files
all preserve it, as do locked, missing, independent-clone, and currently-running
checkouts. That removal unpins the branch; local cleanup then runs before a
merged remote deletion whose exact head is protected by force-with-lease.
Finally, retire scaffolds a one-shot `retire-<slug>` task whose body invokes the
`retro/done-ticket` skill against the named ticket. The retro
skill opens the PR that records the `## Retro` marker, edits the knowledge base
if warranted, and deletes the source task directory in the same PR. The retire
task is scaffolded straight to `active`; `coga retire` launches it unless
`--no-launch` is passed.

- `coga retire <slug>` — scaffold and launch an agent retire task.
- `coga retire <slug> --no-launch` — scaffold the retire task (already
  `active`) and print the explicit `coga launch <slug>` command.

Refuses if the target task is not `status: done`. Use `coga delete` for an
abandoned ticket where retro has nothing to extract. Checkout hygiene is
best-effort: a cleanup failure is reported and never aborts the retire run.
Sweeping branches with no live ticket remains the separate `branch-sweep`
job's.

## coga skill

Manage project-local skills under `coga/skills/`. `coga skill install`
and `coga skill install-*` never write into `coga/bootstrap/`; bootstrap
skills are package-backed batteries. `coga skill status` reports bundled
bootstrap skills as `package-backed`, and reports a project-local skill with
the same ref as a `local-override`. `coga skill update --all` updates
project-local managed skills and skips bundled skills with the package update
path: upgrade the `coga` package.

The subcommands cover three source types: `install <owner/repo-or-url> [skill]`
for GitHub, `install-url <url>` for an arbitrary URL downloaded locally first,
and `install-local <path>` for an already-downloaded directory. `update <skill>`
/ `update --all` (with optional `--pr` to open one draft skill-update PR) and
`remove <skill>` (exact-name only, shown as a normal git delete) round out the
surface. A local install is supported but intentionally not remotely managed:
`gh skill` records `local-path`, `gh skill update --all` skips it without
GitHub metadata, and Coga's URL updater ignores it. The combined update report
currently emits no per-skill row for that directory. Treat it as pinned and
reinstall from the reviewed local source explicitly; absence from a weekly
report does not prove it was checked.

`coga skill` is a thin wrapper around GitHub CLI's `gh skill`, not a new
package manager. GitHub-backed installs and updates delegate straight to
`gh skill ... --dir coga/skills`. Constraints that come with that
substrate:

- `gh skill` is a GitHub CLI public-preview feature and needs `gh` **2.90.0+**.
  When `gh skill` is unavailable Coga fails loud with an actionable upgrade
  hint rather than degrading silently.
- `gh skill` writes source metadata into a GitHub/local install. For an
  arbitrary-URL install that provenance would only remember the temporary
  download path, so Coga writes its own `.coga-source.json` next to the
  installed skill — original URL, selector, timestamp, content/tree digests,
  and a `local_adaptation_notes` field. The notes field is hand-edited in the
  JSON (no CLI flag, keeping the surface small) and a clean `coga skill
  update` preserves it.
- An arbitrary-URL skill's original frontmatter `name` must be either an Agent
  Skills-compatible name or Coga's intentional extension: slash-separated
  components that each meet the Agent Skills name rules. Coga validates that
  original value before giving `gh skill install` an isolated, slash-free
  staging name, then restores the validated Coga name and canonical path.
  Update and checked-status downloads pass through the same validation.
- **Local adaptation is detected by digest**, comparing the skill's current
  tree digest against the recorded `installed_tree_digest`. `coga skill
  install-url` refuses to overwrite a locally-adapted skill unless `--force`
  is passed (`install-url` is the only install path with a Coga digest to
  compare, so it is the only one with the guard). `--force` is forwarded to
  the underlying `gh skill install`, rewrites `installed_tree_digest` to the
  freshly installed tree, and resets `local_adaptation_notes` to empty — the
  forced overwrite discards the adaptation, so preserving the note would
  mis-describe the new tree. Force applies only when the exact target directory
  contains a `SKILL.md`; a flat ref that collides with an existing namespace
  directory is refused so its nested skills cannot be deleted. The inverse is
  refused too: a namespaced ref cannot be installed beneath an existing flat
  skill, where recursive discovery would hide it from status, updates, and the
  generated agent skill view. `--force` overrides neither namespace collision.
- **`conflict` is its own status.** URL-backed update/status checks fetch
  upstream before classifying: locally adapted with upstream unchanged stays
  `skipped-local-adaptation`; locally adapted **and** upstream changed
  reports `conflict` (carrying both refs/digests in details). `coga skill
  update` and `coga skill status --check` use the same vocabulary for the
  same on-disk state, and the skill-update PR body renders conflicts in a
  dedicated section.
- `gh skill update --dir` has a known bug that relocates or deletes skills in
  nested custom directories. Keep Coga-managed skills at a flat
  `coga/skills/<ns>/<name>/` layout so `--dir` updates stay safe.

`gh` is an external CLI dependency, not a pip package — it belongs in the
README `External CLI Tools` list, never in `requirements.txt`.

## coga block --task \<slug\> --reason "..."

Record a concrete unresolved ask and move the task to `status: blocked`
without changing `step:`. The blocker is appended to the task blackboard,
the transition is logged/synced, the owner is notified live, and the launched
session is released. Use this when an agent needs a human answer before the
current workflow step can continue.

`--reason` is required and should be specific enough for the human to answer
from `coga status --blocked` without reading the whole ticket.

## coga unblock \<slug\> [--answer "..."] | coga unblock --all

Resolve open blockers and move `blocked -> active` while preserving `step:`.
With `--answer`, records the resolution non-interactively. Without it, prompts
in the terminal after showing the open blocker asks. `coga launch <slug>` can
then resume the same workflow step from the files. On an `in_progress` ticket
with open asks — an interactive blocked-launch session recording the
resolution it just discussed — it resolves the asks only, leaving status and
`step:` untouched.

`coga unblock --all` walks **every** blocked task in turn: for each it prints
the task and its open blocker asks (the cause), then prompts for an answer.
A non-empty answer is appended to that task's blackboard and the task is
reactivated (`blocked -> active`); a **blank** answer skips the task, leaving it
blocked. The run ends with an `Unblocked N, skipped M` summary. `--all` is the
clear-the-queue counterpart to naming one slug — it takes no slug and rejects
`--answer` (each task is answered per-ticket at its prompt). After it finishes,
`coga launch <slug>` each reactivated task.

## coga megalaunch [DIR] [--pick] [--relaunch] [--max-tasks N] [--agent <type>]

Attempt launchable work sequentially using the shared megalaunch engine —
the bare sweep covers the configured current user's own tickets; an explicit
`--pick` selection may reach any owner's. Three ways in, one engine:

- **Bare `coga megalaunch`** sweeps every launchable `active` or
  `in_progress` task — `active` work starts, `in_progress` work resumes.
- **`coga megalaunch --pick`** opens an interactive arrow-key picker over
  every non-terminal task — any owner, any status except `done`/`canceled`,
  with **no** launchability pre-filter: every `draft` (offered even when
  not-yet-ready — see the prepare phase below), plus every `active`,
  `in_progress`, `paused`, and `blocked` ticket, including human-assigned,
  stepless, or ask-less ones. Hiding them would let you pick "everything" and
  silently miss real work; a checked row that can't actually launch is not
  dropped but reported by the staged run (`skipped-human-gate` /
  `skipped-unlaunchable`). Nothing starts checked: ↑/↓ (or `j`/`k`)
  move the cursor, Space toggles the row, `a`/`n` check all/none, Enter
  launches the checked set, `q`/Esc quits without launching. The confirmed set
  runs as an explicit selection and is saved for `--relaunch`.
- **`coga megalaunch --relaunch`** replays the last confirmed selection
  (saved machine-locally under the gitignored `.coga/`, since one person's
  queue is not team state). Saved tasks that no longer exist are skipped
  with a warning. For a single task, plain `coga launch <slug>` remains the
  attended one-off.

Both the sweep and the picker cover `in_progress` work: that status means a
session some other process started (or that crashed mid-step), and
megalaunch resumes it exactly like a manual `coga launch <slug>` would.

An explicit selection reaches wider than the sweep and runs in **three
staged phases**, so every human-in-the-loop step happens before the first
working launch:

1. **Prepare** — a picked `draft` is, by definition, not-yet-ready work. When
   the confirmed pick contains any draft, megalaunch asks once — *"N picked
   drafts — run the guided authoring interview to make them ready before
   launching? [Y/n]"* — and if you agree, runs the guided `coga ticket`
   interview on each picked draft, turning it into a launchable shape
   (workflow, contexts, assignee). You end an interview at once if that draft
   is already fine; decline the prompt and picked drafts go straight to
   phase 2 (an unready one is reported, not launched). A pick with no drafts
   is never prompted.
2. **Check** — every picked `draft`/`paused`/`blocked` ticket is validated
   against the prospective `active` view it would get, without writing that
   state. Picks that still can't launch are reported now.
3. **Launch** — each cleared ticket is re-read and reclassified when its own
   turn arrives, then preflighted against its current prospective view. Only
   after those preflights pass is that ticket activated and launched. A
   resumed `blocked` pick returns to `blocked` if its session exits with the
   ask still open; a pick not reached under `--max-tasks` remains unchanged.
   The prospective view and its source ticket revision stay bound together
   through activation and the following `in_progress` write: if the ticket
   changes during preflight, activation sync, or start publication, megalaunch
   refuses that launch rather than overwriting or spawning against the newer
   revision. The final activation snapshot is itself reclassified, including
   open blocker asks parsed from its captured bytes, so resolving the last ask
   in the read/capture window cannot make an ask-less blocked ticket launch.
   With Git sync enabled, both lifecycle writes use that source as an exact
   whole-ticket control compare-and-set and must publish durably before spawn,
   so two checkouts cannot both claim one revision. After
   `mark_in_progress` returns, the live ticket must still equal the exact
   preflighted `in_progress` bytes. An unclaimed megalaunch start or resume
   writes a unique, visible `launch_generation` before spawn; another
   megalaunch refuses a published generation instead of replacing it. The
   final shared
   `before_spawn` seam rereads those local bytes and freshly verifies the whole
   ticket on every effective control destination immediately before the PTY.
   A changed or unverifiable claim refuses the child and retains
   `in_progress`; it never compensates backward to `active`, because an
   ordinary `coga launch` may already be running from the same generation and
   changing the blackboard. Step advancement and lifecycle transitions that
   end or park the session clear the generation; ordinary `coga launch` is the
   explicit recovery path for an abandoned one. Preflight also
   materializes the
   exact prompt, resolved secret environment, and agent used by the spawn, so
   no fallible input derivation is repeated after lifecycle state is written.

Checking a task in the picker is the deliberate human act of selecting it for
an attempted launch, and another owner's ticket launches when reached. A
selected task that still can't launch (terminal, or a draft the interview left
with no workflow to activate) is reported as `skipped-unlaunchable` rather
than silently dropped — you picked it, so its outcome is owed back.

The sweep silently filters out tickets whose `owner` is not
`load_config().current_user` (including owner-less tickets, so other owners'
work is not counted as skip noise), skips human gates and open blockers,
preflights launch requirements, then
runs one eligible step at a time. An agent step is a normal **interactive**
launch — the agent REPL streams live to the console under the PTY watcher, and
the done-sentinel (`coga bump` / `mark done` / `mark canceled` / `block`)
releases it before the sweep moves on — never a headless `claude -p` run, which would buffer all
output until the run ends. The TTY is transport, not an approval gate:
megalaunch composes its own session-conduct layer (`prompt-megalaunch.md`)
telling the agent to announce its plan and continue, while a decision or
capability that genuinely requires the owner must end in `coga block`, not a
conversational "shall I proceed?" or "blocked" reply. A normal final response does not release the queue. The
recurring-style idle-timeout / max-session
backstops are armed so a wedged REPL can't starve the queue; because the REPLs
(and the `--pick` prompt) are interactive, megalaunch requires a TTY and fails
loud without one. A timed-out result names the exact trigger and configured
duration (`idle-timeout ... 900s` or `max-session ...`) instead of collapsing
both limits into one ambiguous message. The run summary distinguishes
launched, completed, canceled, blocked,
skipped-human-gate, skipped-unresolved-blocker,
skipped-unlaunchable, and failed.

Megalaunch is on-demand only — there is no shipped recurring template for it;
you run the sweep when you want the queue drained.

**Drain order.** Tasks are serviced oldest-first — the first `coga/log.md`
line per ref, which is committed content, so the order survives clones where
file mtimes don't. On top of that, a **sub-directory whose tasks are named
`1-schema`, `2-migrate`, `3-cutover` runs in that number order**: numbering is
a plain naming convention on the task directory (`mkdir` / `mv`, the same
verbs that organize `tasks/`) — no flag, no frontmatter field, no config. The
rules that keep it from reshuffling work that didn't ask for it:

- A sub-directory opts in by having **at least one** `<n>-` task. A sub-tree
  with no numbered task keeps its plain per-task age slots, as does every
  top-level task (`tasks/` itself is not a pipeline, so a top-level `1-foo`
  is just a name).
- An opted-in sub-directory runs as one contiguous block, **anchored at its
  oldest task** — a numbered sub-tree runs when its first task would have run,
  never jumping the queue.
- Inside the block, numbered tasks run by number (`02-` == `2-`, and `10-`
  sorts after `9-`), then any unnumbered siblings by age. `2fa-login` is not
  numbered — the digits must be the whole first segment.

`coga status --order-by created` shows the identical order. The `--pick`
list is instead *displayed* like the default `coga status` view — last
updated, newest first, tasks with no recorded activity last — so the picker
and the triage view read as one list; a confirmed selection still launches
in drain order, so a numbered pipeline runs `1-`, `2-`, `3-` regardless of
how its rows were displayed.

`coga validate` warns (`duplicate-task-number`) when two tasks in one
directory claim the same position — the one case where the order you wrote
down is ambiguous and the sort silently invents an answer from creation time.
Gaps and unnumbered siblings are legal and unflagged.

Pass `--agent <type>` to run picked-draft guided authoring interviews and to
launch swept agent-owned tasks (and launchable tasks in the picker's confirmed
set) with that configured agent type. The override is ephemeral and applies to
authoring plus the first launched step—later steps follow the ticket's resolved
assignee, so `other-agent` rotation keeps its meaning. Megalaunch deliberately
keeps its own human gate: unlike an explicit `coga launch --agent` assist, a
human-assigned working step still skips.

An optional positional `DIR` scopes the sweep or the picker to tasks under
`tasks/<DIR>/` (nested ones included), exactly like `coga status <dir>` —
`coga megalaunch marketing` drains only that sub-tree, and an unknown
directory fails loud instead of sweeping nothing silently. It composes with
`--agent` and `--pick`.

## coga slack --task \<target\> --message "..."

Manual broadcast escape hatch — posts a short FYI to the team Slack
channel without changing task state. Use for events that don't
coincide with a state transition (e.g. announcing a hand-edit to a
ticket, surfacing a non-blocker mid-step, or reporting from a stateless
`bootstrap/<name>` command ticket). For FYIs that *do*
coincide with a `bump`, use `bump --message` instead — one post,
not two. Notifications are optional on first run (a fresh repo selects no
channels), so with nothing configured this posts nothing and does not crash.
For a bootstrap target only, a successful FYI also signals that target's
supervised agent session complete; ordinary task FYIs never advance or end a
workflow.
Once Slack is selected it is fail-loud (see `coga/sync`): commands crash if
`$SLACK_WEBHOOK_URL` is unset and the user hasn't opted out via
`[notification.slack].enabled = false`.

## coga digest [--announce-empty | --quiet-empty]

Post one outcome-focused daily digest through the configured notification
channel, then record what it covered. This is the **consumer** half of the
digest pipeline: `done`/`canceled` events and recurring scan errors spool
structured records into `coga/recurring/digest/spool.md` as they happen instead
of posting live, and once a day the `recurring/digest` task fires and runs the
registered `digest` recipe. `coga digest` is the hand-run spelling of that same
pass — reach for it to flush the spool now instead of waiting for the schedule.

One pass reads the unconsumed spool records, fetches the configured control
branch, renders `Done:` / `Canceled:` / recurring-error sections from those
records plus an `Also merged (no ticket):` section from commits landed since
the last recorded high-water mark, posts, then advances both watermarks.
Coga's own state-sync commits and commits whose PR already appears under
`Done:` are filtered out, so the digest reports outcomes rather than churn.

The two watermarks live in different files on purpose. The spool is
*compacted*, not emptied — the consumed prefix is trimmed and the newest record
stays as an anchor, so a concurrent producer append lands in a disjoint merge
hunk of that union-merged file. The git high-water mark is single-writer
consumer state and lives in the digest template's `### Digest State` block in
`coga/recurring/digest/ticket.md`.

Idempotent and safe to re-run: with no outcome records and no new commits it
posts nothing, and a failed post leaves the records and the git high-water mark
intact for the next run. An empty spool alone is not enough to skip — the
control-branch scan still runs.

- `--announce-empty` / `--quiet-empty` — on an empty pass, print a one-line note
  or stay silent (default `--quiet-empty`).

Unlike the read-only views, `digest` writes state and posts, so it does trigger
the end-of-command `coga/` state sweep.

## coga secret get \<ref>

Resolve one secret **reference** on demand and print its value to stdout — a
human-facing query, not something agents call. Secrets are declared inline on
each ticket (there is no `[secrets]` catalog), so `get` takes the reference
directly — `op://vault/item/field` (read live via `op read`) or `env:VAR` — and
resolves it through the same shared path `coga launch` uses (no second
resolver). It prints the value only because you explicitly asked; it is never
logged or posted.

Like launch, this fails loud (non-zero, no value printed) when the reference is
a raw literal (nothing to resolve), an `env:VAR` is unset, or `op` is missing /
not signed in / returns non-zero — error messages name the reference, never the
resolved value.

- `coga secret get op://Private/Stripe/api-key` — read and print that
  1Password field.
- `coga secret get env:STRIPE_KEY` — print the value of `$STRIPE_KEY`.

## coga dream

Run Coga's generic cleanup pass now. `dream` is not a built-in command — it
is a default alias for `recurring launch dream`. It creates the
`coga/recurring/dream/` recurring task and launches it interactively.

The instantiated task ref is `recurring/dream`: the `recurring/` directory
marks it as generated, and the current period is recorded in
the blackboard region of `coga/recurring/dream/ticket.md` as
the log's serviced-period ledger. Running
`coga dream` mid-week reuses that task instead of creating a second one. Dream
scans current task state, runs the known Coga housekeeping pass, writes
results to that run's blackboard, and finishes with `coga mark done`.

## coga recurring [--force] [--agent <type>]

## coga recurring --all <path> [--force] [--agent <type>]

Scan `coga/recurring/`, then create and launch every task that is due.
The Typer command head parses `--interactive` / `--force` / `--agent` and
forwards them as ordinary argv to the registered `recurring-scan` recipe.
There is no package-backed scan ticket or `COGA_RECURRING_*` argument
channel.

`--all <path>` is the multi-repo scheduler entry point. It may run from outside
a Coga repo: it recursively finds `coga/` directories containing `coga.toml`
below the explicit path, skips dependency/tool and `_`-prefixed directory trees,
and stops descending once it finds a workspace. Checkouts rejected by Coga's
intentional config guards (including a missing local `user` or stale-key
migration error) are summarized once as unconfigured, omitted from dispatch,
and do not make the parent fail. Git-enabled configured checkouts are grouped by
the resolved URL of their configured remote plus the Coga workspace's path
within the git checkout; one checkout per remote workspace runs (preferring the
first locally configured checkout already on its control branch), and every
duplicate is named and skipped. Distinct Coga workspaces inside one monorepo
remain separate scheduler targets. Each selected repo runs its ordinary
recurring command in a fresh CLI process, sequentially, with a strict entry
gate: `[git]` must be enabled, the configured control branch must be checked
out, and its pre-scan fetch/rebase must succeed before period state is read or
written. TOML parse errors and operational failures remain loud; one selected
repo's failure does not starve later repos, but the parent exits non-zero after
reporting the aggregate, naming each failed repo in the summary. A gate
refusal (a diverged control checkout) is reported once, distilled to the
conflict lines plus the exact resolve command — no rebase progress spew, no
follow-up refresh/sync attempts re-failing against the same divergence, and no
new local commits deepening it. This keeps schedules, task state, config, Slack, and
git sync owned by each repo while allowing one cron entry such as `coga
recurring --all ~/Code` without racing two checkouts of one remote workspace.

Pass `--agent <type>` to run every agent-backed task in the sweep with that
configured agent type. The override is ephemeral: it does not rewrite ticket
assignees, and a period task carrying `ticket.py` keeps its deterministic
execution path. The scanner delegates every template to `coga launch --agent`,
which classifies each period task from its own directory, so the explicit flag
may also assist a current human-owned step. The command passes the override to
the scanner as ordinary `--agent` argv.

For each template (skipping `_`-prefixed files) `coga recurring` enforces
**one live task per template**: if the generated task at `recurring/<name>` is
already `active` or orphaned `in_progress`, that one is
launched/resumed and no duplicate is created; only when none is live does it
get-or-create the current run at `coga/tasks/recurring/<name>/` and advance
the serviced period in the repo-global log. It launches the due ones
**sequentially** — orphaned `in_progress` resumes first, then fresh launches,
each set most-overdue first, one finishing before the next starts. It prints
a scan table (`→ resume` / `→ launch` / `ready` vs `overdue Nd`) before
launching. A current-period `done` task and every `paused` task stay skipped.
A prior-period `done` task that Dream did not reap is deleted before a fresh
`active` task is created from the current template at the stable path, so stale
instructions and blackboard residue cannot shadow the new firing. A stuck
`in_progress` run defers the next period until it reaches `done` or `paused`.

Current period only: it does not chase missed periods. Running `coga
recurring` once a month for a weekly template produces one run (this
period's), not a backlog. It does not install or manage system cron —
nothing runs unless you invoke it. `coga recurring --all <path>` is the
one entry point to wire into a scheduler if you later want that yourself.
Dedup — including after Dream deletes a completed run — reads the repo-global
`coga/log.md`: a `created|reused <task-ref> for <period>` line tagged
`recurring/<name>` records that the period was serviced, and a period at or
below the newest such record does not fire again. The log is the ledger
precisely because it is append-only and union-merged: unlike a mark in a
template's blackboard, it cannot be erased by another writer rewriting that
region, and it outlives the reaped task.

`coga recurring --interactive` is the human-stepped debug knob for a recurring
run. It requires an attended TTY and leaves the recurring liveness backstops
unarmed; a template carrying `ticket.py` runs that file directly and every
other template launches an agent.

`coga recurring --force` **forces a real, full run of every template**. It is
*not* a sandbox: the only difference from a bare `coga recurring` is that it
ignores the schedule and the status filter that skips already-serviced / done /
paused templates this period. For every template it get-or-creates the real
`recurring/<name>` period task and launches it — even one that already ran this
period (the force runner reactivates a `done`/`paused` ticket). A canceled
period task is not a rerunnable completion:
force reports a controlled refusal, continues through later templates, and
exits non-zero after the sweep; the operator must delete the canceled task
before starting a fresh run.
Everything else is identical to a normal run: real Slack,
real digest-spool drain, real git task-state sync, and the real
serviced-period ledger advance. There are no `-dbg-` scratch dirs, no
slug-based suppression, no orphan reaping, and no fold-back-to-template-log
step. Use it to force this period's work to re-run without waiting for the
schedule.

Agent templates — those with no `ticket.py` beside their `ticket.md` — are
skipped when `coga recurring` has no stdin/stdout TTY, because the agent REPL
cannot be driven. A delegating template (`delegate: bootstrap/<name>`) is in
the same class — its period is serviced by an agent launch the sweep performs
in-process, with the sweep keeping the period task's lifecycle bookkeeping —
so it is skipped headless too, including a materialized orphan from an earlier
attended run; that task stays untouched while later deterministic jobs proceed.
Its bootstrap done sentinel is the only clean completion signal; a natural
REPL exit leaves the period unfinished. The runner's push preflight,
compare-and-set period publication, and lease/probe rules are in
`coga/launch-internals`. Templates intended for cron or other unattended
schedulers should carry that deterministic half. Whether a period is
deterministic is never declared: the `ticket.py` file's presence is the whole
signal. `delegate:` declares something
else — which bootstrap target an agent period hands its work to, which no
file's presence can express. Creation freezes that target into the period
ticket; the sweep, `coga recurring launch <name>`, and direct
`coga launch recurring/<name>` retries all route from the snapshot rather than
current template frontmatter, and the sweep rereads it after reconciliation
instead of trusting cached scan dispatch. Sweeps and named launches perform
full admission at their outer boundary and launch each period through an
internal seam; the generation and refusal rules are in `coga/launch-internals`.
The direct spelling has no outer admission: it requires verified control
catch-up before resolving even a locally missing period ref when a remote is
configured,
uses local `HEAD` when none is configured, and remains subject to the same
control-branch and recurring-owner gates. Direct launch also activates a
paused/draft delegated period inline; recurring scans leave paused periods
parked. A period that also carries
`ticket.py` is refused as an ambiguous dispatch shape. A delegate must itself
be agent-backed: a bootstrap target with `ticket.py` is rejected before period
creation, and its deterministic work belongs in the recurring template's own
`ticket.py`.

**Queue conduct.** Like megalaunch, automatic recurring launches (the bare
sweep, `--force`, and on-demand `recurring launch <name>` — everything except
`--interactive`) select the recurring queue session-conduct layer
(`prompt-queue.md`) into each composed agent prompt: the TTY is transport, not
an approval gate, so unavailable input must end in `coga block` rather than a
question that hangs the queue. `--interactive` selects attended conduct
instead. This is composition, not an appended override, and the selector is
the runner's own launch context — there is no CLI flag for it. See
`coga/architecture`.

**Idle-timeout backstop.** An agent template that *does* launch (a TTY is
present) but whose agent stalls or crashes before signalling done — never
reaching `coga bump` / `mark done` / `mark canceled` / `block` — would otherwise block the
sequential sweep forever. Both the bare sweep and `coga recurring --force` arm a
generous idle timeout on each spawned REPL (passed through as `coga launch
--idle-timeout`): if it produces no output and takes no input for that long,
the supervisor tears it down as a non-zero timed-out result so the sweep moves
on without calling the task completed.
`coga recurring --interactive` — a human stepping through by hand — leaves the
REPL unbounded, as does a plain `coga launch`. The default window is 15
minutes; set `COGA_REPL_IDLE_TIMEOUT` (seconds) to change it, or to `0` /
a non-finite value to disarm the backstop for recurring launches. When
configured, `COGA_REPL_MAX_SESSION` / `[launch].max_session` threads the same
way as a wall-clock cap.

**Autofix loop.** Every sweep ends by analyzing itself and files a real
problem as an `active` ticket under `coga/tasks/autofix/`. It never changes
the sweep's exit code. Operator knobs: `COGA_AUTOFIX=0` disables the loop,
`COGA_AUTOFIX_TIMEOUT` (seconds) bounds the call, every run record is kept at
`.coga/recurring-runs/<stamp>.md`, and `coga run autofix-analyze` re-runs the
analysis over a recorded run by hand. `coga recurring launch <name>` closes
the same loop, so the `coga dream` / `coga autoclose` / `coga skill-update`
aliases analyze their run too. The mechanism, the run record's contents, and
the auth fallback are in `coga/recurring`.

Dream, REM, and other recurring maintenance loops all use this surface.

## coga recurring launch \<name\> [--agent <type>]

Create one named recurring template now and launch it, ignoring its
schedule. `name` is the directory name under `coga/recurring/`. The task
ref is `recurring/<name>`, so a manual `launch` and a bare `coga recurring`
converge on one stable task directory (idempotent — a second `launch` reuses
the existing task). An orphaned `in_progress` run is resumed rather than
duplicated; a prior-period `done` run is deleted and replaced, while a
current-period `done` run or any `paused` run is left alone. This is exactly
what the `coga dream` alias expands to.
Unless `--interactive` is set, it passes the same concrete idle-timeout and
max-session limits as the scheduled sweep. `--interactive` leaves those
liveness limits unarmed for debugging one template by hand.
`--agent <type>` applies the same ephemeral override as the full sweep when the
named task is agent-backed. This also makes `coga dream --agent <type>` work
through the alias.

## coga recurring promote \<task\> --schedule "\<cron\>" [--name \<name\>]

Move an existing task out of `coga/tasks/` and into
`coga/recurring/<name>/ticket.md` as a recurring template — the authoring path
for "this ticket should run every period", and the way to make a freshly
created ticket recurring (`coga create`, write the body, then promote).
`--schedule` is required and validated before anything moves. `--name`
overrides the template directory name, which defaults to the task's leaf slug.

The body above the blackboard fence travels verbatim; the blackboard is reset,
because a template blackboard holds durable cross-run state rather than one
run's scratch. `status:`, `step:`, `slug:`, `human:`, and `agent:` are dropped
(the creator re-derives them per period), a frozen `workflow:` snapshot
collapses back to its name, and ticket-level `skills:` are dropped with a
warning — they are never copied into a period task, so process skills belong
on the workflow's steps. Everything else (`title`, `owner`, `assignee`,
`watchers`, `contexts`, `secrets`) passes through.

It refuses instead of guessing: an existing `coga/recurring/<name>/` is never
overwritten, a bad cron leaves the source ticket untouched, and an
`in_progress` or `blocked` task is refused because a template cannot hold a
live run's step or blocker.

## coga recurring list

Read-only view of the recurring system — creates nothing and launches
nothing (the inspectable counterpart of a bare `coga recurring`, which
get-or-creates each due period's task and runs it). Prints two tables: every
template with its schedule, last/next firing, and current-period state
(`due — not created`, `ran this period — task reaped` for a serviced period
whose task Dream removed, or the live instance's status); then the **picked
tasks** — the recurring period tasks already on disk, with their status and
step. A template that fails to load (e.g. missing `schedule`) shows as an
error row instead of crashing the view.

## coga --version

Package version + the version and install source `.coga/` was vendored from
(recorded in `.coga/COGA_PIN` at init). Useful for "is this fixed in your
copy?" questions.

## Aliases

`[aliases]` in `coga.toml` maps a one-word name to an expanded coga
command. Positional args after the alias name forward to the expansion.
Default aliases shipped by `coga init`:

```toml
[aliases]
chat = "launch bootstrap/orient"
build = "launch coga-build"
dream = "recurring launch dream"
pick = "megalaunch --pick"
```

Eight aliases are registered as built-in defaults in `aliases.DEFAULT_ALIASES`,
so they dispatch even in repos whose `coga.toml` predates the line — the four
above plus four the packaged `coga.toml` never mentions:

```
skill-update      = "recurring launch skill-update"
autoclose         = "recurring launch autoclose-merged"
open-pr           = "launch bootstrap/open-pr"
resolve-conflicts = "launch bootstrap/resolve-conflicts"
```

Reading `coga.toml` alone will therefore not show you every available alias.
`create` is a
built-in command, not an alias (it has its own scaffolding behavior beyond
what a `launch bootstrap/...` expansion would give it).

Rules: alias names can't collide with built-in commands; the first
token of the expansion must be a known built-in. Both checked at
config load — fail loud, not silent. Aliases are positional pass-through
only; they don't accept their own flags.

## Pick which command

- Scaffolding a raw new draft → `coga create "<title>"`.
- Guided ticket authoring → `coga ticket` or `coga ticket "<title-or-slug>"`.
- Starting a draft's work → `coga launch <slug>` (activates inline).
- Approving/queueing without launching → `coga mark active <slug>`.
- Pausing a task → `coga mark paused <slug>`.
- Finishing a workflow step, including the final step → `coga bump <slug>`.
- Finishing a ticket with no workflow → `coga mark done <slug>`.
- Intentionally abandoning a ticket →
  `coga mark canceled <slug> --message "<reason>"`.
- Ticket-less chat session → `coga chat` (alias for
  `launch bootstrap/orient`).
- Running Coga cleanup now → `coga dream`.
- Launching every due recurring task → `coga recurring`.
- Launching due recurring tasks across every Coga repo below a parent path →
  `coga recurring --all <path>`.
- Inspecting recurring templates + schedules + instantiated tasks (read-only)
  → `coga recurring list`.
- Forcing a real full run of every template now (ignore schedule + status
  filter) → `coga recurring --force` (`--agent <type>` temporarily selects the
  agent for agent-backed tasks).
- Launching one named recurring task now → `coga recurring launch <name>`
  (`--agent <type>` temporarily selects its agent when agent-backed).
- Starting or resuming agent work on a task → `coga launch <slug>`.
- Turning a described browser task into a concrete automation ticket →
  `coga launch bootstrap/browser-automation`.
- Sweeping all your launchable agent work (active + in_progress) →
  `coga megalaunch`
  (`--agent <type>` runs the sweep with that agent regardless of assignee,
  `coga megalaunch <dir>` scopes it to one `tasks/` sub-tree).
- Picking which tasks to launch (arrow-key checkbox list over any owner's
  non-terminal tasks) → `coga megalaunch --pick`; replaying the
  last confirmed list → `coga megalaunch --relaunch`.
- Other bootstrap ticket → `coga launch bootstrap/<name>`.
- Advancing a workflow-bound task → `coga bump`.
- Catching up tickets after a teammate merged a PR → `coga autoclose`
  (explicit-only; run it by hand).
- Triage view → `coga status`.
- Blocked-work queue → `coga status --blocked`.
- Reading a single task without opening the file → `coga show <slug>`.
- Accounting for agent token spend after the fact → `coga usage`
  (`--by model|agent|step` to re-slice, `--json` to pipe).
- Flushing the pending daily digest now instead of waiting for its
  schedule → `coga digest`.
- Surfacing a non-blocker note tied to a step transition → `coga bump --message`.
- Surfacing a non-blocker note tied to a status transition → `coga mark <state> --message`.
- Surfacing a non-blocker note that doesn't fit a transition → `coga slack`.
- Surfacing a blocker → `coga block --task <slug> --reason "..."`.
- Answering a blocker → `coga unblock <slug> --answer "..."`.
- Throwing away an abandoned ticket → `coga delete <slug>`.
- Wrapping up a finished ticket (retro + source-dir delete via retro PR) →
  `coga retire <slug>`.

There's also `coga validate [--task <slug>] [--json] [--fix] [--check-slack]
[--check-github]`, a static repo + config diagnostic. By default it scans every task; `--task
<slug>` validates exactly one task directory (files plus strict frontmatter
schema) and is what a human or agent runs after a direct hand-edit to a single
ticket. Every task creation path (`coga create`, recurring, and retire, all
through `create_task`), guided ticket-authoring exit, and lifecycle commands
such as mark, bump, and launch-time transitions run that task-scoped check at their
write boundary. A failed check reports the formatted issues and leaves the
written ticket on disk for correction; it does not report command success.
After a direct human edit, run `coga validate --task <slug>` manually because
Coga has no command boundary at which to validate an ordinary file edit.
`--fix` is deliberately narrow: it appends a missing blackboard fence +
rendered region to a `ticket.md` that lacks one, then reports the remaining issues. It does not rewrite
existing files, freeze workflows, delete locks, or push git state. `--check-github`
is an opt-in preflight that mirrors `--check-slack`: it probes git/GitHub auth
readiness so a raw tool failure surfaces as an actionable setup hint before PR
time instead of surprising an agent mid-run. It probes the *configured* remote
(`git remote get-url <cfg.git_remote>`, not a hardcoded `origin`), checks push
access with a non-mutating `git push --dry-run`, fetches the configured control
branch, and verifies before PR handoff that `HEAD` contains every material
control-branch change. Divergence confined to non-overlapping generated
`coga/tasks/**` and `coga/log.md` state is reported but accepted; Coga writes
that state between workflow steps, so requiring literal ancestry would make the
next `open-pr` step stale by construction. Source, docs, config,
mixed, or overlapping state drift remains an error. The preflight also verifies
`gh --version` and `gh auth status --hostname <host>` for the remote's host.
Every probe is fully
non-interactive (`GIT_TERMINAL_PROMPT=0`, ssh `BatchMode=yes`) so a missing
credential fails fast rather than hanging on a hidden prompt; failures are
`(github)` errors excluded from the ok count. It is opt-in because the default
validate path runs no subprocess and reads no network; Coga stores no PAT and
does not reimplement GitHub auth — it just exercises the operator's own `git` and
`gh` setup. Reach for
validation when a command is misbehaving or slack/webhook setup looks broken;
Dream's validate-drift skill is the normal place to apply safe fixes and
broadcast a summary during a Dream run.

## What this context does NOT cover

- The mental model behind these commands (primitives, planes, prompt
  composition, locking) — see `coga/architecture`.
- Where source lives + how to test changes — see `coga/codebase`.
- Reference contracts — frontmatter shapes and primitives are in
  `coga/architecture`; config schemas live in `src/coga/config.py`.
