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

## Open for the design step
- Exact config surface for the cap (`[recurring] max_catchup = 1`?) — name +
  location, then document.
- How to enumerate missed periods for cron-style schedules via `_last_firing` /
  `_period_key` (walk back from now to last-recorded-run).
- Confirm catch-up runs reuse the sweep's sequential + idle-timeout backstop.
- Decide flag-hygiene fix for `--all`/`--interactive`/`--mode` confusion.

## Status
Draft authored interactively. Workflow: code/design-then-implement (step 1
design). Not yet activated/launched — owner to review then
`relay mark active <slug>` → `relay launch <slug>`.
