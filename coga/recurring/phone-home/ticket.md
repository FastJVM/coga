---
schedule: "0 7 * * 1"
schedule_comment: "Every Monday at 7am, when an operator sweeps"
title: Weekly Coga usage snapshot
workflow: phone-home/run
contexts:
  - coga/telemetry
state_keys:
  - period_state
---

## Description

Attempt one weekly usage snapshot from the sibling `ticket.py`, without an
agent. See `coga/telemetry` for the data boundary, opt-out, and loss semantics.
Coga installs no scheduler. This measures repos with active sweeps, not installs.

<!-- coga:blackboard -->

This state is shared by synced clones. Do not copy runtime state into the
packaged seed. Only period_state changes each run; no delivery is retried.

period_state: {"schema":1,"run":1,"repo_id":null,"offset":1547052,"digest":"709c91e9a7920ee6bc09dd21053e33bef9a568b82718f5d573bbfa0c65ba6011"}
