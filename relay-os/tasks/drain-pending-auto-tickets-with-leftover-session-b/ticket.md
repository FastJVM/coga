---
title: Drain pending auto tickets with leftover session budget after recurring sweep
status: in_progress
mode: interactive
owner: nick
human: nick
agent: claude
assignee: nick
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
step: 2 (review-design)
---

## Description

After a bare `relay recurring` sweep finishes its scheduled work, the leftover
usage budget in the current window is wasted: pending ordinary auto tickets sit
untouched until a human launches them, even though the machine is sitting idle
with budget to spare. This ticket adds a **drain**: once the scheduled sweep
completes cleanly, check the remaining usage budget per agent type and launch
pending ordinary auto tickets — `status: active`, `mode: auto`, assigned to a
configured agent type — oldest first, until the budget for that agent runs out.
Stop on the first failed or unfinished non-interactive launch, mirroring how
the sweep already stops on an unfinished recurring launch.

The budget signal is the agent's own subscription usage-window reporting (the
5h/weekly budget), read per agent type rather than relay tracking tokens
itself. The design step's go/no-go probe (decision #1) has been **run against
the real endpoints** — results below:

- **Claude — verified GO (free + fresh).** `GET
  https://api.anthropic.com/api/oauth/usage` with the OAuth bearer token from
  `~/.claude/.credentials.json` returns the subscription window directly
  (`five_hour.utilization`, `seven_day.utilization` as percent-used, plus
  reset times). It is a plain read that costs no tokens and reflects usage as
  of now. Confirmed this is the subscription usage window, not per-minute
  rate-limit headers.
- **Codex — no free/fresh endpoint; primed-snapshot read (Nick's call).**
  Every ChatGPT-backend usage `GET` is Cloudflare-blocked (403); codex only
  emits its window data (`primary` 5h / `secondary` weekly `used_percent`)
  as a `rate_limits` snapshot attached to an actual model call, persisted to
  `~/.codex/sessions/**/rollout-*.jsonl`. The chosen mechanism (verified
  working): fire **one** minimal throwaway `codex exec` at the start of the
  drain to prime a fresh snapshot, then read it from the newest rollout file.
  After the first codex drain launch the snapshot self-refreshes, so
  per-ticket re-reads stay fresh for free.

Any probe that errors, times out, or can't be read is treated as "no budget
signal" → that agent's tickets are conservatively skipped; the probe never
crashes the sweep.

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

## Acceptance Criteria

- [ ] After a **bare** `relay recurring` sweep completes its scheduled launches
      cleanly, the drain runs — including when no recurring tasks were due
      (leftover budget + pending tickets is exactly that case). `--all` and
      `--interactive` sweeps do **not** drain.
- [ ] If the sweep aborts early (a non-interactive recurring launch returned
      unfinished → `sys.exit(1)` in `_stop_if_unfinished_after_launch`), the
      drain does **not** run.
- [ ] The drain is gated by config (`[recurring.drain]`, see Proposed Shape):
      disabled by default; when disabled the sweep behaves exactly as today.
- [ ] Eligible tickets are exactly: `status: active`, `mode: auto`, `assignee`
      is a configured agent type (in `cfg.agents`), and the ticket is an
      ordinary task — **not** under `tasks/recurring/`. `in_progress`, `draft`,
      `paused`, `done`, human-assigned, and `mode: interactive`/`script`
      tickets are excluded.
- [ ] Eligible tickets are serviced oldest-first by `first_activity()` (the
      first parseable `YYYY-MM-DD HH:MM` line in `log.md`).
- [ ] A new `first_activity(task_dir)` helper exists in
      `src/relay/logfile.py`, mirroring `last_activity()` (walks forward, first
      parseable timestamp, `None` when absent/empty/unparseable), with tests.
- [ ] `relay status --order-by created` sorts by `first_activity()` (oldest
      first by default), is listed in `--order-by` choices/help, and has a test.
- [ ] A `UsageProbe` abstraction exists with one implementation per configured
      agent type. The Claude impl reads the live OAuth usage endpoint; the
      Codex impl primes once via a throwaway `codex exec` then reads the newest
      rollout `rate_limits` snapshot. Both fail soft (return "no signal" on any
      error/timeout/missing-credential), never raising into the sweep.
- [ ] "Remaining budget" is computed as the **minimum** of `100 −
      used_percent` across the windows the probe returns (both the 5h and the
      weekly window must clear the threshold), so the binding window governs.
- [ ] A ticket is launched only if its assignee's remaining budget ≥
      `min_remaining_percent`. An agent whose budget is below threshold, or
      whose probe returned no signal, has its remaining tickets skipped for the
      rest of this drain (claude budget re-probed per ticket since it is free;
      once an agent is marked exhausted/unreadable it is not re-probed).
- [ ] The drain stops entirely on the first launched ticket that returns
      unfinished/failed (same check as the recurring sweep), and respects an
      optional `max_tickets` cap.
- [ ] Drained launches go through the same `relay launch <slug>` path a human
      would use; drained tickets keep their own workflow and bump normally.
- [ ] The drain is observable: a single one-line summary is posted to the
      notification channel naming the drained tickets, or stating the drain was
      skipped for lack of budget / unreadable usage — but only when there was
      at least one eligible ticket (no post when nothing was eligible). This is
      a new notification call, not an edit to `_broadcast_scan()`.
- [ ] Command handlers stay thin: selection, ordering, probing, and the drain
      loop live in importable modules (`src/relay/drain.py`,
      `src/relay/usage.py`), not in `commands/recurring.py`.
- [ ] `[recurring.drain]` config keys are parsed in `config.py` with
      validation and defaults, surfaced on `Config`, and covered by tests.
- [ ] `python -m pytest` passes; `relay validate --json` is clean. New behavior
      has unit tests with the network/codex calls mocked (no live calls in the
      suite). `example/` fixtures updated if selection/ordering needs them.

## Proposed Shape

### 1. `first_activity()` + `relay status --order-by created`
- `src/relay/logfile.py`: add `first_activity(task_dir) -> datetime | None`,
  the forward-walking mirror of `last_activity()`. Export it in `__all__`.
- `src/relay/commands/status.py`: add `"created"` to `ORDER_BY_CHOICES`; add a
  `"created_ts"` row value from `first_activity(ref.path)`; sort it
  oldest-first by default (same two-pass None-handling as `updated`, but
  ascending), `--reverse` flips. Update the `--order-by` help string.

### 2. Usage probe — `src/relay/usage.py` (new)
- `@dataclass UsageWindow { label: str; used_percent: float; resets_at:
  datetime | None }` and `@dataclass UsageSnapshot { windows: list[UsageWindow]
  }` with `remaining_percent` = `min(100 - w.used_percent for w in windows)`
  (returns 100.0 if no windows).
- `class UsageProbe(Protocol): def read(self) -> UsageSnapshot | None` — `None`
  means "no signal, skip this agent".
- `ClaudeUsageProbe`: read `~/.claude/.credentials.json` →
  `.claudeAiOauth.accessToken`; `GET https://api.anthropic.com/api/oauth/usage`
  with `Authorization: Bearer <token>` (only required header) and a short
  timeout (~10s) via `urllib.request` (stdlib — no new dep); parse
  `five_hour.utilization` and `seven_day.utilization` into two `UsageWindow`s.
  Any exception / non-200 / missing file → `None`. Caveat to note in code: on
  macOS Claude stores credentials in the Keychain, not this file; the cron
  target is Linux so the file path is the supported one, and a missing file
  fails soft (skip) rather than erroring.
- `CodexUsageProbe`: on first `read()` (memoized for the drain), fire one
  throwaway `codex exec --json -s read-only --skip-git-repo-check "Reply with
  exactly: ok" </dev/null` with a timeout, **stdin redirected from /dev/null**
  (without it codex blocks on "Reading additional input from stdin"). Ignore
  stdout (the `--json` stream does not carry rate_limits). Then read the newest
  `~/.codex/sessions/**/rollout-*.jsonl`, parse the last `rate_limits` object
  → `primary` (5h) and `secondary` (weekly) `used_percent` into `UsageWindow`s
  (`resets_at` is unix epoch seconds). Any failure → `None`.
- `probe_for_agent(cfg, agent_name) -> UsageProbe | None`: dispatch on the
  agent's `cli` (`claude` → ClaudeUsageProbe, `codex` → CodexUsageProbe), else
  `None` (unknown agent CLI → no probe → skip, conservatively).

### 3. Drain orchestration — `src/relay/drain.py` (new)
- `eligible_auto_tickets(cfg) -> list[TaskRef]`: `list_tasks(cfg)` filtered to
  active + auto + assignee in `cfg.agents` + not `is_under(ref.directory,
  "recurring")`; sorted by `first_activity()` ascending (None sorts last).
- `drain_pending_auto_tickets(cfg)`: the loop. Build one probe per agent type
  on demand (so codex is only primed if a codex ticket exists). Maintain a
  per-agent cache of `{exhausted, unreadable}`. For each eligible ticket in
  order: skip if its agent is already exhausted/unreadable; else probe (claude
  re-probed each ticket; mark exhausted when `remaining_percent <
  min_remaining_percent`, mark unreadable when probe returns `None`); if OK,
  launch via the existing `relay launch` entrypoint (non-interactive, same call
  shape the sweep uses with `return_timeout=True`); on an unfinished/failed
  return, stop the whole drain; honor `max_tickets`. Collect drained slugs and
  the stop reason, then post the one-line summary (only if there was ≥1
  eligible ticket). Note: the recurring `mode: auto` template ban
  (`_effective_mode`) does **not** apply here — that guards scheduled
  *recurring template* launches; draining ordinary auto tickets unattended is
  the intended behavior and its visibility comes from the summary + each
  launch's own broadcasts.

### 4. Hook into the sweep — `src/relay/commands/recurring.py`
- In `main()`, for the bare sweep only (`not all_ and not interactive`), call
  `drain.drain_pending_auto_tickets(cfg)` **after** the recurring launch loop,
  and also on the "no recurring tasks due" path (restructure the early
  `return` so the drain still runs). The existing `sys.exit(1)` on an
  unfinished non-interactive recurring launch naturally skips the drain (the
  process ends), satisfying "aborted sweep skips the drain".

### 5. Config — `src/relay/config.py`
- Parse `[recurring.drain]` (new `_parse_recurring`/`_parse_drain` helper, same
  validation style as `_parse_launch`), surfaced on `Config`:
  - `drain_enabled: bool = False` — opt-in; default keeps today's behavior.
  - `drain_min_remaining_percent: float = 20.0` — per-agent floor (applied to
    every returned window).
  - `drain_max_tickets: int = 0` — `0`/absent = unlimited.
- Re-probe cadence (decision #2): claude is re-probed before every ticket
  (free GET); codex's snapshot is re-read each time but only primed once via
  the throwaway, and naturally refreshes after each codex launch.

### 6. Notifications
- One end-of-drain summary via the notification layer (live `post()` — see the
  `relay/sync` context for mechanics), e.g. `🫗 drain: launched 3 pending auto
  ticket(s): a, b, c` or `🫗 drain skipped — <agent> usage at 4% remaining`.
  Gate on "≥1 eligible ticket existed" so quiet sweeps stay silent.

### 7. Tests
- `first_activity()` unit tests (present/absent/unparseable/multi-line).
- `relay status --order-by created` ordering test.
- Usage parsing tests against captured JSON fixtures (Claude usage body; codex
  rollout `rate_limits` line) — no live network/codex calls; monkeypatch the
  HTTP fetch and the codex-exec/rollout-read seams.
- Drain selection/ordering test; drain-loop tests for: budget above/below
  threshold, unreadable→skip-agent, stop-on-unfinished, `max_tickets`, disabled
  (no-op), aborted-sweep-skips-drain.
- Config parsing tests for `[recurring.drain]` defaults + validation.

## Out of Scope

- Any priority/ordering beyond oldest-first by `first_activity()`.
- Draining `mode: interactive` or `mode: script` tickets.
- Resuming orphaned `in_progress` ordinary tickets (period-task orphan
  handling is unchanged).
- A fresh standalone Codex usage endpoint — none exists; the throwaway+rollout
  read is the deliberate mechanism. Likewise no Anthropic Admin/cost API.
- Reading Claude credentials from the macOS Keychain (Linux file path only;
  absence fails soft → skip).
- Cross-window or dollar-based budgeting, historical usage tracking, or any
  persisted budget state in relay (the probe is read-only and stateless).
- Concurrency / parallel draining — the drain is sequential like the sweep.
- Changing the recurring sweep's own launch/stop semantics.
