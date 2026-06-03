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

### 2026-06-03 — expand (claude)

- **Step/agent:** step 2 `expand`, assignee resolved to `claude` (expected —
  `agent → claude`). ✅
- **Launch provenance: auto-relaunched by the supervisor** — the headline result
  this run tests, and it passed. Two independent ground-truth signals agree, no
  self-report:
  1. **`log.md`:** there is **no new** `started (active → in_progress) via relay
     launch` line after draft. That line fires only on a fresh human launch and
     appears exactly once, at 11:43 for step 1 `draft`. The 11:44 line is just
     `launched in interactive mode (assignee=claude, agent=claude)` — the
     supervisor respawning, not a human re-launch.
  2. **Process tree:** my REPL (PID 146216, started 11:44:31) is parented by the
     **original** `relay launch` supervisor (PID 145715), the same invocation
     that started the chain at 11:43 — it is still alive. A fresh human launch
     would be a new supervisor PID.
- **Previous teardown:** clean from the agent side. The draft REPL (PID 145772,
  recorded in the draft entry) is confirmed **not running** — the supervisor
  SIGTERMed it and respawned me as a new PID (146216) under itself. (Terminal
  *usability* after teardown — the #274 symptom — is human-observed; flagging
  for the watcher: cursor visible / input echoes / no alt-screen garble?)
- **Errors / surprises:** none. Appended `## 2. expand (claude)` to
  `artifact.md`.

**Expectation for next boundary (expand → peer-pass):** assignee rotates
claude → codex. Per the task-context table this should **auto-relaunch** (#248
chains agent rotations; the shared workflow file's "stop" is stale). So the
supervisor should tear down my REPL and respawn a **codex** session for
`peer-pass` with no human in between. Human again watches terminal stays usable.

### 2026-06-03 — peer-pass (codex)

- **Step/agent:** step 3 `peer-pass`, assignee resolved to `codex` (expected NOW
  per task context: `other-agent → codex`). ✅
- **Launch provenance: auto-relaunched by the supervisor across the claude →
  codex rotation.** Ground truth, not self-report:
  1. **`log.md`:** there is still only one
     `started (active → in_progress) via relay launch` line, at 11:43 for the
     original human launch. After the 11:45 `advanced to step 3 (peer-pass) →
     assigned to codex` line, the next line is only `launched in interactive
     mode (assignee=codex, agent=codex)` — no fresh human-owned start event.
  2. **Process tree:** the original `relay launch
     verify-relaunch-chain-terminal-teardown` supervisor is still PID 145715
     (started 11:43:39). The current task Codex REPL is PID 147346 (started
     11:45:30) with PPID 145715, so it was spawned by that same supervisor. A
     fresh human launch would have produced a new supervisor PID.
- **Previous teardown:** clean from the agent side. The prior step's claude REPL
  PID 146216 is no longer running, and the supervisor respawned a fresh codex
  REPL as PID 147346. Terminal usability after teardown is still
  human-observed; I saw no process-side errors or stuck state.
- **Errors / surprises:** none. Appended `## 3. peer-pass (codex)` to
  `artifact.md`. The cross-agent auto-relaunch occurred as expected by this
  task's #248 context, despite the older shared workflow table's stale "stop"
  expectation.

**Expectation for next boundary (peer-pass → human-check):** assignee rotates
codex → nick. This should **stop** at the human gate after my `relay bump`,
not auto-relaunch another agent. Human watches that the codex REPL teardown
leaves the terminal usable, then relaunches for `finalize` after the human check.
