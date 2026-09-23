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
  in_progress`), a `coga block`, blocker reminders, and explicit FYIs
  (`coga slack`, `coga bump --message`), plus recurring script failures and
  warnings that declared recurring state did not advance.
- **Outcomes** — done and canceled tickets, `autoclose-merged` completions,
  recurring-scan errors, and recurring watchdog timeouts also post live, one
  message per event, through the outcome-only `notify` path. Cancellation
  entries carry their required reason. There is no batched rollup, and
  commits that reach `main` without a Done ticket are not announced — `git
  log` and GitHub are the record for those.
- **Silent** — routine lifecycle churn posts nothing at all: draft creation,
  `mark active`, manual or non-timeout `mark paused`, message-less `coga bump`,
  successful recurring creates, and relaunching an already-`in_progress`
  ticket.

Agents and humans add one-line FYIs on top with `coga slack` (see the
[command contract](../src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md)).

Surface is separate from destination. The ordinary flow webhook carries
operating awareness and ticket outcomes. The important webhook carries
action-needed alerts: explicit `coga slack --important`, recurring script
failures, stale declared period state, recurring scan errors, and watchdog
timeouts.

A fresh `coga init` selects **no** channels, so a brand-new repo is silent until
you turn a channel on. Once Slack is configured and enabled, delivery failures
are reported rather than dropped quietly. Most fail loud; state-transition
posts made after a durable mutation and the advisory period-state warning use
best-effort guards so a Slack failure cannot undo the state change.

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
  explicit and automatic failure alerts land. It becomes an operational
  prerequisite once recurring jobs run. If an important post has no resolved
  destination, Coga raises rather than quietly rerouting — a human-action alert
  in the wrong channel is worse than a loud misconfiguration.
- **Pings need a mapping.** `[notification.slack.users]` maps a Coga name (the
  token in a ticket's `owner`) to a Slack member ID, so that person
  gets a real `<@…>` ping. Without a mapping they're still named, just in plain
  text. `--important` uses that same task-owner mention: the owner is the triage
  point, and can hand the alert to someone else in its Slack thread. There is no
  separate recipient-routing setting.
- **Opting out.** For solo, dev, or CI use, set `[notification.slack].enabled =
  false` in `coga.local.toml`.
- **GIFs, optionally.** `[notification.slack.gifs]` can attach a randomly chosen
  GIF to `done` and `block` events. Skip a kind to keep it text-only.

Default `coga validate` warns without network I/O when Slack is selected and
enabled but `important_webhook` is unresolved. The `enabled = false` opt-out
suppresses this warning with delivery. You can probe the primary webhook with
`coga validate --check-slack`; it POSTs an empty-text payload — a real network
call, but nothing visible lands in the channel — and reports whether the
endpoint accepted it.

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

## Git sync

Git is the sync layer, the way Slack is the human sync layer. Every command that
mutates ticket state publishes the task under `coga/tasks/` and the audit log
straight to the control branch on the remote, so the git-backed repo never
drifts from the team's live state. This is on by default, with sensible
defaults (`remote = "origin"`, `control_branch = "main"`) even with no `[git]`
table. The full contract is the `coga/sync` context; three properties matter
in practice:

- **Coga never commits on your branch.** State is built into a commit on top
  of the remote control tip and pushed there directly; a checkout on the
  control branch fast-forwards to it, a feature checkout keeps its published
  ticket dirty and is otherwise untouched (don't add `coga/tasks/**` or
  `coga/log.md` to a PR). Coga never stashes or rebases your work.
- **A failed push never blocks you.** The on-disk markdown is the source of
  truth; Git is only the sync layer. A push that can't reach the remote is
  surfaced to stderr and the log, the file stays as written, and the next
  Coga command retries it.
- **Stale copies are refused, not overlaid.** If another checkout advanced a
  ticket since yours last saw it, the publish is refused and names the fix
  (`git checkout origin/main -- <path>`).

To opt out (a repo with no remote — dev, test, solo branches), set `[git].enabled
= false` in `coga.toml` or `coga.local.toml`. It turns off *sync*, not policy:
the recurring `owner` gate below still reads the remote if one is configured,
so a machine-local setting can't quietly hand recurring back to a stale clone.

The first property cuts both ways. The end-of-command sweep commits *everything*
dirty under `coga/` and lands it on control from whichever branch you ran the
command on — a context or skill you were still editing for a PR included. Commit
in-flight `coga/` edits onto the feature branch before running any mutating
`coga` command there; the incidents and the exact command set are recorded in
the `coga/codebase` context under "Which checkout you invoke coga from". A repo
whose product lives under `coga/` and wants that rule enforced rather than
remembered can wrap `coga` in a shell function or git hook that refuses
mutating commands when `HEAD` is not the control branch; Coga ships no switch
for it, by design (it is repo policy, not core behavior).

One more `[git]` key is about checkouts rather than sync:
`worktrees_ticket_owned` (default `false`, `coga.toml` only) declares that
every linked worktree of the repository belongs to a Coga ticket, which lets
the weekly branch sweep remove a landed, pristine worktree no live ticket
records instead of leaving its branch `skipped-worktree-pinned`. The
`dev/code` context states the assumption a repo opts into.

## Recurring maintenance

Recurring work lives as **templates** under `coga/recurring/<name>/`. `coga
recurring` scans them and launches any that are due; each due template gets a
real task at the stable path `tasks/recurring/<name>/`, using the same ticket,
workflow, blackboard, and log machinery as any other task. The serviced period
is recorded as a validated calendar-period key in the repo-global `coga/log.md`
so the next scan knows what's already done. A malformed record is shown as an
error by `coga recurring list` and `coga status`; it never counts as serviced.

- `coga recurring list` shows the templates and their schedules.
- `coga recurring --force` runs every template regardless of schedule.
- `coga recurring --all <path>` sweeps every Coga repo below a path — one
  scheduler entry (a cron line, say) can serve many repos without centralizing
  their state.
- `coga recurring launch <name>` creates and launches one template on demand;
  several aliases wrap this (`coga dream`, `coga skill-update`, `coga autoclose`).

Point a single cron entry at `coga recurring` (or `coga recurring --all`) and the
schedules inside the templates do the rest.

### Autoclose's retire worklist

The daily `autoclose-merged` sweep closes merged final-step tickets and runs
the shared retire proofs to dispose of their feature checkouts. Refused
checkouts stay in `coga/recurring/autoclose-merged/retires.md`, a durable
markdown worklist beside the recurring template. Read that file to see what
still needs attention; the period task's blackboard is a report of one run.
The [`coga/autoclose/sweep` skill](../coga/skills/coga/autoclose/sweep/SKILL.md)
owns the disposal, manual-remedy, and worklist discharge rules.

**Adopting it in a repo initialized before Coga shipped this** (the sweep
formerly wrote the list only to the period task, so follow-ups older than a
day were lost): upgrade the installed Coga package — the template's `ticket.py`
calls the packaged recipe, so the durable write and the prune apply on the next
sweep with no template edit. Then, in your repo:

1. Add `**/retires.md merge=union` to `coga/.gitattributes` (a fresh
   `coga init` writes it). Without it a state merge between two branches that
   both touched the worklist can conflict instead of taking both sides.
2. Re-copy the packaged `coga/recurring/autoclose-merged/ticket.md` and
   `coga/workflows/autoclose-merged/sweep.md` from the installed package's
   `templates/coga/` resources, or edit your local copies: their prose still
   describes the period-task blackboard as the only surface, and a local
   workflow override composes into every future period task's prompt. The
   behavior does not depend on those files, only their accuracy does.
3. Backfill debt the old sweep already lost, if you want it listed: for each
   `done` ticket that still carries a `branch:` or `worktree:` under `## Dev`,
   add one line under `## Follow-ups (open)` in the file's documented shape.
   The next sweep validates every line (a malformed one fails the run loudly)
   and drops any entry whose checkout is already gone, so seeding a generous
   list is safe.

A repo that carried a private maintenance script for the same file can drop
it: the shipped sweep and `coga retire` now perform its add and prune.

If two people have clones of the same repo, name one of them in the committed
`coga.toml` — `owner = "<name>"` — so only their machine sweeps it. Everyone
else's recurring launches (including `--force`) are refused with the owner's
name; `--all` skips repos they don't own and keeps going. It's a policy gate,
not a lock: it stops two *operators* racing, not one operator running two
clones. Leave `owner` unset and nothing changes.

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

## Weekly telemetry and opt-out

For the shared/local `[telemetry] enabled = false` opt-out, release-wheel
verification, project read-back and deletion, see [Telemetry operations](telemetry.md).
The [behavioral contract](../coga/contexts/coga/telemetry/SKILL.md) owns what is sent
and when; telemetry is a sweep activity signal, not an install count.
