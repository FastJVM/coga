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
step: 3 (open-pr)
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

pr: https://github.com/FastJVM/coga/pull/1097
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
  (setup-python installs into the base interpreter). Filed as draft
  `fix-release-env-fixture-interpreter-symlink-in-fre` (open-pr step, owner-approved).

## Peer review

- Codex **completed** direct review of final head
  `3cb85786bda42ecb30f2d31b88cc536ff2e16b62` against base
  `6b413aea74f7001a8e3f58023393af521001190a` on 2026-10-24 UTC.
  Re-reviewed all six diff paths after reconciliation; `git range-diff`
  confirms all four feature patches are unchanged. No nested review CLI,
  review tool, or subagent ran. No unresolved code findings.
- Claude authored the original implementation. Codex independently reviewed
  that implementation, then authored and self-reviewed the corrections.
  The aggregate review is recorded as `self`; fully independent review of
  reviewer-authored changes is not claimed.
- Fixed four findings with the attending owner's approval: unique concurrency
  groups for main pushes; plain CLI output with `TERM=dumb`; Linux ripgrep
  for the existing migration-runbook test; and absolute skill-link targets
  when Windows drives differ. The owner approved the product fix with
  "yeah" after the first hosted Windows run exposed it. Existing tests and
  skip rules are retained; one regression test was added.
- Checked triggers, matrix, Python floor, install/Git setup, shell behavior,
  permissions, cancellation, test isolation, cross-drive link resolution,
  repeated view refreshes, and context ownership. The testing topic stays
  local-only; the skill-management topic and packaged twin match. The new
  cross-drive regression failed before the fix; afterward the five focused
  skill-view/link tests passed. Native Windows CI exercises the corrected
  drive layout; no interactive terminal surface changed.
- Final local verification **passed** on `3cb85786b` with
  `GITHUB_ACTIONS=true CI=true TERM=dumb /tmp/coga-windows-ci-peer-yo9wanrn/python311/bin/python3.11 -m pytest`.
  Result: **4049 passed, 10 skipped in 370.19s**, Python 3.11.15.
  The earlier head `a87f21bb94af3e6c5df40244e0a51494722be2d4`, base
  `1b58dfef71d04cf1a97b6e6e6be3925b627f8c81`, passed with **4049 passed,
  10 skipped in 400.79s**, Python 3.11.15. Head `8f0fcab9d` also passed
  (4049 passed, 10 skipped in 374.29s). The isolated copied base interpreter
  uses the documented editable test-extra install and avoids the existing
  venv-symlink fixture bug. Actionlint 1.7.11, `git diff --check`, and scoped
  task validation passed on the final head.
- Disposable [PR #1095](https://github.com/FastJVM/coga/pull/1095),
  [run 40039260714](https://github.com/FastJVM/coga/actions/runs/40039260714),
  **completed successfully** on head
  `8f0fcab9d39a1bdcb4b8789d7a104a7401078995` against base
  `05596b689f01e62ccb5118465aac79f0ecebebb6` before the final control-only
  rebases. All files outside `coga/tasks/` and `coga/log.md` remain identical;
  these receipts retain their actual head/base and are not re-stamped.
  [Linux](https://github.com/FastJVM/coga/actions/runs/40039260714/job/120706206829):
  **4049 passed, 10 skipped in 394.21s**, Python 3.11.17.
  [Windows](https://github.com/FastJVM/coga/actions/runs/40039260714/job/120706207080):
  **3957 passed, 102 skipped in 4770.02s**, Python 3.11.9.
  PR #1095 is closed without merging; its scratch branch is deleted.
- Required deliberate Windows failure: closed disposable
  [PR #1094](https://github.com/FastJVM/coga/pull/1094),
  [run 40028184483](https://github.com/FastJVM/coga/actions/runs/40028184483),
  [Windows job](https://github.com/FastJVM/coga/actions/runs/40028184483/job/120669536523).
  Scratch head `696ec4ebf5c7da1d20a26e8449907ada239b9f5a`, diff base
  `c18e2be3a6d01706c06a0621d846dff3958f5ea2`, adds only a top-level
  `import fcntl` to `src/coga/cli.py` beyond feature head `fd5821a822`.
  Setup/install succeeded; Python 3.11.9 pytest failed with 35 collection
  errors, all `ModuleNotFoundError: No module named 'fcntl'`, exit 1.
  That scratch branch is deleted. The eventual feature PR must retain this
  run link; the expected negative result does not apply to the feature head.
- Prerequisite PR #1093 is merged. Rebased onto current main, preserving the
  projected ticket byte-for-byte each time. Intervening main changes were
  unrelated ticket/log state. Final base is
  `6b413aea74f7001a8e3f58023393af521001190a`; code, workflow, docs,
  and tests are identical to the CI revision. Final head is
  `3cb85786bda42ecb30f2d31b88cc536ff2e16b62`; the final local suite passed
  and the branch was pushed with an explicit lease on `a87f21bb9`.
  The final fetch returned the same main tip. Only the projected ticket
  remains dirty and was never staged or committed. Control still records
  peer-review and GitHub has no PR for the feature branch.
- The actual feature PR remains for `open-pr`; its own two green jobs and the
  owner's merge remain acceptance requirements. No lifecycle field was
  edited manually, and no scratch PR was recorded as the task's PR.

### Historical verification (not receipts for the final head)

- Original implement head `2ab0ff48e036e88d5029c437f51b38d2d48eb336`, base
  `726a08778adc39d9f964db49a852d1d3bc27cc32`: the recorded
  `python3.11 -m venv <scratch>/venv311 && <scratch>/venv311/bin/python -m pip install -e ".[test]" && <scratch>/venv311/bin/python -m pytest -q -p no:cacheprovider`
  had 1 failed, 4047 passed, 10 skipped (the known release_env symlink bug).
  `.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_clean_install_harness.py::test_release_check_requires_completed_logged_clean_task`
  passed once on Python 3.12.12 at the same head/base.
- `.venv/bin/python -m pytest` at head `fd5821a8222783573b31b59efe5f8c016175512b`,
  base `c18e2be3a6d01706c06a0621d846dff3958f5ea2`: 4048 passed, 10 skipped
  in 368.05s on Python 3.12.12. Plain scratch-base Python 3.11.15
  `python -m pytest` at head `022d368e2ca980468e6acfd03d9faeb9d7c86324`,
  base `b4fc6ab1965db0395c822400f38e96101271a19e`: 4048 passed, 10 skipped
  in 395.40s, before the hosted-runner fixes.
- The negative probe's Linux job unexpectedly had 5 failed, 4043 passed,
  10 skipped in 306.23s on Python 3.11.17. Four ANSI-sensitive CLI assertions
  reproduced with `GITHUB_ACTIONS=true CI=true`; adding `TERM=dumb` made
  all four pass. A missing-command `rg` stub reproduced the fifth inventory
  failure. All five passed together with plain output and real ripgrep
  (5 passed in 5.01s) before the final rebase. The full local and
  hosted Linux runs at `a327a1792` below supersede those diagnostic runs.
- First hosted validation at head `a327a1792a09cb777d3cf10617608f6a7b806425`,
  base `b7aeba3f2b40c31083eae6d2286f14061efae200`:
  [Linux](https://github.com/FastJVM/coga/actions/runs/40029431893/job/120673709066)
  passed (4048 passed, 10 skipped, 387.03s, Python 3.11.17), while
  [Windows](https://github.com/FastJVM/coga/actions/runs/40029431893/job/120673708864)
  had 228 failed, 3728 passed, 102 skipped in 3409.40s on Python 3.11.9.
  All reported exception results shared the cross-drive `ValueError` in
  `refresh_agent_skill_view`: package skills on D:, temporary repos on C:.
  Local full-suite receipt at that head/base: 4048 passed, 10 skipped in
  382.42s, Python 3.11.15, using the final-local command above.
- Cross-drive regression command:
  `/tmp/coga-windows-ci-peer-yo9wanrn/python311/bin/python3.11 -m pytest tests/test_init.py::test_agent_skill_view_links_bundled_skills_on_another_drive -q`
  reproduced the original ValueError before the fix (1 failed in 0.60s).
  Afterward `.../python3.11 -m pytest tests/test_init.py -k 'agent_skill_view or link_skills' -q`
  passed (5 passed, 142 deselected in 0.28s).
- Full Python 3.11.15 suite with `GITHUB_ACTIONS=true CI=true TERM=dumb`
  passed (4049 passed, 10 skipped in 380.61s) on the code tree committed as
  `3ec31d8fe` over base `9a66f93dc331634fd822e0d1c7f8d4409c793400`.
  The final control-only rebase moved that receipt's commit identity; the new
  full suite on the final head passed separately, without re-stamping this result.


---

## Blockers

- [x] [2026-10-22 11:50] [agent:claude] id=20261022T115057 Merge windows-native/01-core-port-cli-and-test-suite-pass-on-native-window before starting this CI ticket. It is still at owner-held review-design, and main retains unconditional POSIX-only imports that prevent the Windows test job from passing.
  resolved: [2026-10-23 13:55] [human:nicktoper] Predecessor windows-native/01 merged via PR #1093 (merge commit 5132aa6ac) after conflict resolution; origin/main no longer has module-level fcntl/termios/tty imports, so the CI ticket can proceed.

---

## Blocker reminders

- 9f1f52929c3a last_reminded: 2026-10-23 10:25

## PR

```yaml
title: Run pytest on Linux and Windows for PRs and main pushes
author: claude/codex
author_evidence: Claude (claude-opus-5-5, attended implement session) authored the initial workflow and
  testing topic. Codex authored owner-approved corrections for concurrency, runner setup, and cross-drive
  generated skill links, including their regression test and documentation.
head: 3cb85786bda42ecb30f2d31b88cc536ff2e16b62
base: 6b413aea74f7001a8e3f58023393af521001190a
depth: deep
rationale: Direct re-review completed after control-only rebases; all four feature patches are unchanged.
  Reviewer-authored corrections were self-reviewed. Both hosted jobs passed at the recorded earlier head/base;
  their entire code, docs, workflow, and test tree matches the final head. The full local suite passed
  on the final head. The actual feature PR still needs its own checks before owner merge.
implementation: Adds pull-request and main-push pytest jobs on ubuntu-latest and windows-latest with Python
  3.11 and the documented editable test-extra install. Fixes generated skill links when the installed
  package and repository are on different Windows drives, retaining relative links where possible. Documents
  both behaviors.
deviations: Adds PR-only cancellation and unique main-push groups, Linux ripgrep, and TERM=dumb. Hosted
  Windows exposed a cross-drive ValueError, so the owner approved the small application fix, regression
  test, and skill-management topic/twin update. No existing tests or skip rules were weakened.
limitations: 'Hosted Ubuntu and Windows verification passed on 8f0fcab9d against 05596b689. Final head
  3cb85786b differs only in ticket/log state; hosted receipts retain their original scope. Its local suite
  passed: 4049 passed, 10 skipped. The feature PR needs its own two green jobs before owner merge. Interactive
  launch remains an EC2 check, and coga validate is not part of CI. The required deliberate regression
  was detected in [scratch run 40028184483](https://github.com/FastJVM/coga/actions/runs/40028184483),
  [Windows job](https://github.com/FastJVM/coga/actions/runs/40028184483/job/120669536523): Python 3.11.9,
  35 expected fcntl import errors. Scratch PRs #1094 and #1095 are closed and their branches deleted;
  the negative result applies to scratch commit 696ec4ebf5c7da1d20a26e8449907ada239b9f5a, not this feature
  head.'
files:
  .github/workflows/test.yml: Run the complete Python 3.11 suite on Linux and Windows for PRs and main
    pushes, with correct concurrency and the environment required by existing tests.
  docs/contexts/coga-dev/testing/SKILL.md: Replace the obsolete no-CI decision and document platform/floor
    coverage, runner requirements, and continued step verification; this development topic stays local-only.
  docs/contexts/coga/skill-management/SKILL.md: Document relative skill links with absolute targets across
    Windows drives and the machine-local generated view.
  src/coga/agent_skills.py: Prevent launch/init failures when bundled skills and the repository are on
    different Windows drives by falling back to an absolute link target.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/skill-management/SKILL.md: Keep the shipped
    skill-management topic byte-identical to its canonical source.
  tests/test_init.py: Reproduce cross-drive relpath failure and verify readable bundled skills, preserved
    relative local links, and repeated refreshes.
review:
  reviewer: codex
  kind: self
  status: passed
  head: 3cb85786bda42ecb30f2d31b88cc536ff2e16b62
  base: 6b413aea74f7001a8e3f58023393af521001190a
  detail: Direct re-review completed on all six final diff paths after control-only rebases; all four
    feature patches are unchanged. Codex independently reviewed Claude's implementation, then authored
    and self-reviewed four owner-approved corrections. No fully independent review of reviewer-authored
    changes is claimed. No unresolved code findings; both hosted jobs passed at their recorded earlier
    revision. The final full local suite passed after the last rebase.
checks:
- command: GITHUB_ACTIONS=true CI=true TERM=dumb /tmp/coga-windows-ci-peer-yo9wanrn/python311/bin/python3.11
    -m pytest
  status: passed
  head: 3cb85786bda42ecb30f2d31b88cc536ff2e16b62
  base: 6b413aea74f7001a8e3f58023393af521001190a
  detail: 'Linux, Python 3.11.15: 4049 passed, 10 skipped in 370.19s. Final rebased head; isolated base-interpreter
    copy with the documented editable test-extra install.'
- command: python -m pytest
  status: passed
  head: 8f0fcab9d39a1bdcb4b8789d7a104a7401078995
  base: 05596b689f01e62ccb5118465aac79f0ecebebb6
  detail: 'Hosted ubuntu-latest, Python 3.11.17: 4049 passed, 10 skipped in 394.21s. Pre-rebase head 8f0fcab9d
    in [validation PR #1095](https://github.com/FastJVM/coga/pull/1095); [Linux job](https://github.com/FastJVM/coga/actions/runs/40039260714/job/120706206829).'
- command: python -m pytest
  status: passed
  head: 8f0fcab9d39a1bdcb4b8789d7a104a7401078995
  base: 05596b689f01e62ccb5118465aac79f0ecebebb6
  detail: 'Hosted windows-latest, Python 3.11.9: 3957 passed, 102 skipped in 4770.02s. Pre-rebase head
    8f0fcab9d in [validation PR #1095](https://github.com/FastJVM/coga/pull/1095); [Windows job](https://github.com/FastJVM/coga/actions/runs/40039260714/job/120706207080).'
- command: git diff --check origin/main...HEAD
  status: passed
  head: 3cb85786bda42ecb30f2d31b88cc536ff2e16b62
  base: 6b413aea74f7001a8e3f58023393af521001190a
  detail: No whitespace errors in the final six-path feature diff.
- command: /tmp/coga-windows-ci-peer-yo9wanrn/actionlint .github/workflows/test.yml
  status: passed
  head: 3cb85786bda42ecb30f2d31b88cc536ff2e16b62
  base: 6b413aea74f7001a8e3f58023393af521001190a
  detail: Actionlint 1.7.11; no diagnostics.
- command: .venv/bin/python -m coga.cli validate --task windows-native/02-pr-ci-with-linux-and-windows-test-jobs
    --json
  status: passed
  head: 3cb85786bda42ecb30f2d31b88cc536ff2e16b62
  base: 6b413aea74f7001a8e3f58023393af521001190a
  detail: 'ok_count: 1; no issues or fixes.'
- command: python -m pytest
  status: not-run
  detail: The actual feature PR is opened by the following mechanical step; its own Ubuntu and Windows
    checks remain required before owner merge.
```
