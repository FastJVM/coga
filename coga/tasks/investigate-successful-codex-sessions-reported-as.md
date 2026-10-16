---
title: Investigate successful Codex sessions reported as failed
status: in_progress
owner: nicktoper
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 5 (open-pr)
agent: claude
---

## Description

Determine why apparently successful Codex sessions are recorded with
`outcome_status: failed` in their activity records, and correct the
classification only where lifecycle and process evidence prove it wrong. A
success-looking final message or passing tests alone is not proof of success.

Reproduce with a live Codex session, bootstrap first (`coga orient` or
`coga ticket`, closed the way a human closes it), then an ordinary ticket
step. Capture the launch target, raw process exit status, supervisor exit
`kind`, done sentinel, recorded `outcome_status`, and expected workflow
progress. Preserve real failures, crashes, interrupts, and timeouts.

The owner approved the narrow misclassification fix at `review-design` on
2026-10-15, with normalized exit evidence fields and the full lifecycle
reproduction still required during implementation. The original outcome
alternatives were:

- **Misclassification confirmed:** fix the mapping for the confirmed
  mechanism, add a regression test, and update the `outcome_status` meaning
  in coga/internals/activity-capture (canonical and packaged twin).
- **Classification correct** (Codex really exits non-zero, and `failed`
  correctly means process failure): no mapping change. Deliver the evidence,
  clarify the `outcome_status` definition in activity-capture, and, if the
  owner approves, start recording `exit_code` / exit `kind` so future
  records can be audited. This may be a docs-only change.

### Finding (design step, 2026-10-08)

The leading hypothesis was right in effect but wrong in detail. In the observed fast double-Ctrl-C probes, Codex was **killed by SIGINT**
rather than choosing a non-zero exit code. Live repro under the real supervisor
(`repl_supervisor.run_with_done_marker(["codex"], …)` in a tmux pane, codex-cli
0.160.1, Claude Code 2.1.294, idle composer, no prompt sent):

| CLI | Human quit path | `ReplOutcome` | Label inferred from current mapping |
|---|---|---|---|
| codex | Ctrl-C ×2, 0.05 s apart | `130 crash` (2/2) | `failed` |
| codex | Ctrl-C ×2, 0.2 s apart | `130 crash` (1/2), `0 natural` (1/2) | `failed` / `completed` |
| codex | Ctrl-C ×2 or ×3, 1 s apart | `0 natural` (5/5) | `completed` |
| codex | `/quit`, `/exit`, Ctrl-D | `0 natural` | `completed` |
| claude | Ctrl-C ×2, 0.05 s apart | `0 natural` | `completed` |

`130 crash` is `_classify_exit`'s report for `WIFSIGNALED` + `SIGINT`
(`128 + 2`). Human Ctrl-C was the observed trigger; the result itself does
not identify the signal sender. The exact Codex-internal reason was not
established, and the spec does not depend on it. Claude Code never died by
signal on any quit path tried. These supervisor-only probes did not launch
a bootstrap target or ordinary ticket and did not persist activity records;
the table infers activity labels from the mapping code. The observed
Codex-specific, timing-dependent mechanism is consistent with the population:
all 24 `failed` records are codex, mostly bootstrap or
owner-step sessions that a human closes, and the reported 2026-10-05 session's
transcript ends on a clean `task_complete` four minutes before its
`ended_at`.

**Misclassification fix approved** for the exact `crash` / `128 + SIGINT`
result, whether idle or mid-turn. The schema already has `interrupted` for
it. This approval does not establish the cause of any historical record or
complete the required end-to-end reproduction. The owner reports closing
the session with Ctrl-C, consistent with the probe mechanism.
Past records cannot be reclassified because
they store no exit code. Any remaining `failed` records with very short
`elapsed_seconds` (0–8 s) look like genuine startup failures and must stay
`failed`.

### Acceptance criteria

- [x] Complete the outstanding live lifecycle reproduction: first a real
      Codex bootstrap launch closed by the human, then an ordinary ticket
      step that advances through a matching done sentinel. For each, record
      the launch target, raw child wait/exit evidence, normalized supervisor
      exit code and kind, sentinel observation, persisted `outcome_status`,
      and expected versus observed workflow progress. Include a real model
      turn. Clearly distinguish raw evidence from normalized results; record
      unavailable evidence as a gap rather than claiming completion. Arrange
      human launches from their terminal; do not nest agent launches inside
      this launched session. Preserve real failures and timeout behavior.
- [x] `_session_outcome_status` in `src/coga/commands/launch.py` returns
      `interrupted` when `outcome.kind == "crash"` and
      `outcome.exit_code == 128 + signal.SIGINT`.
- [x] Every other mapping is unchanged: `timeout` → `timed_out`; any other
      `crash` (for example `128 + SIGSEGV`, `128 + SIGKILL`, the `1, crash`
      fallback) → `failed`; `natural` with non-zero code → `failed`
      (including natural exit code 130 and the non-TTY fallback
      `natural -SIGINT` result); `done` and `natural 0` → `completed`;
      the `KeyboardInterrupt` → `interrupted` and other-exception → `failed`
      paths in `spawn_agent_session` are untouched.
- [x] `ReplOutcome`, `_classify_exit`, `AgentSessionResult`, and every
      caller's handling of exit code and `kind` are unchanged. Only the
      activity label moves. Chains, megalaunch, and recurring still see
      `130 crash` exactly as before.
- [x] Regression test in `tests/test_launch.py`: extend the
      `test_spawn_captures_failed_and_timed_out_sessions` parametrization (or
      add a sibling) with `ReplOutcome(130, "crash")` → `interrupted`,
      `ReplOutcome(128 + signal.SIGSEGV, "crash")` → `failed`,
      `ReplOutcome(130, "natural")` → `failed`, and
      `ReplOutcome(-signal.SIGINT, "natural")` → `failed`. Assert that
      returned exit code and `termination_kind` remain unchanged.
- [x] Activity records gain
      `exit_code` (int or null) and `exit_kind` (`natural` | `done` |
      `timeout` | `crash` | null), added without a schema bump the way
      `usage_reason` was: older records read back null. A test in
      `tests/test_usage.py` round-trips them and reads an old record as null.
      These are normalized supervisor results, not raw child wait status;
      done teardown reports 0 and timeout reports 124. Spawn capture tests
      assert both fields reach capture unchanged for returned outcomes and
      remain null when the supervisor raises.
- [x] `docs/contexts/coga/internals/activity-capture/SKILL.md` and its
      byte-identical twin
      `src/coga/resources/templates/coga/bootstrap/contexts/coga/internals/activity-capture/SKILL.md`
      define each `outcome_status` value against the supervisor outcome:
      `completed` = done teardown or natural exit 0; `interrupted` = the
      launching process got `KeyboardInterrupt`, or the supervisor returned
      exactly `crash` with code `128 + SIGINT`; `failed` = any other crash,
      non-zero natural result (including non-TTY `natural -SIGINT`), or a
      spawn-path exception; `timed_out` = idle or max-session teardown. Human
      Ctrl-C is the observed example, not signal provenance proved by the
      record. State that `outcome_status` describes the process, not whether
      the work succeeded. Name the new normalized exit fields and their
      limits: they cannot reconstruct raw termination or identify the sender.
- [x] `python -m pytest tests/test_launch.py tests/test_usage.py tests/test_packaging.py`
      passes.

### Proposed shape

1. `src/coga/commands/launch.py`, `_session_outcome_status()`: add one branch
   before the `failed` branch, using `signal.SIGINT` (not a literal 130) and
   a one-line comment naming the Codex double-Ctrl-C case.
2. `tests/test_launch.py`: the parametrized cases above.
3. `src/coga/usage.py`, the record dataclass that holds
   `usage_reason`, plus its `from_dict`-style reader (the
   `usage_reason=_optional_str_value(...)` site) and `capture_session()`,
   gain `exit_code` / `exit_kind` keyword arguments defaulting to None.
   `spawn_agent_session` in `commands/launch.py` keeps `outcome` in scope and
   passes `outcome.exit_code` / `outcome.kind` from its `finally`. Both stay
   None on the exception paths, where no `ReplOutcome` exists.
4. Update both activity-capture twins in one edit. If
   `docs/contexts/coga/internals/agent-spawn/SKILL.md` (which owns
   `ReplOutcome.kind`) needs a pointer, add one line linking to
   activity-capture rather than restating the mapping.

### Out of scope

- Changing `_classify_exit` or `ReplOutcome.kind` (a SIGINT death stays
  `crash` for exit-code consumers), or the PTY proxy's handling of Ctrl-C.
- Making Codex exit cleanly on a fast double Ctrl-C. That is upstream Codex
  behavior.
- Rewriting the 24 historical `failed` records. They hold no exit evidence.
- Megalaunch's no-progress `failed` *result* in `megalaunch.py`.
- Treating SIGHUP or SIGTERM from outside Coga as interrupts. Those were not
  observed on a human quit path; closing the terminal also kills `coga`
  before capture runs.
- Done-signal or sentinel problems (`where-have-code-review-disappeared`).

## Context

### Evidence already on disk

The reported 2026-10-05 session is in `coga/log.md` (search session_id
`01a10dfa-c7d1-7062-b33d-94413f67a6c1`): `[bootstrap/orient]`, cli `codex`,
`outcome_status: failed`, with outcome text "Merged all five open PRs… 80
passed". Its Codex transcript is under
`~/.codex/sessions/2026/10/05/rollout-2026-10-05T14-31-41-01a10dfa-*.jsonl`.
As of 2026-10-08, `coga/log.md` holds 24 `outcome_status: failed` records,
all codex. Claude has 0 failures in about 665 completed records, and codex
has about 351 completed. Of the 24, 15 are bootstrap sessions (9
`bootstrap/orient`, 6 `bootstrap/ticket`), which suggests interactive,
human-closed sessions. Records store neither `exit_code` nor exit `kind`, so
past records cannot confirm a mechanism. Confirming one needs a live repro.

### Where `failed` comes from

- `commands/launch.py` `_session_outcome_status`: `timeout` gives
  `timed_out`; `crash` **or any non-zero `exit_code`** gives `failed`;
  anything else gives `completed`. It never produces `interrupted`, although
  the schema defines it.
- An exception raised in `spawn_agent_session` is also recorded `failed`.
- `repl_supervisor._classify_exit` returns 0 for a done-signal teardown and
  passes a `natural` exit's raw status through. `run_with_done_marker`
  drives the session.
- `usage.py` (`OutcomeStatus`) only stores the value.

The original hypothesis (Codex *exits* non-zero on quit, classified
`natural`) did not hold. The confirmed mechanism is a SIGINT death
classified `crash`; see "Finding" under `## Description`.

### How to reproduce

The design step drove the real supervisor from a tmux pane. The driver was a
script calling `coga.repl_supervisor.run_with_done_marker([cli],
dict(os.environ), session_id="probe")` and writing the `ReplOutcome`. Wait
about 10 s for startup, press Escape to dismiss Codex's "Update available"
screen if shown, then `tmux send-keys C-c` twice with a 0.05 s gap. Run with
cwd at a Codex-trusted folder (the repo), or Codex stops at its folder-trust
screen. With no prompt sent, no model turn is spent. Outside the supervisor
(`bash -c 'codex'` in tmux), the same keys exited 0 in every trial, so test
through `run_with_done_marker`, not a bare shell. Codex's own SQLite log
(`~/.codex/logs_2.sqlite`) only reaches back to about 2026-10-07 and holds
nothing for the reported session.

Megalaunch's no-progress `failed` *result* (`megalaunch.py`) is a separate
field from `outcome_status`; leave it unchanged.

### Related ticket

`where-have-code-review-disappeared` owns workflow chains that stop
advancing (sentinel and stale environment). The two tickets share
`_classify_exit` only in passing. If a done-signal teardown ever turns out to
be recorded `failed`, coordinate the fix with that ticket.

### Topics (cited, not attached)

- coga/internals/activity-capture (`docs/contexts/coga/internals/activity-capture/SKILL.md`):
  this ticket edits its `outcome_status` definition, so read it first,
  especially the schema-2 activity fields and "Capture point and gates".
- coga/internals/agent-spawn (`docs/contexts/coga/internals/agent-spawn/SKILL.md`):
  owns `ReplOutcome.kind` (`natural` / `done` / `timeout` / `crash`), which
  this ticket does not change.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Design step (2026-10-08, claude)

- Live repro done under the real supervisor (tmux + `run_with_done_marker`).
  A fast Codex double Ctrl-C gives `130 crash` (SIGINT death) and
  would map to `failed`; the probe itself did not capture an activity record.
  Slow Ctrl-C, `/quit`, `/exit`, and Ctrl-D give
  `0 natural`. Claude gives `0 natural`. Table and steps are in
  Description and Context.
- Outcome proposed: **misclassification confirmed**. Map SIGINT-crash to
  `interrupted`. Leave `ReplOutcome.kind` and exit codes alone.
- Not done in this step: an ordinary ticket step closed by a done sentinel
  (that path is `done` → 0 → `completed` by code, and no failure record
  shows a bump), and a Codex quit after a real model turn. One after-turn
  trial outside the supervisor exited 0.

## Owner review (2026-10-15)

- Owner approved the proposed design choices and reported closing the session
  with Ctrl-C. This is consistent with the observed mechanism, but does not
  prove the exit status of that historical session.
- Q1 resolved: add nullable `exit_code` / `exit_kind` as normalized supervisor
  results, with backward-compatible reads and spawn-to-capture tests.
- Q2 resolved: the exact `crash` / `128 + SIGINT` result is `interrupted`
  whether idle or mid-turn; the record does not establish signal sender.
- Evaluator must-fix 1 accepted: the bootstrap and ordinary-ticket lifecycle
  reproductions remain explicit implementation acceptance criteria. Relabeled
  the probe table as inferred activity labels, not persisted capture evidence.
- Evaluator must-fix 2 accepted: narrowed the documentation predicate and
  preserved nonzero-natural fallback behavior, including `-SIGINT`.
- Added unchanged termination-kind assertions and exception-path null checks
  from the evaluator's optional recommendations. No implementation changes.
- Owner approved advancement to `implement`. Review-design is complete;
  the next session implements the approved scope and gathers the outstanding
  lifecycle evidence. No implementation code changed in this review assist.

## Open Questions

None about design scope. Required live lifecycle evidence remains outstanding
implementation work.

## Evaluator review

Cold review, 2026-10-08 (Codex). **Needs owner resolution before
implementation.** The narrow mapping change is implementable and belongs in
the existing shared spawn infrastructure. It preserves caller exit behavior;
the remaining issues are the evidence requirement and the proposed definition.
This is not owner approval of either outcome or the optional schema fields.

### Must resolve before implementation

1. **High — the required lifecycle reproduction is incomplete, and the
   acceptance criteria do not carry the missing work forward.** Description
   requires a real bootstrap launch followed by an ordinary ticket step,
   capturing raw status, supervisor kind, sentinel, persisted activity label,
   and expected workflow progress. The Finding / How to reproduce sections
   instead describe a direct `run_with_done_marker([cli], ...,
   session_id="probe")` invocation with no model turn. That helper neither
   launches a bootstrap target nor writes an activity record:
   `src/coga/commands/launch.py::spawn_agent_session` performs the latter in
   its `finally`. The table's label is therefore supported by the mapping
   code, not a demonstrated capture through this probe. The blackboard also
   explicitly records the missing ordinary step. The historical record for
   `01a10dfa-c7d1-7062-b33d-94413f67a6c1` in `coga/log.md` confirms the reported
   symptom but contains no exit evidence. Before handing off, either retain
   the original requirement as an explicit outstanding implementation
   acceptance criterion with those evidence fields, or explicitly accept the
   narrower supervisor reproduction and revise the scope. Do not present the
   required end-to-end investigation as already complete.

2. **Medium — scope the documented interrupt definition to the actual
   predicate, without inferring signal sender.** The proposed documentation
   says an agent killed by SIGINT is `interrupted`, while the acceptance
   criteria require every non-zero `natural` result to remain `failed`.
   `src/coga/repl_supervisor.py::run_with_done_marker`'s non-TTY fallback
   returns `ReplOutcome(-signal.SIGINT, "natural")` for a SIGINT death (both
   the subprocess and gated-fork routes), so that case stays `failed` under
   this design. Also, `_classify_exit` retains the signal number, not its
   sender: externally sent SIGINT and a terminal Ctrl-C are indistinguishable
   once represented as `130 crash`. Keep the narrow implementation, but
   define `interrupted` as launcher `KeyboardInterrupt` or the exact
   `crash` / `128 + SIGINT` result; describe human Ctrl-C as the observed
   example, not provenance proved by the record. Explicitly preserve the
   fallback's non-zero-natural behavior. This avoids expanding the fix into
   the out-of-scope supervisor contract.

### Optional recommendations and owner decisions

- Resolve Open Questions 1 and 2 at the owner gate. If Q1 is accepted, name
  `exit_code` / `exit_kind` as **normalized supervisor results**, not raw
  child wait status. `repl_supervisor._classify_exit` deliberately reports 0
  for done teardown and 124 for timeout, including after child signal death.
  These fields explain the activity mapping but cannot reconstruct raw
  termination or identify the signal sender.
- If adding those fields, extend the spawn capture assertions as well as
  `UsageRecord` round-trip tests: assert code/kind reach capture unchanged
  for returned outcomes and remain null when the supervisor raises. A
  serialization-only test would miss omitted launch-to-capture wiring.
  In `test_spawn_captures_failed_and_timed_out_sessions`, also assert
  `result.termination_kind == repl_outcome.kind`; today it checks exit code
  and reason but not kind.

### Verification and scope

- Checked the named launch mapping, exception paths, `AgentSessionResult`,
  `ReplOutcome`, `_classify_exit`, `usage.UsageRecord.from_json` /
  `capture_session`, launch and usage fixtures, and packaging twin discovery.
  The named edit points exist. Launch and megalaunch consume exit code/kind
  independently of the activity label, consistent with the proposed boundary.
- Read product vision, activity-capture, agent-spawn, extension-model,
  knowledge, and testing topics. The activity-capture twin paths are correct;
  cited topics and the frozen evaluate-design → owner review-design workflow
  fit this work. The packaged workflow is
  `src/coga/resources/templates/coga/bootstrap/workflows/code/design-then-implement.md`.
- Baseline checks (no implementation changes):
  `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q tests/test_repl_supervisor.py -k classify_exit tests/test_launch.py::test_spawn_captures_failed_and_timed_out_sessions tests/test_launch.py::test_spawn_captures_interrupted_session`
  → 4 passed, 31 deselected (the filter selects only classifier tests).
  `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q tests/test_launch.py::test_spawn_captures_failed_and_timed_out_sessions tests/test_launch.py::test_spawn_captures_interrupted_session`
  → 3 passed. No fresh live Codex reproduction was performed in this review.
- Only this blackboard was edited; no ticket-body edits, branch, code, or PR.


## Dev

branch: codex-sigint-interrupted

Plan (implement, 2026-10-15, claude): code + tests + both activity-capture
twins on the branch first; then the human runs the live lifecycle repro from
their terminal with this checkout's `.venv/bin/coga` on the branch (owner
chose: bootstrap `coga orient` with codex, one real turn, fast Ctrl-C x2;
then a throwaway workflow ticket launched with codex that bumps; throwaway
deleted afterwards). Raw wait status is not captured (owner declined strace).

## Implement (2026-10-15, claude)

Implemented the approved scope on `codex-sigint-interrupted` (commit
`1ae28db6d`, pushed):

- `launch._session_outcome_status`: exactly `crash` + `128 + signal.SIGINT`
  → `interrupted`; all other mappings unchanged. `ReplOutcome`,
  `_classify_exit`, `AgentSessionResult`, and caller exit handling untouched.
- `usage.UsageRecord` / `from_json` / `capture_session`: nullable `exit_code`
  and `exit_kind` (new `ExitKind` literal, validated on read, no schema
  bump). `spawn_agent_session` holds `outcome` (None until the supervisor
  returns) and passes its code/kind from the `finally`.
- Tests: parametrized mapping cases in
  `test_spawn_captures_failed_and_timed_out_sessions` (130 crash →
  interrupted; SIGSEGV/SIGKILL/`1` crash, natural 130, natural `-SIGINT` →
  failed; done 0 / natural 0 → completed), with termination_kind and
  exit-field capture asserts; null exit fields on the `KeyboardInterrupt`
  path and on a new supervisor-exception → failed test; usage round-trip,
  pre-field schema-2 record reads null, invalid `exit_kind` rejected,
  schema-1 reads null.
- Docs: activity-capture twins define every `outcome_status` value and the
  exit fields' limits; agent-spawn twins gained a one-line pointer.

### Live lifecycle reproduction (owner ran from `/home/n/Code/coga`)

Ran with a non-editable install of the branch commit (scratch venv), because
launch prepares `main` and the editable install would run main's code. The
agent inside each session used the global `coga` (main) for `mark done`;
capture ran in the branch supervisor. codex-cli 0.162.1.

| | Bootstrap | Ordinary ticket step |
|---|---|---|
| Launch target | `coga chat --agent codex` → `bootstrap/orient` | throwaway `probe-codex-done-sentinel`, `direct/body` step `execute`, `--agent codex` |
| Real model turn | yes: 1 human turn, 3 agent turns, 344 output tokens | yes: agent read README, wrote blackboard line, ran `coga mark done` |
| How it ended | human fast Ctrl-C ×2 after the reply | agent's `coga mark done` (done sentinel) |
| Raw child evidence | **gap**: no watcher line printed; only terminal `^C`. `130 crash` is produced by `_classify_exit` solely for `WIFSIGNALED` + SIGINT, so death by SIGINT is derived, not observed raw | watcher printed `child exited: killed by our signal 15` (SIGTERM teardown) |
| Normalized supervisor | `130 crash` (launch printed `agent exited with code 130`; shell `$?` = 130) | `0 done` (`reporting exit 0 (done-signal received)`; shell exit 0) |
| Sentinel | none expected; none | matching sentinel observed (done-signal teardown) |
| Persisted record | `outcome_status: interrupted`, `exit_code: 130`, `exit_kind: crash` (session `01a14307-c50f-71c2-843f-82160a439c0c`) | `outcome_status: completed`, `exit_code: 0`, `exit_kind: done` (session `01a14308-dbc0-74c0-a644-4c133203322e`) |
| Workflow progress | expected none (stateless); none | expected `task done`; log `[agent:codex] task done`, launch read "task is done" |

Before the fix this bootstrap would have been `failed` (old mapping: any
crash → failed). The probe ticket was deleted afterwards (`coga delete`
from `/home/n/Code/coga`). Not exercised live: timeout and genuine crash
paths (covered by the unit cases); raw wait status (owner declined strace).

## PR

```yaml
title: Record SIGINT-crash sessions as interrupted, with exit evidence
author: claude
author_evidence: Implement session ran as Claude Code (claude-opus-5-5); see Implement handoff.
head: 1ae28db6d85ed7620765b8dbdd9a4ae827701b2a
base: 6738fe520a9272f3b534255187c93cfa21ab0f75
depth: skim
rationale: One-branch mapping change plus two nullable record fields; read the activity-capture definition and the live-repro table.
implementation: Maps exactly ReplOutcome crash/128+SIGINT to outcome_status interrupted and persists the supervisor's normalized exit_code/exit_kind on activity records.
deviations: Also added a supervisor-exception capture test and extra crash cases (SIGKILL, 1-crash fallback, done/natural 0) beyond the listed parametrization.
limitations: Raw child wait status was not captured in the live repro; historical failed records stay unreclassifiable; timeout/genuine crash verified by unit tests only.
files:
  src/coga/commands/launch.py: Add the SIGINT-crash interrupted branch and pass outcome code/kind to capture.
  src/coga/usage.py: Add nullable exit_code/exit_kind (ExitKind) to UsageRecord, its reader, and capture_session.
  tests/test_launch.py: Mapping cases, unchanged exit/kind asserts, exit-field capture and null-on-exception tests.
  tests/test_usage.py: Exit-field round-trip, old-record null reads, invalid exit_kind rejection.
  docs/contexts/coga/internals/activity-capture/SKILL.md: Define each outcome_status value and the exit fields' limits.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/internals/activity-capture/SKILL.md: Byte-identical packaged twin.
  docs/contexts/coga/internals/agent-spawn/SKILL.md: One-line pointer to activity-capture for the mapping.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/internals/agent-spawn/SKILL.md: Byte-identical packaged twin.
review:
  reviewer: none
  kind: none
  status: not-run
  detail: No code review yet; the workflow's later review step owns it. Design approval is not code review.
checks:
  - command: .venv/bin/python -m pytest -q tests/test_launch.py tests/test_usage.py tests/test_packaging.py
    status: passed
    head: 1ae28db6d85ed7620765b8dbdd9a4ae827701b2a
    base: 6738fe520a9272f3b534255187c93cfa21ab0f75
    detail: 286 passed.
  - command: .venv/bin/python -m pytest -q
    status: passed
    head: 78617aefd018a35b8885795316eba3384dafaa8b
    base: fc2f267cf8d5199b6671f59e911667047f61e1c4
    detail: 3682 passed on the pre-rebase commit (src/tests/docs identical to 1ae28db6d) before rebasing onto a main that brought only coga/ state commits; not re-run after rebase.
  - command: live Codex bootstrap + ordinary-step repro (owner terminal, branch install)
    status: passed
    head: 1ae28db6d85ed7620765b8dbdd9a4ae827701b2a
    base: 6738fe520a9272f3b534255187c93cfa21ab0f75
    detail: Records interrupted/130/crash and completed/0/done as expected; see table.
```

