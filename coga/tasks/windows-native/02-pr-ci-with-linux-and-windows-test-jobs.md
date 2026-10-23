---
title: PR CI with Linux and Windows test jobs
status: in_progress
owner: nicktoper
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 2 (peer-review)
agent: claude
---

## Description

Add PR CI so Windows support can't silently regress after the port. Today
`.github/workflows/` holds only `release.yml`, and no tests run on PRs at
all. Add a workflow that runs `python -m pytest` on pull requests and pushes
to `main`, on both `ubuntu-latest` and `windows-latest`, with Python 3.11
(the floor).

Start after `windows-native/01-core-port-cli-and-test-suite-pass-on-native-window`
is merged; before that, the Windows job can't pass.

Done when the workflow is merged, both jobs pass on its own PR, and a
deliberately broken commit on a scratch branch shows the Windows job failing
(for example a top-level `import fcntl` in a module the CLI imports). Link
that run in the PR.

## Context

- Install as the repo documents: `python -m pip install -e ".[test]"`, then
  `python -m pytest`.
- Some tests may need git identity (`git config user.name/email`) set in CI.
- Tests that need a real agent CLI, network or AWS must already skip
  cleanly. If one doesn't, fix the skip; don't add it to CI.
- Interactive launch is checked on EC2 (the interactive-launch ticket), not
  in CI.
- `coga-dev/testing` (`docs/contexts/coga-dev/testing/SKILL.md`) owns test
  expectations. Add one line there saying PR CI exists and what it runs.
  This development topic is local-only (`coga-dev/packaging`).

<!-- coga:blackboard -->
## Dev

branch: coga/windows-native-02-pr-ci-with-linux-and-windows-t-6501cb


## Implementation preflight — 2026-10-22

- Codex checked a clean `main`, fetched and fast-forwarded it to
  `e2958c82d4fa7e3b9a930e7df7e0e311afba0fea`, and fetched again before
  handing off; the remote tip was unchanged.
- The required predecessor,
  `windows-native/01-core-port-cli-and-test-suite-pass-on-native-window`, is
  still `in_progress` at step 3 (`review-design`, owner-held), with no
  recorded implementation branch or PR. GitHub PR searches for `core-port`
  and Windows titles found no merged core-port PR; merged PR #1026 is the
  Windows EC2 harness, not the port.
- Current main still imports `fcntl` unconditionally at module scope in
  `src/coga/git.py`, `src/coga/launch.py`, and
  `src/coga/repl_supervisor.py`; `src/coga/commands/megalaunch.py` still
  imports `termios` and `tty`. The prerequisite's promised Windows import
  fixes have not landed, so a Windows test job cannot yet pass.
- Follow the ticket's explicit start-after-merge constraint: block on
  `windows-native/01-core-port-cli-and-test-suite-pass-on-native-window` being
  merged. No implementation branch, workflow changes, PR, or test run was
  made in this attempt.
- Resume after that merge: add the Python 3.11 Linux/Windows workflow,
  replace the obsolete no-CI posture in `coga-dev/testing`, run the suite,
  and prepare the implementation handoff. Later PR steps still owe both
  green jobs and the linked scratch-branch Windows failure run.

## Implement handoff — 2026-10-23 (claude, attended)

- Blocker resolved: owner reviewed PR #1093; Claude rebased it onto main in a
  scratch worktree (one test_compose conflict; dropped a branch commit's
  restored principles copy in `coga/context.md` to follow main's 4c9d8699f),
  force-pushed with lease, owner merged (5132aa6ac). `coga unblock` ran.
- Owner explicitly reversed the 2026-09-24 no-pytest-CI decision in this
  session (asked because `coga-dev/testing` required an owner decision).
- Commit `2ab0ff48e` adds `.github/workflows/test.yml`: `pull_request` + push
  to `main`; matrix `ubuntu-latest`/`windows-latest`, Python 3.11,
  `fail-fast: false`, `contents: read`; global git identity; `python -m pip
  install -e ".[test]"`; `python -m pytest`. Concurrency cancels superseded
  PR runs only. `coga-dev/testing` "CI posture and receipts" now records the
  CI and the decision; verifiers still record exact commands and counts.
- **Next steps (open-pr/review) still owe:** both jobs green on this PR, and
  the scratch-branch failure run linked in the PR. A pushed scratch branch
  alone does **not** trigger the workflow (no `push` trigger outside `main`):
  open a draft PR from the scratch branch (e.g. targeting this feature
  branch; `pull_request` has no base filter) with a top-level `import fcntl`
  in a CLI-imported module, capture the failing Windows run URL, then close
  it and delete the scratch branch.
- **Adjacent bug, not fixed here:**
  `tests/test_clean_install_harness.py::test_release_check_requires_completed_logged_clean_task`
  fails in a fresh `python3.11 -m venv` (`ModuleNotFoundError: No module
  named 'yaml'`). The `release_env` fixture symlinks `sys.executable` to
  `tools/coga/bin/python`; a venv interpreter symlinked outside its venv
  starts as the base interpreter, which lacks the venv's site-packages. It
  passes in `.venv` only because that base 3.12 has PyYAML. CI is unaffected
  (setup-python installs into the base interpreter). No follow-up ticket yet.

## PR

```yaml
title: Run pytest on Linux and Windows for PRs and main pushes
author: claude
author_evidence: Attended implement session ran as Claude (claude-opus-5-5); see implement handoff.
head: 2ab0ff48e036e88d5029c437f51b38d2d48eb336
base: 726a08778adc39d9f964db49a852d1d3bc27cc32
depth: skim
rationale: Small additive workflow plus one doc paragraph; read it for the trigger choice and the reversed owner decision. Real CI runs are still pending.
implementation: Adds a Python 3.11 pytest matrix on ubuntu-latest and windows-latest for pull requests and pushes to main, and records the PR CI posture in coga-dev/testing.
deviations: Adds a concurrency group that cancels superseded PR runs (not asked for; saves Windows runner time).
limitations: The workflow has not run on GitHub yet; both green jobs and the deliberately broken scratch-branch Windows failure are owed by later steps. coga validate is not run in CI.
files:
  .github/workflows/test.yml: New PR/main-push pytest workflow on Linux and Windows, Python 3.11.
  docs/contexts/coga-dev/testing/SKILL.md: Replace the no-CI posture with the PR CI posture and the 2026-10-23 owner decision, as the ticket requires.
review:
  reviewer: none
  kind: none
  status: not-run
  detail: Implement step; review belongs to later workflow steps.
checks:
  - command: python3.11 -m venv <scratch>/venv311 && <scratch>/venv311/bin/python -m pip install -e ".[test]" && <scratch>/venv311/bin/python -m pytest -q -p no:cacheprovider
    status: failed
    head: 2ab0ff48e036e88d5029c437f51b38d2d48eb336
    base: 726a08778adc39d9f964db49a852d1d3bc27cc32
    detail: Python 3.11.15 -- 1 failed, 4047 passed, 10 skipped. Sole failure is the pre-existing test_clean_install_harness release_env venv-symlink bug (no PyYAML in the uv base 3.11); unrelated to this diff, which touches no Python.
  - command: .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_clean_install_harness.py::test_release_check_requires_completed_logged_clean_task
    status: passed
    head: 2ab0ff48e036e88d5029c437f51b38d2d48eb336
    base: 726a08778adc39d9f964db49a852d1d3bc27cc32
    detail: Python 3.12.12 -- 1 passed; base interpreter has PyYAML.
```

---

## Blockers

- [x] [2026-10-22 11:50] [agent:claude] id=20261022T115057 Merge windows-native/01-core-port-cli-and-test-suite-pass-on-native-window before starting this CI ticket. It is still at owner-held review-design, and main retains unconditional POSIX-only imports that prevent the Windows test job from passing.
  resolved: [2026-10-23 13:55] [human:nicktoper] Predecessor windows-native/01 merged via PR #1093 (merge commit 5132aa6ac) after conflict resolution; origin/main no longer has module-level fcntl/termios/tty imports, so the CI ticket can proceed.

---

## Blocker reminders

- 9f1f52929c3a last_reminded: 2026-10-23 10:25
