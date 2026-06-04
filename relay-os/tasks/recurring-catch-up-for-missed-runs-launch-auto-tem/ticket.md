---
title: 'recurring: catch-up for missed runs + launch auto templates interactively'
status: done
mode: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts:
- relay/architecture
- relay/cli
- relay/codebase
skills: []
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
  - name: open-pr
    skills:
    - code/open-pr
  - name: review
    skills: []
    assignee: owner
---

## Description

`relay recurring` currently materializes only the latest scheduled firing for
each recurring template. If nobody ran the sweep for several periods, the
older missed periods are silently abandoned. That was an intentional
"current-period only" rule, but it makes local/cron outages too easy to miss.

Change the bare recurring sweep to recover a bounded catch-up backlog. The cap
is repo config under `[recurring] max_catchup = 1`; it counts missed periods
before the current period, so the default behavior for a weekly template last
run in week 17 and scanned in week 21 is to launch week 20, then week 21, and
warn that weeks 18-19 were dropped. Existing repos that do not declare the key
use the default. A first-ever scan with no recorded prior period still creates
only the current period, because Relay has no durable fact proving older
periods were actually missed rather than predating the template.

Also change recurring's `mode: auto` handling. Auto templates should no longer
be skipped during recurring scans. Period tickets keep `mode: auto` on disk,
but `relay recurring` and `relay recurring launch <name>` launch them with the
same ephemeral `mode_override="interactive"` path used by `relay launch --mode
interactive`. If an auto template would need that interactive override and
stdin/stdout are not both terminals, fail hard with a clear non-zero error
before silently skipping it. The global `relay launch` auto ban remains in
place until streaming exists; recurring is explicitly routing auto templates
through interactive launches.

Fix the small CLI flag hygiene issue while touching this path: `relay
recurring --all --interactive` should be rejected as redundant instead of
silently ignoring `--interactive`. Do not add a `--mode` flag to `relay
recurring`; Typer's current unknown-option error is already loud enough.

## Acceptance Criteria

- `load_config()` exposes `cfg.recurring_max_catchup`, parsed from
  `[recurring].max_catchup`, defaulting to `1`, accepting `0`, and rejecting
  booleans, negative integers, and non-integers with `ConfigError`.
- Bare `relay recurring` enumerates missed unique period keys between the most
  recent handled period and the current period, scaffolds at most
  `max_catchup` missed periods plus the current period, launches selected runs
  oldest-first, and warns on stderr plus Slack when older missed periods were
  dropped by the cap.
- Catch-up is idempotent: a period with an existing task directory or a
  `scaffolded <slug>` line in the template `blackboard.md` is handled and is
  not re-scaffolded, including after a completed period task has been deleted.
- Catch-up launches reuse the existing sequential sweep and idle-timeout
  backstop. If a non-`--interactive` catch-up or current run returns
  unfinished, the existing stop-before-next-task behavior still applies.
- `mode: auto` and missing-`mode` recurring templates scaffold period tickets
  as `mode: auto` but recurring launches them with
  `mode_override="interactive"` under a TTY. The ticket file is not rewritten
  to `interactive`.
- A launchable auto recurring template with no stdin/stdout TTY exits non-zero
  with a clear error and does not silently enter `DueScan.errors` as a skipped
  template. Avoid creating a new missing auto period task solely to fail after
  the write.
- `relay recurring --all --interactive` exits non-zero with a clear redundant
  flag message. `relay recurring --all` keeps launching non-script debug runs
  interactively, with script templates still run as scripts.
- Documentation and contexts are updated in the same PR: README,
  `docs/design.md` (there is no `docs/spec.md` in this checkout),
  `relay-os/bootstrap/contexts/relay/{architecture,cli}/SKILL.md`, the matching
  packaged copies under
  `src/relay/resources/templates/relay-os/bootstrap/contexts/relay/`,
  `relay-os/contexts/relay/recurring/SKILL.md`,
  `relay-os/contexts/relay/current-direction/SKILL.md`, and any recurring
  templates/comments found by searching for the old "current period only" or
  "`mode: auto` temporarily skipped" language.
- Tests under `tests/` cover config parsing, catch-up enumeration and cap
  warnings, idempotent re-runs, no-prior-ledger first runs, auto-to-interactive
  launch override, auto no-TTY hard failure, and the `--all --interactive`
  rejection.

## Proposed Shape

1. Add config support in `src/relay/config.py`.
   - Add `recurring_max_catchup: int = 1` to `Config`.
   - Add a small `_parse_recurring(shared.get("recurring")) -> int` helper.
   - Keep the key in shared `relay.toml`, not `relay.local.toml`; this is repo
     behavior, not a machine secret. Existing repos inherit the default without
     a migration.
   - Document the optional `[recurring] max_catchup = 1` block in
     `src/relay/resources/templates/relay-os/relay.toml` and the live
     `relay-os/relay.toml` if the implement branch intentionally updates the
     repo's own config comments.

2. Refactor `src/relay/recurring.py` so scaffolding can target an explicit
   scheduled firing.
   - Introduce a small candidate representation, e.g. `PeriodCandidate` with
     `fire_time`, `period_key`, and `target_slug`.
   - Add helpers that parse handled period keys from the template
     `blackboard.md` ledger and from existing task slugs. The blackboard
     remains the durable ledger; existing task dirs count too.
   - Enumerate unique period keys by walking cron firings backward from
     `_last_firing(schedule, now)` and computing `_period_key(schedule,
     fire_time)`. Stop when a handled key is found. If no handled key exists,
     treat the template as first-run and do not infer older missed periods.
   - Split the result into `current` and `missed_before_current`. Drop older
     missed periods beyond `cfg.recurring_max_catchup`, keep the newest capped
     missed periods, then return/create candidates sorted by `fire_time`.
   - Avoid making `now` mean both "scan time" and "target firing." Add an
     explicit-fire helper such as `scaffold_template_for_fire(...)`, then leave
     `scaffold_template(cfg, template, now, ...)` as the current-period wrapper
     for `relay recurring launch <name>` and existing call sites.
   - Extend `DueScan` with warnings (separate from hard template errors) so
     cap drops can be printed and sent to Slack without pretending the template
     failed to scan.

3. Replace recurring auto-mode skipping with launch-time coercion.
   - Change `_effective_mode()` so `mode: auto` returns `"auto"` instead of
     raising when a TTY is available. Keep explicit `mode: interactive` without
     a TTY as the existing per-template scan skip unless the implementer finds
     a narrower change is required.
   - Add a fatal path for launchable auto templates without a TTY. This can be
     a distinct exception that `scan_due`/`scan_debug` do not fold into
     `DueScan.errors`, or a command-level preflight before any new auto period
     task is written. The important behavior is non-zero, clear, and not a
     silent skip.
   - In `src/relay/commands/recurring.py`, compute the per-task launch override:
     `interactive` flag forces `"interactive"`; otherwise a ticket whose
     on-disk mode is `"auto"` also gets `"interactive"`; script tasks get no
     override.
   - Apply the same helper in `_launch_scaffolded()` so
     `relay recurring launch <name>` auto templates also run interactively.
   - Preserve the existing unfinished-run gate: coerced auto templates in a
     bare sweep should still stop the sweep if they return unfinished; only
     `--interactive` is the human-driven "continue anyway" path.

4. Update CLI reporting.
   - `_print_table()` can keep using the existing `ready` / `overdue Nd`
     labels; catch-up periods will naturally show older `last_fire` values.
   - `_broadcast_scan()` should still post one scaffold notification per
     created task. Add a warning summary for dropped catch-up periods, including
     the template name, dropped count, and oldest/newest dropped period keys.
   - Reject `--all --interactive` before the `--all` short-circuit with a
     Typer error or `sys.exit(2)` message explaining that `--all` already
     launches non-script templates interactively.

5. Update tests.
   - Extend `tests/test_config.py` for the recurring cap default, explicit
     value, zero, and invalid values.
   - Extend `tests/test_recurring.py` with weekly catch-up fixtures: last
     handled week 17, scan in week 21, default cap creates weeks 20 and 21 and
     warns about 18-19; cap 0 creates only week 21 and warns; a higher cap
     creates every missing week; a second scan creates nothing new.
   - Keep the deleted-period ledger regression and add a catch-up variant so a
     deleted handled period remains handled.
   - Replace the auto-skip tests with auto-coercion tests that assert the
     scaffolded ticket remains `mode: auto`, `relay.commands.launch.launch`
     receives `mode_override="interactive"`, and no-TTY auto exits non-zero
     without creating the missing task.
   - Add CLI coverage for `relay recurring launch <name>` with an auto
     template and for `relay recurring --all --interactive`.

## Out of Scope

- Implementing streamed `mode: auto` agent launches or lifting the global
  `relay launch` auto ban.
- Installing cron/systemd timers or changing `relay-os/scripts/cron.sh`
  beyond documentation if needed.
- Unbounded historical backfills, manual date ranges, or a command to recover
  deliberately dropped periods.
- Changing the existing status model for recurring period tasks, including the
  rule that prior stuck runs stay visible in `relay status` rather than
  blocking new scaffolds.
- Adding a `relay recurring --mode` flag.
