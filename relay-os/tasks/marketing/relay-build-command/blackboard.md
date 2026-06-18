# Blackboard — relay-build-command (design step)

## DIRECTION CHANGE (owner = zach, 2026-06-18, in-chat) — supersedes earlier plan

`relay build` is **NOT a `.py` command**. It is a thin **alias**:
`build = "launch relay-build"`. `setup.py` is deleted, not renamed to `build.py`.
Rationale (zach): Relay's code is meant to be very thin; behaviour that can live
in a ticket + alias should not be a `.py`, because ticket/toml-resident things
are far easier to change. Matches the existing `chat`/`dream` alias precedent.

Consequence: the whole earlier `launch()` "Option A vs B / run_launch" question
is **moot for this ticket**. An alias dispatches through normal `relay launch`
CLI parsing, so Typer fills in real option defaults — the `OptionInfo` sentinel
crash is never reached. No edits to `launch.py` or `recurring.py`.

## Findings (still valid)

- Onboarding flow + packaged `relay-build` ticket already shipped (origin/main
  `b3512a67`, PR #384): `workflows/build/onboarding.md` and
  `src/relay/resources/templates/relay-os/tasks/relay-build/` both exist.
- Existing alias config: `_DEFAULT_ALIASES` (cli.py) = {chat, dream}; packaged
  `relay.toml [aliases]` = chat + dream (claude/codex commented); live
  `relay-os/relay.toml [aliases]` = chat, claude, codex.
- No live `relay-os/tasks/relay-setup/`; live + packaged `init/setup.md` exist.

## The OptionInfo bug — now OUT OF SCOPE here, but real and reproduced

Confirmed it crashes the *real* `relay dream` (= `relay recurring launch dream`)
in a TTY: `recurring._launch_created` (recurring.py:498) omits idle_timeout /
max_session → they arrive as Typer `OptionInfo` → `repl_supervisor.py:286`
`float >= OptionInfo` → TypeError. The scheduled sweep (bare `relay recurring`,
recurring.py:129-151) sets the timeouts, so only the on-demand single-task
launchers (`relay dream`, `relay recurring launch <x>`, old `relay setup`) break.
This is Nico's `recurring`/core-primitive domain → its own ticket.
Repro scripts (untracked scratch, safe to delete): `scratch_repro_launch_optioninfo.py`,
`scratch_repro_recurring_e2e.py` (runs the literal `relay dream`, fully sandboxed).

## Open Questions (for review-design)

1. **Alias placement.** RESOLVED (zach, 2026-06-18): **both** — packaged
   `relay.toml [aliases]` (editable) AND `_DEFAULT_ALIASES` in cli.py (fallback),
   mirroring `dream`.
2. Accept dropping `setup.py`'s custom messages? `relay build` with no repo →
   `launch`'s generic "No relay.toml found" (not "run `relay init` first"); a
   `done` relay-build ticket → `launch` re-activates and re-launches (vs setup's
   "already done, nothing to do"). **Recommendation:** accept — thinner, still
   fail-loud; matches the alias model.

## Coordination note

`relay-init-captures-name-via-user-param` (PR #391, at `review` on main) also
edits `init.py` (name capture via `--user`). This ticket's only `init.py` change
is the next-steps text + removing the dead `via_setup` path — different region,
same file. Implementer: rebase on main and reconcile.

## Dev (implement step, 2026-06-18)

branch: relay-build-alias
worktree: /Users/zach2179/Desktop/relay-build-alias  (off local `main` 64940a98)
pr: https://github.com/FastJVM/relay/pull/397

- No git remote on this checkout; `main` ≡ feature-branch code (they differ only
  in `relay-os/tasks/` state markdown). main has all PR #384 prereqs + the old
  setup files being deleted. PR #391 name-capture is **not** in local main, so
  init.py reconciliation is moot here — next-steps edit applies cleanly.
- `OBSOLETE_PATHS` decision: `prune_obsolete` only `unlink`s files (leaves the
  parent dir), so adding the directory entries `tasks/relay-setup` and
  `workflows/init` (not `.../setup.md`) — both get `shutil.rmtree`'d, no empty
  `workflows/init/` left behind. `init/` was relay-owned (only setup.md shipped).
- Live `relay-os/relay.toml [aliases]` has chat/claude/codex (no dream); packaged
  has chat/dream. Adding `build` to both per ticket; matching each file's style.

### Implemented — commit 7a6a9f7d on `relay-build-alias` (14 files, +84/−539)

What changed (matches ticket Proposed Shape 1-6 exactly):
- `cli.py`: dropped setup import/registration/`_BUILTIN_COMMANDS` entry; added
  `"build": "launch relay-build"` to `_DEFAULT_ALIASES` (+ comment).
- Deleted `commands/setup.py` and `tests/test_setup.py`.
- `init.py`: next-steps now points at `relay build` (no name-capture/scan claim);
  removed dead `via_setup` param + branch. (PR #391 name-capture not in local
  main, so no reconcile needed.)
- `update.py`: `OBSOLETE_PATHS` += `tasks/relay-setup`, `workflows/init` (dir
  entries → `shutil.rmtree`, no empty `init/` left behind).
- Deleted packaged `relay-setup` template (3 files) + live & packaged
  `workflows/init/setup.md` (init/ dirs auto-removed).
- `relay.toml` (packaged + live): added `build = "launch relay-build"`.
- Tests: updated `test_init.py` (EXPECTED_FILES, fake_clone fixture, renamed
  `test_init_ships_build_ticket_template`); added 2 `build`-alias tests in
  `test_aliases.py`.

Verification:
- My touched files: `test_init.py` + `test_aliases.py` → 87 passed.
- Full suite: 777 passed, 1 skipped, **2 failed** — both in
  `test_autoclose_sweep.py`, **pre-existing & unrelated**: they reproduce
  identically on unmodified base `main`. Cause: live
  `recurring/autoclose-merged/blackboard.md` has a stale committed
  `last_serviced_period: 2026-06-17` vs the test's expected `2026-06-11`. No
  autoclose file is in my diff. Different domain (recurring/autoclose).
- `relay validate --json`: **identical** issue set before/after my change
  (ok_count 86, 25 pre-existing issues in unrelated tasks — relay/cli context,
  bootstrap/ticket skill, nick assignee, v2/* missing-step). My change adds zero
  new issues. (Non-zero exit is pre-existing repo cruft, not this ticket.)

No push, no PR (that's `code/open-pr`). Ready to bump to `open-pr`.

### open-pr step (2026-06-18)

- **Remote resolution.** The implement-step note "no git remote on this checkout"
  was correct — none of the shared Desktop worktrees had an `origin`. `gh` auth is
  fine (logged in as `lilfedor`). Canonical repo is **`FastJVM/relay`** (confirmed
  by zach in-chat + verified: PR #384 MERGED, PR #391 OPEN, modern
  `src`/`relay-os`/`tests`/`docs` layout). NB the unrelated `lilfedor/relay` repo
  is an abandoned early prototype — do not push there.
- Added `origin = https://github.com/FastJVM/relay.git` and fetched. The branch's
  merge-base with `origin/main` is `64940a98` (shared ancestry confirmed); branch
  adds exactly 1 commit (`7a6a9f7d`). `origin/main` is 17 commits ahead (other work
  landed since the branch was cut) but the PR three-dot diff is exactly this
  ticket's **14 files, +84/−539**. Did not rebase (merge-time reconciliation is the
  human reviewer's call).
- Pushed `relay-build-alias` and opened **PR #397**:
  https://github.com/FastJVM/relay/pull/397 (base `main`, body links the ticket).
- **CI:** `gh pr checks` → "no checks reported" — the repo has no CI workflows
  configured, so there is no green/red signal to wait on (not a failure).
