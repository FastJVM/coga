---
slug: warn-on-launch-when-the-installed-coga-predates-th
title: Warn on launch when the installed coga predates the source tree
status: in_progress
mode: agent
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: dev/with-self-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: self-qa
    skills:
    - code/self-qa
    assignee: agent
  - name: pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 2 (self-qa)
---

## Description

Add a warn-only version-skew guard: when a coga command operates on a repo
that is itself a coga source checkout (contains `src/coga/`), and the
*running* installed package was built before the latest commit touching
`src/coga/`, print a loud stderr warning naming both sides and the remedy
(`uv tool upgrade coga` / reinstall from the checkout).

Scope decisions to settle during implementation:

- **Where the guard fires.** `coga launch` entry is the minimum (that's
  where a stale binary burns hours of agent work); consider also `coga
  validate` as the diagnostic surface. Keep it out of read-only commands'
  hot path if it costs a subprocess.
- **How skew is detected.** Cheapest deterministic option: at build/install
  time the package already knows its vendored/built commit SHA (`coga
  --version` prints it). Compare that SHA's commit date against
  `git log -1 --format=%ct -- src/coga/` of the repo being operated on;
  warn when the source tree is newer. Must degrade silently when the repo
  is not a coga source checkout, has no git, or the package carries no
  build SHA — the guard is for coga developers and must never bother normal
  users.
- **Warn, never refuse.** Running a slightly stale coga is usually fine;
  the guard exists to make the skew *visible*, not to block work.

## Why

2026-07-01/02: three launch sessions in a row silently lost `log.md` audit
lines from detached isolation worktrees. The bug (detached-HEAD sync had no
landing path for `merge=union` files) was fixed in source at 11:02
(419dcdff), yet the 11:31 session still failed — the running `coga` was a
uv tool build from 21:06 the previous night, installed from a sibling
checkout. Nothing surfaced that the binary predated the fix; the skew was
only found by diffing the installed package's `git.py` against source.
Recovery cost a manual salvage session (PR #500).

## Context

<!-- coga:blackboard -->

## Dev
branch: warn-version-skew
worktree: ../coga-warn-version-skew

## Design decisions (implement step)

**Signal chosen: installed-package build/install time vs latest `src/coga`
commit time.** Investigated the alternatives the ticket floated:

- The ticket suggests reusing the build SHA that `coga --version` prints. But
  `--version` only prints the `COGA_PIN` upstream SHA, and that pin only exists
  in a *vendored* repo (`coga init`), not in a coga **source checkout** — which
  is exactly the motivating scenario (dev running a `uv tool install .` binary
  in the coga repo). Verified: this repo has no `COGA_PIN`; `coga --version`
  prints just `coga 0.2.0`. So the pin can't drive the guard here.
- The running binary carries **no** embedded build SHA today. Embedding one at
  build time (hatchling hook) is heavy, can't help already-installed stale
  binaries (the guard code itself must already be in the binary), and uv's
  build-from-checkout `.git` availability is uncertain. Rejected as out of
  scope for a warn-only guard.
- Verified the deterministic signal that *is* available: the uv-tool install
  writes package files with real install-time mtimes (checked
  `site-packages/coga/__init__.py` mtime == install time, not zeroed). So
  `mtime(coga.__file__)` is a reliable "built/installed at" timestamp.

Guard logic (`src/coga/version_skew.py`):
1. git toplevel of the operated-on repo must contain `src/coga/` → else it's
   not a coga source checkout, silent skip.
2. If the running package dir is *inside* `<root>/src` (editable / pythonpath
   dev run) → the running code IS the source, no skew possible, skip.
3. build_time = mtime of `coga.__file__`; skipped if implausibly old
   (< 2020-01-01, guards against reproducible-build zeroed mtimes).
4. src_ct = `git log -1 --format=%ct -- src/coga` (latest source change).
5. Warn to stderr, naming both sides + remedy, only when `src_ct > build_time`.
   Never refuses; wrapped so any exception is swallowed (guard must never break
   a command).

Fires on: `coga launch` entry (primary — where a stale binary burns agent
hours) and `coga validate` (diagnostic surface). Kept out of read-only hot
paths. Normal users: the `src/coga/` check short-circuits instantly.

Tests: `tests/test_version_skew.py`, real-git tmp repo (mirrors test_git.py
style), monkeypatch only `_installed_build_time` for determinism.

## Implementation result (implement step — done)

Commit `c73dec8b` on branch `warn-version-skew` (worktree
`../coga-warn-version-skew`). Files:
- new `src/coga/version_skew.py` — the guard.
- `src/coga/commands/launch.py` — call after preflights pass, before the
  status flip/spawn (see note below on placement).
- `src/coga/commands/validate.py` — call after `load_config`, stderr-only.
- new `tests/test_version_skew.py` — 11 tests, all green.

**Launch placement note.** First put the guard right after `load_config`, but
two existing tests (`test_launch_fails_loud_on_op_read_error`,
`test_launch_refuses_and_stays_active_when_push_auth_broken`) assert fail-loud
preflight paths spawn/mutate *nothing*, and they patch `subprocess.run`
globally — so the guard's `git rev-parse` probe tripped them. Moved the call to
just after `_preflight_push_auth` (all fail-loud preflights passed → session
will run), which respects that invariant without weakening the tests. Warning
still precedes the expensive agent spawn.

**Verification.** `python3.12 -m pytest -p no:randomly` → 1043 passed, 1
skipped. `coga validate --json` on the example fixture → exit 0, clean JSON on
stdout, guard no-ops in-tree. Simulated stale out-of-tree install → warning
renders correctly (both sides + `uv tool upgrade` / reinstall remedy).

**Pre-existing flake (NOT mine — follow-up candidate).**
`tests/test_usage_probe.py::test_codex_probe_primes_once_across_reads` fails
only under `pytest-randomly` order (passes isolated, per-file, and in
deterministic full runs on both this branch and `main`). Order-dependent test
isolation issue in the codex usage probe; untouched by this change.
