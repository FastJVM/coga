# Telemetry

Coga sends a single anonymous, **opt-out** install ping once a day. This page is
the full, plain-language account of what it sends, why, and how to turn it off.
It exists because phoning home is in tension with Coga's "own the substrate,
local by default" principle — the price of doing it at all is total legibility.

## Why

It is a post-launch product-market-fit signal, nothing more: how many real
installs exist, whether they're actually used, and whether they're still active.
At ~100 users that question is answered by eyeballing an internal Slack channel
— there is no datastore, no dashboard, and no per-user analytics.

## What is sent — the complete payload

Exactly three fields, and nothing else on the wire:

```json
{
  "instance_id": "<uuid4>",
  "tickets_total": 12,
  "last_run": "2026-06-19"
}
```

| Field | What it is | Why |
| --- | --- | --- |
| `instance_id` | A random UUIDv4, generated once and stored in machine-local state (`$XDG_STATE_HOME/coga/instance-id`, default `~/.local/state/coga/instance-id`). | The only join key — lets us count distinct installs. Not derived from any machine, user, or repo identity. |
| `tickets_total` | A bare integer count of `ticket.md` files in the repo. | Answers "is this install actually used?" No status, slug, title, or content. |
| `last_run` | Today's date in UTC (`YYYY-MM-DD`). | Answers "is this install still active?" Coarse day granularity, no finer timestamp. |

**Never sent:** repo name or path, cwd, hostname, username, git remote, ticket
slugs/titles/bodies, command names or arguments, IP or geo, or any fine-grained
timestamp. Run `coga telemetry show` to print the exact payload (and the
deciding enabled/disabled state) without sending anything.

## How it's sent

- **A recurring task, not a hook.** The daily `coga/recurring/telemetry/` task
  (`mode: script`) runs `coga telemetry send`. The recurring period gives the
  once-per-day cadence and idempotency. Nothing runs in the foreground dispatch
  path; no telemetry code runs on an ordinary `coga` command.
- **Fail silent-for-you, never wrong.** A send failure (network error, non-2xx,
  exception) never crashes the run — `coga telemetry send` reports the outcome
  and exits 0. Because it runs as a script step, that outcome is captured into
  the recurring task's run history, so a failure is recorded, never swallowed.
- **Coverage limit.** Telemetry rides the recurring system, so an install that
  never services its recurring tasks sends nothing. That's an accepted gap.

## The endpoint

The ping POSTs to a tiny GCP Cloud Function we own (see
[`telemetry-endpoint/`](../telemetry-endpoint/README.md)). The function:

- **drops the client IP at the edge** — it reads no IP header, and a Cloud
  Logging exclusion filter keeps `remoteIp` out of the request logs;
- **forwards only the three known fields** to an internal Slack channel via a
  webhook held server-side as a secret (never in the client) — any extra key is
  ignored; and
- **stores nothing** — the Slack channel is the record.

The endpoint URL is a constant in the client, overridable with
`COGA_TELEMETRY_URL` to point a checkout at a test relay.

## How to disable

Telemetry is on by default. Any **one** of these turns it off, resulting in zero
network calls (env beats config):

```toml
# coga.toml or coga.local.toml
[telemetry]
enabled = false
```

```sh
export COGA_TELEMETRY_DISABLE=1   # Coga's kill switch
export DO_NOT_TRACK=1             # the cross-tool standard, also honored
```
