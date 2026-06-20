---
title: Drain pending auto tickets with leftover session budget after recurring sweep
status: in_progress
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
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
step: 1 (design)
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
  differ. Design step picks one and says why. (See locked decision below —
  preference is the first `log.md` timestamp.)
- Other open points for the design step: the threshold that counts as enough
  budget to start a ticket (a crude heuristic like ">X% of window remains"
  is acceptable), whether usage is re-probed between drained launches, and
  whether the drain still runs when the recurring sweep itself stopped early
  on an unfinished launch (default: no — an aborted sweep skips the drain).
- Out of scope: any priority/ordering system beyond oldest-first, draining
  `mode: interactive` tickets, and resuming orphaned `in_progress` ordinary
  tickets (period-task orphan handling stays as is).

### Decisions locked with Nick (2026-06-20) — design refines, does not re-open

1. **Budget signal — read from the server, per agent type.** Prefer reading
   remaining usage from the agent's API server (Anthropic for `claude`,
   OpenAI for `codex`) over scraping CLI `/usage` output, since a server read
   is more stable headless. Design must *verify the mechanism actually works*
   (a real go/no-go probe of the endpoint, not just documentation) before
   writing the design, and must confirm the signal reflects the subscription
   **usage window** (the 5h/weekly budget) rather than only per-minute API
   rate-limit headers. The probe is an interface with one implementation per
   configured agent type. If usage can't be read for an agent type →
   conservatively skip the drain for that agent. If no stable read exists at
   all, come back with the documented fallbacks (time-box / fixed N cap /
   skip).
2. **Threshold — a `relay.toml` config key.** The "enough budget to start a
   ticket" threshold is tunable config (e.g. minimum % of window remaining,
   optional max-tickets-per-drain cap), not a hardcoded constant. Design names
   the exact key(s) and default(s) and says whether usage is re-probed
   between launches.
3. **Ordering — oldest-first by creation = first `log.md` timestamp.** Add a
   `first_activity()` helper mirroring the existing `last_activity()` in
   `src/relay/logfile.py` (first parseable `YYYY-MM-DD HH:MM` line = the
   draft/create entry). This is committed content, so it survives `git clone`
   / checkout — unlike file mtime, which resets on checkout and would collapse
   to "all equal" on the cron machine. `relay status` already orders by
   `last_activity` (committed), so this stays in the same robust family.
   Consistency add: expose `relay status --order-by created` backed by the
   same `first_activity()` helper so a human can inspect the exact order the
   drain will service tickets in.
