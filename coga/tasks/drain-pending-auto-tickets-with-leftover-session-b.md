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
step: 4 (open-pr)
---

## Description

> **Rescoped 2026-07-01 (Nick, blocker resolution):** the original shape — a
> new drain bolted onto the tail of `coga recurring` — was superseded by work
> that landed after design. `src/coga/megalaunch.py` already IS the sequential
> drain of active agent-assigned tickets; what it lacked was a trustworthy
> budget signal (it summed coga's own `## Usage` token records, the model this
> ticket rejected). This ticket now folds the OAuth usage-window budget model
> INTO megalaunch instead of building a second drain path. The scheduled
> trigger/orchestration layer is owned by the sibling ticket
> `nightly-auto-drain-run-for-ready-tickets`, which imports this engine.
> The pre-rescope body text is in git history.

Coga's drain (megalaunch) launches active, agent-assigned tickets
sequentially, oldest first, until the assigned agent's own budget says stop.
The budget signal is the agent's subscription usage-window reporting (the
5h/session window plus the weekly window), read per agent type rather than
coga tracking tokens itself. Coga does not try to predict a ticket's cost.
It drains sequentially: launch one eligible ticket, re-read that agent's usage
state, then decide whether to launch the next ticket. An agent whose usage
can't be read is skipped conservatively — never launched blind.

The design step's go/no-go probe (decision #1) was **run against the real
endpoints** — results below:

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

- The drain engine lives in `src/coga/megalaunch.py` (`run_megalaunch`,
  `_launch_until_stop`), with the thin CLI entry in
  `src/coga/commands/megalaunch.py`. Before this ticket its budget guard
  (`budget_state`) summed coga's own `## Usage` token records against
  `[megalaunch]` token budgets — coga-tracked accounting, replaced here.
- Megalaunch launches every ticket as a supervised **interactive** REPL
  (`autonomy_override="interactive"` under the PTY watcher), so it does not
  hit the `autonomy: auto` launch gate in `src/coga/commands/launch.py`. That
  gate (owned by `auto/stream-agent-progress-in-auto-mode-and-recurring-l`)
  blocks only unattended auto launches — the nightly trigger's problem, not
  this engine's.
- Drained tickets are ordinary tasks under `coga/tasks/`, launched the same
  way a human `coga launch <slug>` would be; they keep their own workflows
  and bump normally. Do not confuse them with period tasks — the `recurring/`
  path is the period-task identity marker and ordinary tickets never carry it.
- The drain is observable in Slack: one live end-of-run post
  (`coga.notification.post`) naming what was launched, or that budget skipped
  everything. This is a new notification point in the megalaunch command, not
  an edit to any recurring-sweep broadcast or digest spool.
- "Oldest first" is anchored to the first `log.md` timestamp per ref (locked
  decision #3 below) — committed content, so the order survives clone/
  checkout where file mtimes collapse to "all equal".
- Ownership split with `nightly-auto-drain-run-for-ready-tickets`: this
  ticket owns the engine (probes, guards, ordering, the megalaunch loop);
  nightly owns the scheduled trigger, orchestration, and cross-agent
  reattribution, importing this engine. Neither ships a second
  usage-reading path.

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
2. **Threshold — a `coga.toml` config key.** The "enough budget to start a
   ticket" threshold is tunable config (e.g. minimum % of window remaining,
   optional max-tickets-per-drain cap), not a hardcoded constant. Design names
   the exact key(s) and default(s) and says whether usage is re-probed
   between launches.
3. **Ordering — oldest-first by creation = first `log.md` timestamp.** Add a
   `first_activity()` helper mirroring the existing `last_activity()` in
   `src/coga/logfile.py` (first parseable `YYYY-MM-DD HH:MM` line = the
   draft/create entry). This is committed content, so it survives `git clone`
   / checkout — unlike file mtime, which resets on checkout and would collapse
   to "all equal" on the cron machine. `coga status` already orders by
   `last_activity` (committed), so this stays in the same robust family.
   Consistency add: expose `coga status --order-by created` backed by the
   same `first_activity()` helper so a human can inspect the exact order the
   drain will service tickets in.

## Acceptance Criteria

- [ ] A `UsageProbe` abstraction exists (`src/coga/usage_probe.py` — the
      `usage.py` name was already taken by session token records) with one
      implementation per supported agent CLI. The Claude impl reads the live
      OAuth usage endpoint; the Codex impl primes once per drain via a
      throwaway `codex exec` then reads the newest rollout `rate_limits`
      snapshot written after the primer started. Both fail soft (return "no
      signal" on any error/timeout/missing-credential/stale file), never
      raising into the run.
- [ ] Megalaunch's budget guard is the usage-window check: `budget_state`'s
      coga-tracked token summing is **replaced** by
      `usage_probe.check_budget`. A launch is allowed only when the agent's
      5h/session window has at least `min_session_remaining_percent` remaining
      and the weekly window clears its reset-aware pacing reserve. An agent
      with no probe implementation, or whose probe returns no signal, is
      skipped conservatively (`skipped-budget`) — "unreadable" never means
      "safe to drain".
- [ ] The weekly guard is time-to-reset aware: a linear pacing curve requires
      ~100% remaining a full window before reset, relaxing to the hard
      `min_weekly_remaining_percent` floor inside the final
      `weekly_final_window_hours`. A missing weekly reset time blocks the
      launch. Care a lot about weekly budget seven days out; spend leftover
      allotment aggressively on the last day without hitting zero.
- [ ] The agent's usage is re-probed before **every** launch (the candidate
      check and the per-step loop both go through the probe), so budget spent
      by one launch counts against the next decision. Claude's re-probe is a
      free GET; codex re-reads the rollout snapshot its own launches keep
      rewriting (the throwaway primer fires once per drain).
- [ ] Tasks are serviced oldest-first by `first_activity()` — the earliest
      parseable `YYYY-MM-DD HH:MM` line per ref in the repo-global
      `coga/log.md`. Refs with no log line sort last, stable by slug.
- [ ] `first_activity()` / `first_activity_map()` helpers exist in
      `src/coga/logfile.py`, mirroring `last_activity()` (minimum timestamp
      wins, since `merge=union` can leave the log unsorted; `None`/absent when
      unparseable), with tests.
- [ ] `coga status --order-by created` sorts by the same helper (oldest first
      by default, `--reverse` flips), is listed in `--order-by` choices, and
      has tests — a human can inspect the exact order the drain services
      tickets in.
- [ ] Megalaunch eligibility is otherwise unchanged: `status: active`,
      assignee a configured agent type, non-script current step, no open
      blockers. (Narrowing to `autonomy: auto` belongs to the nightly
      trigger's selection, not this attended engine.)
- [ ] `[megalaunch]` gains `min_session_remaining_percent` (default 5.0),
      `min_weekly_remaining_percent` (default 5.0), and
      `weekly_final_window_hours` (default 24.0), parsed with validation and
      covered by tests. The replaced token keys (`token_guard`,
      `default_token_budget`, `window_hours`, `agent_token_budgets`) still
      parse as deprecated no-ops so existing configs keep loading.
- [ ] The drain is observable: `coga megalaunch` posts a single live one-line
      summary (`coga.notification.post`, not `notify`) naming launched slugs,
      or stating budget/eligibility skips — silent only when the run produced
      no results at all. Slack failures follow the live-post fail-loud
      semantics in `coga/sync`; stdout gets the summary before the post.
- [ ] This ticket does **not** touch the `autonomy: auto` launch gate in
      `src/coga/commands/launch.py` — megalaunch's supervised interactive
      launches never hit it.
- [ ] `python -m pytest` passes; `coga validate --task <slug>` is clean. New
      behavior has unit tests with network/codex calls mocked (no live calls
      in the suite; the megalaunch test fixture stubs probe construction so
      the suite can never read real credentials).

## Proposed Shape

(As implemented after the rescope; the pre-rescope recurring-sweep shape is
in git history.)

### 1. Usage probe — `src/coga/usage_probe.py` (new)
- `UsageWindow { used_percent, resets_at }` (with `remaining_percent`),
  `UsageSnapshot { agent, session, weekly }`, `BudgetDecision { allowed,
  detail, snapshot }`.
- `ClaudeUsageProbe`: bearer token from `~/.claude/.credentials.json` →
  `GET https://api.anthropic.com/api/oauth/usage` (via `requests`, already a
  coga dependency through the Slack channel); parses `five_hour` /
  `seven_day` utilization + reset times. macOS-Keychain caveat noted in code;
  any failure → `None`.
- `CodexUsageProbe`: one memoized throwaway
  `codex exec --json -s read-only --skip-git-repo-check` per drain (stdin
  from `/dev/null` — without it codex blocks), then reads the newest
  `~/.codex/sessions/**/rollout-*.jsonl` **modified after the primer
  started**; parses the last `rate_limits` object (`primary` 5h /
  `secondary` weekly; `resets_at` epoch seconds) via a depth-first key search
  since the rollout nesting is not a stable API. Stale/missing → `None`.
- `weekly_required_remaining_percent(mcfg, hours_to_reset)`: the linear
  pacing curve — 100% required a full window (168h) out, hard floor inside
  `weekly_final_window_hours`; defaults give ~84/68/53/37/21% at 6/5/4/3/2
  days and 5% in the final 24h.
- `budget_allows_launch(snapshot, mcfg, now)`: session floor + weekly pacing;
  missing weekly reset time blocks.
- `build_probes(cfg)`: agent name → probe, dispatched on the agent's `cli`
  basename (`claude`/`codex`); unknown CLIs get no probe.
- `check_budget(probes, agent, mcfg)`: no probe / no signal → not allowed,
  with a human-readable `detail`.

### 2. Megalaunch fold-in — `src/coga/megalaunch.py`
- `run_megalaunch(cfg, ..., probes=None)` builds probes once per run
  (injectable for tests) and iterates `_tasks_oldest_first(cfg)`.
- `budget_state`/`BudgetState` and the `usage.load_records` plumbing are
  deleted; `_candidate_result` and `_launch_until_stop` call
  `usage_probe.check_budget` — the per-step loop re-probes before every
  launch. `skipped-budget` results carry the decision detail.
- `commands/megalaunch.py` posts the end-of-run one-liner via
  `notification.post` after echoing the summary to stdout.

### 3. Ordering — `src/coga/logfile.py` + `coga status`
- `first_activity_map(cfg)` / `first_activity(cfg, ref)`: earliest parseable
  log timestamp per ref (minimum wins — `merge=union` can leave the log
  unsorted).
- `status.py`: `"created"` in `ORDER_BY_CHOICES`, `created_ts` row value,
  oldest-first by default with the same two-pass None-handling as `updated`.

### 4. Config — `src/coga/config.py`
- `[megalaunch]` keys `min_session_remaining_percent = 5.0`,
  `min_weekly_remaining_percent = 5.0`, `weekly_final_window_hours = 24.0`
  (percent keys validated 0–100, hours positive). The old token keys remain
  parsed as deprecated no-ops so live configs keep loading; a follow-up
  removes them once `coga.toml` is hand-cleaned (agents don't edit it).

### 5. Tests
- `tests/test_usage_probe.py`: Claude parse + fail-soft, Codex prime/fresh/
  stale/missing-CLI/prime-once, pacing-curve values, guard decisions,
  registry dispatch. No live network or codex calls.
- `tests/test_megalaunch.py`: probe-based guard skips (low session, no probe,
  unreadable), re-probe between launches, oldest-first servicing; the `repo`
  fixture stubs `build_probes` so no test can touch real credentials.
- `tests/test_logfile.py` (new), `tests/test_status.py` (order-by created),
  `tests/test_config.py` (new keys + deprecated keys still load).

## Out of Scope

- Any priority/ordering beyond oldest-first by `first_activity()`.
- The scheduled/unattended drain trigger, `autonomy: auto` selection, and
  cross-agent reattribution — owned by
  `nightly-auto-drain-run-for-ready-tickets`, which imports this engine.
- Re-enabling `autonomy: auto` launches / streaming auto output — owned by
  `auto/stream-agent-progress-in-auto-mode-and-recurring-l`; megalaunch's
  supervised interactive launches don't need it.
- A fresh standalone Codex usage endpoint — none exists; the throwaway+rollout
  read is the deliberate mechanism. Likewise no Anthropic Admin/cost API.
- Reading Claude credentials from the macOS Keychain (Linux file path only;
  absence fails soft → skip).
- Cross-window or dollar-based budgeting, historical usage tracking, or any
  persisted budget state in coga (the probe is read-only and stateless).
- Concurrency / parallel draining — the drain stays sequential.
- Changing the recurring sweep's own launch/stop semantics.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev
branch: megalaunch-usage-probe
worktree: /home/n/Code/claude/coga-megalaunch-usage-probe

## Rescope implementation plan (2026-07-01, claude, implement)

Resumed after Nick's rescope answer (see resolved blocker): fold the OAuth
usage-window budget model INTO `src/coga/megalaunch.py`, dedup with
nightly-auto-drain (that ticket already recorded the split: THIS ticket = the
engine — probes + guards + selection; nightly = trigger/orchestration/
reattribution — consistent with the rescope).

Key finding: megalaunch launches every ticket with
`autonomy_override="interactive"` under a PTY, so it never hits the
autonomy=auto gate at `launch.py:278-290`. The rescoped scope (probe folded
into megalaunch) is therefore shippable NOW; the gate only blocks the
unattended path, which nightly-auto-drain owns.

Nick was AFK when asked, so three forks were taken with the recommended
option, recorded here as PROVISIONAL — override at review:

1. **Replace, not augment.** The OAuth usage-window guard replaces
   `budget_state()`'s UsageRecord summing. The old `[megalaunch]` token keys
   (`token_guard`, `default_token_budget`, `window_hours`,
   `agent_token_budgets`) stay *parsed but unused* (deprecated) because the
   live `coga/coga.toml` sets `default_token_budget` and agents must not edit
   coga.toml; follow-up: a human removes the key, then the config fields can
   be dropped.
2. **Eligibility unchanged.** Megalaunch keeps draining all active
   agent-assigned tickets (any autonomy) as supervised interactive REPLs;
   only the budget guard changes. The autonomy filter stays available to the
   nightly path via its own selection.
3. **End-of-run live Slack post added** (`coga.notification.post` one-liner
   from the megalaunch command; fail-loud per coga/sync). Nothing posted when
   there were no results at all.

Plan of record:
- New `src/coga/usage_probe.py`: `UsageWindow`/`UsageSnapshot` dataclasses;
  `ClaudeUsageProbe` (GET api.anthropic.com/api/oauth/usage, bearer from
  `~/.claude/.credentials.json`); `CodexUsageProbe` (lazy one-shot
  `codex exec` primer + freshness-guarded newest-rollout `rate_limits` read);
  `budget_allows_launch()` with session reserve floor + linear weekly pacing
  (100% at window start → floor inside the final window). All probe failures
  soft → None → skip that agent.
- New `[megalaunch]` keys: `min_session_remaining_percent = 5.0`,
  `min_weekly_remaining_percent = 5.0`, `weekly_final_window_hours = 24.0`.
- Megalaunch: probes built once per run (injectable for tests), re-checked
  before every launch; agents whose cli has no probe impl or whose probe
  returns no signal → `skipped-budget` (conservative).
- Ordering: `first_activity_map()`/`first_activity()` in `logfile.py` (first
  parseable log line per ref); megalaunch services oldest-first;
  `coga status --order-by created` added on the same helper.
- Ticket body rewrite: `mode:` → `autonomy:` drift + criteria re-anchored to
  the megalaunch fold-in.

## Implement step done (2026-07-01, claude)

Committed on `megalaunch-usage-probe` (fd94c953), worktree
`/home/n/Code/claude/coga-megalaunch-usage-probe`, clean tree, no push/PR yet.

What shipped (details in ticket body `## Proposed Shape`, rewritten to match):

- `src/coga/usage_probe.py` — UsageProbe/ClaudeUsageProbe/CodexUsageProbe,
  `weekly_required_remaining_percent` pacing curve, `budget_allows_launch`,
  `build_probes` (cli-dispatched), `check_budget`. All failures soft.
- `src/coga/megalaunch.py` — `budget_state`/`BudgetState`/UsageRecord summing
  deleted; probe-based guard in both `_candidate_result` and the per-step
  launch loop (re-probe before every launch); `_tasks_oldest_first` via new
  `logfile.first_activity_map`.
- `src/coga/config.py` — `[megalaunch]` gains the three reserve keys; old
  token keys parse as deprecated no-ops (live coga.toml sets
  `default_token_budget`; agents must not edit it — human follow-up to remove,
  then drop the fields).
- `coga status --order-by created`; `commands/megalaunch.py` posts a live
  end-of-run one-liner (post, not notify).
- Tests: new test_usage_probe.py + test_logfile.py; test_megalaunch/status/
  config updated. Full suite: 1013 passed, 1 skipped (known hatchling skip).
- Ticket body rewritten: mode:→autonomy: drift fixed, criteria/shape
  re-anchored to the megalaunch fold-in (pre-rescope text in git history).

Verification beyond the suite:
- Live ClaudeUsageProbe run (free GET): session 87.0% / weekly 95.0%
  remaining, guard allowed=True — real endpoint + parse + pacing verified.
- `coga status --order-by created` smoke-run against this repo; ordering
  renders. `coga validate --task <slug>` clean.

For review (provisional decisions Nick can override, from the rescope plan
above): replace-not-augment the token guard; megalaunch eligibility unchanged
(autonomy filter left to nightly); live Slack post on megalaunch runs.

## Design-drift audit + block (2026-07-01, claude, interactive)

Nick reopened this via `coga ticket` while it sat `in_progress` on `implement`.
Two actions taken: (1) renamed relay→coga throughout ticket.md (it was authored
against the old **relay** fork — every `src/relay/`, `relay.toml`, `relay …`
path was wrong for this repo); (2) blocked for rescope. The frozen design is
stale in three material ways and should NOT be implemented as written:

- **`mode:` → `autonomy:` (semantic).** Current coga has no `mode` field; it is
  `ticket.autonomy`. The 13 `mode: auto`/`mode: interactive` references in the
  acceptance criteria + proposed shape were intentionally left un-renamed (a
  find-replace would hide the drift) — the eligibility predicate targets a
  field that no longer exists and must be rewritten against `autonomy`.
- **Hard precondition still unmet.** `src/coga/commands/launch.py:285` still
  refuses auto launches: "Cannot launch: autonomy=auto is temporarily
  disabled." The ticket's own criteria say implementation must stop if this
  block is present. It is.
- **Overlap with work that landed after design.**
  - `src/coga/megalaunch.py` already IS a drain (`run_megalaunch`,
    `_launch_until_stop`, `budget_state`, `autonomy_override="auto"`, run
    summaries) — but gates on coga-tracks-tokens-itself
    (`agent_token_budgets`/`token_guard`/`UsageRecord` sums), the approach THIS
    ticket explicitly rejected in favor of an OAuth usage-window probe.
  - `src/coga/usage.py` already exists but is session token-record accounting,
    NOT the OAuth `five_hour/seven_day` probe this ticket's `usage.py` proposed
    — name collision, different thing.
  - `nightly-auto-drain-run-for-ready-tickets` (separate `in_progress` ticket,
    at review-design) covers "make spare overnight budget useful" — likely the
    same feature under another name. Also `mode-autonomy-split/`,
    `awaken-recurring-auto-blocked-tasks`, `wire-autonomy-triage-into-...`.

Rescope decision needed before implement: reconcile with megalaunch (adopt the
OAuth-probe budget model into it vs. a second drain path), dedup vs.
nightly-auto-drain, and confirm the autonomy=auto gate lands first.

## Pre-launch decisions with Nick (2026-06-20)

Three design inputs locked before launching the design step (full text now in
ticket.md `## Context` → "Decisions locked with Nick"):

1. Budget: read remaining usage from the **server** per agent type
   (Anthropic/OpenAI), not CLI `/usage` scraping. Design must *prove the
   endpoint works* (go/no-go) and confirm it's the subscription usage window,
   not per-minute rate-limit headers. Unreadable → skip drain for that agent.
2. Threshold: a **`coga.toml` config key** (min % remaining, optional max
   cap), not hardcoded. Design names key + default + re-probe cadence.
3. Ordering: **oldest-first by first `log.md` timestamp** via a new
   `first_activity()` helper (mirror of `last_activity()`). Committed content
   → survives clone (file mtime does not). Bonus consistency add:
   `coga status --order-by created` on the same helper.

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
   `coga.notification.post` one-liner, not a digest `notify` record. This is
   immediate enough for unattended cron and follows `coga/sync` fail-loud
   semantics.
5. **Config location.** `[recurring.drain]` chosen (the drain is a recurring-
   sweep tail). Alternatives: top-level `[drain]` or fold into `[launch]`.

## Review-design notes (2026-06-24)

- Nick confirmed the threshold must be a `coga.toml` safety reserve: configure
  how much usage must remain before Coga is allowed to drain, and if the
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
  until the agent's own usage windows say to stop. Coga should not estimate
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
- Nick called out that the hard floors must be explicit `coga.toml` settings.
  Spec now includes the intended `[recurring.drain]` block and a table showing
  the default weekly pacing thresholds: 100% required at 7 days, then about
  84/68/53/37/21% at 6/5/4/3/2 days, then 5% during the final 24h.

## Evaluator follow-up fixes (2026-06-24)

- Fresh `eval/ticket-diagnostic` found four gaps: current `mode: auto` launch
  block, missing `coga/sync` notification context/contract, Codex stale
  rollout risk, and validation noise from using the wrong global `coga` shim.
- Auto-mode decision: this drain ticket **does not** re-enable ordinary
  `mode: auto`. It depends on
  `auto/stream-agent-progress-in-auto-mode-and-recurring-l` (or equivalent
  removal of the launch block) landing first. If the block remains at
  implementation time, the implementer should stop and report the dependency
  rather than shipping a nonfunctional drain.
- Notification decision: attached `coga/sync`; end-of-drain summary uses
  `coga.notification.post`, not `notify`, so configured Slack failures fail
  loud and no digest spool entry is created.
- Codex freshness guard added: record `started_at` before the throwaway
  `codex exec`; accept only a rollout file modified after `started_at` and
  containing parseable `rate_limits`; stale/missing data returns `None` and
  skips codex drains.
- Validation note: `/home/n/.local/bin/coga` imports `/home/n/Code/claude/coga`, not
  this checkout. For this task, verify with
  `PYTHONPATH=/home/n/Code/claude/coga/src python -m coga.cli ...`.

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

The description is strong for a cold start: clear trigger (after a bare `coga recurring` sweep), precise selection criteria (`status: active`, `mode: auto`, assignee is a configured agent type), ordering, stop condition, and where the budget signal comes from. The ## Context section correctly anchors the code (`src/coga/commands/recurring.py` run loop, `src/coga/recurring.py`) and correctly states there is no budget tracking in coga today — I verified both.

Two things an agent will have to guess:
- **"Oldest first" by what clock?** Tickets are plain directories; frontmatter has no created-date field. Git history, directory mtime, and slug ordering all give different answers. This should be pinned in the ticket or explicitly delegated to design.
- **"The sweep's existing Slack summary" doesn't quite exist.** Slack output is per-event `notify()` calls in `_broadcast_scan()` (which fires *before* launches), not an end-of-sweep summary. The drain report will need a new notification point, not an edit to an existing summary. Minor, but the agent will trip on the framing.

### 2. Workflow fit — correct choice

`code/design-then-implement` fits well. This is exactly the "thin ticket with a genuinely open design question" shape the workflow exists for: the per-agent usage-probe mechanism is unverified, and the workflow's `review-design` gate puts a human between that investigation and implementation. An `implement`-only workflow would have been a mistake here.

### 3. Context relevance — relevant set; one candidate missing

- `coga/recurring` — clearly right; explains the sweep semantics, stop-on-unfinished behavior, and the `recurring-` prefix distinction the ticket leans on.
- `coga/codebase` — justified for any ticket editing `src/coga/` (it carries test/fixture expectations).
- `dev/code` — justified; the workflow produces a branch and PR, which is exactly this context's attach condition.
- **Possibly missing: `coga/sync`.** The `coga/recurring` context explicitly says Slack posting mechanics are out of its scope and live in `coga/sync`, and this ticket has a Slack-observability requirement. `notify()` is simple enough that this is borderline, but it's the one defensible addition.

### 4. Broad contexts vs. copied facts — handled well

The ticket already copied the load-bearing facts into ## Context (where the sweep lives, no existing budget tracking, the `recurring-` prefix rule, the conservative skip-on-unreadable default). `coga/codebase` is the broadest attachment (~165 lines, including wheel-packaging gotchas irrelevant here), but it's the conventional attachment for coga-source work and carries the test/fixture rules the implement step genuinely needs. No attachment exists solely to deliver one fact. Acceptable.

### 5. Scope — one feature, but with a detachable risky core

This is one coherent feature, not an obvious bundle. However, it contains three pieces of unequal risk: (a) a per-agent usage-probe capability (new, external-facing, unverified), (b) the drain loop itself (straightforward, mirrors existing sweep logic), and (c) Slack observability (small). The usage probe is the part that could blow up; if it proves infeasible the whole ticket's shape changes. The design step absorbs this, but the ticket should explicitly permit the design step to come back with "no stable programmatic usage interface exists; here are fallbacks (time-box, N-tickets cap, skip feature)" rather than treating the probe as a settled premise.

### 6. Assumptions to question before launch

- **"Claude Code and Codex both expose how much of the current usage window remains" — stated as fact, not verified.** Both expose usage *interactively* (`/usage`, `/status`), but a stable *programmatic/headless* interface is exactly the part the ticket itself admits "needs verifying." The description asserts the capability; the context hedges it. The hedge should win: the assertion in ## Description should be softened, or the design step's first deliverable should be a go/no-go on the probe mechanism. This is the single biggest pre-launch risk.
- **"Enough budget to start a ticket" may be unknowable.** Ticket cost varies wildly; any threshold is a heuristic. Fine to delegate to design, but the owner should expect a crude answer (e.g., "drain only if >X% of window remains") and decide whether that's acceptable.
- **Re-check cadence is implicit.** "Until the budget runs out" implies re-probing between launches, but probing mid-sweep may itself be slow or rate-limited. Design detail, but worth a line.
- **Interaction with the sweep's stop conditions.** If the recurring sweep itself stopped early on an unfinished launch, does the drain still run? The description says "after a bare sweep finishes its scheduled work" — ambiguous when the sweep aborted. Should be pinned.

### Verdict

Launchable as-is given the design step exists, but I'd make three edits first: pin (or explicitly delegate) the "oldest first" ordering source, soften the usage-reporting assertion to match the context's hedge and authorize a no-go outcome from design, and consider attaching `coga/sync` for the Slack requirement.

---

## Blockers

- [x] [2026-07-01 10:16] [agent:claude] id=20260701T101651 Design stale, needs rescope before implement. (1) Overlaps existing src/coga/megalaunch.py drain (run_megalaunch/budget_state) which uses coga-token-tracking, the model this ticket rejected for an OAuth usage-window probe — reconcile into one drain path or justify two. (2) Likely duplicates in_progress ticket nightly-auto-drain-run-for-ready-tickets. (3) Precondition unmet: autonomy=auto still disabled at launch.py:285. (4) mode->autonomy semantic drift throughout criteria. Decide reconcile/dedup path before implement resumes.
  resolved: [2026-07-01 13:06] [human:nicktoper] Rescope (Nick, 2026-07-01): fold this ticket's OAuth usage-window budget model (Claude GET /api/oauth/usage five_hour/seven_day; Codex prime-once + rollout rate_limits snapshot) INTO the existing src/coga/megalaunch.py drain rather than building a second drain path. megalaunch already does sequential active-ticket draining but gates on coga-tracked tokens (agent_token_budgets/token_guard/UsageRecord); replace/augment that guard with the OAuth usage-window probe (per-agent UsageProbe, fail-soft). Dedup vs nightly-auto-drain-run-for-ready-tickets: reconcile into this one path. Hard precondition unchanged: the autonomy=auto launch gate (launch.py:285) must land first before drain can actually launch. Also fix mode->autonomy semantic drift throughout the ticket during re-scope. The 'test' junk blocker is cleared as noise.

- [x] [2026-07-01 10:17] [agent:claude] id=20260701T101757 test
  resolved: [2026-07-01 13:06] [human:nicktoper] Rescope (Nick, 2026-07-01): fold this ticket's OAuth usage-window budget model (Claude GET /api/oauth/usage five_hour/seven_day; Codex prime-once + rollout rate_limits snapshot) INTO the existing src/coga/megalaunch.py drain rather than building a second drain path. megalaunch already does sequential active-ticket draining but gates on coga-tracked tokens (agent_token_budgets/token_guard/UsageRecord); replace/augment that guard with the OAuth usage-window probe (per-agent UsageProbe, fail-soft). Dedup vs nightly-auto-drain-run-for-ready-tickets: reconcile into this one path. Hard precondition unchanged: the autonomy=auto launch gate (launch.py:285) must land first before drain can actually launch. Also fix mode->autonomy semantic drift throughout the ticket during re-scope. The 'test' junk blocker is cleared as noise.

## Usage

{"agent":"claude","cache_creation_input_tokens":605217,"cache_read_input_tokens":20984265,"cli":"claude","input_tokens":26960,"model":"claude-fable-5","output_tokens":209411,"provider":"anthropic","schema":1,"session_id":"d4f2fb1e-47e5-426a-a0d5-1d494463d366","slug":"drain-pending-auto-tickets-with-leftover-session-b","step":"implement","title":"Drain pending auto tickets with leftover session budget after recurring sweep","ts":"2026-07-02T04:40:36.778749Z","usage_status":"ok"}
