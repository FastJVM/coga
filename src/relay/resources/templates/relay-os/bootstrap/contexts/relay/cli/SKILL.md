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

## relay uninstall [--yes] [--purge]

Remove the Relay footprint from the current repo: `relay-os/`, the agent skill
symlinks in `.claude/` and `.codex/`, unmodified Relay orientation guides
(`CLAUDE.md` / `AGENTS.md`), the relay-managed `.gitignore` block, and the
`~/.local/bin/relay` shim if it points back into this repo.

It prints the plan and asks for confirmation; `--yes` skips the prompt for
scripted runs. Edited `CLAUDE.md` / `AGENTS.md` files are renamed to
`<name>.relay-bak` rather than deleted. Without `--purge`, the global
`relay-os` package is left installed and the command prints the exact pipx/pip
uninstall commands. With `--purge`, it also uninstalls the global package; if
the running CLI is this repo's vendored copy, there is no separate global
package to remove.

## relay build

First-run onboarding entry point — the command to tell new users about. `build`
is not a built-in; it is a default alias for `launch relay-build`, so it
launches the packaged `relay-build` ticket through the normal `relay launch`
path (one question → agent-led chat → vision → starter tickets). Because it
dispatches through `relay launch` CLI parsing it requires an already-init'd
repo, and capturing your name is `relay init`'s job, not `build`'s. There is no
separate `relay setup` command — initialize the repo with `relay init`, then run
`relay build`.

## relay create "\<title\>" [--workflow \<name\>] [--mode interactive|auto|script]

Scaffold a new raw `draft` ticket and post `✨` when a notification channel
is selected (a fresh repo selects none, so this is silent out of the box).
Does not launch an agent. Step one of the boot path: `relay create` → edit the
body / workflow / contexts as needed → `relay launch <slug>`. Launch activates
a draft inline; use `relay mark active <slug>` only when you want to
approve/queue without launching. This is the raw-create path — no guided
interview.

`--workflow <name>` (path under `relay-os/workflows/`) is optional *in
draft only*. A workflow-less draft is a valid authoring state; the workflow
can be added to the ticket any time before activation. The bumpability gate
lives at activation, not here: `relay mark active` refuses a workflow-less
ticket with an error pointing at `--workflow` or `relay ticket`, and
`relay validate` reports a workflow-less `active`/`in_progress`/`paused`
ticket as an `active-no-workflow` **error** (a stuck task no `relay bump` can
advance). Once a ticket leaves `draft`, a workflow is mandatory. For guided
authoring that fills the workflow in for you, use `relay ticket`.

The deliberate separation keeps the moment of authorship distinct from
the moment of starting work. Tickets you mean to draft now and start
later get the same call; nothing fires the agent until you choose to.

## relay ticket [\<title-or-slug\>] [--agent <type>]

Run the guided ticket-authoring interview (`bootstrap/ticket`).

- `relay ticket` — ask for a title, create a draft, and fill it.
- `relay ticket "Add retry to webhook handler"` — create that draft, then
  launch the authoring skill against it.
- `relay ticket add-retry` — edit an existing ticket at any status. Editing
  leaves the status unchanged; for an `in_progress` or `done` ticket it
  prints a heads-up first (revising one in flight or already finished is
  unusual) but does not refuse.

The guided authoring flow chooses workflow/context/assignee with the human,
edits the ticket, and leaves status unchanged. After the session it
validates the task; a draft handed back with no workflow is rejected at the
terminal rather than later at activation. For a new draft, the boot sequence
is: `relay ticket "<title>"` → review/edit → `relay launch <slug>`, which
activates the draft inline as it starts work.

For the standard `claude` and `codex` CLIs, `relay ticket` passes the
composed authoring prompt as system/developer context instead of as the first
user message. That lets the first real human exchange set the agent session
title for later resume. Set `[agents.<type>].discussion` to override the argv
template for another agent.

## relay project [\<seed\>] [--agent <type>]

Plan a whole project into an ordered set of `draft` tickets. Runs the
`bootstrap/project` skill in an interactive session: it interviews the human
(outcome → prior art → constraints → dependencies & sign-off, one question at
a time), proposes the ordered ticket list for the human to prune/reorder, then
scaffolds the surviving set with `relay create` — one launchable step per
ticket. Where `relay ticket` authors one ticket, `relay project` decomposes a
project into many.

- `relay project` — start from the first interview question.
- `relay project "<seed>"` — seed the interview with a one-line description or
  a path/link to a vision doc; the agent reads it and confirms/fills gaps
  rather than starting cold. Covers the vision-to-plan case.
- `relay project --agent <type>` — run the interview with a specific agent.

The interview questions and decomposition rules live in the skill, not in CLI
code, so they can't drift. The command creates only `draft`s and never
activates or launches them — the human owns what happens next. Like
`relay ticket`, it requires a TTY (interactive). After the session it lists the
created drafts and fails loud if any has a schema error.

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

`relay launch` owns the `active` → `in_progress` start transition, and will
activate a `draft`/`paused`/`done` ticket inline first (launching is the
readiness signal). `relay bump` no longer marks final-step tickets done. The
status state machine and the step state machine are separate.

## relay launch \<target\>

Compose every relevant file (rules + repo context + ticket contexts +
current step's skill + blackboard + ticket body) into one prompt and
start the configured agent. Accepts `status: active` or `in_progress`
directly; a `draft` / `paused` / `done` ticket is activated inline first —
typing `relay launch` is the readiness signal, so it activates the ticket for
you (re-activating a `done` ticket restarts its workflow at step 1) rather
than refusing. A ticket that can't be activated — no workflow, or an empty
`required` extension field — still fails loud with the same remedy `mark
active` gives. Launching an `active` ticket then marks it
`in_progress` (posting `▶️`) before spawning the agent; launching an
already-`in_progress` ticket resumes it without another status flip. Interactive launches require stdin and stdout to both be
terminals. **`mode: auto` is temporarily disabled** — auto runs (claude
`-p`, codex `exec`) buffer stdout until completion, leaving the operator
with no live console signal. Use `mode: script` for unattended wrappers
and CI until streaming lands. `mode: script` runs the step's skill script
directly. Script launches inject task metadata env vars including
`RELAY_TASK_SLUG`, `RELAY_TASK_DIR`, and `RELAY_TASK_BLACKBOARD`.

- `relay launch <slug>` — accepts any unique prefix (git-short-SHA-style).
  A top-level task is its bare leaf slug; a nested task is referenced by its
  path under `tasks/` (`marketing/relay-crm`), matching what `relay status`
  prints — the bare leaf alone won't resolve.
- `relay launch <slug> --agent <type>` — one-off agent-type override
  (e.g. `--agent claude`); does not rewrite the ticket's `assignee:`.
- `relay launch <slug> --prompt-report` — print composed prompt layers,
  exact context/skill refs, bytes, and approximate token counts without
  spawning an agent.
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

`launch` does not probe `gh` for PR state before composing the prompt —
auto-bumping a ticket whose final-step PR has merged is the job of
`relay automerge` / the `autoclose-merged` recurring sweep, never launch. It
does, though, **pre-flight git push access**: before flipping status or
spawning the agent, it runs a non-interactive `git push --dry-run` against the
configured remote (the same probe as `relay validate --check-github`) and
refuses the launch if push auth is broken. Relay drives the whole session
through git/gh (branch push, `gh pr create`, every `relay bump` syncs ticket
state), so a dead remote means a run guaranteed to fail at ship time — fail
loud at the door, not after a long run. The gate self-skips for bootstrap
shims, `[git].enabled = false`, and non-git checkouts.

All of relay's git subprocesses run non-interactively (`GIT_TERMINAL_PROMPT=0`,
SSH `BatchMode=yes`), so a credential-less remote fails fast instead of hanging
on a prompt. Note the asymmetry: the launch-entry gate is **fatal** (refuse to
start), but a mid-workflow ticket-state sync miss (`relay bump` / `mark`) stays
**non-fatal** — reported to stderr + `log.md`, then continue — because the
on-disk markdown is the source of truth and aborting there would stall the
supervised chain.

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

### Releasing an interactive REPL

Interactive agent REPLs (`claude`, `codex`) don't terminate on their own —
they wait for the human to type `/exit`. To let `relay recurring
--interactive` (and any other unattended caller of an interactive launch)
move on without manual intervention, **emit `<<<RELAY_SESSION_DONE_a9f3c41e>>>`
on a line by itself** as your final action once the task is finished.
`relay launch`'s PTY supervisor watches for that marker and SIGTERMs the
REPL when it appears (escalating to SIGKILL after a short grace period if
the REPL ignores the signal).

Emit it after `relay mark done`, after `relay panic`, or any other
end-of-session signal — anywhere the next iteration would belong to a
different task or to the human. Don't emit it mid-work; it terminates the
session immediately. Don't quote the literal in prose unless you actually
mean to release the REPL.

`--prompt-report` is for prompt-scope inspection. Its token counts use a
dependency-light `characters / 4` estimate, so treat them as a prompt-bloat
guardrail and task-to-task comparison, not exact provider billing.

## relay status

List the live tasks in the repo — `draft`, `active`, `in_progress`, and
`paused`. `done` tasks are hidden by default; pass `--all` (`-a`) to include
them. Bootstrap shims have no status and don't appear here. Pipe through
`grep` for ad-hoc slicing of any column. When done tasks are hidden the
output ends with a `(N done tasks hidden — use --all to show)` note.

An optional positional argument and the `--no-recurse` flag are two orthogonal
axes — *which* directory, and *how deep*. Tasks are directories (a `ticket.md`
directory at any depth), so the argument is just a directory path in the tree
and there is no Relay-invented vocabulary to learn:

- `relay status <dir>` — only tasks under `tasks/<dir>/`, nested ones
  included, so it reads like `ls -R <dir>`. The path can be nested
  (`relay status marketing` shows the whole sub-tree; `relay status
  marketing/social` narrows to that sub-directory).
- `relay status --no-recurse` — only tasks sitting directly under `tasks/`
  (none in a sub-directory), the way `ls` (without `-R`) lists one level.
  This is the top-level slice.
- `relay status <dir> --no-recurse` — combine the axes: only the tasks
  directly in `tasks/<dir>/`, excluding deeper sub-directories.
- An unknown directory fails loud, listing the directories that do exist,
  rather than printing a silently empty list. A *known* directory that
  currently holds no tasks is not an error — it prints `(no tasks in <dir>)`.

`relay status --dirs` (`-d`) flips the listing to the *directories* themselves
instead of the tasks: it prints every plain (non-task) directory under `tasks/`,
one path per line, and nothing else. It honors both axes — a `<dir>` argument
lists the sub-directories below that directory (the directory itself is the
query, not a result), and `--no-recurse` keeps only the immediate level. An
unknown `<dir>` fails loud the same way; an empty result prints a `(no
directories ...)` note. This is the read-only counterpart to the `mkdir` /
`mv` / `rm` you'd use to manage them.

There is no command to create, rename, or delete one of these directories —
they are plain directories, so you manage them with the shell: `mkdir
relay-os/tasks/<dir>` to make one (`mkdir -p` to nest), `mv` a task directory
to move it, `rm` to remove it. The filter only reads `tasks/`; like the rest of
`relay status` it mutates nothing and hits no network.

Generated recurring period tasks are machine-authored jobs scaffolded ahead of
execution under `tasks/recurring/` (`recurring/<name>`), so they render in a
**second `Recurring` table** below the hand-authored backlog rather than mixed
in with it. `relay recurring list` is the schedule-aware view of those.

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

`relay automerge` is an explicit-only surface — you run it by hand to
catch up tickets whose PR merged out of band. It is no longer wired into
any implicit trigger: `relay status` does **not** trigger automerge (it is
a strictly read-only view that never hits the network or mutates ticket
state as a side effect of rendering — principle 6, fail loud, names
`status`/`show`/`validate` as forbidden mutators), and there is no
post-merge git hook. The explicit command surfaces `gh` errors (missing,
unauthed) loudly.

Posts a distinct Slack line with the ticket title, previous step, and linked
PR (`🎉 *<slug>* "<title>": <prev> → done — <pr-url|PR #<N>> merged`), so the
team can tell auto-bumps apart from manual ones.

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
  installed skill — original URL, selector, timestamp, content/tree digests,
  and a `local_adaptation_notes` field. The notes field is hand-edited in the
  JSON (no CLI flag, keeping the surface small) and a clean `relay skill
  update` preserves it.
- **Local adaptation is detected by digest**, comparing the skill's current
  tree digest against the recorded `installed_tree_digest`. `relay skill
  install-url` refuses to overwrite a locally-adapted skill unless `--force`
  is passed (`install-url` is the only install path with a Relay digest to
  compare, so it is the only one with the guard). `--force` is forwarded to
  the underlying `gh skill install`, rewrites `installed_tree_digest` to the
  freshly installed tree, and resets `local_adaptation_notes` to empty — the
  forced overwrite discards the adaptation, so preserving the note would
  mis-describe the new tree.
- **`conflict` is its own status.** URL-backed update/status checks fetch
  upstream before classifying: locally adapted with upstream unchanged stays
  `skipped-local-adaptation`; locally adapted **and** upstream changed
  reports `conflict` (carrying both refs/digests in details). `relay skill
  update` and `relay skill status --check` use the same vocabulary for the
  same on-disk state, and the skill-update PR body renders conflicts in a
  dedicated section.
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
not two. Notifications are optional on first run (a fresh repo selects no
channels), so with nothing configured this posts nothing and does not crash.
Once Slack is selected it is fail-loud (see `relay/sync`): commands crash if
`$SLACK_WEBHOOK_URL` is unset and the user hasn't opted out via
`[notification.slack].enabled = false`.

## relay secret get \<ref>

Resolve one secret **reference** on demand and print its value to stdout — a
human-facing query, not something agents call. Secrets are declared inline on
each ticket (there is no `[secrets]` catalog), so `get` takes the reference
directly — `op://vault/item/field` (read live via `op read`) or `env:VAR` — and
resolves it through the same shared path `relay launch` uses (no second
resolver). It prints the value only because you explicitly asked; it is never
logged or posted.

Like launch, this fails loud (non-zero, no value printed) when the reference is
a raw literal (nothing to resolve), an `env:VAR` is unset, or `op` is missing /
not signed in / returns non-zero — error messages name the reference, never the
resolved value.

- `relay secret get op://Private/Stripe/api-key` — read and print that
  1Password field.
- `relay secret get env:STRIPE_KEY` — print the value of `$STRIPE_KEY`.

## relay dream

Run Relay's generic cleanup pass now. `dream` is not a built-in command — it
is a default alias for `recurring launch dream`. It scaffolds the
`relay-os/recurring/dream/` recurring task and launches it interactively.

The instantiated task ref is `recurring/dream`: the `recurring/` directory
marks it as generated, and the current period is recorded in
`relay-os/recurring/dream/blackboard.md` as `last_serviced_period`. Running
`relay dream` mid-week reuses that task instead of creating a second one. Dream
scans current task state, runs the known Relay housekeeping pass, writes
results to that run's blackboard, and finishes with `relay mark done`.

## relay recurring

Scan `relay-os/recurring/`, then scaffold and launch every task that is due.

For each template (skipping `_`-prefixed files) `relay recurring` enforces
**one live task per template**: if the generated task at `recurring/<name>` is
already `active` or orphaned `in_progress`, that one is
launched/resumed and no duplicate is scaffolded; only when none is live does it
get-or-create the current run at `relay-os/tasks/recurring/<name>/` and advance
the template blackboard's `last_serviced_period` line. It launches the due ones
**sequentially** — orphaned `in_progress` resumes first, then fresh launches,
each set most-overdue first, one finishing before the next starts. It prints
a scan table (`→ resume` / `→ launch` / `ready` vs `overdue Nd`) before
launching. `done` and `paused` tasks are skipped — never relaunched; a stuck
`in_progress` run defers the next period until it reaches one of those.

Current period only: it does not chase missed periods. Running `relay
recurring` once a month for a weekly template produces one run (this
period's), not a backlog. It does not install or manage system cron —
nothing runs unless you invoke it. `relay-os/scripts/cron.sh` is the
optional entry point if you later wire it into a scheduler yourself.
Dedup after Dream deletes a completed run comes from
`last_serviced_period >= current period_key`; the template `log.md` is
append-only human history, not the dedup source.

`relay recurring --interactive` launches every due task in interactive mode
for that run from an attended TTY, even ones whose template says `mode: auto`
— the debug knob for stepping through a recurring run by hand. It threads
`relay launch --mode interactive` through and rewrites no ticket files.

`relay recurring --all` **forces a real, full run of every template**. It is
*not* a sandbox: the only difference from a bare `relay recurring` is that it
ignores the schedule and the status filter that skips already-serviced / done /
paused templates this period. For every template it get-or-creates the real
`recurring/<name>` period task and launches it — even one that already ran this
period (`relay launch` re-activates a `done`/`paused` ticket, restarting its
workflow at step 1). Everything else is identical to a normal run: real Slack,
real digest-spool drain, real git task-state sync, and the real
`last_serviced_period` high-water advance. There are no `-dbg-` scratch dirs, no
slug-based suppression, no orphan reaping, and no fold-back-to-template-log
step. Use it to force this period's work to re-run without waiting for the
schedule.

**`mode: auto` templates are temporarily skipped** with a stderr line and
a Slack scan-error summary. The auto-launch path produces no live console
output, so scheduled runs would sit silently. **`mode: interactive` templates
are also skipped when `relay recurring` has no stdin/stdout TTY**, because the
agent REPL cannot be driven. Templates should use `mode: script` (or
`mode: interactive` when the scan is launched from a real TTY) until streaming
lands.

**Idle-timeout backstop.** A `mode: interactive` template that *does* launch
(a TTY is present) but whose agent stalls or crashes before signalling done —
never reaching `relay bump` / `mark done` / `panic` — would otherwise block the
sequential sweep forever. Both the bare sweep and `relay recurring --all` arm a
generous idle timeout on each spawned REPL (passed through as `relay launch
--idle-timeout`): if it produces no output and takes no input for that long,
the supervisor tears it down (reported as a clean exit) so the sweep moves on.
`relay recurring --interactive` — a human stepping through by hand — leaves the
REPL unbounded, as does a plain `relay launch`. The default window is 15
minutes; set `RELAY_REPL_IDLE_TIMEOUT` (seconds) to change it, or to `0` /
a non-finite value to disarm the backstop for the sweep.

Dream, REM, and other recurring maintenance loops all use this surface.

## relay recurring launch \<name\>

Scaffold one named recurring template now and launch it, ignoring its
schedule. `name` is the directory name under `relay-os/recurring/`. The task
ref is `recurring/<name>`, so a manual `launch` and a bare `relay recurring`
converge on one stable task directory (idempotent — a second `launch` reuses
the existing task). An orphaned `in_progress` run is resumed rather than
duplicated; a `done` or `paused` run is left alone. This is exactly what the
`relay dream` alias expands to.
`--interactive` runs it in interactive mode even if the template says
`mode: auto`, for debugging one template by hand.

## relay recurring list

Read-only view of the recurring system — scaffolds nothing and launches
nothing (the inspectable counterpart of a bare `relay recurring`, which
get-or-creates each due period's task and runs it). Prints two tables: every
template with its schedule, last/next firing, and current-period state
(`due — not scaffolded`, or the live instance's status); then the **picked
tasks** — the recurring period tasks already on disk, with their status and
step. A template that fails to load (e.g. missing `schedule`) shows as an
error row instead of crashing the view.

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
build = "launch relay-build"
dream = "recurring launch dream"
```

`chat`, `build`, and `dream` are also registered as built-in default aliases,
so they dispatch even in repos whose `relay.toml` predates the line. `create` is a
built-in command, not an alias (it has its own scaffolding behavior beyond
what a `launch bootstrap/...` expansion would give it).

Rules: alias names can't collide with built-in commands; the first
token of the expansion must be a known built-in. Both checked at
config load — fail loud, not silent. Aliases are positional pass-through
only; they don't accept their own flags.

## Pick which command

- Scaffolding a raw new draft → `relay create "<title>"`.
- Guided ticket authoring → `relay ticket` or `relay ticket "<title-or-slug>"`.
- Starting a draft's work → `relay launch <slug>` (activates inline).
- Approving/queueing without launching → `relay mark active <slug>`.
- Pausing a task → `relay mark paused <slug>`.
- Finishing a task (final step, or no workflow) → `relay mark done <slug>`.
- Ticket-less chat session → `relay chat` (alias for
  `launch bootstrap/orient`).
- Running Relay cleanup now → `relay dream`.
- Launching every due recurring task → `relay recurring`.
- Inspecting recurring templates + schedules + instantiated tasks (read-only)
  → `relay recurring list`.
- Forcing a real full run of every template now (ignore schedule + status
  filter) → `relay recurring --all`.
- Launching one named recurring task now → `relay recurring launch <name>`.
- Starting or resuming agent work on a task → `relay launch <slug>`.
- Other bootstrap shim → `relay launch bootstrap/<name>`.
- Advancing a workflow-bound task → `relay bump`.
- Catching up tickets after a teammate merged a PR → `relay automerge`
  (explicit-only; run it by hand).
- Triage view → `relay status`.
- Reading a single task without opening the file → `relay show <slug>`.
- Surfacing a non-blocker note tied to a step transition → `relay bump --message`.
- Surfacing a non-blocker note tied to a status transition → `relay mark <state> --message`.
- Surfacing a non-blocker note that doesn't fit a transition → `relay slack`.
- Surfacing a blocker → `relay panic`.
- Throwing away an abandoned ticket → `relay delete <slug>`.
- Wrapping up a finished ticket (retro + source-dir delete via retro PR) →
  `relay retire <slug>`.

There's also `relay validate [--task <slug>] [--json] [--fix] [--check-slack]
[--check-github]`, a static repo + config diagnostic. By default it scans every task; `--task
<slug>` validates exactly one task directory (files plus strict frontmatter
schema) and is what a human or agent runs after a direct hand-edit to a single
ticket. Relay-owned commands that mutate a task — draft, ticket-authoring exit,
mark, bump, launch-time transitions, recurring/retire scaffolding — run that
same task-scoped check after the write and before reporting success, so
malformed frontmatter fails at the edge of the edit instead of drifting until
launch. `--fix` is deliberately narrow: it creates missing `blackboard.md` and
empty `log.md` files, then reports the remaining issues. It does not rewrite
existing files, freeze workflows, delete locks, or push git state. `--check-github`
is an opt-in preflight that mirrors `--check-slack`: it probes git/GitHub auth
readiness so a raw tool failure surfaces as an actionable setup hint before PR
time instead of surprising an agent mid-run. It probes the *configured* remote
(`git remote get-url <cfg.git_remote>`, not a hardcoded `origin`), checks push
access with a non-mutating `git push --dry-run`, and verifies `gh --version` and
`gh auth status --hostname <host>` for that remote's host. Every probe is fully
non-interactive (`GIT_TERMINAL_PROMPT=0`, ssh `BatchMode=yes`) so a missing
credential fails fast rather than hanging on a hidden prompt; failures are
`(github)` errors excluded from the ok count. It is opt-in because the default
validate path runs no subprocess and reads no network; Relay stores no PAT and
does not reimplement GitHub auth — it just exercises the operator's own `git` and
`gh` setup. Reach for
validation when a command is misbehaving or slack/webhook setup looks broken;
Dream's validate-drift skill is the normal place to apply safe fixes and
broadcast a summary during a Dream run.

## What this context does NOT cover

- The mental model behind these commands (primitives, planes, prompt
  composition, locking) — see `relay/architecture`.
- Where source lives + how to test changes — see `relay/codebase`.
- Reference contracts — frontmatter shapes and primitives are in
  `relay/architecture`; config schemas live in `src/relay/config.py`.
