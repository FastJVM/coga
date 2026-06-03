The blackboard is a notepad to be written to often as the human and agent works through a task.

## Relaunch test log

### 2026-06-03 — draft (claude)

- **Step/agent:** step 1 `draft`, assignee resolved to `claude` (expected — `agent → claude`). ✅
- **Launch provenance:** hand-launched by a human (fresh `relay launch`). Ground
  truth: `log.md` shows `started (active → in_progress) via relay launch` at
  11:43, which fires only on a fresh human launch; and the process tree shows my
  REPL (PID 145772) parented by the launch invocation, not respawned by a
  supervisor teardown. This is step 1, so there is no prior agent to have chained
  from.
- **Previous teardown:** N/A (first step — no prior REPL).
- **Errors / surprises:** none. `artifact.md` created with the `# Relay relaunch
  chain — test artifact` heading and `## 1. draft (claude)` section.

**Expectation for next boundary (draft → expand):** same assignee (claude → claude),
so the supervisor should auto-relaunch into `expand` in a fresh process. Human
watches that the terminal stays usable (cursor visible, input echoes) after my
REPL is torn down — that is the #274 fix under test.
