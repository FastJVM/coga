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

period_state: {"schema":1,"run":2,"repo_id":null,"offset":1664035,"digest":"48c6b49abc5055d307a917ba3e030c429a7db95e9921277c612d9b20dac73e95"}
