---
name: telemetry/send
description: One-step script workflow that sends the anonymous, opt-out install ping.
steps:
  - name: send
    skills:
      - coga/telemetry/send
    assignee: agent
---

## send

Script step. Runs `coga/telemetry/send`, which calls `coga telemetry send`:
build the three-field payload (`instance_id`, `tickets_total`, `last_run`) and
POST it to the GCP relay, unless telemetry is disabled (`[telemetry] enabled =
false`, `COGA_TELEMETRY_DISABLE=1`, or `DO_NOT_TRACK=1`), in which case it is a
clean no-op. A send failure is reported and exits 0 — it never crashes the
daily run.
