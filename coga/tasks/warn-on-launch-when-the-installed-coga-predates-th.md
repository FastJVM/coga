---
slug: warn-on-launch-when-the-installed-coga-predates-th
title: Warn on launch when the installed coga predates the source tree
status: in_progress
mode: agent
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
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
step: 4 (review)
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
pr: https://github.com/FastJVM/coga/pull/511

## PR (pr step — done)
Pushed `warn-version-skew` and opened PR #511
(https://github.com/FastJVM/coga/pull/511). Auth probed clean
(`gh auth status` → logged in as nicktoper; working tree clean, on branch).
No CI is configured on this repo — `gh pr checks 511` reports "no checks
reported", so there is no green/red signal to gate on; the human reviews
directly. Range is `merge-base..HEAD` (2 commits: c73dec8b implement,
82fa9927 self-qa); branch is well behind `main` per the self-qa note, a
rebase before merge is likely wanted.

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

## Self-QA (self-qa step — done)

Ran `/code-review` and `/simplify` against my range (`merge-base(HEAD, main)..HEAD`
— **not** `git diff main`, which is polluted because this branch is behind a
much-advanced main; noted below for the PR step). Commit `82fa9927`.

**Acted on — one substantive finding (code-review + altitude, should-fix).**
The editable/in-tree short-circuit was scoped to the *operated* repo's git root
(`_is_within(package_dir, git_root / "src")`). "Am I running live editable
source?" is a property of where the *package* lives, not which repo you operate
on. So a coga dev who installs editable from checkout A and then runs coga
inside worktree/checkout B (our normal flow — this session included) got a
spurious "version skew → reinstall" warning that reinstalling can't even fix.
- Fix: new `_is_running_live_source(package_dir)` resolves the *package's own*
  git checkout and short-circuits when the package sits under that checkout's
  `src/`. Altitude review caught that the naive generalization
  (`_source_checkout_root(package_dir) is not None`, dropping `_is_within`)
  *overshoots*: it would also silence a frozen non-editable `.venv` copy living
  inside the tree — exactly the stale binary the guard exists to catch. Keeping
  the `src/`-membership check draws the line (editable → under `src/`; in-tree
  venv → not).
- Tests: added `test_no_warning_when_editable_source_in_other_checkout` (the
  false-positive fixed) and `test_warns_for_frozen_venv_copy_inside_source_tree`
  (the overshoot guarded). Also added a `frozen_install` fixture pinning the
  three pure decision tests to a non-live-source install dir — before, they
  silently depended on the test-runner's own editable install and one flipped
  to a false pass under the new (more correct) behavior.

**Reviewed and deliberately NOT changed.**
- *Clock-skew false positive* (committer `%ct` vs local mtime): a one-time
  spurious warning is possible right after reinstalling at HEAD if a commit's
  committer date is a few seconds ahead. Warn-only and self-correcting; a robust
  fix needs an arbitrary grace margin that weakens the guard. Left as a known
  limitation for the human reviewer.
- *Uncommitted src edits are invisible*: detection is commit-time based by
  design and documented as such; running-against-uncommitted-source is out of
  scope for a commit-vs-build comparison.
- *Reuse of `git._toplevel` / `git._run_git`*: the module keeps its own
  fully-non-raising `_run_git` and toplevel logic on purpose — the helpers are
  called directly by tests expecting None-not-raise, and the module avoids
  coupling to `git.py`'s raising API. Left as-is (per-module-runner convention).

**Verification.** `python3.12 -m pytest -p no:randomly` → 1045 passed, 1 skipped
(+2 new tests). `coga validate --json` on the `example/` fixture → exit 0, clean
JSON on stdout, empty stderr (guard no-ops in-tree). Working tree clean.

**For the PR step:** branch is well behind `main` (merge-base is the ticket's
own creation commit). `git diff main` shows large unrelated deletions from
main's advance (git.py/bump.py refactors, #509/#510). The actual change is only
the 4 files in `merge-base..HEAD`. A rebase onto `main` before merge is likely
wanted; version_skew.py is new so conflicts should be minimal, but launch.py /
validate.py import lines may need reseating.

## Usage

{"agent":"claude","cache_creation_input_tokens":494177,"cache_read_input_tokens":14805982,"cli":"claude","input_tokens":23096,"model":"claude-opus-4-8","output_tokens":158530,"provider":"anthropic","schema":1,"session_id":"183c4002-70d9-49f1-9292-146bff66235f","slug":"warn-on-launch-when-the-installed-coga-predates-th","step":"implement","title":"Warn on launch when the installed coga predates the source tree","ts":"2026-07-03T21:48:56.624528Z","usage_status":"ok"}

{"agent":"claude","cache_creation_input_tokens":274747,"cache_read_input_tokens":6949393,"cli":"claude","input_tokens":16939,"model":"claude-opus-4-8","output_tokens":86721,"provider":"anthropic","schema":1,"session_id":"ca0aadda-6aeb-4f46-b992-e794c393f88e","slug":"warn-on-launch-when-the-installed-coga-predates-th","step":"self-qa","title":"Warn on launch when the installed coga predates the source tree","ts":"2026-07-03T22:06:37.672031Z","usage_status":"ok"}

{"agent":"claude","cache_creation_input_tokens":70604,"cache_read_input_tokens":720229,"cli":"claude","input_tokens":18866,"model":"claude-opus-4-8","output_tokens":8055,"provider":"anthropic","schema":1,"session_id":"90992b33-7a19-4667-b45a-22cbaeee905c","slug":"warn-on-launch-when-the-installed-coga-predates-th","step":"pr","title":"Warn on launch when the installed coga predates the source tree","ts":"2026-07-03T22:07:59.004745Z","usage_status":"ok"}
