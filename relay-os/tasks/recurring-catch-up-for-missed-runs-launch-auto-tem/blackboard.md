# Blackboard — recurring catch-up + auto-as-interactive

## Decisions settled at authoring (with owner, nick)
- **Catch-up depth:** configurable cap, **default 1**. Recover missed periods
  oldest-first, bounded by the cap. Log what's dropped past the cap (fail loud).
- **Auto + no TTY:** **hard error**, exit non-zero. Do NOT skip silently.

## Key source locations
- `src/relay/commands/recurring.py` — `main()` sweep (`scan_due` → launch loop).
  Note `--all` short-circuits at L85 before reading `--interactive` (silent
  ignore — flag-hygiene nit to fix or document).
- `src/relay/recurring.py`:
  - `scan_due` (~L124) — "current period only" get-or-create. This is where
    catch-up enumeration goes.
  - `_effective_mode` — currently RAISES on `mode: auto` (the temporary ban).
    Change 2 replaces this with auto→interactive coercion + no-TTY hard error.
  - period ledger: template `blackboard.md` via `_record_run` /
    `_period_already_scaffolded` — source of truth for "did this period run".
  - `_last_firing` / `_period_key` — schedule→period math; basis for
    enumerating the missed-period set.

## Contexts/docs that must move with the code (same PR)
- `relay/architecture`, `relay/cli` — both state "current period only / does
  not chase missed periods" and the "mode:auto temporarily skipped" rule.
- README + `docs/spec.md`.
- Keep live `relay-os/` and packaged
  `src/relay/resources/templates/relay-os/` copies in sync.

## Design findings
- Config surface settled as shared `[recurring] max_catchup = 1`, parsed into
  `Config.recurring_max_catchup`. `0` should mean current-period only; invalid
  values fail config load.
- Catch-up should enumerate unique period keys by walking cron firings backward
  from the current firing to the most recent handled period. Handled means
  either an existing task slug or a `scaffolded <slug>` line in the template
  `blackboard.md` ledger. If there is no handled prior period, first scan is
  current-only because there is no durable baseline for older missed runs.
- The cap counts missed periods before the current period. With default `1`,
  last-handled W17 and current W21 should recover W20 plus current W21, warning
  that W18-W19 were dropped.
- Catch-up runs should flow through the same bare-sweep launch loop, ordering
  by `last_fire` and using the existing idle-timeout / unfinished-run stop
  behavior.
- Auto recurring templates should keep `mode: auto` on the period ticket and
  be launched with `mode_override="interactive"`. Auto without a TTY is a fatal
  recurring error, not a `DueScan.errors` skip.
- `--all --interactive` should be rejected as redundant because `--all` already
  forces non-script debug runs through interactive launches. Do not add a
  recurring-level `--mode` flag.
- Live repo has `docs/design.md`, not `docs/spec.md`. The implementation step
  should update `docs/design.md` and the old references/search hits, not invent
  a new `docs/spec.md` just to satisfy the draft wording.

## Open Questions
- None after source review. The remaining choices are implementation details
  within the ticket spec.

## Status
Owner review pass complete for step 2. The ticket spec now carries the
implementation contract, including the `docs/design.md` correction; no open
questions remain. Ready to bump to `implement`.
