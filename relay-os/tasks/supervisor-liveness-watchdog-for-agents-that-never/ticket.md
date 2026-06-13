---
title: Supervisor liveness watchdog for agents that never signal done
status: done
mode: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts:
- dev/code
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
  - name: review
    skills: []
    assignee: owner
---

## Description

Priority: medium today, CRITICAL-PATH for trustworthy unattended execution.

**What already exists (PR #277, do not re-implement).** The *detection* half of
the liveness watchdog already landed. `run_with_done_marker`
(`repl_supervisor.py:114`) takes an `idle_timeout` parameter: when the REPL
produces no output for that many seconds, the supervisor tears it down via the
existing SIGTERM->SIGKILL escalation (`_trigger_term` at `:203`, breach check at
`:251-256`, `_KILL_GRACE_SECONDS` at `:53`). `relay launch --idle-timeout`
(`commands/launch.py:88`) exposes it, and the recurring sweep arms a 900s default
(`_RECURRING_IDLE_TIMEOUT_SECONDS`, `recurring.py:41`; `RELAY_REPL_IDLE_TIMEOUT`
override; disarmed for `--interactive`). A real-PTY test already covers the
teardown: `tests/test_repl_supervisor.py:139`
(`test_idle_timeout_terminates_silent_child`, `sleep 30` vs a 0.5s limit).

**What's still broken — this ticket.** A breached idle-timeout is currently
reported as a *clean done*. `_classify_exit` (`repl_supervisor.py:316`) takes
only a `sent_term: bool` and maps *any* supervisor-sent SIGTERM/SIGKILL to exit 0
/ "done-signal received" (the `sent_term` branch at `:333-348`). It cannot tell a
cooperative teardown (agent signalled done, then we SIGTERM'd the lingering REPL)
from a timeout teardown (agent never signalled, we killed it). The docstring even
admits the idle-timeout path is "reported exit 0" (`:139`), and the existing test
*asserts* exit 0 for a timeout. So the wedge is reported as success.

Why that's dangerous, precisely (the original ticket overstated this — here is
the accurate version): `_stop_if_unfinished_after_launch` (`recurring.py:852`)
ignores the exit code; it re-reads ticket status from disk. So an **auto-mode**
timeout leaves the ticket `in_progress` and the sweep already stops loudly. The
real silent failure is **interactive-mode**: a timed-out interactive ticket hits
the `interactive or ticket.mode == "interactive"` branch (`recurring.py:872`) and
is **paused** — `mark_paused` with `actor=human:<user>` and "paused (... → paused)
— interactive recurring launch exited unfinished". A genuine wedge is recorded as
if a human deliberately parked the run. Indistinguishable from intent; no timeout
trace anywhere.

Scope — close the classification gap, not the (already-landed) detection:
1. **Thread a termination *kind* (done vs timeout) through `_trigger_term` ->
   `_classify_exit`.** `_trigger_term` has three call sites: sentinel (:248) and
   pty-byte-match (:273) are both *done*; only the idle-timeout breach (:255) is
   *timeout*. A timeout teardown returns non-zero with a timeout note instead of
   "done-signal received". Update the existing test's assertion (it currently
   asserts 0) and add a done-teardown case so both kinds are pinned.
2. **Durable timeout record.** On a timeout teardown, write a `log.md` entry +
   Slack post classifying it as a *timeout* — distinct from a clean done and from
   a deliberate `relay panic`. Prefer surfacing the kind *up* to `recurring.py`
   (which already calls `notify`/`mark_paused`) rather than wiring Slack/`log.md`
   into the supervisor, which today only writes to the console — and let
   `_stop_if_unfinished_after_launch` branch on kind=timeout instead of mistaking
   an interactive timeout for a human pause.
3. **Config surface (still greenfield).** `config.py` has no `[launch]`/timeout
   keys; today it's a hardcoded constant + env var. Add per-task / per-mode
   config in `relay.toml` (interactive humans may want no timeout; unattended
   runs want one) so the limit isn't only an env override.
4. **Optional, decide on review — max-session wall-clock duration.** Idle-output
   timeout misses an agent stuck in an *output-producing* infinite loop. Since we
   are building the config surface anyway, a wall-clock cap alongside `idle_timeout`
   is cheap and closes that gap. In scope unless the human drops it; flagged here
   so "and/or" doesn't become silent scope drift.

Acceptance: a timed-out REPL (idle past the limit) is classified as a **timeout**
— non-zero exit, a timeout entry in `log.md` and Slack, and *not* reported as a
clean done or recorded as a human pause — verified against a real PTY that sleeps
past the limit (extend the existing `tests/test_repl_supervisor.py` coverage).

## Context

Already-landed detection (PR #277), do not redo: `repl_supervisor.py`
`run_with_done_marker` (:114, `idle_timeout` param), idle breach + teardown
(:251-256), `_trigger_term` (:203), `_KILL_GRACE_SECONDS` (:53);
`commands/launch.py:88` (`--idle-timeout`); `commands/recurring.py`
`_RECURRING_IDLE_TIMEOUT_SECONDS` (:41), `_recurring_idle_timeout` (:911);
`tests/test_repl_supervisor.py:139`.

This ticket's surface: `repl_supervisor.py` `_classify_exit` (:316) and its
`sent_term` branch (:333-348) — currently a bool, needs a done-vs-timeout kind;
`commands/recurring.py` `_stop_if_unfinished_after_launch` (:852) and the
interactive-pause branch (:872-896) — the masquerade to fix; `config.py` —
greenfield `[launch]`/timeout keys. Reuse the existing SIGTERM->SIGKILL teardown;
do not add a second kill path. Related:
`stream-agent-progress-in-auto-mode-and-recurring-l`.
