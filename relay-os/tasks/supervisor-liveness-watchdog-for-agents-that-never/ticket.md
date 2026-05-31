---
title: Supervisor liveness watchdog for agents that never signal done
status: draft
mode: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts: []
skills: []
workflow: null
---

## Description

Priority: medium today, CRITICAL-PATH the moment recurring lands. The
supervisor detects *cooperative* termination only; a genuinely wedged agent
hangs indefinitely.

Why now: recurring tasks launch **sequentially, each blocking until exit**
(`recurring.py:70`). With no watchdog, a single wedged task — stuck tool call,
infinite loop, or an agent that finished but never called `relay bump` — stalls
the entire sweep, and every later recurring task silently never runs. Attended
interactive use is unaffected (a human Ctrl-Cs it); this is purely an
unattended-execution problem, which is exactly the mode recurring introduces.
Treat this as a fast-follow to recurring + autobump, not a someday.

`run_with_done_marker` (`repl_supervisor.py:79`) detects task completion through
two cooperative channels: the `RELAY_DONE_SENTINEL` file (written by `relay
bump`/`mark done`/`panic`) and a PTY byte-match on `DONE_MARKER`. There is **no
timeout, no max-session duration, and no "no output for N minutes -> act"
watchdog** — the `select()` proxy loop will shuttle bytes forever. An agent
stuck in a tool call, or one that simply never calls any relay command, is never
detected; it blocks until a human notices and kills it, and (under cron /
recurring) blocks the sweep indefinitely. The code comments worry about a
"wedged REPL blocking the sweep" (`repl_supervisor.py:48-50`) but only handle the
case where the agent *did* signal done and then ignored SIGTERM — not the case
where it never signals at all.

Add a liveness watchdog:
- a configurable max-session duration and/or idle-output timeout
- on breach: a clear warning, then a graceful SIGTERM->SIGKILL escalation
  (reuse the existing `_KILL_GRACE_SECONDS` teardown), and a `log.md` entry +
  Slack post classifying it as a timeout (distinct from a clean done or a
  deliberate panic)
- per-task / per-mode configurability (interactive humans may want no timeout;
  unattended/recurring runs definitely want one)

This is a prerequisite for trustworthy unattended execution and pairs with the
auto-mode streaming work — especially now that recurring is about to land.

Acceptance: an agent that produces no output / never signals for longer than the
configured limit is torn down cleanly with a timeout classification in `log.md`
and Slack; tested against a real PTY that sleeps past the limit.

## Context

Code: `src/relay/repl_supervisor.py` (loop ~174, teardown/`_KILL_GRACE_SECONDS`
~190-199, done channels ~201-216, exit classification `_classify_exit` ~251).
Related: `stream-agent-progress-in-auto-mode-and-recurring-l`.
