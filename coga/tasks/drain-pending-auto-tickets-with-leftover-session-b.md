---
slug: drain-pending-auto-tickets-with-leftover-session-b
title: Drain pending auto tickets with leftover session budget after recurring sweep
status: in_progress
autonomy: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
- coga/recurring
- coga/codebase
- dev/code
- coga/sync
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
step: 3 (implement)
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
5h/session window plus the weekly window), read per agent type rather than
relay tracking tokens itself. Relay does not try to predict a ticket's cost.
It drains sequentially: launch one eligible ticket, re-read that agent's usage
state, then decide whether to launch the next ticket. The design step's
go/no-go probe (decision #1) has been **run against the real endpoints** —
results below:

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
- Launch precondition: ordinary `mode: auto` launches must already be
  re-enabled before this ticket can ship. In the current codebase,
  `relay launch` temporarily refuses `mode: auto` because auto runs have no
  live progress stream; the separate blocker is
  `auto/stream-agent-progress-in-auto-mode-and-recurring-l`. This ticket does
  not own streaming auto-mode output or re-enabling auto launches.
- The drain should be observable in Slack: post which tickets were drained,
  or that the drain was skipped for lack of budget. Note there is no
  end-of-sweep Slack summary today — output is per-event `notify()` calls in
  `_broadcast_scan()`, which fire *before* launches — so this is a new live
  notification point, not an edit to an existing summary or digest spool.
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
- [ ] This ticket does **not** re-enable ordinary `mode: auto` launches. Before
      implementation proceeds, the existing auto-mode launch block in
      `src/relay/commands/launch.py` must already be gone or explicitly
      resolved by `auto/stream-agent-progress-in-auto-mode-and-recurring-l`.
      If that blocker is still present, implementation stops and reports the
      dependency instead of shipping a drain that can only fail on launch.
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
- [ ] Budget guards are checked against the agent's own **session** and
      **weekly** windows. A launch is allowed only when the 5h/session window
      has at least `drain_min_session_remaining_percent` remaining and the
      weekly window has at least its reset-aware pacing reserve remaining.
      Missing or empty required window data is "no signal" and skips that
      agent; it never means "safe to drain".
- [ ] The weekly guard is time-to-reset aware. For most of the week, preserve
      more of the weekly budget according to a linear pacing curve: at a full
      weekly window before reset, require nearly all weekly budget to remain;
      during the final `drain_weekly_final_window_hours` before reset, require
      only the hard `drain_min_weekly_remaining_percent` floor. This matches
      the intent: care a lot about weekly budget seven days before reset, but
      spend leftover allotment aggressively on the last day without hitting
      zero. If the weekly reset time is missing, the probe returns "no signal".
- [ ] A ticket is launched only if its assignee clears both guards. Treat these
      as safety reserves: if the session window is below its configured floor
      (for example 5% remaining), or the weekly window is below its effective
      pacing reserve, Relay launches nothing else for that agent in this drain.
      An agent whose budget is below guard, or whose probe returned no signal,
      has its remaining tickets skipped for the rest of this drain (claude
      budget re-probed per ticket since it is free; once an agent is marked
      exhausted/unreadable it is not re-probed). The expected recurring cron
      timing is overnight, so this guard is about avoiding zero/exhaustion, not
      reserving daytime interactive capacity inside the same 5h session.
- [ ] The drain stops entirely on the first launched ticket that returns
      unfinished/failed (same check as the recurring sweep), and respects an
      optional `max_tickets` cap.
- [ ] Drained launches go through the same `relay launch <slug>` path a human
      would use; drained tickets keep their own workflow and bump normally.
- [ ] The drain is observable: a single one-line summary is posted through the
      live notification path (`relay.notification.post`, not `notify`) naming
      the drained tickets, or stating the drain was skipped for lack of budget /
      unreadable usage — but only when there was at least one eligible ticket
      (no post when nothing was eligible). This is a new notification call, not
      an edit to `_broadcast_scan()`. Slack failures follow the live-post
      fail-loud semantics documented in `relay/sync`.
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
  datetime | None; window_minutes: int | None = None }` and `@dataclass
  UsageSnapshot { windows: list[UsageWindow] }`. The probe must return one
  session window and one weekly window for the agent family, including
  `resets_at` for the weekly window. A parser that cannot produce the required
  windows returns `None` from the probe rather than an empty or partial
  snapshot.
- Add a helper such as `budget_allows_launch(snapshot, cfg, now) -> bool` that:
  session remaining = `100 - session.used_percent`; weekly remaining =
  `100 - weekly.used_percent`; session must be at or above
  `drain_min_session_remaining_percent`; weekly must be at or above the
  effective weekly floor. Effective weekly floor:
  `drain_min_weekly_remaining_percent` during the final
  `drain_weekly_final_window_hours` before reset; otherwise
  `drain_min_weekly_remaining_percent + (100 -
  drain_min_weekly_remaining_percent) * ((hours_until_reset -
  drain_weekly_final_window_hours) / (weekly_window_hours -
  drain_weekly_final_window_hours))`, clamped to
  `[drain_min_weekly_remaining_percent, 100]`. `weekly_window_hours` comes from
  the weekly window's `window_minutes` when available, else defaults to 168.
  With the default config, the weekly floor is roughly:
  - 7 days before reset: 100% remaining required.
  - 6 days before reset: 84% remaining required.
  - 5 days before reset: 68% remaining required.
  - 4 days before reset: 53% remaining required.
  - 3 days before reset: 37% remaining required.
  - 2 days before reset: 21% remaining required.
  - Final 24h before reset: 5% remaining required.
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
- `CodexUsageProbe`: on first `read()` (memoized for the drain), record
  `started_at`, then fire one throwaway `codex exec --json -s read-only
  --skip-git-repo-check "Reply with exactly: ok" </dev/null` with a timeout,
  **stdin redirected from /dev/null** (without it codex blocks on "Reading
  additional input from stdin"). Ignore stdout (the `--json` stream does not
  carry rate_limits). Then read the newest
  `~/.codex/sessions/**/rollout-*.jsonl`, but accept it only if the file was
  modified after `started_at` and contains parseable `rate_limits`; otherwise
  return `None` rather than using stale data. Parse the last fresh
  `rate_limits` object → `primary` (5h) and `secondary` (weekly)
  `used_percent` into `UsageWindow`s (`resets_at` is unix epoch seconds). Any
  failure → `None`.
- `probe_for_agent(cfg, agent_name) -> UsageProbe | None`: dispatch on the
  agent's `cli` (`claude` → ClaudeUsageProbe, `codex` → CodexUsageProbe), else
  `None` (unknown agent CLI → no probe → skip, conservatively).

### 3. Launch Precondition
- This ticket depends on ordinary `mode: auto` launches being available. If the
  temporary block in `src/relay/commands/launch.py` and its coverage in
  `tests/test_launch_auto.py` are still present, do not implement around it or
  treat the refusal as a drained-ticket failure. Stop with a clear blocker that
  `auto/stream-agent-progress-in-auto-mode-and-recurring-l` must land first.
- If that dependency has landed before implementation, this ticket should keep
  its own scope to the drain/usage work and add only drain-specific tests; the
  auto-mode streaming policy and architecture-doc update belong to the blocker.

### 4. Drain orchestration — `src/relay/drain.py` (new)
- `eligible_auto_tickets(cfg) -> list[TaskRef]`: `list_tasks(cfg)` filtered to
  active + auto + assignee in `cfg.agents` + not `is_under(ref.directory,
  "recurring")`; sorted by `first_activity()` ascending (None sorts last).
- `drain_pending_auto_tickets(cfg)`: the loop. Build one probe per agent type
  on demand (so codex is only primed if a codex ticket exists). Maintain a
  per-agent cache of `{exhausted, unreadable}`. For each eligible ticket in
  order: skip if its agent is already exhausted/unreadable; else probe (claude
  re-probed each ticket; mark exhausted when either the session guard or the
  weekly guard fails, mark unreadable when probe returns `None`); if OK,
  launch via the existing `relay launch` entrypoint (non-interactive, same call
  shape the sweep uses with `return_timeout=True`); on an unfinished/failed
  return, stop the whole drain; honor `max_tickets`. Collect drained slugs and
  the stop reason, then post the one-line summary (only if there was ≥1
  eligible ticket). Note: the recurring `mode: auto` template ban
  (`_effective_mode`) does **not** apply here — that guards scheduled
  *recurring template* launches; draining ordinary auto tickets unattended is
  the intended behavior and its visibility comes from the summary + each
  launch's own broadcasts.

### 5. Hook into the sweep — `src/relay/commands/recurring.py`
- In `main()`, for the bare sweep only (`not all_ and not interactive`), call
  `drain.drain_pending_auto_tickets(cfg)` **after** the recurring launch loop,
  and also on the "no recurring tasks due" path (restructure the early
  `return` so the drain still runs). The existing `sys.exit(1)` on an
  unfinished non-interactive recurring launch naturally skips the drain (the
  process ends), satisfying "aborted sweep skips the drain".

### 6. Config — `src/relay/config.py`
- Parse `[recurring.drain]` (new `_parse_recurring`/`_parse_drain` helper, same
  validation style as `_parse_launch`), surfaced on `Config`:
  - `drain_enabled: bool = False` — opt-in; default keeps today's behavior.
  - `drain_min_session_remaining_percent: float = 5.0` — fixed per-agent
    reserve for the 5h/session window.
  - `drain_min_weekly_remaining_percent: float = 5.0` — hard floor for the
    weekly window; the effective weekly pacing reserve never drops below this.
  - `drain_weekly_final_window_hours: float = 24.0` — within this many hours
    before weekly reset, use only the hard weekly floor; before that, linearly
    pace from near-100% reserve at the start of the weekly window down to the
    hard floor.
  - `drain_max_tickets: int = 0` — `0`/absent = unlimited.
- Example `relay.toml` block:

  ```toml
  [recurring.drain]
  enabled = true
  min_session_remaining_percent = 5.0
  min_weekly_remaining_percent = 5.0
  weekly_final_window_hours = 24.0
  max_tickets = 0
  ```

- Re-probe cadence (decision #2): claude is re-probed before every ticket
  (free GET); codex's snapshot is re-read each time but only primed once via
  the throwaway, and naturally refreshes after each codex launch.

### 7. Notifications
- One end-of-drain summary via the live notification layer
  (`relay.notification.post`, not `notify`), e.g. `drain: launched 3 pending
  auto ticket(s): a, b, c` or `drain skipped: codex session 4% remaining below
  5% reserve`. Gate on "≥1 eligible ticket existed" so quiet sweeps stay
  silent. Because this uses the live `post()` path, configured Slack failures
  fail loud per `relay/sync`; no daily-digest spool entry is created.

### 8. Tests
- `first_activity()` unit tests (present/absent/unparseable/multi-line).
- `relay status --order-by created` ordering test.
- Usage parsing tests against captured JSON fixtures (Claude usage body; codex
  rollout `rate_limits` line) — no live network/codex calls; monkeypatch the
  HTTP fetch and the codex-exec/rollout-read seams. Include a Codex stale-file
  test: a successful primer followed by no rollout modified after `started_at`
  returns `None` and skips codex drains.
- Drain selection/ordering test; drain-loop tests for: session guard fail,
  weekly guard fail early in the weekly window, weekly final-day hard floor,
  unreadable→skip-agent, stop-on-unfinished, `max_tickets`, disabled (no-op),
  aborted-sweep-skips-drain.
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

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Pre-launch decisions with Nick (2026-06-20)

Three design inputs locked before launching the design step (full text now in
ticket.md `## Context` → "Decisions locked with Nick"):

1. Budget: read remaining usage from the **server** per agent type
   (Anthropic/OpenAI), not CLI `/usage` scraping. Design must *prove the
   endpoint works* (go/no-go) and confirm it's the subscription usage window,
   not per-minute rate-limit headers. Unreadable → skip drain for that agent.
2. Threshold: a **`relay.toml` config key** (min % remaining, optional max
   cap), not hardcoded. Design names key + default + re-probe cadence.
3. Ordering: **oldest-first by first `log.md` timestamp** via a new
   `first_activity()` helper (mirror of `last_activity()`). Committed content
   → survives clone (file mtime does not). Bonus consistency add:
   `relay status --order-by created` on the same helper.

## Open Questions (for review-design / Nick)

1. **`drain_enabled` default.** Spec sets it to `false` (opt-in) so existing
   repos see no behavior change until they flip it on. The feature's whole
   point is "just drain after the sweep", which argues for `true`. Picked the
   conservative default — confirm or flip.
2. **Reserve defaults.** Spec now uses separate guards:
   `drain_min_session_remaining_percent = 5.0`,
   `drain_min_weekly_remaining_percent = 5.0`, and
   `drain_weekly_final_window_hours = 24.0`. Confirm these defaults and whether
   `drain_max_tickets` should stay `0` = unlimited.
3. **Codex throwaway cost — resolved toward support.** Priming codex costs one
   tiny `codex exec` per drain (~17k input tokens, mostly cached; 27 output)
   and only fires if a codex-assigned auto ticket exists. Current spec keeps
   codex support with the primer + rollout snapshot read; failures skip codex
   conservatively.
4. **Summary channel — resolved toward live post.** Spec posts a live
   `relay.notification.post` one-liner, not a digest `notify` record. This is
   immediate enough for unattended cron and follows `relay/sync` fail-loud
   semantics.
5. **Config location.** `[recurring.drain]` chosen (the drain is a recurring-
   sweep tail). Alternatives: top-level `[drain]` or fold into `[launch]`.

## Review-design notes (2026-06-24)

- Nick confirmed the threshold must be a `relay.toml` safety reserve: configure
  how much usage must remain before Relay is allowed to drain, and if the
  remaining budget is too low (e.g. 5%) launch nothing else for that agent.
- Nick confirmed the check is **session + weekly**. The implementation must use
  the binding window: both the 5h/session window and the weekly window have to
  clear the configured reserve floor.
- Codex remains special: there is no clean free/fresh standalone usage endpoint.
  The current spec keeps codex support via one minimal `codex exec` primer,
  then reads the fresh `rate_limits` snapshot from the newest rollout file. If
  that primer or snapshot read fails, codex drains are skipped conservatively.
- Nick reframed the intent: consume leftover Claude and Codex allotment by
  running ordinary auto tickets after recurring, sequentially and reasonably,
  until the agent's own usage windows say to stop. Relay should not estimate
  ticket cost or run work in parallel.
- Spec adjusted from one shared `min_remaining_percent` to separate guards:
  fixed 5h/session reserve (`drain_min_session_remaining_percent`, default
  5.0) plus a weekly pacing reserve with a hard floor
  (`drain_min_weekly_remaining_percent`, default 5.0).
- Nick clarified the overriding goal is **do not run out of tokens**. Recurring
  runs overnight when humans are not using the account, so the session guard
  does not need to preserve daytime interactive headroom inside the same 5h
  window.
- Nick clarified the weekly window is different: when reset is far away (e.g.
  seven days), preserve a lot of weekly budget; on the last day before reset,
  it is acceptable to spend leftover allotment more aggressively. Spec updated
  to use a linear weekly pacing reserve: near-100% required remaining at the
  start of the weekly window, linearly down to the hard weekly floor by the
  final `drain_weekly_final_window_hours` (default 24h). The weekly reserve
  never drops below the hard floor, so the drain still avoids token exhaustion.
- Nick called out that the hard floors must be explicit `relay.toml` settings.
  Spec now includes the intended `[recurring.drain]` block and a table showing
  the default weekly pacing thresholds: 100% required at 7 days, then about
  84/68/53/37/21% at 6/5/4/3/2 days, then 5% during the final 24h.

## Evaluator follow-up fixes (2026-06-24)

- Fresh `eval/ticket-diagnostic` found four gaps: current `mode: auto` launch
  block, missing `relay/sync` notification context/contract, Codex stale
  rollout risk, and validation noise from using the wrong global `relay` shim.
- Auto-mode decision: this drain ticket **does not** re-enable ordinary
  `mode: auto`. It depends on
  `auto/stream-agent-progress-in-auto-mode-and-recurring-l` (or equivalent
  removal of the launch block) landing first. If the block remains at
  implementation time, the implementer should stop and report the dependency
  rather than shipping a nonfunctional drain.
- Notification decision: attached `relay/sync`; end-of-drain summary uses
  `relay.notification.post`, not `notify`, so configured Slack failures fail
  loud and no digest spool entry is created.
- Codex freshness guard added: record `started_at` before the throwaway
  `codex exec`; accept only a rollout file modified after `started_at` and
  containing parseable `rate_limits`; stale/missing data returns `None` and
  skips codex drains.
- Validation note: `/home/n/.local/bin/relay` imports `/home/n/Code/relay`, not
  this checkout. For this task, verify with
  `PYTHONPATH=/home/n/Code/codex/relay/src python -m relay.cli ...`.

## Budget-probe go/no-go (2026-06-20, design step) — REAL probes run

Decision #1 required a real endpoint probe, not docs. Done. Results:

### Claude — GO (clean, fresh, free) ✅
- Endpoint: `GET https://api.anthropic.com/api/oauth/usage`
- Auth: `Authorization: Bearer <token>` is the ONLY required header
  (verified: token-only → HTTP 200; beta header not needed; no auth → 429).
- Token source (Linux/headless): `~/.claude/.credentials.json` →
  `.claudeAiOauth.accessToken` (also carries `.subscriptionType` = "max",
  `.expiresAt`, `.scopes`). NOTE macOS stores creds in Keychain, not this
  file — cron target is Linux so file path is the realistic one; note the
  caveat for the implementer.
- Body confirms the SUBSCRIPTION USAGE WINDOW (not per-minute rate headers):
  `five_hour.utilization` (e.g. 2.0 = percent used) + `resets_at`;
  `seven_day.utilization` (4.0) + `resets_at`; plus a structured `limits[]`
  array (`kind`: session/weekly_all/weekly_scoped, `percent`, `severity`,
  `resets_at`, `is_active`). remaining% = 100 − utilization.

### Codex — NO clean standalone GET ⚠️ (skip-or-stale)
- ChatGPT-backend GETs are Cloudflare-blocked: `chatgpt.com/backend-api/
  codex/usage|rate_limits|account|me` all → HTTP 403 (HTML bot page), with
  and without codex client headers.
- `api.openai.com/v1/me` → 200 but identity only, NO window/usage data.
- Codex auth: `~/.codex/auth.json` (auth_mode="chatgpt", `.tokens.access_token`,
  `.tokens.account_id`).
- Codex DOES expose the identical window data, but only as a `rate_limits`
  snapshot **attached to a `responses` API call**, persisted into
  `~/.codex/sessions/<Y>/<M>/<D>/rollout-*.jsonl`. Structure verified:
  `{primary:{used_percent,window_minutes:300,resets_at}, secondary:
  {used_percent,window_minutes:10080,resets_at}, plan_type:"pro"}`.
  → primary = 5h window, secondary = weekly window. Same family as Claude.
- Consequence: the only no-extra-cost codex read is the LAST persisted
  rollout snapshot — which is only as fresh as the last codex run (could be
  hours/days stale). There is no free fresh probe. Per decision #1's
  "unreadable → conservatively skip", codex's branch is either (a) read the
  newest rollout snapshot iff within a freshness bound, else skip; or
  (b) skip codex drains entirely for v1. ← surfaced to Nick as the one fork.

### Implication for the interface
One `UsageProbe` interface, one impl per agent type. Claude impl is the
live GET. Codex impl is the rollout-snapshot read (or a no-op skip). Probe
must fail SOFT (any error/timeout/unreadable → treat as "no budget signal"
→ skip that agent's drain), never crash the sweep.

### Nick's call (2026-06-20): codex = "fire one throwaway at beginning"
Chose option 3, minimized to a SINGLE priming probe. VERIFIED it works:
- `codex exec --json -s read-only --skip-git-repo-check "Reply with exactly:
  ok" </dev/null` → exit 0, replied "ok", usage 16952 input / 27 output
  tokens (cached 4992) — tiny cost against the window.
- Immediately after, newest `~/.codex/sessions/<Y>/<M>/<D>/rollout-*.jsonl`
  (13s old) carried a FRESH `rate_limits`: primary{used_percent 1.0,
  window_minutes 300}, secondary{used_percent 6.0, window_minutes 10080},
  plan_type "pro". `resets_at` = unix epoch seconds.
- GOTCHAS for implementer: (1) MUST redirect stdin `</dev/null` or codex
  blocks on "Reading additional input from stdin..."; (2) the `--json`
  experimental event stream does NOT include rate_limits — read it from the
  rollout file, not stdout; (3) read-only sandbox + --skip-git-repo-check
  keeps the throwaway safe/contained.
- Mechanism: prime codex ONCE per drain (lazily, only if codex-eligible
  tickets exist), then read newest rollout snapshot. After the first codex
  drain launch, the snapshot self-refreshes (each codex launch rewrites it),
  so per-ticket re-reads stay fresh for free.

## Bootstrap interview notes (2026-06-11)

- Origin: Nick's one-liner — after a recurring launch sweep, if auto tickets
  are pending and the session has token budget left, run them.
- Budget signal: initially leaned "let design decide", then Nick clarified
  that usage limits ARE readable — Claude Code, Codex, and other agents
  report how much of the current usage window remains. Ticket now states
  the mechanism (read per-agent usage limits) and leaves only the exact
  invocation + threshold to the design step.
- Eligibility: status active + mode auto + assignee is a configured agent
  type, oldest first.
- Drain policy: drain until budget runs out; stop on first failure /
  unfinished non-interactive launch (mirrors existing sweep behavior).
- Workflow: code/design-then-implement — chosen because the usage-reading
  mechanism per agent still needs verification before implementing.
- First draft slug started with `recurring-` (the period-task identity
  prefix) — deleted and re-drafted to avoid colliding with
  `_RECURRING_PREFIX` matching.
- Nick approved the ticket as written. The older overlapping draft
  `token-budget-aware-idle-execution-of-low-priority` (agent-side end-of-
  session idle-pick shape) was deleted as superseded by this ticket.
  `autoroute-agent-based-on-remaining-usage` is a related-but-distinct
  empty draft (which agent to route to by remaining usage) and was left
  in place.

## Evaluator review

## Ticket Review: drain-pending-auto-tickets-with-leftover-session-b

### 1. Description clarity — good, with two underspecified details

The description is strong for a cold start: clear trigger (after a bare `relay recurring` sweep), precise selection criteria (`status: active`, `mode: auto`, assignee is a configured agent type), ordering, stop condition, and where the budget signal comes from. The ## Context section correctly anchors the code (`src/relay/commands/recurring.py` run loop, `src/relay/recurring.py`) and correctly states there is no budget tracking in relay today — I verified both.

Two things an agent will have to guess:
- **"Oldest first" by what clock?** Tickets are plain directories; frontmatter has no created-date field. Git history, directory mtime, and slug ordering all give different answers. This should be pinned in the ticket or explicitly delegated to design.
- **"The sweep's existing Slack summary" doesn't quite exist.** Slack output is per-event `notify()` calls in `_broadcast_scan()` (which fires *before* launches), not an end-of-sweep summary. The drain report will need a new notification point, not an edit to an existing summary. Minor, but the agent will trip on the framing.

### 2. Workflow fit — correct choice

`code/design-then-implement` fits well. This is exactly the "thin ticket with a genuinely open design question" shape the workflow exists for: the per-agent usage-probe mechanism is unverified, and the workflow's `review-design` gate puts a human between that investigation and implementation. An `implement`-only workflow would have been a mistake here.

### 3. Context relevance — relevant set; one candidate missing

- `relay/recurring` — clearly right; explains the sweep semantics, stop-on-unfinished behavior, and the `recurring-` prefix distinction the ticket leans on.
- `relay/codebase` — justified for any ticket editing `src/relay/` (it carries test/fixture expectations).
- `dev/code` — justified; the workflow produces a branch and PR, which is exactly this context's attach condition.
- **Possibly missing: `relay/sync`.** The `relay/recurring` context explicitly says Slack posting mechanics are out of its scope and live in `relay/sync`, and this ticket has a Slack-observability requirement. `notify()` is simple enough that this is borderline, but it's the one defensible addition.

### 4. Broad contexts vs. copied facts — handled well

The ticket already copied the load-bearing facts into ## Context (where the sweep lives, no existing budget tracking, the `recurring-` prefix rule, the conservative skip-on-unreadable default). `relay/codebase` is the broadest attachment (~165 lines, including wheel-packaging gotchas irrelevant here), but it's the conventional attachment for relay-source work and carries the test/fixture rules the implement step genuinely needs. No attachment exists solely to deliver one fact. Acceptable.

### 5. Scope — one feature, but with a detachable risky core

This is one coherent feature, not an obvious bundle. However, it contains three pieces of unequal risk: (a) a per-agent usage-probe capability (new, external-facing, unverified), (b) the drain loop itself (straightforward, mirrors existing sweep logic), and (c) Slack observability (small). The usage probe is the part that could blow up; if it proves infeasible the whole ticket's shape changes. The design step absorbs this, but the ticket should explicitly permit the design step to come back with "no stable programmatic usage interface exists; here are fallbacks (time-box, N-tickets cap, skip feature)" rather than treating the probe as a settled premise.

### 6. Assumptions to question before launch

- **"Claude Code and Codex both expose how much of the current usage window remains" — stated as fact, not verified.** Both expose usage *interactively* (`/usage`, `/status`), but a stable *programmatic/headless* interface is exactly the part the ticket itself admits "needs verifying." The description asserts the capability; the context hedges it. The hedge should win: the assertion in ## Description should be softened, or the design step's first deliverable should be a go/no-go on the probe mechanism. This is the single biggest pre-launch risk.
- **"Enough budget to start a ticket" may be unknowable.** Ticket cost varies wildly; any threshold is a heuristic. Fine to delegate to design, but the owner should expect a crude answer (e.g., "drain only if >X% of window remains") and decide whether that's acceptable.
- **Re-check cadence is implicit.** "Until the budget runs out" implies re-probing between launches, but probing mid-sweep may itself be slow or rate-limited. Design detail, but worth a line.
- **Interaction with the sweep's stop conditions.** If the recurring sweep itself stopped early on an unfinished launch, does the drain still run? The description says "after a bare sweep finishes its scheduled work" — ambiguous when the sweep aborted. Should be pinned.

### Verdict

Launchable as-is given the design step exists, but I'd make three edits first: pin (or explicitly delegate) the "oldest first" ordering source, soften the usage-reporting assertion to match the context's hedge and authorize a no-go outcome from design, and consider attaching `relay/sync` for the Slack requirement.
