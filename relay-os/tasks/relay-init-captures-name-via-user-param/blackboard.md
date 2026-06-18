The blackboard is a notepad to be written to often as the human and agent works through a task.

## Design notes (design step)

Investigated the live #391 branch (`init-captures-name-impl`, worktree
`/Users/zach2179/Desktop/relay-init-name-impl`) — the *current* worktree
(`feat/relay-init-captures-name`) does NOT contain #391's name-capture work, so
the spec is written against the impl branch.

What #391 does today (the thing we're revising):
- `_do_init` calls `_prompt_user_name()` up front (before the slow clone), then
  uses the name for two things: `render_local_toml(name)` and
  `_stamp_user_into_delivered_tickets(relay_os, name)`.
- `setup._ensure_user` shares the same `_prompt_user_name()` helper; on the fresh
  `relay setup` path it's a no-op echo because `_do_init` already set `user`.
- `new-user` placeholder ships in two tickets: `tasks/relay-setup/ticket.md` and
  `tasks/browser-automation/ticket.md` (owner + human lines).

The switch to `--user` is mechanical for direct `relay init`. The only real
ripple is the setup path (see Open Question 1).

## Decisions (resolved live with owner, 2026-06-18)

Re-oriented on `marketing/relay-build-command` (draft): name capture lives in
`relay init` ONLY; `relay setup` → `relay build` later, which requires an
already-init'd repo and does NOT capture the name. So `relay setup` is a dying
path and my ticket should stay a pure `relay init` change.

1. **`new-user` stamping on the `relay setup`-creates-a-fresh-repo path →
   Option A: don't handle it.** Leave `setup.py` / `_ensure_user` untouched; the
   `via_setup=True` branch in `_do_init` writes the empty template and does not
   stamp. Accepted: that transient path may leave `new-user` in onboarding
   tickets until `marketing/relay-build-command` redesigns onboarding. Only the
   direct `relay init --user` path stamps. (Owner picked A.)

2. **`--user` alongside `--update` → silently ignore.** `--update` stays exactly
   as-is; `--user` is simply not read/passed on that path. Default chosen to keep
   the "`--update` is unchanged" promise; low-stakes, override at review-design if
   desired.

3. **Error exit code → `sys.exit(2)`** for both missing-`--user` and
   invalid-`--user`, matching the existing `init` arg errors (`--all` misuse,
   `relay-os already exists`).

## Open Questions

None outstanding — all resolved above. (review-design: override any of the three
defaults if you disagree.)

## Dev

This ticket lands on the existing #391 PR, so it reuses #391's branch/worktree
rather than cutting a new one (per task context).

- branch: `init-captures-name-impl`
- worktree: `/Users/zach2179/Desktop/relay-init-name-impl`
- pr: https://github.com/FastJVM/relay/pull/391

open-pr step (done): pushed `35918848` to update #391; rewrote the PR body to the
`--user` param flow via `gh pr edit` (title unchanged — the new-user/gate/placeholder
scope still holds). CI: `gh pr checks 391` → no checks configured on this repo, so
nothing to wait on. Owner merges #391 — no second PR.

Note: the editable `relay` install points at the primary checkout
(`/Users/zach2179/Desktop/relay-cli/src`), so tests must run with
`PYTHONPATH=<worktree>/src` to exercise the worktree code.

## Implement step (done)

Committed on `init-captures-name-impl` (no push/PR yet — that's `code/open-pr`).

What changed (`src/relay/commands/init.py`):
- Added `--user NAME` option to `init()`; passed to `_do_init(..., user=...)`
  only on the fresh path. `--update` / `--update --all` never read it (Decision 2).
- Extracted the validation predicate into `_clean_user_name(raw) -> str | None`
  (strip + reject empty/`"`/`\\`), now the single source of truth shared by the
  `--user` param and `_prompt_user_name`.
- Added `_require_user_name(user)`: errors (exit 2) on a missing flag and on an
  invalid value, with distinct messages. Validated **before** mkdir/clone, so a
  bad invocation writes nothing.
- `_do_init` now takes `user`; `name = None if via_setup else _require_user_name(user)`.
  When `name is None` (the `relay setup` path), it writes the empty
  `LOCAL_TOML_TEMPLATE` and skips stamping (Decision 1 / Option A).
- `_prompt_user_name` kept (now only `setup._ensure_user` uses it); `setup.py`
  untouched.

Tests (`tests/test_init.py`): dropped the autouse prompt-stub fixture; added
`--user tester` to the name-agnostic fresh-init invocations; converted the two
name-specific tests to pass `--user` (`"  marc  "` also covers stripping); added
`test_init_without_user_errors` and `test_init_rejects_invalid_user`. Kept the
`_prompt_user_name` validation-loop test (still live via setup). No
`setup.py`/`test_setup.py` changes; example fixture unaffected (init isn't
re-run on it).

Verification: `python -m pytest` → 785 passed, 1 skipped (pre-existing).
`relay init --help` shows `--user`; bare `relay init <dir>` exits 2 and writes
no `relay-os/`.

PR #391 body still needs updating to the param flow — that's part of `code/open-pr`.
