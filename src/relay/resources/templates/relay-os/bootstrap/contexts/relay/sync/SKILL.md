---
name: relay/sync
description: Slack and git as relay's sync layers — why Slack is required by default, how task-state git sync works, why failures crash, and how to design new features that respect sync.
---

# Sync layers — Slack and git

## Slack — the team sync point

Agents work asynchronously. The humans they collaborate with do not.
Multi-user coordination needs a channel where state changes surface as
they happen, or the human side accumulates a stale mental model of what
the agents are doing. That channel, in relay, is Slack.

State-changing CLI commands reach that channel via an incoming webhook,
but not all at the same urgency. A channel shared across many projects and
tickets drowns in real-time chatter — humans tune it out, which defeats the
point. So relay routes events into **two tiers**:

- **Live (urgent)** — posted the moment they happen. A stuck agent or a
  failure must never wait. This is the `slack.post` path.
- **Batched (routine)** — collapsed into **one daily digest**, grouped per
  project then per person. This is the `slack.notify` path: each event
  appends a structured JSONL record to the `recurring/digest/` ticket's
  blackboard (its `## Spool (pending)` section), and the digest recurring
  ticket flushes the spool once a day via `relay digest` (drain → group
  project → person → ticket → post one message → empty the spool).

Live (urgent) surface — still posts immediately:

- `relay panic` — blocker, owner named.
- `relay slack` — explicit FYI (manual broadcast escape hatch); an
  intentional human broadcast, so batching it would surprise the sender.
- `relay launch` script-mode failure — non-zero exit on a `mode: script`
  step.
- `relay launch` — an approved `active` ticket starts and becomes
  `in_progress`. The session-start signal stays live (one per task).

Batched surface — spooled into the daily digest (live fallback below):

- `relay draft` / `relay create` (and `relay ticket "<title>"`'s raw draft
  creation) — a new draft ticket lands in the queue.
- `relay mark active` — the moment work is approved.
- `relay mark paused` / `relay mark done` — control-plane transitions away
  from active or in-progress work.
- `relay bump` — step movement (workflow plane only). Optional `--message`
  still piggy-backs an FYI; it rides the spooled record's detail line.
- `relay automerge` (explicit-only; never `relay status`, which is
  read-only) — auto-bumps active/in-progress
  tickets to `done` when their blackboard `## Dev` PR has merged.
- `relay recurring` — one record per scaffolded recurring task, plus an
  end-of-run summary when any templates failed to parse.

The digest is **opt-in by installing the `recurring/digest/` ticket**. When
that ticket is absent, `slack.notify` degrades to a live `post`, so a repo
without the digest keeps the original real-time behavior on every event.
Owners ping as `<@ID>` and watchers cc exactly as a live post does — the
digest reuses `slack._mention`.

Slack is not an "FYI nice-to-have" — it's the synchronization point
between async agents and the people approving, unblocking, or watching
their work.

What deliberately does *not* post at all: relaunching an
already-`in_progress` interactive or auto ticket. The sync-relevant start
transition already happened when the ticket moved `active` → `in_progress`;
subsequent launches are resume attempts.

## Slack required by default

When `[slack].enabled` is true (the default), commands crash on any
Slack failure:

- `[slack].webhook` resolves empty (key absent, or an `env:` reference
  whose variable is unset) → `typer.Exit(1)` with a message pointing the
  user at the `[slack].webhook` key or the opt-out.
- Network or webhook-rejection error during `requests.post` →
  `typer.Exit(1)` with the error and (when `task_path` is given) a line
  appended to that task's `log.md`.

Why crash instead of degrading to stderr-only? Because a silent FYI
becomes a stale mental model on the human side, and that's worse than a
noisy retry. Loud failures force resolution; quiet ones rot.

## Why no Slack retry

Earlier versions of `slack.post` retried with exponential backoff. PR
#56 removed that. An FYI is fire-and-forget — by the time a retry
succeeds 6 seconds later, the message is already stale relative to
local state, and a delayed sync is a dishonest sync. Better to fail
fast and let the user retry the command (which re-derives the message
from current state), or use the manual `relay validate --check-slack`
probe before the next batch of work.

## The Slack opt-out is an exit, not a default

`[slack].enabled = false` in `relay.local.toml` silences every Slack
call to stderr and never crashes. It exists for genuinely solo
contexts: dev/test runs against fake tickets, CI environments where you
don't want webhook spam, single-developer experimentation branches.

The cost of opting out is being out of the sync loop — no teammate sees
your launches, bumps, or panics. Treat `enabled = false` as a
deliberate exit, not a way to "make the warning go away." Once you're
working with another person, turn it back on.

When suppressed, each call still writes one line to stderr (`[slack]
disabled (post suppressed): <message>`) so the user notices their
opt-out is active. Quiet opt-outs become forgotten opt-outs.

## Pinging the owner and watchers

A post names the ticket's `owner` in its `[<project>] [<owner>]` prefix
and cc's any `watchers`. For those names to actually *notify* someone,
Slack needs the `<@U…>` member-ID mention form — a plain `@name` or
`[name]` in incoming-webhook text never pings.

`[slack.users]` in `relay.toml` supplies the mapping: a relay name (the
token used in a ticket's `owner` / `watchers` fields) → a Slack member
ID. `slack.post` resolves `owner` and `watchers` through it, emitting
`<@U…>` for mapped names and plain text for the rest. A watcher is cc'd
only when mapped — cc'ing an unmapped name notifies no one and is just
noise.

The mapping is supplied by hand because an incoming webhook is
write-only: it can't call `users.list` / `users.lookupByEmail` to resolve
a name itself. Member IDs aren't secret, so the table lives in shared
`relay.toml`, not `relay.local.toml`.

## Slack implementation pointers

- `src/relay/slack.py::post(cfg, message, *, task_path=None, owner=None,
  watchers=None, image_url=None)` — the **live** path. Three branches: not
  enabled → stderr; enabled + no webhook → crash; enabled + webhook → POST
  then crash on failure. The private `_mention` helper renders a name as
  `<@ID>` when mapped.
- `src/relay/slack.py::notify(cfg, slack_text, *, kind, detail, ticket=None,
  owner=None, watchers=None, task_path=None, image_url=None)` — the
  **batchable** path. When `digest_spool_path(cfg)` is non-None (the
  `recurring/digest/` ticket is installed), it appends a structured record to
  the spool; otherwise it falls back to `post(slack_text, …)`. `kind` is a
  short event tag; `detail` is the digest one-liner.
- `src/relay/slack.py::render_digest(cfg, records, *, date_label)` — groups
  drained records project → person → ticket and returns one message (no
  `[project]` prefix — `relay digest` hands it to `post`, which adds it).
- `[slack].webhook` in `relay.toml` (or `relay.local.toml`) — the single
  source for the webhook URL. It is a bearer token, so the committed value
  is an `env:SLACK_WEBHOOK_URL` reference, resolved like `[secrets]` via
  `config._resolve_secret_value`. A bare exported `SLACK_WEBHOOK_URL` with no
  `webhook` key is *not* configured — the environment reaches relay only
  through that reference. A literal URL is accepted by the parser but must
  never be committed; use `env:` indirection.
- `cfg.slack_enabled` (`bool`, default `True`) and `cfg.slack_webhook`
  (`str | None`) — both come from `relay.config`. `[slack].enabled` and
  `[slack].webhook` each resolve with `relay.local.toml` overriding shared
  (`_resolve_slack_enabled` / `_resolve_slack_webhook`), so a machine can
  carry its own webhook while shared `relay.toml` holds a safe `env:`
  reference or omits the key.
- `cfg.slack_users` (`dict[str, str]`, relay name → Slack member ID) —
  parsed from `[slack.users]` in `relay.toml` by `_parse_slack_users`.
- Live callers (`post`): `commands/panic.py`, `commands/slack.py`,
  `commands/launch_script.py` (failure path only), and
  `commands/launch.py` / `mark.mark_in_progress` (active → in_progress
  session start). Batchable callers (`notify`): `commands/create.py`,
  `commands/retire.py`, `commands/recurring.py` (per-scaffold + error
  summary), `mark.mark_active` / `mark_paused` / `mark_done`,
  `bump.advance_step`, and `automerge.auto_bump_merged`. Both paths pass
  `task_path=ref.path` (when a task exists) so a live-post failure trace lands
  in the task's `log.md`.
- `relay validate --check-slack` — probes the webhook with an
  empty-text payload that Slack rejects without notifying the channel.
  Honors the opt-out (skipped when `enabled = false`).

## The daily digest — a blackboard producer/consumer

The digest collapses the batchable surface into one Slack message a day. It
is a **producer → blackboard → consumer** pipeline with no side mechanism:

- **Producer.** `slack.notify` appends one JSONL record per event to the
  `recurring/digest/` ticket's `blackboard.md`, under a `## Spool (pending)`
  section. The record is self-describing — `ts`, `project`, `kind`, `detail`,
  and (when present) `ticket`, `owner`, `watchers`. JSONL so `detail` can hold
  any text (arrows, pipes, emoji) with no escaping. Captured at event time, so
  a task deleted later the same day is already recorded — no git-log scan.
- **The spool is a real blackboard.** It is git-tracked, human-readable, never
  a hidden dotfile — consistent with relay's no-hidden-state rule. It shares
  the file with `recurring._record_run`'s `scaffolded …` ledger lines; the
  flush parses only valid-JSON lines and rewrites only the spool section, so
  the ledger is untouched.
- **Consumer.** The `recurring/digest/` ticket (`mode: script`, daily
  `schedule:`) fires through the normal `relay recurring` scan. Its one
  workflow step runs the `relay/digest/flush` skill, whose `script:` calls
  `relay digest` → `commands/digest.run_digest`: drain the spool, render via
  `render_digest`, `post` one message, leave the spool emptied. An empty spool
  is a silent no-op (idempotent), so a quiet day or a same-day re-run posts
  nothing.
- **The primitive.** `src/relay/spool.py::append_record(path, record)` /
  `drain(path)` / `read_records(path)` operate on a blackboard's
  `## Spool (pending)` JSONL section via `atomicio.atomic_write_text`. Relay
  runs one CLI process at a time, so appends and drains are serialized by that
  — no lock is introduced, consistent with the no-mutex model. The primitive
  is deliberately Slack-agnostic; the digest is its first caller.

## Git — durable task-state sync

Slack tells the team what changed; git makes the markdown state durable and
shareable. Relay-owned commands that mutate a task directory should commit
the resolved task directory path under `relay-os/tasks/` (top-level or grouped
one level deep) and push it after the Slack post, so `origin/main` does not
drift from the state humans saw in Slack.

Current surface:

- `relay draft` / `relay create` raw scaffolds.
- `relay mark active`, launch-time `active → in_progress`, `relay mark paused`,
  and `relay mark done`.
- `relay bump`.
- `relay automerge`, through the shared `mark_done` finalizer.
- `relay recurring` and `relay retire` scaffolds.
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

- `[git].enabled = false` suppresses sync with a stderr line. Like Slack's
  opt-out, this is a deliberate exit for dev/test/solo repos, not the normal
  team path.
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
(a blocker, a failure, an intentional human FYI), `notify` for routine
state changes that can wait for the daily digest. Pick the tier by urgency:
would a teammate need this within minutes (live), or is once-a-day, grouped
per person, enough (batched)? Don't add silent state mutations that bypass
both. Conversely, don't emit chatter that doesn't represent a state change —
Slack is the sync log, not a debug stream.

If the command mutates a task directory through Relay-owned code, it should
also call `git.sync_task_state` after the Slack post unless the path is
explicitly deferred and documented. The git sync call belongs at the logic
boundary where the file write, validation, log append, and Slack post have
all finalized.

When the post needs to describe state that has *just* changed, the
command echoes the local outcome to stdout *before* calling
`slack.post`. That way, if Slack crashes the user still sees the
local-state confirmation on stdout above the error on stderr, and can
reason about idempotency (most state changes — like `bump` — should
not be re-run blindly after a Slack failure).

## Future direction — bidirectional sync

Today the sync is outbound only: agents/CLI → channel. The obvious next
step is inbound: humans replying / reacting / running slash commands in
the channel that reach back into the agent. A Slack app with the events
API or slash-command endpoints would close the loop.

The current `slack.post` API doesn't preclude this — it just doesn't
implement it yet. When designing new sync-touching features, avoid
baking in "outbound-only" assumptions; treat the Slack channel as a
two-way medium that's currently used in one direction.
