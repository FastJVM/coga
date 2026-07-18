---
slug: recurring-bugs/coga-usage-cannot-locate-claude-transcript-or-sess
title: coga usage cannot locate claude transcript or session id for some launches
status: done
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
---

## Description

After some agent launches during `coga recurring --all` (2026-07-17), the
usage-accounting step could not find the session's transcript and printed:

```
coga usage: claude transcript not found: /home/n/.claude/projects/-home-n-Code-codex-coga/<id>.jsonl
coga usage: missing claude session id
```

The launch itself is reported as exit 0 / done — usage logging simply no-ops
for those sessions, so per-session token/usage accounting is silently missing.
Low severity (cosmetic + a gap in usage history), but it is a real fail-quiet:
the message is printed but the data is just dropped.

**Fix direction:** make the transcript/session-id lookup robust to the cases
that miss (interactive REPL torn down by the done-sentinel before the
transcript path is resolvable; a session id that never got recorded; a
launch whose project dir differs from the resolved path). Either resolve the
transcript reliably, or — if it genuinely can't be found — record the miss in
`log.md`/usage as an explicit "usage unavailable for session X" rather than a
bare stderr line, so the gap is auditable instead of silent.

## Context

- Emitters: the `coga usage` accounting path invoked after an agent session
  exits (see the launch teardown in `src/coga/commands/launch.py` and the
  usage module it calls).
- Correlates with the done-sentinel teardown: the two misses in the sweep
  followed sessions ended via `$COGA_DONE_SENTINEL` (bump/mark/block) and a
  `bootstrap/orient` launch — worth checking whether the transcript path is
  resolved before vs after teardown.
- Lowest priority of the recurring-bugs set; no correctness impact on tasks,
  only on usage history completeness.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Already satisfied

- The permitted auditable-fallback path landed on `main` in PR #583
  (`10d88e4d`). `capture_session()` always appends a schema-2 record after
  parsing; a missing Claude session id or transcript produces
  `usage_status: "unknown"` with the available session identity, timing, and
  process outcome instead of dropping the session.
- `spawn_agent_session()` captures after done-sentinel teardown, then syncs
  exactly `coga/log.md`, so the fallback record is durable even though it lands
  after the agent's final workflow transition.
- The 2026-07-17 sweep already left concrete records for the affected paths:
  `bootstrap/orient` and `bootstrap/ticket` have schema-2 log entries with
  `usage_status: "unknown"`, non-null session ids, elapsed time, and
  `outcome_status: "completed"`. `coga usage --json --task bootstrap/orient`
  reports 6 sessions / 6 unknown sessions, making the accounting gap visible.
- Verification on current `main`: `PYTHONPATH=/home/n/Code/codex/coga/src
  python3.12 -m pytest -q tests/test_usage.py tests/test_launch.py` → 96 passed;
  task-scoped `coga validate --json` → 1 ok, no issues.

No new branch or diff is warranted: adding transcript-discovery heuristics would
broaden the ticket beyond its already-shipped explicit-unknown fallback and
risk attributing another Claude session's transcript.
