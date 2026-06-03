The blackboard is a notepad to be written to often as the human and agent works through a task.

## Findings (implement step)

Current behavior in `src/relay/compose.py`:
- **Missing context** (loop ~190-199): `resolve_context_path` returns `None` → the
  loop silently skips it, no layer appended. This is the silent-drop the ticket
  flags.
- **Missing skill** (`_skill_layers` ~279-296, `_step_layers` ~309-327): not silent,
  but not fail-loud either — injects a `*Skill file not found. Checked: …*`
  placeholder layer and launches anyway.

`src/relay/validate.py` **already** catches all three statically (`broken-context`,
plus `broken-skill` for ticket-level and step skills, lines ~536-577). So acceptance
criterion 3 ("validate already catches the same condition statically") is already
satisfied — no validate change needed.

Stale ticket pointers: `docs/spec.md` and `docs/spec-audit.md` do **not** exist in
the repo (only `docs/vision.md`, `docs/design.md`, `docs/market-thesis.md`). The
behavioral contract is still clear from the vision + the existing validate checks, so
I'm proceeding without them.

## Plan / decisions

- Add `ComposeError(RuntimeError)` to `compose.py`.
- Context loop: raise when `resolve_context_path` is `None`, naming ref + ticket
  slug + the exact checked paths (`context_resolution_paths`).
- `_skill_layers` and `_step_layers`: raise instead of the placeholder layer, same
  message shape (using `skill_resolution_paths`). **Decision:** rip out the
  placeholder fallbacks rather than keep them — they're the soft-fail the ticket
  wants gone (fail-loud principle).
- Out of scope: the *workflow-definition*-missing placeholder (`_step_layers`
  ~334-360) — that's a frozen-snapshot fallback, not a context/skill, and not what
  this ticket targets. Leaving it.
- `launch.py`: wrap both compose call sites (`compose_prompt_report` ~123,
  `compose_prompt` ~349) with `except ComposeError → _bail(...)` so launch refuses
  to start with a clean red error, no traceback.
- Tests: cover missing-context and missing-skill (ticket-level + step) raising at
  compose, and launch bailing.

## What changed (done)

`src/relay/compose.py`:
- New `ComposeError(RuntimeError)`, exported in `__all__`.
- Context loop now raises `ComposeError` (was: silently skip) when
  `resolve_context_path` is `None`, naming task slug + ref + checked paths +
  the fix.
- `_skill_layers` / `_step_layers` raise `ComposeError` (was: `*Skill file not
  found*` placeholder layer) when a skill is unresolved. Both now take `slug=`
  for the message. New `_missing_skill_message` / `_checked_context_paths`
  helpers.

`src/relay/commands/launch.py`:
- Pre-flight `compose_prompt(...)` BEFORE `mark_in_progress`, catching
  `ComposeError → _bail`. This is the key behavioral guarantee: a missing ref
  refuses to start *without* flipping the ticket to `in_progress` or posting a
  "▶️ started" Slack broadcast for a task that never runs.
- Also wrapped the `--prompt-report` compose and the in-loop per-step compose
  (defends chained steps that reference a later missing skill).

Tests (`tests/test_compose.py`, `tests/test_launch.py`):
- compose raises on missing context / missing ticket-level skill / missing
  step skill — each asserts ref, slug, and exact `…/SKILL.md` path in message.
- launch bails exit-code 2 on a missing context, agent never spawned, ticket
  stays `active`.

## Verification

- `pytest tests/test_compose.py tests/test_launch*.py` → 67 passed.
- Full suite → 517 passed, 1 deselected.
- Deselected `test_packaging.py::test_wheel_includes_bootstrap_batteries` —
  fails identically on clean `main` (pip wheel build error in this venv,
  `tool.hatch.build` force-include). **Pre-existing, unrelated to this change.**
- Ran via the venv backing the `relay` shim
  (`/home/n/Code/relay/relay-os/.relay/.venv`) with `PYTHONPATH=<worktree>/src`,
  since that venv's editable install points at a different checkout.

## Notes / scope decisions

- Acceptance criterion 3 ("validate already catches this statically") was
  ALREADY satisfied — `validate.py` has `broken-context` / `broken-skill`
  checks for ticket contexts, ticket skills, and step skills. No validate
  change made.
- Stale ticket pointers: `docs/spec.md` and `docs/spec-audit.md` don't exist
  in the repo. Did not chase them; contract is clear from vision + validate.
- Left the *workflow-definition*-missing placeholder in `_step_layers`
  untouched — it's a frozen-snapshot fallback, not a context/skill, out of
  scope for this ticket.

## Dev

branch: fail-loud-compose
worktree: ../relay-fail-loud-compose
pr: https://github.com/FastJVM/relay/pull/269

## Peer review (codex)

Ran `codex review --base main` from `../relay-fail-loud-compose`.

Finding:
- **P2 must-fix:** `relay ticket <slug>` also composes prompts for guided
  authoring. With the new strict `ComposeError`, an editable task whose context
  ref was deleted exited with an uncaught exception before the authoring command
  could render a normal CLI error.

Fix applied:
- `src/relay/commands/ticket.py` catches `ComposeError` around
  `compose_prompt(...)` and routes it through `_bail(...)`, matching the clean
  launch error path.
- Added `tests/test_ticket.py::test_ticket_reports_compose_error_for_broken_editable_task`
  to assert exit code 2, the broken context/slug/path in output, and no agent
  spawn.
- Commit: `b87a486` (`peer-review: handle compose errors in ticket authoring`).

Verification after fix:
- `PYTHONPATH=src python -m pytest tests/test_ticket.py` → 7 passed.
- `PYTHONPATH=src python -m pytest tests/test_compose.py tests/test_launch.py tests/test_ticket.py` → 65 passed.
- `PYTHONPATH=src python -m pytest` → 518 passed, 1 skipped.
- Pytest emitted a cache-write warning for `.pytest_cache` being read-only in
  this sandbox; tests still passed.
