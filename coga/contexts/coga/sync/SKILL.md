---
name: coga/sync
description: Notifications and git as coga's sync layers — why notifications are optional on first run but configured Slack fails loud, how task-state git sync works, why failures crash, and how to design new features that respect sync.
---

# Sync layers — notifications and git

## Notifications — the team sync point

Agents work asynchronously. The humans they collaborate with do not.
Multi-user coordination needs a channel where state changes surface as
they happen, or the human side accumulates a stale mental model of what
the agents are doing. That channel, in coga, is the notification layer. Slack
is the first backend behind it, not the whole abstraction.

Coga commands reach that channel through configured notification backends
(`channels = ["slack"]` today), but not every state change belongs there. A
channel shared across many projects and tickets drowns in lifecycle chatter —
humans tune it out, which defeats the point. So coga routes
notification-worthy events into **two tiers** and keeps routine lifecycle churn
out of notifications entirely:

- **Live (urgent)** — posted the moment they happen. A stuck agent or a
  failure must never wait. This is the `notification.post` path.
- **Outcome digest** — done tickets and recurring scan errors, collapsed into
  **one daily digest**. This is the `notification.notify` path: each outcome/error
  appends a structured JSONL record to the dedicated `recurring/digest/spool.md`
  file (its `## Spool (pending)` section), and the digest recurring
  ticket flushes the spool once a day via `coga digest` (read unconsumed → fetch
  `origin/main` → render Done + Also merged → post one message → drain (advance
  the watermark + trim the consumed prefix) → record a git high-water mark).

Live (urgent) surface — still posts immediately:

- `coga panic` — blocker, owner named.
- `coga slack` — explicit FYI (manual broadcast escape hatch); an
  intentional human broadcast, so batching it would surprise the sender.
- `coga bump --message "<FYI>"` — explicit FYI attached to step movement.
  Message-less bumps are silent.
- `coga launch` script-step failure — non-zero exit on a script step
  step.
- `coga launch` — an approved `active` ticket starts and becomes
  `in_progress`. The session-start signal stays live (one per task).

Outcome digest surface — spooled into the daily digest (live fallback below):

- `coga mark done` — done tickets, including manual/script-mode completions
  that have no PR number.
- the `autoclose-merged` recurring sweep (never `coga status`, which is
  read-only) — auto-bumps active/in-progress
  tickets to `done` when their blackboard `## Dev` PR has merged. This daily
  sweep is the sole trigger; there is no manual `automerge` command.
- `coga recurring` — only the end-of-run summary when templates failed to
  parse (`recurring-error`).

Silent lifecycle surface — no notification post, no spool record:

- `coga create` and `coga ticket "<title>"'s raw draft
  creation.
- `coga mark active` and `coga mark paused`.
- `coga bump` with no `--message`.
- Successful `coga recurring` creates.
- `coga retire` creating.

The digest is **opt-in by installing the `recurring/digest/` ticket**. When
that ticket is absent, `notification.notify` degrades to a live `post` for the
same outcome/error events. It does not revive the silent lifecycle surface.
Owners ping as `<@ID>` and watchers cc exactly as a live post does — the
digest reuses Slack-channel mention rendering.

Notifications are not an "FYI nice-to-have" — they are the synchronization
point between async agents and the people approving, unblocking, or watching
their work. Slack is channel #1 because it is where this team currently
coordinates.

What also deliberately does *not* post at all: relaunching an
already-`in_progress` interactive or auto ticket. The sync-relevant start
transition already happened when the ticket moved `active` → `in_progress`;
subsequent launches are resume attempts.

## Notifications optional on first run; configured Slack fails loud

A fresh `coga init` selects no notification channels (`[notification]
channels = []`), so a brand-new user runs `draft`/`mark`/`launch`/`bump`
without configuring anything. Notifications are opt-in: a repo turns Slack on
by selecting the channel and pointing it at a webhook (see `coga/cli` for the
exact snippet). With no channel selected, `notification.post` takes its
no-channel branch — one stderr line, no crash. When `[notification].channels`
is absent entirely, Slack is *inferred* only from opt-in/compat evidence (a
`[notification.slack]` table, a legacy `[slack]` table, or a bare
`SLACK_WEBHOOK_URL`); with none of those, channels resolve to `()`.

Once Slack *is* selected and enabled (`[notification.slack].enabled` defaults
to true), the fail-loud contract holds — commands crash on any live
Slack-channel failure:

- `[notification.slack].webhook` resolves empty (key absent, or an `env:` reference
  whose variable is unset) → `typer.Exit(1)` with a message pointing the
  user at the `[notification.slack].webhook` key, removing slack from
  `[notification].channels`, or the opt-out.
- Network or webhook-rejection error during `requests.post` →
  `typer.Exit(1)` with the error and (when `task_path` is given) a line
  appended (tagged with that task's ref) to the repo-global `coga/log.md`.

Why crash instead of degrading to stderr-only? Because a silent FYI
becomes a stale mental model on the human side, and that's worse than a
noisy retry. Loud failures force resolution; quiet ones rot. That bargain
applies once a team has opted in — before then there is no sync loop to keep
honest, which is why first run selects nothing.

## Why no notification retry

Earlier versions of `notification.post` retried with exponential backoff. PR
#56 removed that. An FYI is fire-and-forget — by the time a retry
succeeds 6 seconds later, the message is already stale relative to
local state, and a delayed sync is a dishonest sync. Better to fail
fast and let the user retry the command (which re-derives the message
from current state), or use the manual `coga validate --check-slack`
probe before the next batch of work.

## The notification opt-out is an exit, not a default

`[notification.slack].enabled = false` in `coga.local.toml` silences every
Slack-channel call to stderr and never crashes. It exists for genuinely solo
contexts: dev/test runs against fake tickets, CI environments where you
don't want webhook spam, single-developer experimentation branches.

The cost of opting out is being out of the sync loop — no teammate sees
your launches, bumps, or panics. Treat `enabled = false` as a
deliberate exit, not a way to "make the warning go away." Once you're
working with another person, turn it back on.

When suppressed, each call still writes one line to stderr (`[slack] disabled
(post suppressed): <message>`) so the user notices their
opt-out is active. Quiet opt-outs become forgotten opt-outs.

## Pinging the owner and watchers

A post names the ticket's `owner` in its `[<project>] [<owner>]` prefix
and cc's any `watchers`. For those names to actually *notify* someone,
Slack needs the `<@U…>` member-ID mention form — a plain `@name` or
`[name]` in incoming-webhook text never pings.

`[notification.slack.users]` in `coga.toml` supplies the mapping: a coga name (the
token used in a ticket's `owner` / `watchers` fields) → a Slack member
ID. `notification.post` resolves `owner` and `watchers` through it, emitting
`<@U…>` for mapped names and plain text for the rest. A watcher is cc'd
only when mapped — cc'ing an unmapped name notifies no one and is just
noise.

The mapping is supplied by hand because an incoming webhook is
write-only: it can't call `users.list` / `users.lookupByEmail` to resolve
a name itself. Member IDs aren't secret, so the table lives in shared
`coga.toml`, not `coga.local.toml`.

## Message format conventions

Every **per-ticket** notification rendered for Slack (live or spooled) follows
one uniform shape.
When adding or editing a call site, match these rules instead of inventing a
new string:

- **Owner is the prefix, not the text.** `post()`/`notify()` already prepend
  `[<project>] [<owner>]` and ping the owner as `<@ID>`. Never add an in-text
  `(owner: …)` suffix — it duplicates the prefix ping.
- **Title is always present.** `*{slug}* "{title}"`, so a single Slack line is
  self-contained without opening the repo.
- **`→` is a transition and shows the prior state.** Step/status moves render
  `{prev-step} → {new-step}` or `{prev-step} → done`. A workflow-less ticket
  has no prior step, so its done posts collapse the transition ("finished").
- **`:` introduces the body** after `*{slug}* "{title}"`; **`(key: value)` is
  an aside** (`(assignee: …)`, `(step N/total)`); **`—` is reserved for the
  optional trailing FYI** (`bump --message`, pause reasons, retire
  annotations).
- **PR references are Slack links**: `<{url}|PR #{N}>`, never plain `PR #N`
  (plain text doesn't link in incoming-webhook posts).
- Message strings are built **at the call sites** (`commands/*.py`,
  `autoclose.py`) — `advance_step`/`mark_done` receive finished `slack_text`,
  and `post()`/`notify()` never reformat. `tests/test_notification_messages.py`
  snapshots the formats; extend it when a string changes.
- **Keep the live text and the digest detail in step.** A call site that uses
  `notify` posts the live string only as a fallback; the spooled record's
  `detail` line must carry the same transition and PR link, or digest users
  see a poorer message than live users (the merged-PR auto-close regressed
  exactly this way once).

## Notification implementation pointers

- `src/coga/notification/__init__.py::post(cfg, message, *, task_path=None, owner=None,
  watchers=None, image_url=None)` — the **live** path. Three branches: not
  configured channel(s). Slack has three branches: not enabled → stderr;
  enabled + no webhook → crash; enabled + webhook → POST then crash on
  failure.
- `src/coga/notification/slack.py::SlackChannel` — the Slack backend. It owns
  Slack text rendering (project/owner prefix, watcher cc, image attachment),
  mention rendering, and the webhook POST.
- `src/coga/notification/__init__.py::notify(cfg, slack_text, *, kind, detail, ticket=None,
  owner=None, watchers=None, task_path=None, image_url=None)` — the
  **outcome digest** path. It accepts only `done` and `recurring-error`
  records. When `digest_spool_path(cfg)` is non-None (the
  `recurring/digest/spool.md` file is installed), it appends a structured record
  to the spool; otherwise it falls back to `post(slack_text, …)`. `kind` is the
  event tag; `detail` is the digest one-liner.
- `src/coga/notification/__init__.py::render_digest(cfg, records, *, date_label,
  also_merged=None)` — renders Done owner sections, an optional "Also merged
  (no ticket)" section, and recurring errors (no `[project]` prefix — `coga
  digest` hands it to `post`, which adds it).
- `[notification].channels = ["slack"]` selects the enabled backend list.
  Unknown channel names fail config load until their backend exists.
- `[notification.slack].webhook` in `coga.toml` (or `coga.local.toml`) — the single
  source for the webhook URL. It is a bearer token, so the committed value
  is an `env:SLACK_WEBHOOK_URL` reference, resolved via
  `config._resolve_secret_value`. Legacy `[slack].webhook` and a bare exported
  `SLACK_WEBHOOK_URL` still resolve as deprecated compatibility fallbacks.
  A literal URL is accepted by the parser but must never be committed; use
  `env:` indirection.
- `cfg.slack_enabled` (`bool`, default `True`) and `cfg.slack_webhook`
  (`str | None`) — compatibility fields holding the effective Slack-channel
  config. `[notification.slack].enabled` and `[notification.slack].webhook`
  each resolve with `coga.local.toml` overriding shared, so a machine can
  carry its own webhook while shared `coga.toml` holds a safe `env:`
  reference or omits the key.
- `cfg.slack_users` (`dict[str, str]`, coga name → Slack member ID) —
  parsed from `[notification.slack.users]` in `coga.toml`; legacy
  `[slack.users]` remains a deprecated compatibility input.
- Live callers (`post`): `commands/panic.py`, `commands/slack.py`,
  `commands/launch_script.py` (failure path only),
  `commands/bump.py` when `--message` is present, and
  `commands/launch.py` / `mark.mark_in_progress` (active → in_progress
  session start). Outcome callers (`notify`): `mark.mark_done` (including
  the autoclose sweep and script-mode completion) and `commands/recurring.py`'s error
  summary. Both paths pass
  `task_path=ref.path` (when a task exists) so a live-post failure trace lands
  in the repo-global `coga/log.md`, tagged with the task ref.
- `coga validate --check-slack` — probes the webhook with an
  empty-text payload that Slack rejects without notifying the channel.
  Honors the opt-out (skipped when `enabled = false`).

## The daily digest — a blackboard producer/consumer

The digest collapses outcomes into one notification message a day. It is a
**producer → blackboard + git high-water → consumer** pipeline with no side
mechanism:

- **Producer.** `notification.notify` appends one JSONL record per outcome/error to the
  dedicated `recurring/digest/spool.md` file's `## Spool (pending)` section. The
  record is self-describing — a unique `id`, `ts`, `project`, `kind`, `detail`,
  and (when present) `ticket`, `owner`, `watchers`. JSONL so `detail` can hold
  any text (arrows, pipes, emoji) with no escaping. Captured at event time, so
  a task deleted later the same day is already recorded.
- **Git high-water.** `coga digest` also fetches the configured control branch
  (`origin/main` by default), scans commits since the `### Digest State`
  `last_commit`, and falls back to the last 24 hours on the first run or when
  the recorded commit is unavailable. Merge commits whose PR number already
  appears in a Done record are attributed to that ticket and omitted from
  "Also merged"; remaining non-Coga-state commits render under "Also merged
  (no ticket)." Coga's own state-sync commits are filtered by subject:
  `Sync task state: …` and `Ticket: <slug> — <status>`.
- **The spool is a real, dedicated file.** `recurring/digest/spool.md` is
  git-tracked, human-readable, never a hidden dotfile — consistent with coga's
  no-hidden-state rule. It is kept *separate* from the digest ticket and marked
  `merge=union` (`.gitattributes`) so concurrent producer appends merge without
  ever touching the ticket's YAML frontmatter. The git high-water mark
  (`### Digest State`) lives in the ticket, not the spool, because it is
  single-writer consumer state that must not ride union semantics.
- **Consumer.** The `recurring/digest/` ticket (a script task, daily
  `schedule:`) fires through the normal `coga recurring` scan. Its one
  workflow step runs the `coga/digest/flush` skill, whose `script:` calls
  `coga digest` → `commands/digest.run_digest`: read the **unconsumed** records,
  fetch/scan git, render via `render_digest`, `post` one message, **drain**
  (advance the watermark + trim the consumed prefix), and update
  `### Digest State`. Records are de-duped by content before rendering, so the
  same event recorded by two clones posts once. Empty spool is not enough to
  skip posting; new merged commits can still produce a digest. The command posts
  nothing only when there are no Done records, no recurring errors, and no
  post-filter new commits.
- **The primitive.** `src/coga/spool.py::append_record(path, record)` /
  `read_unconsumed(path)` / `drain(path)` / `read_records(path)` operate on the
  spool file's `## Spool (pending)` JSONL section via
  `atomicio.atomic_write_text`. There is no lock and no "one process at a time"
  assumption (there never was — two clones against one origin routinely race):
  the spool is mergeable **by construction**, the contract documented next. The
  primitive is deliberately notification-agnostic; the digest is its first
  caller.

### Why the spool is a contended file, and how it stays mergeable

State-plane writes — ticket transitions, the digest spool, recurring markers,
dream logs — are committed **directly to `origin/main`** by `sync_task_state` /
`_push_control_branch`, with no branch and no PR. (Only `(#NN)` commits go
through PRs; those are the code plane.) So any number of coga processes — in
this repo, in another clone, on another machine — push state straight to the
same `main`. The digest spool (`recurring/digest/spool.md`'s
`## Spool (pending)`) is the hottest such file: every done/error event appends
to it, and the daily `coga digest` drains it. Two writers therefore routinely
collide on it during a rejected-push → `rebase --autostash` recovery.

git resolves a 3-way merge cleanly only when the two sides' changed line ranges
don't touch. The spool is engineered around that one fact, with **two** distinct
concurrency cases and a different mechanism for each:

1. **Append vs append** (two producers each add a record at the bottom). Plain
   git conflicts — both insert at the same EOF anchor. This is resolved by
   marking the spool file `merge=union` in `.gitattributes`: union keeps
   **both** sides' lines. It is *safe here precisely because both sides only
   add* — there is nothing to resurrect. Records carry a unique `id`, so the
   ours-then-theirs order union picks is harmless (the digest de-dups by
   content, and orders by `ts`/`id`, not file position).

2. **Drain vs append** (the digest consumes while a producer adds). This is the
   dangerous case, and `merge=union` makes it *worse*: if union ever sees a hunk
   where one side **deleted** lines, it keeps them — resurrecting just-consumed
   records (the historical `e66c302 "restore PR #368 spool record"` bug; stale
   records lingering for days). The fix is structural, not a merge driver:

   - Producers **append only at the bottom**, never touching the watermark or
     existing records.
   - A `consumed_through: <id>` watermark in a fixed slot names the last record
     the digest has posted.
   - The digest **drains by compacting the consumed *prefix*** — it deletes the
     run of already-posted records from the **top**, but always **keeps the
     newest record in place as an anchor** (and never empties the tail).

   Now the delete (top) and any concurrent append (bottom) are separated by the
   anchor — disjoint hunks — so git auto-merges them with **no conflict and no
   resurrection**, and `merge=union` is never invoked on a delete. The watermark
   stops the retained anchor being re-posted next run. Size stays bounded to
   ~one digest interval of records plus the anchor.

**The invariant, stated once:** deletes only at the top, appends only at the
bottom, always an untouched anchor between them. `merge=union` is the *backstop*
for the pure-append collision (case 1); prefix-compaction is what guarantees
union never has to touch a delete (case 2). The original `drain` violated this
by rewriting the whole section to empty — deleting the very region producers
append to — which was the entire root cause of the recurring conflict markers
and orphaned `autostash` stashes.

The same-branch push retry that triggers all this (`git.py::_rebase_onto_remote`)
is itself hardened to never leave the wound behind: it stashes dirty changes
explicitly (not `rebase --autostash`), and on any rebase or pop failure resets
to the pre-sync tip and re-applies the stash there — so a failed recovery leaves
no conflict markers and no orphaned stash, only a reported sync miss.

(Process-level races within a single clone — a recurring sweep and an agent's
`coga mark`/`bump` both `rebase --autostash`-ing one working tree — are a
separate concern handled by per-agent worktree isolation, tracked in its own
ticket. coga is intentionally lock-free; this contract is what makes that safe
for the spool.)

## Git — durable task-state sync

Notifications tell the team what changed; git makes the markdown state durable
and shareable. Coga-owned commands that mutate a task directory should commit
the resolved task directory path under `coga/tasks/` (top-level or nested
in a sub-directory) and push it after the live notification post, so
`origin/main` does not drift from the state humans saw in the channel.

Current surface:

- `coga create` raw creates.
- `coga mark active`, launch-time `active → in_progress`, `coga mark paused`,
  and `coga mark done`.
- `coga bump`.
- the `autoclose-merged` sweep, through the shared `mark_done` finalizer.
- `coga recurring` and `coga retire` creates.
- `coga panic` — the blocker written to the blackboard + log, synced before
  the teardown signal so the commit lands while the process still owns itself.
- `coga ticket` authoring — the edits the launched agent makes to `ticket.md`
  (and the blackboard) inside the subprocess, committed once control returns
  and the result passes validation. coga never calls `ticket.write()` for
  those external edits, so this is the only thing that lands them.

Both `panic` and `ticket` sync through the same `git.sync_task_state` helper,
strictly scoped to the task dir — `coga panic` in particular often fires from
a feature worktree with uncommitted *code*, which is never swept in.

Task state reaches the control branch from **any** branch. When HEAD is the
control branch, Coga commits the task dir and pushes. When HEAD is a feature
branch, Coga commits the task dir on the current branch (so the checkout
reflects ticket state) **and** lands the same files on the control branch
without ever checking out `main`: it builds the control branch's tree in a
*temporary index* (`GIT_INDEX_FILE`), overlays the working-tree task dir,
`commit-tree`s onto the fetched control tip, and pushes that commit straight to
`refs/heads/<control>`. The feature working tree — staged and unstaged code
alike — is never touched, stashed, or reset. A detached HEAD takes the same
cross-branch path but skips the local commit (it would be orphaned).

The push to `refs/heads/<control>` is a compare-and-swap: if the control branch
moved under us (another coga process, a teammate), the
push is rejected non-fast-forward, and a bounded fetch-rebuild-retry loop
refetches the new tip and rebuilds. That push *is* the serialization point — no
lock file is introduced, consistent with `coga/architecture`'s no-mutex model.
Concurrent local or cross-machine processes each fetch→build→push; exactly one
fast-forwards per round and the losers retry, so nothing on the control branch
is clobbered.

Scope is narrow. `src/coga/git.py::sync_task_state(cfg, task_path, *,
message)` stages and commits only the task directory pathspec. It must not use
`git add -A`, and it must not sweep unrelated unstaged or pre-staged files into
the task-state commit — the temp-index plumbing makes that structural for the
cross-branch land, since every staging op runs against the throwaway index.

### The catch-all subtree sweep — `sync_coga_state`

The per-transition syncs above each commit the *one* file a command intended to
change, with a human-readable message. But two classes of write land *past* the
last per-command sync and would otherwise sit dirty forever:

- **Machine side-effects.** The dominant one is the per-session `## Usage`
  record `coga launch` appends *after* the agent's final `bump`/`mark` (so
  after the last sync). The digest spool and stray launch log lines are the same
  shape.
- **Human hand-edits.** A person editing a ticket body, blackboard, or context
  directly in the working tree — no command ran, so nothing committed it.

`src/coga/git.py::sync_coga_state(cfg, *, message="Sync coga state")` closes
both. In the normal nested layout it commits **everything dirty under the
`coga/` subtree** (`cfg.repo_root`, where `coga.toml` lives). In older/root
layouts where `coga.toml` lives at the git toplevel, it scopes to the known
Coga OS pathspecs (`tasks`, `contexts`, `skills`, `workflows`, `recurring`,
`bootstrap`, `coga.toml`, `context.md`, `log.md`) instead of treating the whole
git root as Coga state. A full `git status` under those pathspecs captures
modifications, deletions, renames, **and new untracked files**. This is *not*
the forbidden `git add -A`: the subtree/pathspec boundary is exactly the
OS-state line the "Scope is narrow" rule draws, so product code (`src/`,
`tests/`) is structurally never swept in. Branch handling and the
`merge=union` split reuse the same machinery as `sync_paths` (union files —
`log.md`, the digest spool — committed locally + union-merged onto the control
branch, never landed via the wholesale-replace overlay); union membership is
asked of git directly via `git check-attr merge`, so any future `merge=union`
file is handled automatically. Same non-fatal failure model: a sweep that can't
reach the control branch is surfaced (stderr + `coga/log.md`), never a crash.

It is wired at two boundaries, *in addition to* — never replacing — the
per-transition syncs, which keep the readable git history and digest filtering:

- **Launch teardown**, after `usage_tracking.capture_session`, so each step's
  usage record commits promptly. A supervised chain reaches this finally once
  per step, where the CLI-dispatch boundary fires only once for the whole
  launch.
- **The CLI dispatch boundary** (`cli.py::main`'s `finally` around `app()`),
  for mutating commands only. Read-only commands (`status`, `show`, `validate`,
  `usage`), read-only group subcommands (`skill status`, `recurring list`,
  `secret get`), no-args/help group invocations (`mark`, `skill`),
  `init`/`uninstall`, and `--help`/option invocations are excluded —
  `coga/principles` #6 forbids a render from mutating as a side effect.

The semantics this buys (and accepts): a human hand-edit commits on the **next
coga command**, not the instant they save. Lazy, on-access convergence — the
working tree is the source of truth and git catches up at the next invocation.
This is the deliberate no-daemon alternative to instant commits (`coga/
architecture`: "no database, no daemon, no in-memory state"). The sweep's commit
subject (`Sync coga state`) is filtered out of the daily digest's "Also merged"
section alongside the per-transition state-sync subjects.

Failure model:

- `[git].enabled = false` suppresses sync with a stderr line. Like the
  notification opt-out, this is a deliberate exit for dev/test/solo repos, not
  the normal team path.
- A non-git checkout is a soft warning and no-op.
- Git operation failures (missing git, invalid repo state, commit failure,
  fetch/push failure, no remote, or contention exhausting the retry loop) crash
  loud: stderr plus a repo-global `coga/log.md` line, then `typer.Exit(1)`. The same-branch push
  stays crash-loud on non-fast-forward; only the cross-branch land retries
  (where rebuilding is trivial because no working tree is involved).

Config lives in `[git]`: `enabled` defaults true, `remote` defaults `origin`,
and `control_branch` defaults `main`. `enabled` may be overridden in
`coga.local.toml`; remote and branch are shared repo policy.

## Design rule for new features

If a new command changes state that other team members need to know
about, it must reach the sync layer — `post` for genuinely urgent events
(a blocker, a failure, an intentional human FYI), `notify` for outcomes or
scheduled-work errors that belong in the daily digest. Pick the tier by
urgency and substance: would a teammate need this within minutes (live), is it
a daily outcome/error (digest), or is it lifecycle audit noise that belongs
only in the global `coga/log.md` and git? Don't add silent state mutations that bypass both
when the team needs awareness. Conversely, don't emit chatter that doesn't
represent an outcome, urgent exception, or explicit FYI — notifications are the
sync surface, not a debug stream.

If the command mutates a task directory through Coga-owned code, it should
also call `git.sync_task_state` after the live notification post unless the path is
explicitly deferred and documented. The git sync call belongs at the logic
boundary where the file write, validation, log append, and notification post
have all finalized. A meaningful per-transition sync is still required even
though the CLI-dispatch `sync_coga_state` sweep would eventually catch the
files — the sweep is a backstop with a generic message, not a substitute for the
readable, individually-attributed state commit (and the digest's commit-subject
filter relies on those per-transition subjects).

When the post needs to describe state that has *just* changed, the
command echoes the local outcome to stdout *before* calling
`notification.post`. That way, if the notification channel crashes the user
still sees the local-state confirmation on stdout above the error on stderr,
and can reason about idempotency (most state changes — like `bump` — should not
be re-run blindly after a notification failure).

## Future direction — bidirectional sync

Today the sync is outbound only: agents/CLI → channel. The obvious next step is
inbound: humans replying / reacting / running slash commands in the channel
that reach back into the agent. For Slack, an app with the events API or
slash-command endpoints would close the loop.

The current `notification.post` API doesn't preclude this — it just doesn't
implement it yet. When designing new sync-touching features, avoid
baking in "outbound-only" assumptions; treat the Slack channel as a
two-way medium that's currently used in one direction.
