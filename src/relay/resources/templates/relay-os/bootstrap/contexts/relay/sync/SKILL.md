---
name: relay/sync
description: Slack as relay's point of sync between agents and humans — why it's required by default, why failures crash, and how to design new features that respect the sync layer.
---

# Slack — the team sync point

Agents work asynchronously. The humans they collaborate with do not.
Multi-user coordination needs a channel where state changes surface as
they happen, or the human side accumulates a stale mental model of what
the agents are doing. That channel, in relay, is Slack.

State-changing CLI commands post to the same Slack channel via an
incoming webhook. The current broadcast surface:

- `relay draft` / `relay create` — a new raw draft ticket lands in the queue.
- `relay ticket "<title>"` — also posts the raw draft creation before the
  authoring interview starts.
- `relay recurring` — one post per scaffolded recurring task,
  plus an end-of-run summary when any templates failed to parse.
- `relay mark active` — the moment work is approved, distinct from
  the *session* opening.
- `relay launch` — an approved `active` ticket starts and becomes
  `in_progress`.
- `relay mark paused` / `relay mark done` — control-plane transitions away
  from active or in-progress work.
- `relay bump` — step movement (workflow plane only).
  Optional `--message` piggy-backs an FYI onto any transition broadcast.
- `relay automerge` (and the `post-merge` hook + `relay status` callers
  that wrap it) — auto-bumps active/in-progress tickets to `done` when their
  blackboard `## Dev` PR has merged. Posts a distinct
  `🎉 *<slug>* "<title>" auto-bumped on merge of PR #<N>` line.
- `relay panic` — blocker, owner named.
- `relay slack` — explicit FYI (manual broadcast escape hatch).
- `relay launch` script-mode failure — non-zero exit on a
  `mode: script` step.

Slack is not an "FYI nice-to-have" — it's the synchronization point
between async agents and the people approving, unblocking, or watching
their work.

What deliberately does *not* post: relaunching an already-`in_progress`
interactive or auto ticket. The sync-relevant start transition already
happened when the ticket moved `active` → `in_progress`; subsequent launches
are resume attempts.

## Required by default

When `[slack].enabled` is true (the default), commands crash on any
Slack failure:

- `$SLACK_WEBHOOK_URL` is unset → `typer.Exit(1)` with a message
  pointing the user at the env var or the opt-out.
- Network or webhook-rejection error during `requests.post` →
  `typer.Exit(1)` with the error and (when `task_path` is given) a line
  appended to that task's `log.md`.

Why crash instead of degrading to stderr-only? Because a silent FYI
becomes a stale mental model on the human side, and that's worse than a
noisy retry. Loud failures force resolution; quiet ones rot.

## Why no retry

Earlier versions of `slack.post` retried with exponential backoff. PR
#56 removed that. An FYI is fire-and-forget — by the time a retry
succeeds 6 seconds later, the message is already stale relative to
local state, and a delayed sync is a dishonest sync. Better to fail
fast and let the user retry the command (which re-derives the message
from current state), or use the manual `relay validate --check-slack`
probe before the next batch of work.

## The opt-out is an exit, not a default

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

## Implementation pointers

- `src/relay/slack.py::post(cfg, message, *, task_path=None, owner=None,
  watchers=None, image_url=None)` — the only public function. Three
  branches: not enabled → stderr; enabled + no webhook → crash; enabled +
  webhook → POST then crash on failure. The private `_mention` helper
  renders a name as `<@ID>` when mapped.
- `$SLACK_WEBHOOK_URL` — the only place the URL lives. The webhook is
  a bearer token; relay never reads it from `relay.toml`.
- `cfg.slack_enabled` (`bool`, default `True`) and `cfg.slack_webhook`
  (`str | None`) — both come from `relay.config`. `[slack].enabled` in
  `relay.local.toml` overrides shared.
- `cfg.slack_users` (`dict[str, str]`, relay name → Slack member ID) —
  parsed from `[slack.users]` in `relay.toml` by `_parse_slack_users`.
- Callers that post: `commands/create.py` (ticket created),
  `commands/launch.py` (active → in_progress), `commands/mark.py`
  (active / paused / done), `commands/recurring.py`
  (per-scaffold + error summary), `commands/bump.py`, `commands/slack.py`,
  `commands/panic.py`, `commands/launch_script.py` (failure path only), and
  `automerge.auto_bump_merged` (called by `commands/automerge.py` and
  opportunistically by `commands/status.py`). Each passes
  `task_path=ref.path` (when a task exists) so failure traces also
  land in the task's `log.md` for non-interactive runs.
- `relay validate --check-slack` — probes the webhook with an
  empty-text payload that Slack rejects without notifying the channel.
  Honors the opt-out (skipped when `enabled = false`).

## Design rule for new features

If a new command changes state that other team members need to know
about, it must post. Don't add silent state mutations that bypass the
sync layer. Conversely, don't post chatter that doesn't represent a
state change — Slack is the sync log, not a debug stream.

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
