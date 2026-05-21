## Dev
branch: split-control-plane-into-relay-mark
worktree: (working in primary checkout — no separate worktree)
pr: (not yet opened)

## Status

Implementation complete. All 308 tests pass (1 pre-existing, unrelated
failure on `test_status_narrow_terminal_keeps_each_task_on_one_line`
introduced by commit 160b815 — totals summary line wrapping).

## What was done

**Code:**

- `src/relay/mark.py` — new module with `mark_active`, `mark_paused`,
  `mark_done` finalizers. `mark_done` signature preserved so the
  existing `automerge.auto_bump_merged` caller keeps working.
- `src/relay/commands/mark.py` — new Typer sub-app with `active`,
  `paused`, `done` subcommands. Transition rules: active from
  {draft, paused}; paused from {active}; done from {active}.
- `src/relay/commands/create.py` — new Typer command. Scaffolds a
  `draft` ticket via `scaffold_task()` and posts `✨` to Slack. No
  agent launch.
- `src/relay/commands/launch.py` — stripped of factory mode and
  soft-warn-on-active. Errors on non-active status with a hint to
  run `relay mark active <slug>`.
- `src/relay/commands/bump.py` — no longer flips status to done past
  the final step. Errors with a hint to run `relay mark done <slug>`.
- `src/relay/cli.py` — registered `mark` sub-app and `create` command.
- `src/relay/automerge.py` — routed through the shared `mark_done`
  helper for consistency.

**Filesystem:**

- Deleted `relay-os/bootstrap/ticket/` (no longer a factory — `create`
  is its own command).
- Removed `create = "launch bootstrap/ticket"` from `[aliases]` in
  both `relay-os/relay.toml` and `example/relay-os/relay.toml`.

**Tests:**

- `tests/test_mark.py` — new. Full coverage of all three subcommands,
  transition rules, error cases, `--message`, prefix resolution.
- `tests/test_launch.py` — removed soft-warn / factory / title-arg /
  draft-flip tests; added `test_launch_rejects_draft_with_mark_active_hint`.
- `tests/test_commands.py` — replaced bump-to-done tests with
  bump-past-final-step-errors tests.
- `tests/test_smoke.py` — updated end-to-end flow to use `relay mark
  done` for the final transition.
- `tests/test_aliases.py` — updated user-alias-override test to use
  `chat` instead of `create` (since `create` is no longer an alias).
- `tests/test_create.py` — added tests for the new built-in create
  command (scaffolds draft, doesn't spawn agent, respects `--mode`,
  rejects empty title).

**Docs:**

- `README.md` — three-step boot sequence (`create` → `mark active` →
  `launch`); new `relay mark <state>` section; rewrote `launch`,
  `bump`, and Aliases sections.
- `relay-os/contexts/relay/cli/SKILL.md` — added `relay create` and
  `relay mark` sections; rewrote `launch` and `bump`; updated Aliases
  and "Pick which command" lists.
- `relay-os/contexts/relay/architecture/SKILL.md` — rewrote "Two state
  machines per ticket" (control plane owned by `relay mark`; data
  plane owned by `relay bump`); updated "Status is the signal"
  (no auto-flip from draft); updated Bootstrap shims (no longer
  factories).
- `relay-os/contexts/relay/sync/SKILL.md` — replaced factory-mode
  Slack source lines; added `relay mark` post lines.
- `relay-os/contexts/relay/current-direction/SKILL.md` — updated
  alias-mechanism, `relay bump`, and launch sections to match the
  new behavior.
- `docs/design.md` — fixed the "Status is the signal" section
  (launch no longer auto-flips drafts).

## Tradeoffs / decisions made along the way

- **No `--launch` shortcut on `relay create`.** The whole point of the
  split is "each command does one thing." Adding a shortcut that fires
  three steps from one command would just re-conflate the planes under
  a different name. Three explicit steps (`create` → `mark active` →
  `launch`) is the design.
- **`mark_done` signature preserved.** Automerge needed to keep working
  without me also rewriting it. The helper takes the same args as
  before; only the call site moved.
- **Pre-existing `test_status_narrow_terminal_keeps_each_task_on_one_line`
  failure left alone.** Caused by commit 160b815 (totals summary line),
  not by this work. Out of scope for this ticket.
- **`docs/design.md` partially updated.** The "CLI shape" section
  (lines 7-77) is a historical M1 snapshot and was already stale (those
  flags don't exist in current CLI). I only touched the "Status is the
  signal" section, which directly contradicted new behavior.
