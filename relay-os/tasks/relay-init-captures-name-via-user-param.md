---
slug: relay-init-captures-name-via-user-param
title: relay init captures name via --user param
status: done
autonomy: interactive
owner: zach
human: zach
agent: claude
assignee: zach
contexts: []
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
secrets: null
---

## Description

Revise the open, unmerged work in PR #391 (from `marketing/relay-init-captures-name`)
so `relay init` takes the operator's name as a `--user NAME` parameter instead of
the interactive prompt that PR introduced. `relay init --user zach` writes `user`
to `relay.local.toml` (validated: non-empty, no `"` or `\`); a bare `relay init`
errors and asks for the flag; `relay init --update` is unchanged. This keeps init
scriptable — Nico's review ask — while still leaving `current_user` valid the
moment init finishes. Also update PR #391's description to match the param flow.

## Context

- Origin: Nico's only review comment on PR #391 — "no prompt; pass it as a param
  instead please (so we can script the init)." Settled with Nico (2026-06-18):
  `--user` param, no prompt, and no auto-detect from `git config`/`$USER`.
- Lands on the existing PR, not a new one. Do the work on branch
  `init-captures-name-impl` (#391's branch; worktree
  `/Users/zach2179/Desktop/relay-init-name-impl`), push to update #391, and
  `gh pr edit` its body. The owner merges #391 after — do not open a second PR.
- Code: the init prompt added in #391 — the `init._prompt_user_name()` call in
  `_do_init` (`src/relay/commands/init.py`) — becomes a `--user` option read with
  the same validation. `setup._ensure_user` keeps its shared prompt for the
  onboarding path (name capture is **not** moved to `relay setup`/`build` —
  decided against). `relay init --update` already skips name capture; leave it.
- Bare `relay init` with no `--user`: error with a clear "pass `--user NAME`"
  message rather than writing `user = ""`. With prompt and auto-detect both ruled
  out, the flag is required for a fresh init.
- Relationship: this revises the deliverable of `marketing/relay-init-captures-name`
  (currently at its human-review step) before merge. That ticket's other scope —
  stamping out `new-user`, the empty/filled gate, the browser-automation
  placeholder — stays as implemented in #391; only the name-capture mechanic changes.

## Acceptance Criteria

- [ ] `relay init` has a `--user NAME` option. `relay init --user marc <path>`
      writes `user = "marc"` to `<path>/relay-os/relay.local.toml` and prints a
      confirmation naming the value.
- [ ] A bare `relay init` (no `--user`, fresh init) exits non-zero (2) **before**
      cloning/writing anything and prints a message telling the operator to pass
      `--user NAME`. No `relay-os/` is created.
- [ ] `relay init --user ''` and `relay init --user 'a"b'` / `--user 'a\b'` exit
      non-zero (2) with a "non-empty, no quotes or backslashes" message; the name
      is `.strip()`-ed before validation (so `--user '  marc  '` stores `marc`).
- [ ] No interactive prompt is reachable from `relay init` — the command is fully
      scriptable (no stdin read on the fresh path).
- [ ] `relay init --update` and `relay init --update --all` are unchanged: they
      do not require, read, or fail on `--user`, and still skip name capture.
- [ ] `relay setup` is left untouched and still works end to end on a fresh dir:
      `_do_init(via_setup=True)` writes the empty `user = ""` template (no error,
      no `--user` needed) and `_ensure_user`'s existing prompt fills in the name.
- [ ] After `relay init --user NAME`, no delivered ticket under
      `tasks/**/ticket.md` still contains the `new-user` placeholder — it is
      stamped with the `--user` name (preserving #391's stamping on the direct
      init path). The `relay setup`-creates-a-repo path is **not** in scope for
      stamping (see Out of Scope).
- [ ] `current_user` (config.py) loads without error immediately after
      `relay init --user NAME` finishes — `user` is never written empty on the
      fresh `relay init` path.
- [ ] `python -m pytest tests/test_init.py tests/test_setup.py` passes; tests are
      updated to drive init via `--user` and to cover the bare-init and
      invalid-`--user` error paths.
- [ ] PR #391's description is updated to describe the `--user` flow (done in the
      open-pr step). No second PR is opened.

## Proposed Shape

All code is in `src/relay/commands/init.py` and `src/relay/commands/setup.py`
plus their tests. No changes to `config.py`, templates, or the `--update` path.

1. **Extract validation from the prompt** (`init.py`). Pull the rule out of
   `_prompt_user_name()` into a pure helper:
   `_clean_user_name(raw: str) -> str | None` — returns the stripped name when
   valid (non-empty, no `"`, no `\`), else `None`. `_prompt_user_name()` keeps
   its loop but delegates to `_clean_user_name`, so its behavior and the shared
   prompt text are unchanged (still used by `setup._ensure_user`).

2. **Add the `--user` option** to `init()` (`init.py`):
   `user: Optional[str] = typer.Option(None, "--user", help=...)`. Help text
   notes it is required for a fresh init and ignored under `--update`. The
   dispatch passes it only to the fresh path: `_do_init(path or Path("."), user=user)`.
   `--update` / `--update --all` ignore `user` (do not pass it through).

3. **Rework `_do_init`** signature to
   `_do_init(path: Path, *, user: str | None = None, via_setup: bool = False)`:
   - Remove the `name = _prompt_user_name()` call.
   - Resolve the name early, right after the `relay_os.exists()` guard and
     **before** `clone_upstream`/`mkdir` (fast-fail, nothing on disk):
     - `via_setup` is `True` → `name = None` (the setup path captures it later
       in `_ensure_user`; keep writing the empty `LOCAL_TOML_TEMPLATE`).
     - `via_setup` is `False` and `user is None` → `typer.secho` a "pass
       `--user NAME`" error to stderr and `sys.exit(2)`.
     - `via_setup` is `False` and `user` is set → `name = _clean_user_name(user)`;
       if `None`, `typer.secho` the invalid-name error and `sys.exit(2)`.
   - `local_toml.write_text(render_local_toml(name) if name is not None else LOCAL_TOML_TEMPLATE)`.
   - Call `_stamp_user_into_delivered_tickets(relay_os, name)` only when
     `name is not None`.
   - Make the `Wrote ... with user = "{name}"` echo conditional on `name`;
     fall back to the plain `Wrote {local_toml} ...` line when `name is None`.
   - The empty/filled gate (`_repo_is_empty`, `_prune_onboarding_tickets`) and
     the next-steps coax are untouched.

4. **Leave `setup.py` / `_ensure_user` untouched.** `setup()` still calls
   `init_cmd._do_init(target, via_setup=True)` (no `user` kwarg) and
   `_ensure_user` keeps its existing `_prompt_user_name()` prompt. The
   `via_setup=True` branch from step 3 is what keeps this working: it skips the
   required-`--user` check, writes the empty `LOCAL_TOML_TEMPLATE`, and does not
   stamp. Accepted consequence: on the transient `relay setup`-creates-a-fresh-
   repo path the onboarding tickets keep `new-user` (nothing stamps it once the
   prompt moves out of `_do_init`). That path is being deleted by
   `marketing/relay-build-command` (retires `relay setup` for `relay build`,
   which requires an already-init'd repo and drops name capture), so no new
   stamping machinery is built for it here — this stays a pure `relay init`
   change.

5. **Tests.** In `tests/test_init.py`: drop the autouse `stub_name_prompt`
   fixture (init no longer prompts) and the `_real_prompt_user_name` capture is
   now exercised against `_clean_user_name`/`_prompt_user_name` directly; change
   the `CliRunner().invoke(app, ["init", str(target)])` calls to pass
   `["init", "--user", "marc", str(target)]`; add a test that bare `relay init`
   exits 2 with the "pass `--user`" message and creates no `relay-os/`; add a
   test that `--user ''` / `--user 'a"b'` exits 2. The stamping/gate tests stay,
   now driven by `--user`. In `tests/test_setup.py`: existing tests should still
   pass (the new stamp call is a no-op on the seeded fixtures); add coverage that
   the setup path stamps `new-user` if a fixture ships one.

6. **PR #391** (open-pr step, not now). Push the branch
   `init-captures-name-impl` and `gh pr edit 391` the body to describe the
   `--user` flow. Do not open a second PR — the owner merges #391.

## Out of Scope

- Auto-detecting the name from `git config user.name` or `$USER` — explicitly
  ruled out with Nico.
- Any interactive prompt on the `relay init` path — removed, not relocated.
- Moving name capture into `relay setup` / `relay build` — decided against;
  name lives in `relay init` only.
- Any change to `relay setup` / `setup.py` — it is left as-is. Its retirement
  and the `relay build` rework belong to `marketing/relay-build-command`.
- Stamping `new-user` on the `relay setup`-creates-a-fresh-repo path. Accepted
  gap (option A): that path is being retired; only the direct `relay init --user`
  path stamps.
- The `new-user` stamping *mechanic* (on the direct path), the empty/filled gate,
  and the `browser-automation` placeholder — these stay exactly as #391
  implemented them; only where the name comes from changes.
- The `relay init --update` / `--update --all` behavior.
- Opening a new PR or changing #391's branch/base.

<!-- relay:blackboard -->

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
