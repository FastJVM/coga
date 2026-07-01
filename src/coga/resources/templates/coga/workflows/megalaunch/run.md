---
name: megalaunch/run
description: One-step script workflow that runs the shared megalaunch engine.
steps:
  - name: run
    skills:
      - coga/megalaunch/run
    assignee: agent
---

## run

Script step. Runs `coga.megalaunch.run_megalaunch`: scan active tickets,
launch eligible agent-owned work sequentially under the unattended policy, and
write a compact run summary.
