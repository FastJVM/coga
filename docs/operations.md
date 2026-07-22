# Operations

Running Coga day to day: how the team stays in sync, how recurring maintenance
works, and how secrets are handled. All of it is configured in plain files —
`coga.toml` (shared, committed) and `coga.local.toml` (machine-local,
gitignored). Machine-local values override shared ones.

## Notifications

Notifications are the team's sync point. A channel shared across many tickets
drowns in lifecycle chatter, so Coga is deliberately selective about what
reaches it. Events fall into three tiers:

- **Live** — posted the moment they happen: a session starting (`active →
  in_progress`), a `coga block`, blocker reminders, a script-step failure, and
  explicit FYIs (`coga slack`, `coga bump --message`). Anything urgent or
  human-directed never waits.
- **Outcome digest** — done tickets, `autoclose-merged` completions, and
  recurring-scan parse errors are spooled and posted together on a schedule by
  `coga digest`. If the digest ticket isn't installed, these fall back to a live
  post.
- **Silent** — routine lifecycle churn posts nothing at all: draft creation,
  `mark active`/`mark paused`, message-less `coga bump`, successful recurring
  creates, and relaunching an already-`in_progress` ticket.

Agents and humans add one-line FYIs on top with `coga slack` (see the
[reference](reference.md#coga-slack---task-task---message-text)).

A fresh `coga init` selects **no** channels, so a brand-new repo is silent until
you turn a channel on. Once Slack is configured and enabled, any live-channel
failure fails loud rather than dropping the message quietly.

Channels are configured under `[notification]` in `coga.toml`. Slack is the first
channel:

```toml
[notification]
channels = ["slack"]

[notification.slack]
webhook = "env:SLACK_WEBHOOK_URL"
important_webhook = "env:COGA_IMPORTANT_WEBHOOK_URL"
```

A few things worth knowing:

- **The webhook URL is a bearer token, so it's never committed.** Use `env:`
  indirection — each user exports `SLACK_WEBHOOK_URL` locally and Coga resolves
  it at send time. The committed file holds only the pointer.
- **Two destinations.** `webhook` carries ordinary state transitions.
  `important_webhook` is the "a human needs to go do something" channel, where
  `coga slack --important` posts land. If you call `--important` without that key
  set, Coga crashes rather than quietly rerouting — a human-action alert in the
  wrong channel is worse than a loud misconfiguration.
- **Pings need a mapping.** `[notification.slack.users]` maps a Coga name (the
  token in a ticket's `owner`/`watchers`) to a Slack member ID, so that person
  gets a real `<@…>` ping. Without a mapping they're still named, just in plain
  text. `important_recipient` names a single triage owner to @ on every
  `--important` post instead of the ticket owner.
- **Opting out.** For solo, dev, or CI use, set `[notification.slack].enabled =
  false` in `coga.local.toml`.
- **GIFs, optionally.** `[notification.slack.gifs]` can attach a randomly chosen
  GIF to `done` and `block` events. Skip a kind to keep it text-only.

You can probe the webhook with `coga validate --check-slack`. It POSTs an
empty-text payload to the webhook — a real network call, but nothing visible
lands in the channel — and reports whether the endpoint accepted it.

### Webhook failure safety and incident response

Slack request failures report the Requests exception class and a safe network
category (DNS, timeout, connection, proxy, or TLS). Coga deliberately does not
render the exception message because Requests may include the incoming-webhook
URL — including its bearer credential — in that text. The same formatter covers
both notification destinations and the validation probe. The direct Slack HTTP
call-site audit is intentionally small:

- `SlackChannel.send` owns notification posting; both `webhook` and
  `important_webhook` select a destination before going through that one request
  and failure path.
- `probe_slack` owns the opt-in `coga validate --check-slack` request and uses
  the same safe failure formatter.
- Coga has no other direct Slack webhook HTTP request call site.

If a webhook URL or `/services/...` path has appeared in a diagnostic, treat the
webhook as compromised. Rotate or revoke it in Slack, redact the current tracked
`coga/log.md`, and inspect every reachable Git commit plus other copies such as
forks, clones, CI logs, and caches. Committing a redaction removes the value only
from the new tree; it does not erase earlier commits. Rewriting published Git
history and force-pushing is a separate destructive operation that must be
explicitly approved and coordinated with collaborators, and it still cannot
retract credentials from existing copies or logs.

## The digest

Instead of posting every completed ticket the instant it merges, Coga can spool
outcome events and post them together on a schedule. `coga digest` drains the
spool — posting Done tickets and other merged commits — and updates digest state.
On an empty spool it stays silent unless you pass `--announce-empty`. The digest
is itself a recurring template (see below), so it typically runs on a schedule
rather than by hand.

## Git sync

Git is the sync layer, the way Slack is the human sync layer. Every command that
mutates ticket state commits the task directory under `coga/tasks/` and pushes it
to the control branch, so the git-backed repo never drifts from the team's live
state. This is on by default, with sensible defaults (`remote = "origin"`,
`control_branch = "main"`) even with no `[git]` table.

Two properties matter in practice:

- **It works from a feature branch.** When `HEAD` is the control branch, task
  files are committed and pushed directly; on a feature branch (or detached
  HEAD), the same files are landed on the control branch through a
  working-tree-free plumbing path, so your feature checkout isn't disturbed.
- **A failed push never blocks you.** The on-disk markdown is the source of
  truth; Git is only the sync layer. A commit or push that can't reach the remote
  is surfaced to stderr and the task's log, but it never aborts the local state
  change.

To opt out (a repo with no remote — dev, test, solo branches), set `[git].enabled
= false` in `coga.toml` or `coga.local.toml`.

## Recurring maintenance

Recurring work lives as **templates** under `coga/recurring/<name>/`. `coga
recurring` scans them and launches any that are due; each due template gets a
real task at the stable path `tasks/recurring/<name>/`, using the same ticket,
workflow, blackboard, and log machinery as any other task. The serviced period
is recorded in the template so the next scan knows what's already done.

- `coga recurring list` shows the templates and their schedules.
- `coga recurring --force` runs every template regardless of schedule.
- `coga recurring --all <path>` sweeps every Coga repo below a path — one
  scheduler entry (a cron line, say) can serve many repos without centralizing
  their state.
- `coga recurring launch <name>` creates and launches one template on demand;
  several aliases wrap this (`coga dream`, `coga skill-update`, `coga autoclose`).

Point a single cron entry at `coga recurring` (or `coga recurring --all`) and the
schedules inside the templates do the rest.

### Dream: generic ticket cleanup

**Dream** is Coga's built-in maintenance pass — a recurring template
(`coga/recurring/dream/`) plus the `coga dream` alias, not a special command. On
its schedule (or on demand) it scans the ticket set, runs a fixed, explicit list
of housekeeping skills, and writes reviewable results to its blackboard.

Dream is the agent instance of the correction loop, and it obeys the same
"propose, human disposes" rule: where it finds durable drift — a context that no
longer matches reality, an orphaned marker — it opens a **proposal PR** rather
than editing your operating rules directly. Nothing lands on `main` without your
merge.

Dream is deliberately **not** a plugin host. The skills it runs are an ordered
list in its template body — the single control point. Adding a Dream skill is a
normal docs/code change to that list, not a drop-in discovery mechanism. This
keeps the maintenance loop legible: you can read exactly what Dream will do.

### REM: your repo's own maintenance

Where Dream is Coga's generic housekeeping, **REM** is the seam for *your*
repo-specific recurring maintenance. A REM run is an ordinary recurring task
whose body defines that repo's operational checks, domain skills, output
conventions, and review gates. If you want a different maintenance loop than
Dream's, you don't patch Dream — you write your own recurring template. That's
user space, and it uses the exact same machinery.

## Secrets

A task declares the secrets it may use **inline**, in its `secrets:` frontmatter
— there's no central catalog. Each entry is a single-key map pointing at a
reference, never a literal value:

```yaml
secrets:
  - STRIPE_KEY: op://vault/stripe/api-key
  - WEBHOOK_URL: env:SLACK_WEBHOOK_URL
```

Two reference kinds are supported: `op://vault/item/field` (resolved live with
`op read` from 1Password) and `env:VAR` (read from your environment). Both are
safe to commit because they're pointers, not values — a raw literal secret in a
ticket is rejected. At launch, each reference is resolved and injected as the
named environment variable for the task; the source `env:VAR` is scrubbed so the
child process sees only the scoped name. If a reference can't be resolved (`op`
missing or not signed in, an unset variable), the launch fails loud, naming the
Coga secret and its reference — never the value.

You can resolve one reference by hand for debugging:

```sh
coga secret get op://vault/stripe/api-key
```

## Checking readiness

`coga validate` is the catch-all health check. Beyond structure, it can probe the
things operations depend on:

- `coga validate --check-slack` — probe the Slack webhook.
- `coga validate --check-github` — probe git/`gh` auth readiness.

Both make a network call, so they're opt-in rather than part of the default
read-only validate.
