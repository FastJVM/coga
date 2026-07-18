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
`coga/skills`, `coga/contexts`, and `coga/workflows`.

## coga uninstall [--yes] [--purge]

Remove the Coga footprint from the current repo: `coga/`, the agent skill
symlinks in `.claude/` and `.codex/`, unmodified Coga orientation guides
(`CLAUDE.md` / `AGENTS.md`), the coga-managed `.gitignore` block, and the
`~/.local/bin/coga` shim if it points back into this repo.

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
`coga build`.

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
escape `tasks/` (`..`), name a `_`-prefixed (discovery-skipped) segment, or
nest the task inside an existing task directory. Because `/` now means
"sub-directory", a title with a literal slash (`CI/CD pipeline`) is read as a
path — create it at the top level (drop the slash) and `mv` it if needed.

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
- `coga ticket add-retry` — edit an existing ticket at any status. Editing
  leaves the status unchanged; for an `in_progress` or `done` ticket it
  prints a heads-up first (revising one in flight or already finished is
  unusual) but does not refuse.

The guided authoring flow chooses workflow/context/assignee with the human,
edits the ticket, and leaves status unchanged. After the session it
validates the task; a draft handed back with no workflow is rejected at the
terminal rather than later at activation. For a new draft, the boot sequence
is: `coga ticket "<title>"` → review/edit → `coga launch <slug>`, which
activates the draft inline as it starts work.

For the standard `claude` and `codex` CLIs, `coga ticket` passes the
composed authoring prompt as system/developer context instead of as the first
user message. That lets the first real human exchange set the agent session
title for later resume. Set `[agents.<type>].discussion` to override the argv
template for another agent.

## coga project [\<seed\>] [--agent <type>]

Plan a whole project into an ordered set of `draft` tickets. Runs the
`bootstrap/project` skill in an interactive session: it interviews the human
(outcome → prior art → constraints → dependencies & sign-off, one question at
a time), proposes the ordered ticket list for the human to prune/reorder, then
scaffolds the surviving set with `coga create` — one launchable step per
ticket. Where `coga ticket` authors one ticket, `coga project` decomposes a
project into many.

- `coga project` — start from the first interview question.
- `coga project "<seed>"` — seed the interview with a one-line description or
  a path/link to a vision doc; the agent reads it and confirms/fills gaps
  rather than starting cold. Covers the vision-to-plan case.
- `coga project --agent <type>` — run the interview with a specific agent.

The interview questions and decomposition rules live in the skill, not in CLI
code, so they can't drift. The command creates only `draft`s and never
activates or launches them — the human owns what happens next. Like
`coga ticket`, it requires a TTY (interactive). After the session it lists the
created drafts and fails loud if any has a schema error.

## coga mark \<state\> \<slug\> [--message "..."]

Change a ticket's `status`. Three subcommands: `mark active`,
`mark paused`, `mark done`. The verb mirrors the frontmatter field, so
the command shape is `<status field value> on disk` = `<mark
subcommand>`.

- `mark active <slug>` — allowed from `draft` or `paused`. Posts `🚀`.
  Refuses a workflow-less ticket — set `workflow:` or run `coga ticket`
  first.
- `mark paused <slug>` — allowed from `active` or `in_progress`. Preserves
  `step:`. Posts `⏸️`.
- `mark done <slug>` — allowed from `active` or `in_progress`. Clears
  `step:`. Posts `🎉`. Use this to finish a workflow on its final step, or
  to finish any ticket without a workflow.

`--message` piggy-backs an FYI onto the Slack broadcast.

`coga launch` owns the `active` → `in_progress` start transition, and will
activate a `draft`/`paused` ticket inline first (launching is the readiness
signal). `blocked` is command-owned by `coga block` / `coga unblock`, and
`done` is terminal unless a human deliberately edits or reopens the ticket.
`coga bump` no longer marks final-step tickets done. The status state machine
and the step state machine are separate.

## coga launch \<target\>

Compose every relevant file (rules + repo context + ticket contexts +
current step's skill + blackboard + ticket body) into one prompt and
start the configured agent. Accepts `status: active` or `in_progress`
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
`blocked` so blocker queues keep reporting it. Script, auto, and
Script and TTY-less launches of a blocked ticket are still refused until
`coga unblock` records the answer (the `coga megalaunch` *sweep* likewise
still skips it as `skipped-unresolved-blocker`; an explicit `--pick` of a
blocked ticket is the human act and resumes it the same interactive way); a
`done` ticket is refused because it is finished. A ticket
that can't be activated — no workflow, or an empty `required` extension field
— still fails loud with the same remedy `mark active` gives. Launching an
`active` ticket then marks it
`in_progress` (posting `▶️`) before spawning the agent; launching an
already-`in_progress` ticket resumes it without another status flip. Whether
a launch runs a script or spawns an agent is deduced per launch: a
script-backed current step or a ticket-level `script:` runs as a script;
anything else spawns the assignee's agent, which requires stdin and stdout to
both be terminals. Script launches run deterministic code directly without
composing an agent prompt and inject task metadata env vars including
`COGA_TASK_SLUG`, `COGA_TASK_DIR`, and `COGA_TASK_BLACKBOARD`.

- `coga launch <slug>` — accepts any unique prefix (git-short-SHA-style).
  A top-level task is its bare leaf slug; a nested task is referenced by its
  path under `tasks/` (`marketing/coga-crm`), matching what `coga status`
  prints — the bare leaf alone won't resolve.
- `coga launch <slug> --agent <type>` — one-off agent-type override
  for an agent-owned task (e.g. `--agent claude`); does not rewrite the
  ticket's `assignee:` and does not bypass a human handoff.
- `coga launch <slug> --prompt-report` — print composed prompt layers,
  exact context/skill refs, bytes, and approximate token counts without
  spawning an agent. Rejected for script launches, which compose no
  agent prompt.
- `coga launch bootstrap/<name>` — stateless launch target; concurrent launches
  safe.

Discussion bootstrap tickets (`bootstrap/orient`, `bootstrap/ticket`) use
built-in templates for the standard `claude` and `codex` CLIs, or the selected
agent's optional `discussion = "...{prompt}..."` override. In discussion
launches the Coga prompt is context and the first human ask can name the session.
Other task launches keep passing the composed prompt positionally.

`launch` does not probe `gh` for PR state before composing the prompt —
auto-bumping a ticket whose final-step PR has merged is the job of
`coga automerge` / the `autoclose-merged` recurring sweep, never launch. It
does, though, **pre-flight git push access**: before flipping status or
spawning the agent, it runs a non-interactive `git push --dry-run` against the
configured remote (the same push-auth probe `coga validate --check-github`
uses) and refuses the launch if push auth is broken. Coga drives the whole session
through git/gh (branch push, `gh pr create`, every `coga bump` syncs ticket
state), so a dead remote means a run guaranteed to fail at ship time — fail
loud at the door, not after a long run. The gate self-skips for bootstrap
tickets, `[git].enabled = false`, and non-git checkouts.

All of coga's git subprocesses run non-interactively (`GIT_TERMINAL_PROMPT=0`,
SSH `BatchMode=yes`), so a credential-less remote fails fast instead of hanging
on a prompt. Note the asymmetry: the launch-entry gate is **fatal** (refuse to
start), but a mid-workflow ticket-state sync miss (`coga bump` / `mark`) stays
**non-fatal** — reported to stderr + `log.md`, then continue — because the
on-disk markdown is the source of truth and aborting there would stall the
supervised chain.

Agent type comes from the ticket's `assignee` directly — it names an
`[agents.<type>]` block in `coga.toml`. Human assignees aren't
launchable, and `--agent` does not convert a human handoff into an agent
step; reassign to an agent type first.

For workflow-bound interactive tasks, `launch` can continue through
consecutive agent-owned steps in fresh processes. After a clean agent exit,
it re-reads the ticket and continues only if the task is still
`in_progress`, the step advanced, the new current step has `skill:`, and the
concrete assignee did not change. It stops at human/no-skill steps, assignee
handoffs, done, paused, or blocked tasks, no-progress exits, and non-zero exits.

That supervisor loop only exists when a live `coga launch` process is
running around the agent. API/manual sessions do not chain: after `coga bump`,
stop cleanly and let the human relaunch the next step. Only the launch
supervisor re-reads the ticket and starts a fresh step session.

### Releasing an interactive REPL

Interactive agent REPLs terminate through a session-scoped side channel:
`coga bump`, `coga mark done`, and `coga block` write the launched task to
`$COGA_DONE_SENTINEL`, and the PTY supervisor tears the REPL down. A
successful script launch writes the same slug-scoped sentinel after its step
advance (the advance is that launch's `coga bump`), so an agent that drives
its own script step with a nested `coga launch` releases its session too. PTY
output is never a completion channel, so reading or printing prompt text
cannot end a session accidentally.

`--prompt-report` is for prompt-scope inspection. Its token counts use a
dependency-light `characters / 4` estimate, so treat them as a prompt-bloat
guardrail and task-to-task comparison, not exact provider billing.

## coga status

List the live tasks in the repo — `draft`, `active`, `in_progress`, `blocked`,
and `paused`. `done` tasks are hidden by default; pass `--all` (`-a`) to include
them. Bootstrap tickets have no status and don't appear here. Pipe through
`grep` for ad-hoc slicing of any column. When done tasks are hidden the
output ends with a `(N done tasks hidden — use --all to show)` note.

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

## coga bump \<slug\> [--message "..."]

Advance a workflow-bound task one step. Updates `step:`, appends a log
entry. Requires `status: in_progress`. The workflow is frozen into the
ticket at create time, so step semantics don't drift mid-task.

`bump` no longer finishes tickets. Bumping past the last step is an
error pointing you at `coga mark done <slug>`. Bumping a ticket
without a workflow is the same error — those tickets only have one
"step" (the whole ticket), and `mark done` is how you finish them.

`--message` piggy-backs an FYI onto the state-transition Slack
broadcast — one post instead of two. Use it for transition-tied notes
like "PR opened: <link>" or "shipped, watching error rate". For FYIs
that don't fit a transition, reach for `coga slack` instead.

## coga automerge

Walk active / in-progress tickets; bump any whose blackboard `## Dev`
section names a PR that has merged on GitHub. Looks each PR up via
`gh pr view`. Scope: tickets on their final workflow step, or with no
workflow at all. Mid-workflow merges stay alone — those need a human eye.

`coga automerge` is an explicit-only surface — you run it by hand to
catch up tickets whose PR merged out of band. It is no longer wired into
any implicit trigger: `coga status` does **not** trigger automerge (it is
a strictly read-only view that never hits the network or mutates ticket
state as a side effect of rendering — principle 6, fail loud, names
`status`/`show`/`validate` as forbidden mutators), and there is no
post-merge git hook. The explicit command surfaces `gh` errors (missing,
unauthed) loudly.

Posts a distinct Slack line with the ticket title, previous step, and linked
PR (`🎉 *<slug>* "<title>": <prev> → done — <pr-url|PR #<N>> merged`), so the
team can tell auto-bumps apart from manual ones.

## coga delete \<slug\>

Remove a task directory from the working tree — ticket, blackboard,
log, and the directory itself. Recovery is via `git restore`; the
git history is the audit trail, no Slack broadcast. The removal itself
runs through the `bootstrap/delete-task` skill, so the command is a thin
resolver and the same deletion is reachable as a script step.

Bootstrap tickets aren't user-deletable — they're package-backed batteries
managed by the installed Coga package.

## coga retire \<slug\> [--agent <type>] [--no-launch]

Wrap up a `done` ticket: scaffold a one-shot `retire-<slug>` task whose body
invokes the `retro/done-ticket` skill against the named ticket. The retro
skill opens the PR that records the `## Retro` marker, edits the knowledge
base if warranted, and deletes the source task directory in the same PR.
The retire task is scaffolded straight to `active`; `coga retire` launches
it unless `--no-launch` is passed.

- `coga retire <slug>` — scaffold and launch an agent retire task.
- `coga retire <slug> --no-launch` — scaffold the retire task (already
  `active`) and print the explicit `coga launch <slug>` command.

Refuses if the target task is not `status: done`. Use `coga delete` for an
abandoned ticket where retro has nothing to extract. Branch hygiene (pruning
the merged feature branch, sweeping stale branches) belongs in a Dream
worker, not here.

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
surface.

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
- **Local adaptation is detected by digest**, comparing the skill's current
  tree digest against the recorded `installed_tree_digest`. `coga skill
  install-url` refuses to overwrite a locally-adapted skill unless `--force`
  is passed (`install-url` is the only install path with a Coga digest to
  compare, so it is the only one with the guard). `--force` is forwarded to
  the underlying `gh skill install`, rewrites `installed_tree_digest` to the
  freshly installed tree, and resets `local_adaptation_notes` to empty — the
  forced overwrite discards the adaptation, so preserving the note would
  mis-describe the new tree.
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
  every task worth launching — any owner, any status but `done`: every
  `draft` (offered even when not-yet-ready — see the prepare phase below),
  plus `active`, `in_progress`, `paused`, and blocked-with-open-asks that are
  agent-assigned or a script launch. Nothing starts checked: ↑/↓ (or `j`/`k`)
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
2. **Activate** — every picked `draft`/`paused`/`blocked` ticket is brought to
   `active` (a `blocked` ticket keeps its open asks for the launch-time
   resolve-or-re-block preamble), and picks that still can't launch are
   reported now.
3. **Launch** — each activated ticket runs, one at a time; a resumed `blocked`
   pick returns to `blocked` if its session exits with the ask still open.

Checking a task in the picker is thus the deliberate human act of starting
it, and another owner's ticket launches when picked. A selected task that
still can't launch (done, or a draft the interview left with no workflow to
activate) is reported as `skipped-unlaunchable` rather than silently dropped —
you picked it, so its outcome is owed back.

The sweep silently filters out tickets whose `owner` is not
`load_config().current_user` (including owner-less tickets, so other owners'
work is not counted as skip noise), skips human gates and open blockers,
preflights launch requirements, then
runs one eligible step at a time. An agent step is a normal **interactive**
launch — the agent REPL streams live to the console under the PTY watcher, and
the done-sentinel (`coga bump` / `mark done` / `block`) releases it before the
sweep moves on — never a headless `claude -p` run, which would buffer all
output until the run ends. A **script launch** — a script-backed current step
or a ticket-owned `script:` — runs the script directly,
exactly like the `coga launch` supervisor: no agent, no REPL, no assignee
gate; exit 0 advances the step and the chain continues, a non-zero exit
leaves the step put and fails that one task without stopping the sweep. The
recurring-style idle-timeout / max-session
backstops are armed so a wedged REPL can't starve the queue; because the REPLs
(and the `--pick` prompt) are interactive, megalaunch requires a TTY and fails
loud without one. The run summary distinguishes launched, completed, blocked,
skipped-human-gate, skipped-unresolved-blocker,
skipped-unlaunchable, and failed.

Megalaunch is on-demand only — there is no shipped recurring template for it;
you run the sweep when you want the queue drained.

Pass `--agent <type>` to launch the swept tasks (and the picker's confirmed
set) with that configured agent type regardless of each ticket's `assignee:`
— an ephemeral per-launch override with the same semantics as
`coga launch --agent`: the ticket's `assignee:` is never rewritten, a
human-assigned ticket is not converted into an agent step (it still skips as
a human gate), and on a task that chains multiple steps the override applies
only to the first launched *agent* step (script steps run as scripts and
never consume it) — later steps follow the ticket's resolved
assignee, so `other-agent` rotation keeps its meaning.

An optional positional `DIR` scopes the sweep or the picker to tasks under
`tasks/<DIR>/` (nested ones included), exactly like `coga status <dir>` —
`coga megalaunch marketing` drains only that sub-tree, and an unknown
directory fails loud instead of sweeping nothing silently. It composes with
`--agent` and `--pick`.

## coga slack --task \<slug\> --message "..."

Manual broadcast escape hatch — posts a short FYI to the team Slack
channel without changing task state. Use for events that don't
coincide with a state transition (e.g. announcing a hand-edit to a
ticket, or surfacing a non-blocker mid-step). For FYIs that *do*
coincide with a `bump`, use `bump --message` instead — one post,
not two. Notifications are optional on first run (a fresh repo selects no
channels), so with nothing configured this posts nothing and does not crash.
Once Slack is selected it is fail-loud (see `coga/sync`): commands crash if
`$SLACK_WEBHOOK_URL` is unset and the user hasn't opted out via
`[notification.slack].enabled = false`.

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
`last_serviced_period`. Running
`coga dream` mid-week reuses that task instead of creating a second one. Dream
scans current task state, runs the known Coga housekeeping pass, writes
results to that run's blackboard, and finishes with `coga mark done`.

## coga recurring [--force] [--agent <type>]

## coga recurring --all <path> [--force] [--agent <type>]

Scan `coga/recurring/`, then create and launch every task that is due.
The Typer command head parses `--interactive` / `--force` / `--agent` and
launches the stateless package-backed `bootstrap/recurring-scan` script target,
passing those values through an explicit environment contract.

`--all <path>` is the multi-repo scheduler entry point. It may run from outside
a Coga repo: it recursively finds `coga/` directories containing `coga.toml`
below the explicit path, skips dependency/tool trees, and stops descending once
it finds a workspace. Git-enabled checkouts are grouped by the resolved URL of
their configured remote plus the Coga workspace's path within the git checkout;
one checkout per remote workspace runs (preferring the first locally configured
checkout already on its control branch), and every duplicate is named and
skipped. Distinct Coga workspaces inside one monorepo remain separate scheduler
targets. Each selected repo runs its ordinary recurring command in a fresh CLI
process, sequentially, with a strict entry gate: `[git]` must be enabled, the
configured control branch must be checked out, and its pre-scan fetch/rebase
must succeed before period state is read or written. One repo's failure does not
starve later repos, but the parent exits non-zero after reporting the aggregate.
This keeps schedules, task state, config, Slack, and git sync owned by each repo
while allowing one cron entry such as `coga recurring --all ~/Code` without
racing two checkouts of one remote workspace.

Pass `--agent <type>` to run every agent-backed task in the sweep with that
configured agent type. The override is ephemeral: it does not rewrite ticket
assignees, human handoffs remain protected, and script-backed recurring tasks
still run as scripts. The command threads the override through the stateless
scan target as `COGA_RECURRING_AGENT`.

For each template (skipping `_`-prefixed files) `coga recurring` enforces
**one live task per template**: if the generated task at `recurring/<name>` is
already `active` or orphaned `in_progress`, that one is
launched/resumed and no duplicate is created; only when none is live does it
get-or-create the current run at `coga/tasks/recurring/<name>/` and advance
the template blackboard's `last_serviced_period` line. It launches the due ones
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
nothing runs unless you invoke it. `coga/scripts/cron.sh` is the
optional entry point if you later wire it into a scheduler yourself.
Dedup after Dream deletes a completed run comes from
`last_serviced_period >= current period_key`; the repo-global `coga/log.md`
(tagged `recurring/<name>`) is append-only human history, not the dedup source.

`coga recurring --interactive` is the human-stepped debug knob for a recurring
run. It requires an attended TTY and leaves the recurring liveness backstops
unarmed; each template still launches according to its deduced substance
(script when its `script:` or workflow step 1 is script-backed, else agent).

`coga recurring --force` **forces a real, full run of every template**. It is
*not* a sandbox: the only difference from a bare `coga recurring` is that it
ignores the schedule and the status filter that skips already-serviced / done /
paused templates this period. For every template it get-or-creates the real
`recurring/<name>` period task and launches it — even one that already ran this
period (`coga launch` re-activates a `done`/`paused` ticket, restarting its
workflow at step 1). Everything else is identical to a normal run: real Slack,
real digest-spool drain, real git task-state sync, and the real
`last_serviced_period` high-water advance. There are no `-dbg-` scratch dirs, no
slug-based suppression, no orphan reaping, and no fold-back-to-template-log
step. Use it to force this period's work to re-run without waiting for the
schedule.

Agent templates (no `script:` and no script-backed workflow step 1) are
skipped when `coga recurring` has no stdin/stdout TTY, because the agent REPL
cannot be driven. Templates intended for cron or other unattended schedulers
should carry a script.

**Idle-timeout backstop.** An agent template that *does* launch (a TTY is
present) but whose agent stalls or crashes before signalling done — never
reaching `coga bump` / `mark done` / `block` — would otherwise block the
sequential sweep forever. Both the bare sweep and `coga recurring --force` arm a
generous idle timeout on each spawned REPL (passed through as `coga launch
--idle-timeout`): if it produces no output and takes no input for that long,
the supervisor tears it down (reported as a clean exit) so the sweep moves on.
`coga recurring --interactive` — a human stepping through by hand — leaves the
REPL unbounded, as does a plain `coga launch`. The default window is 15
minutes; set `COGA_REPL_IDLE_TIMEOUT` (seconds) to change it, or to `0` /
a non-finite value to disarm the backstop for recurring launches. When
configured, `COGA_REPL_MAX_SESSION` / `[launch].max_session` threads the same
way as a wall-clock cap.

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
named task is agent-backed; script-backed tasks ignore it and still run as
scripts. This also makes `coga dream --agent <type>` work through the alias.

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

`chat`, `build`, `dream`, and `pick` are also registered as built-in default
aliases, so they dispatch even in repos whose `coga.toml` predates the line.
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
- Finishing a task (final step, or no workflow) → `coga mark done <slug>`.
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
- Sweeping all your launchable agent work (active + in_progress) →
  `coga megalaunch`
  (`--agent <type>` runs the sweep with that agent regardless of assignee,
  `coga megalaunch <dir>` scopes it to one `tasks/` sub-tree).
- Picking which tasks to launch (arrow-key checkbox list over any owner's
  tasks, any status but done) → `coga megalaunch --pick`; replaying the
  last confirmed list → `coga megalaunch --relaunch`.
- Other bootstrap ticket → `coga launch bootstrap/<name>`.
- Advancing a workflow-bound task → `coga bump`.
- Catching up tickets after a teammate merged a PR → `coga automerge`
  (explicit-only; run it by hand).
- Triage view → `coga status`.
- Blocked-work queue → `coga status --blocked`.
- Reading a single task without opening the file → `coga show <slug>`.
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
next script-backed `open-pr` step stale by construction. Source, docs, config,
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
