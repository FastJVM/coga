---
name: coga/telemetry/send
description: Send the daily anonymous install ping. Builds the three-field payload (instance_id, tickets_total, last_run) and POSTs it to the GCP relay, unless telemetry is disabled. Fail-silent-for-the-user but never swallowed.
script: run.py
---

# Daily telemetry send

This skill is the `mode: script` body of the `recurring/telemetry/` ticket. It
runs `coga telemetry send`, which:

1. checks the opt-out paths (`[telemetry] enabled = false`,
   `COGA_TELEMETRY_DISABLE=1`, or `DO_NOT_TRACK=1`) — if any is active, it is a
   clean no-op with zero network calls,
2. otherwise builds the exact three-field payload (`instance_id`,
   `tickets_total`, `last_run` — nothing else) and
3. POSTs it to the GCP relay, which drops the client IP and forwards a
   one-line message to internal Slack.

A send failure (network error, non-2xx, exception) is reported on stdout and
exits 0 — it never crashes the daily run, but the outcome line is captured to
the recurring task's run history, so a failure is recorded, never swallowed.

The script imports `coga.telemetry.send` and calls it directly, so it does not
depend on `coga` being on `PATH` inside the script environment.
