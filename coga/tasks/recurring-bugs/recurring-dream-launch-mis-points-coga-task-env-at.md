---
slug: recurring-bugs/recurring-dream-launch-mis-points-coga-task-env-at
title: recurring->dream launch mis-points COGA_TASK_* env at the package template
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 1 (implement)
---

## Description

During `coga recurring --all ~/Code` (2026-07-17), the `xpllm` repo's
`recurring/dream` task launched as an agent, but its injected task-metadata
env vars pointed at the **`bootstrap/recurring-scan` package template**, not
at the real dream task:

```
COGA_TASK_TICKET=.../src/coga/resources/templates/coga/bootstrap/recurring-scan/ticket.md
COGA_TASK_DIR / COGA_TASK_SLUG / COGA_TASK_BLACKBOARD  -> same package template
```

Consequence: when the dream agent ran the `validate-drift` worker script
(which appends its `## Dream Skill: validate-drift` report to
`$COGA_TASK_BLACKBOARD`), the report was written **into the coga package
source tree** at
`src/coga/resources/templates/coga/bootstrap/recurring-scan/ticket.md` in the
`claude/coga` checkout — polluting a shipped template. The dream agent
correctly detected the anomaly, could not revert it (sandbox boundary), and
blocked.

The env vars are being sourced from the outer `bootstrap/recurring-scan`
script launch (the sweep driver) and leaking into the inner agent launch of
`recurring/dream`, instead of being recomputed for the dream task. A nested
launch must re-derive `COGA_TASK_*` from the task it is actually spawning.

**Fix direction:** in the launch path that spawns an agent for a task
(`spawn_agent_session` / the recurring-scan driver), compute the
`COGA_TASK_*` env from the launched task's own ref/dir/blackboard rather than
inheriting whatever the parent process exported. Add a regression test: a
`recurring-scan` script launch that in turn launches an agent task must give
that agent `COGA_TASK_BLACKBOARD` pointing at the task's own `ticket.md`, not
the parent bootstrap template.

## Context

- Env injection for script/agent launches is documented in
  `coga/architecture` ("A script-step launch injects task and skill metadata
  as environment variables"): `COGA_TASK_SLUG`, `COGA_TASK_DIR`,
  `COGA_TASK_TICKET`, `COGA_TASK_BLACKBOARD`, `COGA_TASK_LOG`, etc.
- Shared spawn path: `src/coga/commands/launch.py` `spawn_agent_session(...)`
  and the recurring driver in `src/coga/recurring_runner.py` /
  `bootstrap/recurring-scan/run.py`.
- Secondary hardening: the `validate-drift` worker (and any Dream worker)
  could sanity-check that `$COGA_TASK_BLACKBOARD` is under `coga/tasks/`
  before writing, and refuse to append into a package `resources/templates/`
  path — defense in depth against exactly this mis-point.
- The stray write already landed in `claude/coga`; revert with
  `git -C /home/n/Code/claude/coga checkout -- src/coga/resources/templates/coga/bootstrap/recurring-scan/ticket.md`
  (operational cleanup, not part of the code fix).

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
