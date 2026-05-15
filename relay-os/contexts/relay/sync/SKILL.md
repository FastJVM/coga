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

- `relay create` — a new draft ticket lands in the queue.
- `relay recurring check` — one post per scaffolded recurring task,
  plus an end-of-run summary when any templates failed to parse.
- `relay mark active` — the moment work is approved, distinct from
  the *session* opening.
- `relay mark paused` / `relay mark done` — control-plane transitions
  away from active.
- `relay bump` — step advances (workflow plane only).
  Optional `--message` piggy-backs an FYI onto any transition broadcast.
- `relay automerge` (and the `post-merge` hook + `relay status` callers
  that wrap it) — auto-bumps active tickets to `done` when their
  blackboard `## Dev` PR has merged. Posts a distinct
  `🎉 *<slug>* "<title>" auto-bumped on merge of PR #<N>` line.
- `relay panic` — blocker, owner named.
- `relay slack` — explicit FYI (manual broadcast escape hatch).
- `relay launch` script-mode failure — non-zero exit on a
  `mode: script` step.

Slack is not an "FYI nice-to-have" — it's the synchronization point
between async agents and the people approving, unblocking, or watching
their work.

What deliberately does *not* post: opening an interactive or auto
session on an already-active ticket. That isn't a sync-relevant
transition — tickets are assigned, collision risk between teammates is
low, and the actual state changes (creation, activation, bumps,
panics, slack FYIs) each broadcast on their own. A "started work" line per
launch would turn the channel into a session log instead of a state
log.

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

## Implementation pointers

- `src/relay/slack.py::post(cfg, message, task_path=None)` — the only
  function. Three branches: not enabled → stderr; enabled + no webhook
  → crash; enabled + webhook → POST then crash on failure.
- `$SLACK_WEBHOOK_URL` — the only place the URL lives. The webhook is
  a bearer token; relay never reads it from `relay.toml`.
- `cfg.slack_enabled` (`bool`, default `True`) and `cfg.slack_webhook`
  (`str | None`) — both come from `relay.config`. `[slack].enabled` in
  `relay.local.toml` overrides shared.
- Callers that post: `commands/create.py` (ticket created),
  `commands/mark.py` (active / paused / done), `commands/recurring.py`
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
