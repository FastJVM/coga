---
name: coga/sync
description: Notifications and git as coga's sync layers — why notifications are optional on first run but configured Slack fails loud, how task-state git sync works, why a standalone notification failure crashes while one that follows a committed transition only reports, like a git sync miss, and how to design new features that respect sync.
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
humans tune it out, which defeats the point. Coga therefore makes two
independent routing decisions:

- **Surface** — post, or stay silent. Urgent events and explicit FYIs go
  through `notification.post`; ticket outcomes and recurring errors go through
  `notification.notify`, which admits only those event kinds and posts them
  live the moment they happen. Everything else is silent.
- **Destination** — deliver to the ordinary flow webhook or the important
  webhook. Flow is the operating feed; important is the action-needed queue
  defined by `coga/important`.

Outcomes post immediately because the notification volume is low. Commits
that reach `main` without a Done ticket are intentionally absent from Slack;
`git log` and GitHub are the record.

Live surface (`post`) — posts immediately to the named destination:

- `coga block` — blocker, owner named; flow.
- `recurring/blocker-reminders` — unresolved blocked-task reminders, owner
  named, with the `coga unblock <slug> --answer "..."` command shape. The
  run records a `## Blocker reminders` watermark on the blocked task after
  *attempting* the live post; flow. That watermark is a **permanent dedup key,
  not a cooldown**: `record_reminder` refuses any blocker fingerprint already
  listed under `## Blocker reminders`, so each blocker gets **at most one
  reminder attempt over its whole lifetime**, no matter how many daily sweeps
  run afterwards. Attempt, not delivery — the watermark is written on the
  attempt, and `post` returns quietly when no channel is configured (the
  fresh-init default) or Slack is disabled, so a blocker can burn its one
  attempt without anyone being told. A task that stays blocked for weeks
  therefore goes silent after that single attempt, and a clean sweep reporting
  `no unresolved blockers to remind` can mean "every open ask is already
  watermarked" rather than "nothing is blocked" — read the blocked tasks, not
  the sweep's exit line. Re-reminding on an interval would be a behavior change
  (turning the watermark into a `last_reminded` cooldown), and so would
  watermarking only successful deliveries; neither is a bug fix.
- `coga slack` — explicit FYI (manual broadcast escape hatch); flow unless the
  sender supplies `--important`.
- `coga bump --message "<FYI>"` — explicit FYI attached to step movement.
  Message-less bumps are silent; the FYI stays in flow.
- `coga launch` — an approved `active` ticket starts and becomes
  `in_progress`. The session-start signal stays live (one per task) in flow.
- a recurring period task's `ticket.py` exits non-zero — the generated period
  task stays unfinished and needs diagnosis; important.
- a completed recurring period fails to advance declared state — the next run
  may duplicate work; important, under the existing best-effort warning guard.
- the Dream validate-drift summary — bounded maintenance result; flow.
- the megalaunch drain summary — non-empty aggregate result; flow.
- the `autoclose-merged` sweep's checkout and review-thread summaries
  (see `coga/autoclose/sweep`): disposed checkouts and unanswered review
  threads use flow; refused checkout disposals use important. These use
  plain `post` calls rather than per-ticket `notify` outcomes.
- recurring autofix filing a ticket for a problem it diagnosed in a recurring
  run — not only a failed one: a run that exits zero but whose blackboard shows
  it silently did nothing, or recorded real errors, is classified a problem too.
  Both the sweep's own `run_autofix` and the `coga run autofix-analyze` recipe;
  flow.

Outcome surface (`notify`) — posted live, one message per event:

- `coga mark done` — done tickets, including manual completions that have no
  PR number.
- `coga mark canceled` — intentionally abandoned tickets, with the required
  cancellation reason kept in the outcome record and audit log.
- the `autoclose-merged` recurring sweep (never `coga status`, which is
  read-only) — auto-bumps active/in-progress
  tickets to `done` when their blackboard `## Dev` PR has merged. This daily
  sweep is the sole trigger; there is no manual `automerge` command.
- `coga recurring` — only the end-of-run summary when templates failed to
  parse (`recurring-error`).
- the recurring liveness watchdog — a timed-out run is paused and recorded as
  `recurring-error`. Manual pauses and non-timeout unfinished pauses stay
  silent.
- `run_recurring_scan` — every task the watchdog already paused is
  re-escalated as `recurring-error` on *each* later sweep until that task is
  successfully recovered (#778). Resume only the affected task with
  `coga launch <slug>`; a successful completion stops its future escalations.

Done and canceled outcomes keep the flow destination; all three recurring-error
producers pass `important=True` and land in important. The scan-error summary
posts `fatal=False`: it runs in `_broadcast_scan`, before the launch loop, and
every skipped template it names has already been printed to stderr and to the
scan table, so neither an undeliverable post nor an unresolved
`important_webhook` may abort a sweep whose period tasks have not run yet.

Silent lifecycle surface — no notification post at all:

- `coga create` and `coga ticket "<title>"` — neither raw draft creation
  surface posts.
- `coga mark active` and manual `coga mark paused`.
- `coga bump` with no `--message`.
- Successful `coga recurring` creates.
- `coga retire` creating.
- `recurring/branch-sweep` — the weekly stale-branch prune. `branchsweep.py`
  makes no notification call at all, and deleting a branch whose work already
  landed is not something a human has to act on. `run_branch_sweep_recipe`
  appends a `## Branch Sweep` report to the calling task's blackboard before
  returning, including on failure; without a task blackboard, it writes the
  report to stdout. The report preserves deletion and skip counts, branch
  names, and per-branch decisions for the recurring autofix analyst. A remote
  listing or GitHub lookup failure reports a partial sweep with any completed
  cleanup counted; a worktree or Coga-root discovery failure reports an early
  stop. Console progress and stderr diagnostics remain available too.
- `recurring/skill-update` — the weekly managed-skill refresh. `skill_update.py`
  likewise never notifies: the run's entire output is a reviewable PR, so the
  PR *is* the notification and a post would duplicate it.
- `recurring/resolve-conflicts` — the period template ships only a `ticket.md`
  and emits nothing itself. Its `delegate: bootstrap/resolve-conflicts` target
  posts the per-PR roll-up through the explicit `coga slack` escape hatch
  already listed on the live surface, so the recurring entry is silent by
  design rather than by omission.
- `recurring/address-pr-comments` — the same shape on a daily cadence. The
  period template emits nothing; its `delegate: bootstrap/address-pr-comments`
  target replies on GitHub threads and posts one `coga slack` roll-up per run.

Those four complete the enumeration: `coga/recurring/` ships seven templates —
`address-pr-comments`, `autoclose-merged`, `blocker-reminders`,
`branch-sweep`, `dream`, `resolve-conflicts`, `skill-update` — and every one
of them is now accounted for above. A new template accounted for on none of the three surfaces is an
unreviewed cadence decision, not a neutral default.

**This is an accounting of events, not a partition of templates.** A template
may legitimately span surfaces, and several already do: `autoclose-merged`
posts its checkout and unanswered-review-thread summaries through `post` *and* its per-ticket `done`
outcomes through `notify`, and `resolve-conflicts` and `address-pr-comments`
are silent as period templates while the bootstrap delegates they run post
their roll-ups through the live `coga slack` escape hatch. A cadence audit should ask
whether each *event kind* a template emits has a reviewed surface, not whether
the template name appears exactly once.

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
channels = []`), so a brand-new user runs `create`/`mark`/`launch`/`bump`
without configuring anything. Notifications are opt-in: a repo turns Slack on
by selecting the channel and pointing it at a webhook:

```toml
[notification]
channels = ["slack"]

[notification.slack]
webhook = "env:SLACK_WEBHOOK_URL"
important_webhook = "env:COGA_IMPORTANT_WEBHOOK_URL"
```

(`docs/operations.md` carries the same block inside the operational
walkthrough.) With no channel selected, `notification.post` takes its
no-channel branch — one stderr line, no crash. When `[notification].channels`
is absent entirely, Slack is inferred only from the presence of a
`[notification.slack]` table; without one, channels resolve to `()`.

`coga init` itself completes with a bare `SLACK_WEBHOOK_URL` exported, on
both the empty-repo and the filled-repo path, and its closing tip says how to
opt in. The empty-repo path reads the scaffolded config once, for the seeded
onboarding audit line; `init._load_scaffolded_config` hides the variable for
that read only. The bare-env guard on config load (below) stays armed for the
user's next command.

Once Slack *is* selected and enabled (`[notification.slack].enabled` defaults
to true), the fail-loud contract holds — commands crash on any live
Slack-channel failure:

- `[notification.slack].webhook` resolves empty (key absent, or an `env:` reference
  whose variable is unset) → `typer.Exit(1)` with a message pointing the
  user at the `[notification.slack].webhook` key, removing slack from
  `[notification].channels`, or the opt-out.
- Network or webhook-rejection error during `requests.post` →
  `typer.Exit(1)` with a *redacted* failure category — never the raw exception
  string or response body, both of which can carry the webhook URL — and (when
  `task_path` is given) a line appended (tagged with that task's ref) to the
  repo-global `coga/log.md`. See the redaction rule in the implementation
  pointers below.

Once recurring jobs run, `[notification.slack].important_webhook` is a second
operational prerequisite. Default `coga validate` warns, without a network
probe, whenever Slack is selected, enabled, and that destination is unresolved.
The supported `enabled = false` opt-out suppresses the warning along with
delivery. The warning does not weaken delivery: an automatic important post
still raises rather than falling back to flow. There are exactly **two**
best-effort exceptions, and each is scoped to a durable result that an
announcement must not be allowed to overturn:

- **The declared-period-state warning.** Its existing advisory guard reports
  that raise on stderr, so a failed important post cannot undo a successful
  `mark done`.
- **The script-failure post in `launch_script.py`.** When a recurring period's
  `ticket.py` exits non-zero, the important post announcing that exit passes
  `fatal=False` with `record_failure=not strict_assist`, and the call is
  wrapped so that under strict assist a `typer.Exit` — a missing or failing
  `important_webhook` — is swallowed rather than re-raised. Same shape, same
  reason as the period-state guard: the deterministic failure and its exit code
  are already durable, so a notification outage must not replace that result.
  The scope is `strict_assist` (`publish_aligned_branch is not None`), the live
  human-assist feature-branch publication mode, where the child's exit code is
  the authoritative answer the wrapper reports upward. Outside strict assist
  the miss is still recorded and a configuration `typer.Exit` still propagates.

Both are exceptions to the *fail-loud* half; the miss is always surfaced on
stderr, but it does **not** always reach `coga/log.md`. Two gaps:

- `record_failure=False` — the strict-assist script-failure call above passes
  it, and `SlackChannel.send`'s `fail()` appends to the log only
  `if task_path is not None and record_failure`. Under strict assist the miss
  is stderr-only by construction, which is the point: the deterministic exit
  code is already durable and must stay the authoritative answer.
- an unresolved webhook — `require_webhook` writes its configuration remedy to
  stderr and raises *before* `fail()` is reached, in every mode. A
  configuration miss is therefore never logged, best-effort or not.

So the ordinary delivery-failure path does record to `coga/log.md`; these two
do not. Do not read the best-effort carve-outs as promising the same audit
trail.

**One carve-out: a broadcast that announces an already-committed state
change.** The lifecycle transitions — `bump`, `mark done` / `canceled` /
`in_progress` / `paused`, and `block` — call
`post(..., fatal=False)` (`notify(..., fatal=False)` for outcomes). The
delivery miss is reported *identically* — same stderr line, same `coga/log.md`
entry — it just no longer aborts the command, because the ticket write already
happened and the command has work left that must not be skipped. Concretely:
`coga bump` writes the next step or terminal `done` state, *then* posts when
that transition calls for a broadcast, *then* calls `emit_done_marker`.
Crashing in between left the supervising `coga launch` waiting on a sentinel
nobody would ever write, so a session that had finished its step (PR opened,
ticket advanced) was killed by the idle backstop 15 minutes later and reported
as `timed_out` — an agent sandbox with restricted network is enough to trigger
it. This is the bargain git sync already makes for the same reason: the
markdown on disk is the source of truth, so a failed *announcement* of it must
not decide whether a session ends, and "fail loud" means surface the miss, not
crash.

Misconfiguration (an unresolved webhook for the requested route) rides the same
carve-out: it crashes on the default `fatal=True` path — a rerun reproduces it
identically, so the crash is the fix — and under `fatal=False` it is reported on
stderr and returned, exactly like a delivery miss. What `fatal=False` never buys
is a *reroute*: an important post with no `important_webhook` is dropped, never
sent to flow. The fail-fast configuration gate is `preflight_post(cfg)`:
callers use it *before* the mutation to refuse an unusable selected route
while the ticket still holds its previous state. Existing coverage and its
conditions are listed under *Notification implementation pointers*; not every
`fatal=False` producer preflights. Without that gate, a command can write the
ticket and audit line, then report and drop the undeliverable announcement
under `fatal=False` while finishing its remaining sync and session work.
Preflight preserves refusal before the write; `fatal=False` prevents a
notification failure discovered after the write from aborting completion.

The strict single-checkout assist path has one narrower exception after it has
published lifecycle state under an exact feature lease: a live delivery failure
still reports on stderr, but does not append its audit line. That lease is
already consumed, and leaving a new line dirty would either block the child on
its clean-checkout gate or let CLI teardown sweep unleased bytes. Ordinary
transitions retain the audit append described above.

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
your launches, bumps, or blockers. Treat `enabled = false` as a
deliberate exit, not a way to "make the warning go away." Once you're
working with another person, turn it back on.

When suppressed, each call still writes one line to stderr (`[slack] disabled
(post suppressed): <message>`) so the user notices their
opt-out is active. Quiet opt-outs become forgotten opt-outs.

## Pinging the owner

A post names the ticket's `owner` in its `[<project>] [<owner>]` prefix. The
owner is the only person a post addresses: there is no watcher list and no cc
trailer. For that name to actually *notify* someone, Slack needs the `<@U…>`
member-ID mention form — a plain `@name` or `[name]` in incoming-webhook text
never pings.

`[notification.slack.users]` in `coga.toml` supplies the mapping: a coga name (the
token used in a ticket's `owner` field) → a Slack member ID.
`notification.post` resolves `owner` through it, emitting `<@U…>` for a mapped
name and plain text otherwise.

The mapping is supplied by hand because an incoming webhook is
write-only: it can't call `users.list` / `users.lookupByEmail` to resolve
a name itself. Member IDs aren't secret, so the table lives in shared
`coga.toml`, not `coga.local.toml`.

## Message format conventions

Every **per-ticket** notification rendered for Slack follows one uniform
shape.
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
  an aside** (`(agent: …)`, `(step N/total)`); **`—` is reserved for the
  optional trailing FYI** (`bump --message`, pause reasons, retire
  annotations).
- **PR references are Slack links**: `<{url}|PR #{N}>`, never plain `PR #N`
  (plain text doesn't link in incoming-webhook posts).
- Message strings are built **at the call sites** (`commands/*.py`,
  `autoclose.py`) — `advance_step`/`mark_done` receive finished `slack_text`,
  and `post()`/`notify()` never reformat. `tests/test_notification_messages.py`
  snapshots the formats; extend it when a string changes.

## Notification implementation pointers

- `src/coga/notification/__init__.py::post(cfg, message, *, task_path=None, owner=None,
  image_url=None, important=False, fatal=True,
  record_failure=True)` — the **live** path. Three branches: not
  configured channel(s). Slack has three branches: not enabled → stderr;
  enabled + no webhook → crash; enabled + webhook → POST, then on failure
  report (stderr + `log.md`) and either crash (`fatal=True`, the default) or
  return (`fatal=False`, for a post that follows a committed transition). The
  channel raises `NotificationDeliveryError` for a delivery miss and
  `typer.Exit(1)` for a configuration refusal; `post` is the single boundary
  where *both* become a crash or a return, per `fatal`.
- `src/coga/notification/__init__.py::preflight_post(cfg, *, important=False)`
  — the **fail-fast configuration gate**, the third element of the contract
  alongside surface and destination. It calls `SlackChannel.require_webhook`
  for every enabled channel and raises the same `typer.Exit(1)` with the same
  stderr remedy the post itself would, but *before* any state mutation, so a
  repo whose webhook does not resolve refuses the command with nothing
  half-applied. It is the only place an unresolved webhook can still refuse a
  `fatal=False` producer; after the write, `post` reports and drops. Six
  call sites in five modules, with these admission conditions:
  `commands/bump.py::bump` (terminal bump, or a step advance with
  `--message`); `commands/mark.py` in `done` and `canceled` (every outcome
  command, not only a recorded assist); `commands/launch.py::_launch` (the
  script-assist setup path); `launch_script.py::run_script_phase` (an assist,
  before `ticket.py` publishes a started lifecycle); and
  `autoclose.py::_preflight_recipe_notifications`, the `before_close` hook of
  `run_autoclose_recipe` (every close posts a live per-ticket Done line).
  Ordinary `block` and launch paths do not preflight; their gates above are
  specific to recorded assists. `run_script_phase` wraps the refusal in
  `ScriptPublicationError` for its launch caller. Other callers let the
  configuration exit propagate. `important=True` checks the alert route
  (`important_webhook`) instead of the default one: pass it when the post that
  follows the write routes to important. No current caller passes that form.
  Existing important alerts retain their post-write failure handling: script
  failures, scan-error summaries, and watchdog outcomes use `fatal=False`;
  `mark.py::_warn_if_state_not_advanced` uses the default `fatal=True` inside
  an advisory exception guard. None preflights the important route.
- `src/coga/notification/slack.py::SlackChannel` — the Slack backend. It owns
  Slack text rendering (project/owner prefix, image attachment),
  mention rendering, and the webhook POST.
- `src/coga/notification/__init__.py::notify(cfg, slack_text, *, kind,
  owner=None, task_path=None, image_url=None, important=False,
  fatal=True, record_failure=True)` — the **outcome** path. It accepts only
  `done`, `canceled`, and `recurring-error` (`OUTCOME_EVENT_KINDS`) and
  forwards everything else to `post(slack_text, …)` unchanged; the `kind`
  gate is what keeps it an outcome channel rather than a second general
  broadcaster.
- `[notification].channels = ["slack"]` selects the enabled backend list.
  Unknown channel names fail config load until their backend exists.
- `[notification.slack].webhook` in `coga.toml` (or `coga.local.toml`) — the
  source for the default webhook URL. It is a bearer token, so the committed value
  is an `env:SLACK_WEBHOOK_URL` reference, resolved via
  `config._resolve_secret_value`. The key is required: a bare exported
  `SLACK_WEBHOOK_URL` fails config load with guidance to declare it explicitly.
  A literal URL is accepted by the parser but must never be committed; use
  `env:` indirection.
- `[notification.slack].important_webhook` — a second webhook, pointing at the
  coga-important channel. Posts that need a human to go act route here: an
  explicit `coga slack --important`, a recurring script failure, a stale
  declared-period-state warning, and the recurring scan-error and watchdog
  timeout outcomes. Ordinary lifecycle notifications and Dream and megalaunch
  summaries stay on `webhook`. Resolved by
  `config._resolve_notification_slack_important_webhook` with the same `env:`
  indirection and local-overrides-shared rule. Unset resolves to None and
  `SlackChannel.webhook_for`
  refuses an `--important` post (exit 1, stderr note) rather than rerouting it
  to `webhook`: delivering a human-action alert to the wrong channel while
  reporting success is worse than crashing, and the crash is what gets the
  config fixed. The refusal is absolute; whether it *aborts the caller* is
  `post`'s `fatal` decision, so a `fatal=False` producer drops the alert loudly
  instead of taking its command down. Each downstream repo carries its own
  `coga.toml`, so the unconfigured case is live.
- Important posts carry no dedicated recipient key: `coga slack --important` @'s
  the task owner through the ordinary `[project] [owner]` prefix that
  `SlackChannel.render_text` (via `mention`) puts on every post. Whoever owns the
  task the alert is raised under is who it lands on for triage; redirecting it is
  a human step in the Slack thread, not config (see `coga/important`).
- `cfg.slack_enabled` (`bool`, default `True`), `cfg.slack_webhook`, and
  `cfg.slack_important_webhook` (`str | None`) — fields holding the effective
  Slack-channel config. `[notification.slack].enabled`, `.webhook`, and
  `.important_webhook` each resolve with `coga.local.toml` overriding shared, so a
  machine can carry its own webhook while shared `coga.toml` holds a safe `env:`
  reference or omits the key.
- `cfg.slack_users` (`dict[str, str]`, coga name → Slack member ID) — parsed
  from `[notification.slack.users]` in `coga.toml`.
- Live producers (`post`) — the module that actually calls `post`, not the
  command a user types to reach it: `mark.py::mark_blocked` (the shared blocker
  finalizer behind `coga block`, `fatal=False`); `commands/slack.py` (important
  only with its existing flag); `bump.py::advance_step`, which posts only when
  its caller passes `notify_slack=True` (`commands/bump.py` does so when
  `--message` is present); `mark.py::mark_in_progress` (active → in_progress
  session start, driven by `commands/launch.py`);
  `blocker_reminders.py::remind_blocked_tasks`; the script-failure path
  in `launch_script.py` (important); the stale-period-state warning in
  `mark.py` (important); `dream_validate_drift.py` (flow);
  `autoclose.py::_report_retire_followups` (checkout summaries, flow or
  important) and `_report_followup` (review-thread summaries, flow), both
  `fatal=False`; `recurring_autofix.py` on both its ticket-filing paths
  (`run_autofix` and `run_autofix_analyze_recipe`, flow); and
  `commands/megalaunch.py` (flow). The `commands/*` module fronting a
  lifecycle transition contributes the `preflight_post(cfg)` configuration
  check and the rendered `slack_text`, not the delivery — `commands/block.py`,
  `commands/bump.py`, and `commands/launch.py` each preflight and hand a
  finished string down to `mark.py` / `bump.py`, so grep for an actual `post(`
  call before listing a module here. Outcome producers (`notify`):
  `mark.mark_done` (including the autoclose sweep), `mark.mark_canceled`, the
  recurring scan-error summary (`recurring_runner._broadcast_scan`, important,
  `fatal=False`), the per-sweep re-escalation of already-watchdog-paused tasks
  (`recurring_runner.run_recurring_scan`, important, `fatal=False`), and
  `mark.mark_paused` only when the recurring watchdog supplies `slack_text`. Both paths pass
  `task_path=ref.path` (when a task exists) so a live-post failure trace lands
  in the repo-global `coga/log.md`, tagged with the task ref.
- `coga validate --check-slack` — probes the webhook with an
  empty-text payload that Slack rejects without notifying the channel.
  Honors the opt-out (skipped when `enabled = false`). Default validation does
  no network I/O and separately warns when the important webhook is unresolved.
- `src/coga/slack_response.py` — the response boundary shared by **both** the
  live post (`notification/slack.py`) and the validator's
  `validate.probe_slack`. `classify_slack_response(status_code, text)` returns
  `live` (any 2xx/4xx that is not a revocation), `revoked` (HTTP 404 or a
  `no_service` body), or `unreachable` (5xx; each caller maps a `requests`
  exception into the same category). Neither caller invents its own reading:
  `SlackChannel` reports a revoked webhook as its own failure category rather
  than a generic non-OK response, and `validate` raises `slack-revoked` and
  `slack-unreachable` as distinct `error` issues (alongside
  `slack-misconfigured` for a webhook that never resolved) instead of one
  opaque probe failure. A new Slack caller classifies through this module.
- **Never render a raw Slack exception or response body.** The webhook URL is a
  bearer token, and `requests`/`urllib3` embed the requested URL in their
  exception strings — which the failure path above writes to stderr *and*
  appends to the **git-tracked** repo-global `coga/log.md`. A call site that
  formatted `str(exc)` itself would therefore commit a live credential.
  `format_slack_request_error(exc)` is the only sanctioned rendering: it emits
  an exception class name plus a fixed non-secret category (DNS/name
  resolution, TLS/SSL, proxy, timeout, connection, generic request) and never
  the original message. `redact_slack_webhook_credentials(text)` strips full or
  relative `hooks.slack.com/services/…` paths and is applied to every response
  body before it reaches a detail string. Route new Slack diagnostics through
  those two functions; a third rendering path is the mistake to avoid.

## Git — durable task-state sync

Notifications tell the team what changed; git makes the markdown state durable
and shareable. The whole contract is `src/coga/git.py`, and it fits one page.

### Invariants

1. **Control is canonical.** `[git].remote` + `[git].control_branch`
   (`origin/main` by default) is the only durable home of `coga/tasks/**`,
   `coga/log.md`, and `coga/recurring/**`. A write is durable when, and only
   when, it is on that ref. Coga never creates a commit on any local branch,
   never stashes, never rebases; the checkout's control branch only ever
   fast-forwards. The one stated exception: with no remote configured, the
   local control branch plays the canonical role and the push is skipped.
2. **Nothing is lost.** The markdown on disk is the write. A publish that
   cannot reach control leaves the file exactly as written (dirty), reports
   once on stderr and in `coga/log.md`, never crashes the command, and is
   retried by the next command's end-of-command sweep. `coga/log.md` is only
   ever appended and only ever three-way union-merged, never overlaid.
3. **Nothing moves backward.** Every published path is a compare-and-swap
   against control (the provenance check below). A stale checkout cannot
   overlay a ticket another checkout advanced; the refusal names the one-line
   fix. A control ticket carrying `pending:<uuid>` accepts only its own
   admission (`coga/architecture`, *One shared agent-spawn path*).
4. **One integrate path.** `git.refresh` (fetch + fast-forward) is the only
   way a checkout is brought level with control; `fast_forward_control` is
   the only code that moves the local control ref, after a publish and inside
   `refresh` alike.

### `publish` — the one write primitive

`git.publish(cfg, paths, message, *, expect=None, guard=None, fast_forward=True)`;
`sync_task_state(cfg, task_path, *, message, expect=None, strict=False)`
(task + log), `sync_log(cfg, *, message)` (log only, stderr-only failures),
and `sync_coga_state(cfg)` (the sweep: every dirty path under `coga/tasks/`,
`coga/log.md`, `coga/recurring/`) are thin wrappers over it. Soft-skips, one
calm stderr line each and nothing written: `[git].enabled = false`, not a git
repo, git not on `PATH`, control branch absent locally and on the remote
(`control_branch_mismatch_message` names the `coga.toml` fix).

Config lives in `[git]`: `enabled` defaults true, `remote` defaults `origin`,
`control_branch` defaults `main`, and `worktrees_ticket_owned` defaults
`false`. `enabled` may be overridden in `coga.local.toml`; the other three
are shared repo policy. `worktrees_ticket_owned` is not a sync setting: it is
the repo's declaration that every linked worktree belongs to a Coga ticket,
which lets the weekly branch sweep remove a landed, pristine, unclaimed
worktree — `dev/code` (*Checkout boundary*) states the assumption and
`coga/branch-sweep/sweep` the proofs.

1. **Candidates.** Under `paths`, every file dirty against HEAD, plus a clean
   file whose HEAD copy moved past control from a copy this checkout itself
   derived from (a feature branch that committed Coga state it had published).
   A clean file merely *behind* control is not a write and is left alone.
2. **Base.** `refs/remotes/<remote>/<control>` (optimistic, no fetch on the
   hot path); local `<control>` when there is no remote or the tracking ref
   does not exist yet.
3. **Provenance check.** A candidate that is a symlink is refused outright
   (`read_bytes` would follow it and land the target's bytes — possibly from
   outside the repo — as a regular file); a `merge=union` path missing from
   the working tree is refused rather than published as a deletion, naming
   `git checkout <remote>/<control> -- <path>` (and that refusal is not
   appended to a missing `coga/log.md`, which would recreate it truncated).
   For each non-union candidate, control's blob must be
   one the working copy derives from: HEAD's blob, the merge-base blob, a blob
   this worktree itself published (`refs/worktree/coga/published`, a
   per-worktree tree git keeps private to the checkout), or the working bytes
   themselves (an idempotent retry). `expect={path: bytes | None}` replaces
   that set with the exact bytes the writer read (`None`: must not exist) —
   megalaunch's claim, admission, and released-witness reconciliation, and the
   recurring create's ledger read use it; on a `merge=union` path it adds a
   check that path otherwise never has — but only while that path is a
   candidate. `guard=callable(base)` is the other hook: it runs before each
   attempt with the commit the attempt builds on (re-fetched after a rejected
   push, so a retry never decides on a stale tip), regardless of candidates,
   and refuses by raising. It exists for one decision `expect` cannot express:
   the recurring create must not land once control's *content* records the
   period as serviced, and on a control checkout `coga/log.md` is clean after
   the sweep's first publish, so a blob pin on it is never evaluated for the
   creates that follow. A ticket whose control copy carries
   `pending:<uuid>` accepts only the identical ticket with the prefix
   stripped; a working copy carrying `released:` is never published. Any
   refusal raises `StateRegressionError` before anything is pushed, logs
   "sync refused: `<path>`: control copy changed since this checkout last saw
   it …; take control's copy with `git checkout <remote>/<control> -- <path>`
   and redo the edit", and leaves the file as written.
4. **Tree and push.** A UUID-named temporary `GIT_INDEX_FILE` is seeded from
   base; each candidate is overlaid from the working tree (deleted when the
   file is gone); paths `git check-attr merge` reports as `union` get
   `git merge-file --union` of (merge-base copy, base copy, working copy)
   instead. A tree equal to base's returns `False` (already durable).
   Otherwise `commit-tree` on base and `push <remote> <new>:refs/heads/<control>`.
   A non-fast-forward rejection means base moved: fetch the tracking ref and
   go to 2, at most `MAX_PUBLISH_ATTEMPTS` times. Any other push failure
   re-reads control once: `True` when control now carries the commit,
   `GitError` when it definitely does not, `UncertainPublishError` when
   control cannot be re-read. Every failure leaves the file as written.
5. **Fast-forward.** `fast_forward_control(cfg, root, new, staged=…)` checks
   `merge-base --is-ancestor` *first*: a local control branch that is ahead or
   diverged (unpushed human commits) is left alone, index untouched, with one
   stderr line naming `git pull --rebase <remote> <control>`. When this
   checkout holds the branch, each published file still equal to what
   `publish` read is written to its landed bytes (the union result for the
   log) and staged, so `merge --ff-only` is not refused by the very edit it
   carries; a file a peer changed meanwhile stays dirty for the next sweep.
   Another worktree holding the branch is fast-forwarded through
   `merge --ff-only`; with no holder the ref moves under an old-value guard.
   `fast_forward=False` (Retro's isolated delete) skips this step. Nothing
   ever fast-forwards on a `False` publish except the publishing control
   checkout itself. With no remote this step is the publication: a refused
   fast-forward raises `GitError` ("could not be fast-forwarded"), nothing is
   recorded as published, and the write stays dirty for the next sweep.

Return values: `True` pushed, `False` control already held the tree, `None`
soft-skipped. `sync_task_state(strict=True)` re-raises after reporting; the
strict callers (megalaunch's claim and activation, the recurring delegator's
start, completion, and pause) restore their pre-write bytes and retract their
audit lines (`logfile.retract_log_lines`) on `StateRegressionError` and
`GitError`, and keep the write on `UncertainPublishError` as the legible
evidence for reconciliation.

### `refresh` and the read-only probes

`git.refresh(cfg) -> bool` fetches the control branch, then fast-forwards
when HEAD is the control branch (`True` when level, `False` with the
`pull --rebase` line when ahead, diverged, or blocked by a dirty file control
changed). A feature-branch or detached checkout gets the fetch and nothing
else: it is stale-by-design for tickets other checkouts advance, its own
published ticket stays dirty there, and `stale_coga_task_rels` keeps
`coga status` warning. Callers: `coga launch` teardown on every exit path, the
recurring per-child preflight (bails on `False` with
`STALE_CONTROL_EXIT_CODE`, which suppresses the CLI sweep), and the recurring
scan's pre-scan catch-up. `fetch_control(cfg, root)` is the shared "fetch and
give me the base" for readers of control's exact copy of a ticket
(`tree_bytes(root, base, rel)`).

### `state_lock` — same-checkout serialization

`git.state_lock(cfg)` is a short, kernel-released `fcntl.flock` on a
per-checkout lock file outside the worktree, reentrant within a thread. Every
Coga lifecycle writer takes it around its read-modify-write (`git.write_ticket`,
blackboard updates, delete), `publish` takes it around steps 2–5, and
megalaunch holds it across its whole admission window (final proof, pipe
release, admission publish). It never decides who owns a task; cross-checkout
and cross-machine coordination is the push compare-and-swap.

### What this means for a session

- A control checkout (`main`) is kept clean and level by its own publishes.
- A feature-branch or detached checkout keeps its published ticket and log
  **dirty by design** — Coga never commits on the branch. Do not `git add`
  `coga/tasks/**` or `coga/log.md` into a PR; `coga open-pr`'s single-checkout
  cleanliness gate excludes that live state and its classifier refuses a
  branch whose only commits are Coga state.
- Hand-authored contexts, skills, workflows, and config are review work: the
  sweep never publishes them. Commit them yourself.
- Concurrent sessions editing one checkout's working tree are the one
  unserialized hazard; run them from separate clones or worktrees.

### `merge=union`

`coga/log.md` is the one file `.gitattributes` marks `merge=union`: union
keeps both sides' lines, safe there precisely because every writer only
appends. A file that is compacted, trimmed, or rewritten must never carry the
attribute (union would resurrect the deletion). `git.union_merge_paths` asks
`git check-attr`, so adding an append-only file to `.gitattributes` is enough
to route it through the union merge — and adding a non-append-only one is the
mistake to avoid.

## Design rule for new features

If a new command changes state that other team members need to know about, it
must reach the sync layer. A state-changing command makes three notification
decisions:

1. **Surface.** `post` for an urgent event or explicit FYI, `notify` for a
   ticket outcome or scheduled-work error (it admits only those kinds), or
   silence for lifecycle audit noise that belongs only in the repo-global
   `coga/log.md` and git.
2. **Destination**, chosen at delivery: flow for operating awareness and
   aggregates, important only when a human must act and no durable
   human-owned ticket already holds the ask.
3. **Preflight policy.** When the transition's contract explicitly makes
   notification configuration an admission gate, call
   `notification.preflight_post(cfg)` *before* mutation; select `important=True`
   only if that gated post uses the important route. Gate the call on whether
   this invocation will actually post live, as `bump` does. Preflight refuses an
   unresolved route before the write; `fatal=False` reports and drops failures
   discovered after the write so completion can continue. Using `fatal=False`
   does not itself require preflight: ordinary `block` and launch paths and
   important script-failure, scan-error, and watchdog alerts intentionally
   retain best-effort notification semantics without that admission gate. Keep
   those paths able to finish when their webhook is unavailable. Use the
   inventory under *Notification implementation pointers* to distinguish the
   gated transitions from these deliberate exceptions when adding a caller.

Don't add silent state mutations that bypass both layers
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
readable, individually-attributed state commit.

When the post needs to describe state that has *just* changed, the
command echoes the local outcome to stdout *before* calling
`notification.post`. That way, if the notification channel crashes the user
still sees the local-state confirmation on stdout above the error on stderr,
and can reason about idempotency (most state changes — like `bump` — should not
be re-run blindly after a notification failure).

## Shipping a stored-ticket schema conversion

`coga/current-direction` records the decision the `simplify-ticket-format`
change made — no compatibility reader, no migration tool, no dual-writer
period; the whole stored population converted in the same change. This section
is the procedure that made a code+data conversion of committed `coga/tasks/**`
safe, for the next frontmatter or format change (the parked playbook rename is
one candidate).

1. **One PR carries everything: code, the converted tickets, fixtures, and the
   context edits.** A split merge leaves the running CLI and the stored
   tickets disagreeing — old code reading new tickets, or new code reading old
   ones — with no reader in between to bridge them.
2. **The provenance check is not a schema barrier.** It compares control's
   blob with the copies this checkout derived from (see *`publish`*), so an
   older supervisor that is still running and level with control will happily
   restore a removed field and pass the check.
   Before merge the owner therefore opens a writer quiet window: stop the
   recurring and megalaunch dispatchers, let every old supervisor finish its
   teardown and state sync, suspend scheduled entry points and any writers on
   other machines, and inventory `git worktree list` plus independent clones
   and installed or editable entry points. Registered worktrees are not live
   processes — ten were registered during the conversion and that list proved
   nothing about what was running — so inventory the processes, not just the
   paths.
3. **Refresh the conversion from the exact control revision at the gate.**
   Control moves under a long-running PR (four times during one
   implement+open-pr pass, twice within ten minutes). Rebuild the conversion
   commit on the control tip you are about to merge and re-verify the allowed
   field/token diff per ticket; expect to repeat this.
4. **Rebase rule for a converted ticket that control has since advanced.**
   Take control's version **wholesale** — lifecycle, body, and blackboard —
   then re-apply only the mechanical conversion to it. Neither side of the
   conflict is the answer on its own: the feature side has lost control's
   progress, and the control side has lost the conversion. Prove the result
   with
   `git diff origin/main -- <path>` (or against `git show origin/main:<path>`)
   showing only the conversion's explicitly allowed field additions,
   deletions, renames, and token changes, with no unrelated lifecycle, body,
   or blackboard edits.
5. **Never run a mutating Coga command from the converting feature checkout.**
   Its exit sweep (`sync_coga_state`, above) would publish the converted
   `coga/` files to control before the code lands. Verify with a source-pinned
   `python -m coga.validate --json` and a pure `compose_prompt_report` call, and
   compare before/after validation reports by task and finding kind so the
   only findings that disappear are the intended ones (`unknown-assignee` went
   5 → 0 in the format simplification; no new kinds appeared).
6. **Keep dispatch stopped until the merged writers and state are verified.**
   Update the control checkout and every usable installed or editable writer
   to the merged revision and confirm their import paths. Rebase or reconcile
   feature worktrees and independent clones before permitting Coga writes;
   preserve local work and keep stale checkouts barred from mutation and
   launch teardown while they remain parked. Re-run read-only validation on
   the converted control state, then resume dispatch with fresh processes.
   Never replay an old supervisor's finalizer after merge.

## Future direction — bidirectional sync

Today the sync is outbound only: agents/CLI → channel. The obvious next step is
inbound: humans replying / reacting / running slash commands in the channel
that reach back into the agent. For Slack, an app with the events API or
slash-command endpoints would close the loop.

The current `notification.post` API doesn't preclude this — it just doesn't
implement it yet. When designing new sync-touching features, avoid
baking in "outbound-only" assumptions; treat the Slack channel as a
two-way medium that's currently used in one direction.
