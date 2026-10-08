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
step: 2 (evaluate-design)
agent: claude
launch_generation: pending:6fd877de-c80d-493b-800e-6b434a947421
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

Done is one of two outcomes, chosen by the owner at `review-design`:

- **Misclassification confirmed:** fix the mapping for the confirmed
  mechanism, add a regression test, and update the `outcome_status` meaning
  in coga/internals/activity-capture (canonical and packaged twin).
- **Classification correct** (Codex really exits non-zero, and `failed`
  correctly means process failure): no mapping change. Deliver the evidence,
  clarify the `outcome_status` definition in activity-capture, and, if the
  owner approves, start recording `exit_code` / exit `kind` so future
  records can be audited. This may be a docs-only change.

### Finding (design step, 2026-10-08)

The leading hypothesis was right in effect but wrong in detail. Codex does
not *exit* non-zero when a human quits. It is **killed by SIGINT** when the
human double-taps Ctrl-C quickly. Live repro under the real supervisor
(`repl_supervisor.run_with_done_marker(["codex"], …)` in a tmux pane, codex-cli
0.160.1, Claude Code 2.1.294, idle composer, no prompt sent):

| CLI | Human quit path | `ReplOutcome` | `outcome_status` today |
|---|---|---|---|
| codex | Ctrl-C ×2, 0.05 s apart | `130 crash` (2/2) | `failed` |
| codex | Ctrl-C ×2, 0.2 s apart | `130 crash` (1/2), `0 natural` (1/2) | `failed` / `completed` |
| codex | Ctrl-C ×2 or ×3, 1 s apart | `0 natural` (5/5) | `completed` |
| codex | `/quit`, `/exit`, Ctrl-D | `0 natural` | `completed` |
| claude | Ctrl-C ×2, 0.05 s apart | `0 natural` | `completed` |

`130 crash` is `_classify_exit`'s report for `WIFSIGNALED` + `SIGINT`
(`128 + 2`), a signal Coga did not send. The SIGINT comes from the human's
own keystroke reaching Codex's terminal as a signal rather than a byte. The
exact Codex-internal reason was not established, and the spec does not
depend on it. Claude Code never died by signal on any quit path tried. So the
effect is Codex-specific, timing-dependent, and caused by a human. It matches
the population: all 24 `failed` records are codex, mostly bootstrap or
owner-step sessions that a human closes, and the reported 2026-10-05 session's
transcript ends on a clean `task_complete` four minutes before its
`ended_at`.

**Misclassification confirmed** for this mechanism. A SIGINT death caused by
the human's own Ctrl-C is an interrupt, not a process failure, and the schema
already has `interrupted` for it. Past records cannot be reclassified because
they store no exit code. Any remaining `failed` records with very short
`elapsed_seconds` (0–8 s) look like genuine startup failures and must stay
`failed`.

### Acceptance criteria

- [ ] `_session_outcome_status` in `src/coga/commands/launch.py` returns
      `interrupted` when `outcome.kind == "crash"` and
      `outcome.exit_code == 128 + signal.SIGINT`.
- [ ] Every other mapping is unchanged: `timeout` → `timed_out`; any other
      `crash` (for example `128 + SIGSEGV`, `128 + SIGKILL`, the `1, crash`
      fallback) → `failed`; `natural` with non-zero code → `failed`
      (including a *natural* exit code of 130, which is the child's own
      choice, not a signal death); `done` and `natural 0` → `completed`;
      the `KeyboardInterrupt` → `interrupted` and other-exception → `failed`
      paths in `spawn_agent_session` are untouched.
- [ ] `ReplOutcome`, `_classify_exit`, `AgentSessionResult`, and every
      caller's handling of exit code and `kind` are unchanged. Only the
      activity label moves. Chains, megalaunch, and recurring still see
      `130 crash` exactly as before.
- [ ] Regression test in `tests/test_launch.py`: extend the
      `test_spawn_captures_failed_and_timed_out_sessions` parametrization (or
      add a sibling) with `ReplOutcome(130, "crash")` → `interrupted`,
      `ReplOutcome(128 + signal.SIGSEGV, "crash")` → `failed`, and
      `ReplOutcome(130, "natural")` → `failed`.
- [ ] *(Only if the owner approves Open Question 1.)* Activity records gain
      `exit_code` (int or null) and `exit_kind` (`natural` | `done` |
      `timeout` | `crash` | null), added without a schema bump the way
      `usage_reason` was: older records read back null. A test in
      `tests/test_usage.py` round-trips them and reads an old record as null.
- [ ] `docs/contexts/coga/internals/activity-capture/SKILL.md` and its
      byte-identical twin
      `src/coga/resources/templates/coga/bootstrap/contexts/coga/internals/activity-capture/SKILL.md`
      define each `outcome_status` value against the supervisor outcome:
      `completed` = done teardown or natural exit 0; `interrupted` = the
      launching process got `KeyboardInterrupt`, or the agent was killed by
      SIGINT (a human Ctrl-C reaching the agent's terminal as a signal);
      `failed` = non-zero natural exit, a death by any other signal Coga did
      not send, or a spawn-path exception; `timed_out` = idle or max-session
      teardown. State that `outcome_status` describes the process, not whether
      the work succeeded, and (if Q1 is approved) name the new fields.
- [ ] `python -m pytest tests/test_launch.py tests/test_usage.py tests/test_packaging.py`
      passes.

### Proposed shape

1. `src/coga/commands/launch.py`, `_session_outcome_status()`: add one branch
   before the `failed` branch, using `signal.SIGINT` (not a literal 130) and
   a one-line comment naming the Codex double-Ctrl-C case.
2. `tests/test_launch.py`: the parametrized cases above.
3. If Q1 is approved: `src/coga/usage.py`, the record dataclass that holds
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
  A fast Codex double Ctrl-C gives `130 crash` (SIGINT death) and is
  recorded `failed`. Slow Ctrl-C, `/quit`, `/exit`, and Ctrl-D give
  `0 natural`. Claude gives `0 natural`. Table and steps are in
  Description and Context.
- Outcome proposed: **misclassification confirmed**. Map SIGINT-crash to
  `interrupted`. Leave `ReplOutcome.kind` and exit codes alone.
- Not done in this step: an ordinary ticket step closed by a done sentinel
  (that path is `done` → 0 → `completed` by code, and no failure record
  shows a bump), and a Codex quit after a real model turn. One after-turn
  trial outside the supervisor exited 0.

## Open Questions

1. Should activity records also start storing `exit_code` and `exit_kind`
   (no schema bump, null on old records) so future `failed` /
   `interrupted` labels can be audited? Recommendation: yes. It is about
   10 lines and would have answered this ticket from `log.md` alone. The
   spec marks it conditional.
2. Should a SIGINT death be `interrupted` even when it happens mid-turn
   (a human aborting real work)? The spec says yes: the human chose to stop
   it, which matches the schema's meaning. Say so if you want mid-work
   aborts to stay `failed`. The record cannot tell the two apart.

