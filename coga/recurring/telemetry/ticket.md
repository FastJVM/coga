---
schedule: "30 9 * * *"
schedule_comment: "Every day at 9:30am — send one anonymous install ping (offset from the 9:00 digest)"
title: "Daily telemetry ping"
# A script step sends the ping directly with no agent: the workflow's one step
# references the `coga/telemetry/send` skill, whose `script:` runs `coga
# telemetry send`. No `claude -p` / `codex exec` buffering, so it is safe under
# the temporary mode=auto recurring freeze.
autonomy: auto
workflow: telemetry/send
owner: nick
assignee: claude
---

## Description

Send a single anonymous, opt-out install ping — the post-launch
product-market-fit signal: how many real installs exist, whether they're used,
and whether they're still active. The complete wire payload is exactly three
fields and nothing else:

```json
{"instance_id": "<uuid4>", "tickets_total": 12, "last_run": "2026-06-19"}
```

- `instance_id` — a random UUIDv4 in machine-local state
  (`$XDG_STATE_HOME/coga/instance-id`), generated once, never derived from
  machine/user/repo identity.
- `tickets_total` — a bare count of `ticket.md` files (no status, slug, title,
  or content).
- `last_run` — today's UTC date (`YYYY-MM-DD`), the most recent run by
  construction (the ping fires only when the recurring sweep runs).

Once a day this ticket fires on its schedule and its script step runs `coga
telemetry send`, which builds the payload and POSTs it to the GCP relay (which
drops the client IP and forwards a one-line message to internal Slack). The
recurring period owns the once-per-day cadence — nothing hooks the foreground
dispatch path and nothing runs on every command.

**On by default (opt-out).** The send is a clean no-op (zero network calls)
when any disable path is active: `[telemetry] enabled = false` in
`coga.toml`/`coga.local.toml`, `COGA_TELEMETRY_DISABLE=1`, or the cross-tool
standard `DO_NOT_TRACK=1`. Read exactly what would be sent — without sending —
with `coga telemetry show`.

**Fail silent-for-the-user but never wrong.** A send failure (network error,
non-2xx, exception) never crashes the run: `coga telemetry send` reports the
outcome and exits 0. Because this runs as a `mode: script` step, that outcome
line is captured to this task's run history (`coga/log.md`) — recorded, never
swallowed.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works
through a task.

`coga recurring` keeps the serviced-period high-water mark here and append-only
human history in the repo-global `coga/log.md` (never composed into a run, so
it can grow unbounded). This ping carries no cursor of its own — the recurring
period is the only state that matters, so there are no `state_keys` to advance.
