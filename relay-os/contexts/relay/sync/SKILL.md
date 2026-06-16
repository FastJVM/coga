---
name: relay/sync
description: Notifications and git as relay's sync layers — why a live notification channel is required by default, how task-state git sync works, why failures crash, and how to design new features that respect sync.
---

# Sync layers — notifications and git

## Notifications — the team sync point

Agents work asynchronously. The humans they collaborate with do not.
Multi-user coordination needs a channel where state changes surface as
they happen, or the human side accumulates a stale mental model of what
the agents are doing. That channel, in relay, is the notification layer. Slack
is the first backend behind it, not the whole abstraction.

Relay commands reach that channel through configured notification backends
(`channels = ["slack"]` today), but not every state change belongs there. A
channel shared across many projects and tickets drowns in lifecycle chatter —
humans tune it out, which defeats the point. So relay routes
notification-worthy events into **two tiers** and keeps routine lifecycle churn
out of notifications entirely:

- **Live (urgent)** — posted the moment they happen. A stuck agent or a
  failure must never wait. This is the `notification.post` path.
- **Outcome digest** — done tickets and recurring scan errors, collapsed into
  **one daily digest**. This is the `notification.notify` path: each outcome/error
  appends a structured JSONL record to the `recurring/digest/` ticket's
  blackboard (its `## Spool (pending)` section), and the digest recurring
  ticket flushes the spool once a day via `relay digest` (drain → fetch
  `origin/main` → render Done + Also merged → post one message → empty the
  spool → record a git high-water mark).

Live (urgent) surface — still posts immediately:

- `relay panic` — blocker, owner named.
- `relay slack` — explicit FYI (manual broadcast escape hatch); an
  intentional human broadcast, so batching it would surprise the sender.
- `relay bump --message "<FYI>"` — explicit FYI attached to step movement.
  Message-less bumps are silent.
- `relay launch` script-mode failure — non-zero exit on a `mode: script`
  step.
- `relay launch` — an approved `active` ticket starts and becomes
  `in_progress`. The session-start signal stays live (one per task).

Outcome digest surface — spooled into the daily digest (live fallback below):

- `relay mark done` — done tickets, including manual/script-mode completions
  that have no PR number.
- `relay automerge` (explicit-only; never `relay status`, which is
  read-only) — auto-bumps active/in-progress
  tickets to `done` when their blackboard `## Dev` PR has merged.
- `relay recurring` — only the end-of-run summary when templates failed to
  parse (`recurring-error`).

Silent lifecycle surface — no notification post, no spool record:

- `relay draft` / `relay create` and `relay ticket "<title>"'s raw draft
  creation.
- `relay mark active` and `relay mark paused`.
- `relay bump` with no `--message`.
- Successful `relay recurring` creates.
- `relay retire` creating.

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

## Notifications required by default

When `[notification.slack].enabled` is true (the default), commands crash on
any live Slack-channel failure:

- `[notification.slack].webhook` resolves empty (key absent, or an `env:` reference
  whose variable is unset) → `typer.Exit(1)` with a message pointing the
  user at the `[notification.slack].webhook` key or the opt-out.
- Network or webhook-rejection error during `requests.post` →
  `typer.Exit(1)` with the error and (when `task_path` is given) a line
  appended to that task's `log.md`.

Why crash instead of degrading to stderr-only? Because a silent FYI
becomes a stale mental model on the human side, and that's worse than a
noisy retry. Loud failures force resolution; quiet ones rot.

## Why no notification retry

Earlier versions of `notification.post` retried with exponential backoff. PR
#56 removed that. An FYI is fire-and-forget — by the time a retry
succeeds 6 seconds later, the message is already stale relative to
local state, and a delayed sync is a dishonest sync. Better to fail
fast and let the user retry the command (which re-derives the message
from current state), or use the manual `relay validate --check-slack`
probe before the next batch of work.

## The notification opt-out is an exit, not a default

`[notification.slack].enabled = false` in `relay.local.toml` silences every
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

`[notification.slack.users]` in `relay.toml` supplies the mapping: a relay name (the
token used in a ticket's `owner` / `watchers` fields) → a Slack member
ID. `notification.post` resolves `owner` and `watchers` through it, emitting
`<@U…>` for mapped names and plain text for the rest. A watcher is cc'd
only when mapped — cc'ing an unmapped name notifies no one and is just
noise.

The mapping is supplied by hand because an incoming webhook is
write-only: it can't call `users.list` / `users.lookupByEmail` to resolve
a name itself. Member IDs aren't secret, so the table lives in shared
`relay.toml`, not `relay.local.toml`.

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
  `automerge.py`) — `advance_step`/`mark_done` receive finished `slack_text`,
  and `post()`/`notify()` never reformat. `tests/test_notification_messages.py`
  snapshots the formats; extend it when a string changes.
- **Keep the live text and the digest detail in step.** A call site that uses
  `notify` posts the live string only as a fallback; the spooled record's
  `detail` line must carry the same transition and PR link, or digest users
  see a poorer message than live users (automerge regressed exactly this way
  once).

## Notification implementation pointers

- `src/relay/notification/__init__.py::post(cfg, message, *, task_path=None, owner=None,
  watchers=None, image_url=None)` — the **live** path. Three branches: not
  configured channel(s). Slack has three branches: not enabled → stderr;
  enabled + no webhook → crash; enabled + webhook → POST then crash on
  failure.
- `src/relay/notification/slack.py::SlackChannel` — the Slack backend. It owns
  Slack text rendering (project/owner prefix, watcher cc, image attachment),
  mention rendering, and the webhook POST.
- `src/relay/notification/__init__.py::notify(cfg, slack_text, *, kind, detail, ticket=None,
  owner=None, watchers=None, task_path=None, image_url=None)` — the
  **outcome digest** path. It accepts only `done` and `recurring-error`
  records. When `digest_spool_path(cfg)` is non-None (the
  `recurring/digest/` ticket is installed), it appends a structured record to
  the spool; otherwise it falls back to `post(slack_text, …)`. `kind` is the
  event tag; `detail` is the digest one-liner.
- `src/relay/notification/__init__.py::render_digest(cfg, records, *, date_label,
  also_merged=None)` — renders Done owner sections, an optional "Also merged
  (no ticket)" section, and recurring errors (no `[project]` prefix — `relay
  digest` hands it to `post`, which adds it).
- `[notification].channels = ["slack"]` selects the enabled backend list.
  Unknown channel names fail config load until their backend exists.
- `[notification.slack].webhook` in `relay.toml` (or `relay.local.toml`) — the single
  source for the webhook URL. It is a bearer token, so the committed value
  is an `env:SLACK_WEBHOOK_URL` reference, resolved like `[secrets]` via
  `config._resolve_secret_value`. Legacy `[slack].webhook` and a bare exported
  `SLACK_WEBHOOK_URL` still resolve as deprecated compatibility fallbacks.
  A literal URL is accepted by the parser but must never be committed; use
  `env:` indirection.
- `cfg.slack_enabled` (`bool`, default `True`) and `cfg.slack_webhook`
  (`str | None`) — compatibility fields holding the effective Slack-channel
  config. `[notification.slack].enabled` and `[notification.slack].webhook`
  each resolve with `relay.local.toml` overriding shared, so a machine can
  carry its own webhook while shared `relay.toml` holds a safe `env:`
  reference or omits the key.
- `cfg.slack_users` (`dict[str, str]`, relay name → Slack member ID) —
  parsed from `[notification.slack.users]` in `relay.toml`; legacy
  `[slack.users]` remains a deprecated compatibility input.
- Live callers (`post`): `commands/panic.py`, `commands/slack.py`,
  `commands/launch_script.py` (failure path only),
  `commands/bump.py` when `--message` is present, and
  `commands/launch.py` / `mark.mark_in_progress` (active → in_progress
  session start). Outcome callers (`notify`): `mark.mark_done` (including
  automerge and script-mode completion) and `commands/recurring.py`'s error
  summary. Both paths pass
  `task_path=ref.path` (when a task exists) so a live-post failure trace lands
  in the task's `log.md`.
- `relay validate --check-slack` — probes the webhook with an
  empty-text payload that Slack rejects without notifying the channel.
  Honors the opt-out (skipped when `enabled = false`).

## The daily digest — a blackboard producer/consumer

The digest collapses outcomes into one notification message a day. It is a
**producer → blackboard + git high-water → consumer** pipeline with no side
mechanism:

- **Producer.** `notification.notify` appends one JSONL record per outcome/error to the
  `recurring/digest/` ticket's `blackboard.md`, under a `## Spool (pending)`
  section. The record is self-describing — `ts`, `project`, `kind`, `detail`,
  and (when present) `ticket`, `owner`, `watchers`. JSONL so `detail` can hold
  any text (arrows, pipes, emoji) with no escaping. Captured at event time, so
  a task deleted later the same day is already recorded.
- **Git high-water.** `relay digest` also fetches the configured control branch
  (`origin/main` by default), scans commits since the `### Digest State`
  `last_commit`, and falls back to the last 24 hours on the first run or when
  the recorded commit is unavailable. Merge commits whose PR number already
  appears in a Done record are attributed to that ticket and omitted from
  "Also merged"; remaining non-Relay-state commits render under "Also merged
  (no ticket)." Relay's own state-sync commits are filtered by subject:
  `Sync task state: …` and `Ticket: <slug> — <status>`.
- **The spool is a real blackboard.** It is git-tracked, human-readable, never
  a hidden dotfile — consistent with relay's no-hidden-state rule. It shares
  the file with recurring template state such as `last_serviced_period`; the
  flush parses only valid-JSON lines and rewrites only the spool section, so
  other state is untouched.
- **Consumer.** The `recurring/digest/` ticket (`mode: script`, daily
  `schedule:`) fires through the normal `relay recurring` scan. Its one
  workflow step runs the `relay/digest/flush` skill, whose `script:` calls
  `relay digest` → `commands/digest.run_digest`: read the spool, fetch/scan
  git, render via `render_digest`, `post` one message, drain the spool, and
  update `### Digest State`. Empty spool is not enough to skip posting; new
  merged commits can still produce a digest. The command posts nothing only
  when there are no Done records, no recurring errors, and no post-filter new
  commits.
- **The primitive.** `src/relay/spool.py::append_record(path, record)` /
  `drain(path)` / `read_records(path)` operate on a blackboard's
  `## Spool (pending)` JSONL section via `atomicio.atomic_write_text`. Relay
  runs one CLI process at a time, so appends and drains are serialized by that
  — no lock is introduced, consistent with the no-mutex model. The primitive
  is deliberately notification-agnostic; the digest is its first caller.

## Git — durable task-state sync

Notifications tell the team what changed; git makes the markdown state durable
and shareable. Relay-owned commands that mutate a task directory should commit
the resolved task directory path under `relay-os/tasks/` (top-level or grouped
one level deep) and push it after the live notification post, so `origin/main`
does not drift from the state humans saw in the channel.

Current surface:

- `relay draft` / `relay create` raw creates.
- `relay mark active`, launch-time `active → in_progress`, `relay mark paused`,
  and `relay mark done`.
- `relay bump`.
- `relay automerge`, through the shared `mark_done` finalizer.
- `relay recurring` and `relay retire` creates.
- `relay panic` — the blocker written to the blackboard + log, synced before
  the teardown signal so the commit lands while the process still owns itself.
- `relay ticket` authoring — the edits the launched agent makes to `ticket.md`
  (and the blackboard) inside the subprocess, committed once control returns
  and the result passes validation. relay never calls `ticket.write()` for
  those external edits, so this is the only thing that lands them.

Both `panic` and `ticket` sync through the same `git.sync_task_state` helper,
strictly scoped to the task dir — `relay panic` in particular often fires from
a feature worktree with uncommitted *code*, which is never swept in.

Task state reaches the control branch from **any** branch. When HEAD is the
control branch, Relay commits the task dir and pushes. When HEAD is a feature
branch, Relay commits the task dir on the current branch (so the checkout
reflects ticket state) **and** lands the same files on the control branch
without ever checking out `main`: it builds the control branch's tree in a
*temporary index* (`GIT_INDEX_FILE`), overlays the working-tree task dir,
`commit-tree`s onto the fetched control tip, and pushes that commit straight to
`refs/heads/<control>`. The feature working tree — staged and unstaged code
alike — is never touched, stashed, or reset. A detached HEAD takes the same
cross-branch path but skips the local commit (it would be orphaned).

The push to `refs/heads/<control>` is a compare-and-swap: if the control branch
moved under us (another relay process, a teammate), the
push is rejected non-fast-forward, and a bounded fetch-rebuild-retry loop
refetches the new tip and rebuilds. That push *is* the serialization point — no
lock file is introduced, consistent with `relay/architecture`'s no-mutex model.
Concurrent local or cross-machine processes each fetch→build→push; exactly one
fast-forwards per round and the losers retry, so nothing on the control branch
is clobbered.

Scope is narrow. `src/relay/git.py::sync_task_state(cfg, task_path, *,
message)` stages and commits only the task directory pathspec. It must not use
`git add -A`, and it must not sweep unrelated unstaged or pre-staged files into
the task-state commit — the temp-index plumbing makes that structural for the
cross-branch land, since every staging op runs against the throwaway index.

Failure model:

- `[git].enabled = false` suppresses sync with a stderr line. Like the
  notification opt-out, this is a deliberate exit for dev/test/solo repos, not
  the normal team path.
- A non-git checkout is a soft warning and no-op.
- Git operation failures (missing git, invalid repo state, commit failure,
  fetch/push failure, no remote, or contention exhausting the retry loop) crash
  loud: stderr plus a `log.md` line, then `typer.Exit(1)`. The same-branch push
  stays crash-loud on non-fast-forward; only the cross-branch land retries
  (where rebuilding is trivial because no working tree is involved).

Config lives in `[git]`: `enabled` defaults true, `remote` defaults `origin`,
and `control_branch` defaults `main`. `enabled` may be overridden in
`relay.local.toml`; remote and branch are shared repo policy.

## Design rule for new features

If a new command changes state that other team members need to know
about, it must reach the sync layer — `post` for genuinely urgent events
(a blocker, a failure, an intentional human FYI), `notify` for outcomes or
scheduled-work errors that belong in the daily digest. Pick the tier by
urgency and substance: would a teammate need this within minutes (live), is it
a daily outcome/error (digest), or is it lifecycle audit noise that belongs
only in `log.md` and git? Don't add silent state mutations that bypass both
when the team needs awareness. Conversely, don't emit chatter that doesn't
represent an outcome, urgent exception, or explicit FYI — notifications are the
sync surface, not a debug stream.

If the command mutates a task directory through Relay-owned code, it should
also call `git.sync_task_state` after the live notification post unless the path is
explicitly deferred and documented. The git sync call belongs at the logic
boundary where the file write, validation, log append, and notification post
have all finalized.

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
