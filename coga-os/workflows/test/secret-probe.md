---
name: test/secret-probe
description: One-step script workflow for the auth-path manual test — runs the test/secret-probe skill that prints injected test_* secret key names.
steps:
  - name: probe
    skills:
      - test/secret-probe
    assignee: agent
---

## probe

Script step. Runs the `test/secret-probe` script skill, which prints the names
(never values) of injected `test_*` secret env vars so per-task `secrets:`
gating can be verified.
