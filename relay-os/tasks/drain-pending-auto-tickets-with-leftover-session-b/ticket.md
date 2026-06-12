---
title: Drain pending auto tickets with leftover session budget after recurring sweep
status: draft
mode: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
- relay/recurring
- relay/codebase
- dev/code
skills: []
workflow: code/design-then-implement
---

## Description

After a bare `relay recurring` sweep finishes its scheduled work, it should
check whether the agent still has usage budget left in the current window and,
if so, drain pending ordinary auto tickets: launch tickets that are
`status: active`, `mode: auto`, and assigned to a configured agent type,
oldest first, until the budget runs out. Stop on the first failure or
unfinished non-interactive launch, mirroring how the sweep already stops on an
unfinished recurring launch. The budget signal is the agent's own usage-limit
reporting — Claude Code and Codex both expose how much of the current usage
window remains — so the sweep reads remaining usage per agent type rather than
tracking tokens itself. If the design step finds no stable programmatic way to
read remaining usage for an agent, it should come back with fallback options
(time-box, fixed N-tickets cap, or skip the drain) rather than forcing the
probe.

## Context

- The sweep lives in `src/relay/commands/recurring.py` (run loop) with shared
  logic in `src/relay/recurring.py`. There is no token/budget tracking
  anywhere in relay today.
- The design step must pin down the exact per-agent mechanism for reading
  remaining usage (Claude Code and Codex each expose usage limits, but the
  programmatic invocation needs verifying), the threshold that counts as
  "enough to start a ticket", and what happens when usage can't be read for
  an agent type (conservative default: skip the drain for that agent).
- Drained tickets are ordinary tasks under `relay-os/tasks/`, launched the
  same way a human `relay launch <slug>` would be; they keep their own
  workflows and bump normally. Do not confuse them with period tasks — the
  `recurring-` slug prefix is the period-task identity marker and ordinary
  tickets never carry it.
- The drain should be observable in Slack: post which tickets were drained,
  or that the drain was skipped for lack of budget. Note there is no
  end-of-sweep Slack summary today — output is per-event `notify()` calls in
  `_broadcast_scan()`, which fire *before* launches — so this is a new
  notification point, not an edit to an existing one. (Slack mechanics live
  in the `relay/sync` context if the implement step needs more than
  `notify()`.)
- "Oldest first" needs a concrete ordering source — frontmatter has no
  created-date field, so git history, directory mtime, and slug order all
  differ. Design step picks one and says why.
- Other open points for the design step: the threshold that counts as enough
  budget to start a ticket (a crude heuristic like ">X% of window remains"
  is acceptable), whether usage is re-probed between drained launches, and
  whether the drain still runs when the recurring sweep itself stopped early
  on an unfinished launch (default: no — an aborted sweep skips the drain).
- Out of scope: any priority/ordering system beyond oldest-first, draining
  `mode: interactive` tickets, and resuming orphaned `in_progress` ordinary
  tickets (period-task orphan handling stays as is).
