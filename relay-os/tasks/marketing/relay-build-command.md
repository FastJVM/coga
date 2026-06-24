---
slug: marketing/relay-build-command
title: Add the relay build command (replaces relay setup)
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
---

## Description

Retire `relay setup` and replace it with `relay build` implemented as a thin
**alias** — `build = "launch relay-build"` — **not** a Python command.
`setup.py` is *deleted*, not renamed to `build.py`: per Relay's thin-code /
markdown-first principle, behaviour that can live in a ticket plus an alias
should not be a `.py`. After `relay init`, `relay build` launches the
already-shipped `relay-build` onboarding ticket (one question → agent-led chat →
vision → flat ticket batch).

This shape also sidesteps the latent `launch()` call-from-code crash entirely:
an alias dispatches through normal `relay launch` CLI parsing (argv is rewritten
to `relay launch relay-build` and Typer fills in every option's real default),
so it never passes the `OptionInfo` sentinels that crash in-code callers. The
two deliberate departures from `relay setup` then hold for free: `relay build`
**requires an initialized repo** (because `relay launch` already does — no
special check needed) and **does not capture the user's name** (that moved to
`relay init`).

The onboarding flow (`workflows/build/onboarding.md`) and the `relay-build`
ticket template already landed via PR #384. So this ticket is now almost all
*deletion*: drop the `setup` command, retire the old templates, add one alias.

## Acceptance Criteria

- [ ] `relay setup` no longer exists — gone from the command surface,
      `_BUILTIN_COMMANDS`, and `--help`. `src/relay/commands/setup.py` is
      **deleted** (no `build.py` is created).
- [ ] `relay build` runs as an alias expanding to `launch relay-build` (the
      `→ relay launch relay-build` dispatch line shows) and launches the
      `relay-build` ticket.
- [ ] The `build` alias ships in **both** the packaged `relay.toml` `[aliases]`
      and `_DEFAULT_ALIASES` (cli.py), mirroring `dream` — fresh repos get an
      editable alias, any repo gets a dispatchable fallback.
- [ ] `relay build` with no relay repo fails loud via `launch`'s own config
      error; it never runs `relay init`. No name capture anywhere in the path.
- [ ] `relay init`'s next-steps text points at `relay build` (no name-capture
      claim); the now-dead `via_setup` parameter + branch in `_do_init` are
      removed.
- [ ] The packaged `relay-setup` ticket template and the live + packaged
      `init/setup` workflow are deleted; `tasks/relay-setup` and
      `workflows/init/setup.md` are added to `OBSOLETE_PATHS` so
      `relay init --update` prunes them from existing repos.
- [ ] No changes to `launch.py` or `recurring.py` — the alias path doesn't hit
      the `OptionInfo` bug, so this ticket doesn't touch it.
- [ ] `python -m pytest` passes; `relay validate --json` passes.

## Proposed Shape

**1. The "command" is an alias.** Add `build = "launch relay-build"` to the
packaged `relay.toml` `[aliases]` (live + packaged copies), with a one-line
comment like `dream` has. Also add `"build": "launch relay-build"` to
`_DEFAULT_ALIASES` in `src/relay/cli.py` (one entry in the existing dict,
mirroring `dream`) so repos predating the alias still dispatch it; a user's own
`[aliases]` still overrides.

**2. Delete the command.** Remove `src/relay/commands/setup.py`. In
`src/relay/cli.py`, remove the `from relay.commands import setup as setup_cmd`
import, the `app.command("setup")(setup_cmd.setup)` registration, and `"setup"`
from `_BUILTIN_COMMANDS`. (Net deletion — no `build.py`.)

**3. `src/relay/commands/init.py`.** Repoint the next-steps text (lines ~264-270)
to `relay build` and drop the name-capture sentence (init owns the name now).
Since nothing calls `_do_init(via_setup=True)` anymore, remove the `via_setup`
parameter and make its `if not via_setup:` branch unconditional.

**4. Delete templates (keep live + packaged in sync).** Remove
`src/relay/resources/templates/relay-os/tasks/relay-setup/` (3 files) and both
`src/relay/resources/templates/relay-os/workflows/init/setup.md` and
`relay-os/workflows/init/setup.md` (drop the now-empty `init/` dirs). There is no
live `relay-os/tasks/relay-setup/` to remove.

**5. `src/relay/commands/update.py`.** Add `"tasks/relay-setup"` and
`"workflows/init/setup.md"` to `OBSOLETE_PATHS` (update.py:39) so existing repos
shed them on `relay init --update`. Confirm `prune_obsolete` removes a directory
entry recursively; if it leaves an empty `workflows/init/`, target
`"workflows/init"` instead.

**6. Tests.** Delete `tests/test_setup.py` (the command is gone). In
`tests/test_init.py`: update `EXPECTED_FILES` (L42-48), the fake-clone fixture
(L156, L175-205), and `test_init_ships_setup_ticket_template` + its
"Run `relay setup`" assertion (L520-541) to reference `relay-build`,
`build/onboarding`, and "Run `relay build`". Add (or extend an existing alias
test) asserting `build` is a default alias expanding to `launch relay-build`,
mirroring the `dream`/`chat` alias handling.

## Out of Scope

- **The `OptionInfo` / `run_launch` bug fix.** No longer needed for `build` — the
  alias dispatches through normal CLI parsing and never passes the sentinels. It
  remains a real, separate bug in `recurring._launch_created` (crashes
  `relay dream` / `relay recurring launch <x>` interactively) and in the
  now-deleted `setup.py`; that belongs to Nico's `recurring`/core-primitive
  domain, in its own ticket.
- The onboarding flow content and the `relay-build` ticket template — shipped
  (PR #384).
- Name capture in `relay init` — `relay-init-captures-name` / PR #391.
- Retiring the companion *tickets* (`remove-relay-setup-command`,
  `relay-build-requires-init`) — a CLI/owner project-management action, not code.
- `setup.py`'s custom "run `relay init` first" / "already done" messages —
  deliberately dropped; `relay launch`'s own behaviour (generic config error;
  re-activate-and-launch a done ticket) is the accepted thinner tradeoff.

## Context

- Fresh replacement for `marketing/remove-relay-setup-command` (being closed):
  that ticket was scoped as a straight rename that *carried over* `relay setup`'s
  init-if-needed + name-capture, both of which this session reversed — so a clean
  rewrite is clearer than patching it.
- **Folds in `marketing/relay-build-requires-init`** — "no init-if-needed,
  require an already-init'd repo" is part of defining the renamed command. Retire
  that ticket as subsumed.
- Name capture is **out of scope here** — it lives in `relay init` now
  (`marketing/relay-init-captures-name`); `relay build` just relies on `user`
  being set before launch.
- Files: `src/relay/commands/setup.py` → `build.py`; the command registration +
  `_BUILTIN_COMMANDS` entry in `src/relay/cli.py`; `relay init`'s next-steps text
  repointed at `relay build`; the packaged `relay-setup` ticket template →
  `relay-build`, and the `init/setup` workflow → `build/onboarding` (keep the live
  and packaged copies in sync). The onboarding flow content is designed in
  `marketing/relay-build-onboarding-flow`.
- Carry the latent-bug fix forward: `setup.py`'s `launch_cmd.launch(...)` call
  passes only 6 of `launch()`'s 8 params, omitting `max_session` and
  `return_timeout` (added to `launch` after `setup.py` was written). Because
  `launch` is a Typer command, the unpassed params keep their `typer.Option(...)`
  defaults (`OptionInfo` objects), so the call crashes at launch
  (`repl_supervisor.py`: "'>=' not supported between instances of 'float' and
  'OptionInfo'"). The renamed command must pass all of `launch()`'s params — or,
  better, call a non-Typer helper so new options can't silently become sentinels.
- Companions: `marketing/relay-build-onboarding-flow` (the flow this launches),
  `marketing/relay-init-captures-name` (the init-side name capture this relies on).

<!-- relay:blackboard -->

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
