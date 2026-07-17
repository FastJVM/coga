---
slug: install/warn-loud-when-init-commit-is-skipped
title: Warn loud when init commit is skipped
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts:
- dev/code
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
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

On a machine with no git identity (`user.email` unset — every truly fresh
machine), `coga init` reports full success but the "commit coga/" step
silently fails: `_git_commit_coga_os` swallows `CalledProcessError` and
returns None, so the "Committed coga/ as …" line is simply absent. Files sit
staged, and the user's first `coga create` then surfaces a raw
`fatal: ambiguous argument 'HEAD'` git error (no HEAD exists yet). This is a
fail-loud violation (principle 6). Fix: warn loudly when the commit is
skipped/fails, naming the cause and remedy (`git config user.email …`), or
check git identity up front next to the git/gh dependency check.

## Context

Found in the 2026-07-08 fresh-container retest: verified init exit 0 with
staged-but-uncommitted tree and no warning, then the raw `git rev-parse HEAD`
error on first `coga create`; with identity set the commit works. Touchpoint:
`src/coga/commands/init.py` (`_git_commit_coga_os`, its caller in `_do_init`,
and `_check_external_dependencies` if going the up-front-check route).

<!-- coga:blackboard -->

## Dev
pr: https://github.com/FastJVM/coga/pull/584
branch: init-identity-fail-loud
worktree: /home/n/Code/claude/coga-init-identity

## Implemented (implement step, done)

Commit 2e2b7166 "Fail loud when coga init cannot commit coga/" on the branch
above, rebased onto origin/main cd36a62f (2026-07-16 refresh; clean rebase,
suite re-run green: 1234 passed / 1 skipped). The ticket offered two routes
("warn at commit time" or "check identity up front"); did both, because they
cover different failure sets:

1. **Up-front identity check** — `_check_git_identity` in `_do_init`, next to
   the other fail-before-writes checks: probes `git var GIT_COMMITTER_IDENT`
   (fails exactly when `git commit` would refuse for identity reasons —
   honors config, GIT_* env vars, and git's hostname auto-detection). Exits 2
   with the `git config --global user.email/user.name` remedy, before the
   slow clone/venv, nothing written. Probes from the nearest existing
   ancestor so nested inits with a not-yet-existing target work.
2. **Loud warning when the commit itself fails** (backstop: failing hooks,
   odd repo state) — `_git_commit_coga_os` returns `(sha, error)` instead of
   swallowing `CalledProcessError`; `_do_init` prints a yellow warning with
   git's stderr and the manual `git -C … commit` remedy. "Nothing to stage"
   stays a quiet skip.

Decisions worth knowing for review:

- The test suite redirects HOME (autouse `_isolate_home`), so whether the
  identity probe passes would depend on the host's hostname. Added an autouse
  `_stub_init_identity_check` conftest fixture (mirrors
  `_stub_init_dep_check`); dedicated tests re-install the real check and
  force determinism with `user.useConfigOnly=true` + cleared GIT_*/EMAIL env.
- test_init.py's `_make_git_repo` fakes a repo with a bare empty `.git` dir,
  relying on the commit step silently no-oping. To keep that contract while
  making real failures loud, `_git_commit_coga_os` confirms the repo with
  `git rev-parse --git-dir` first and treats disagreement as the existing
  clean skip — unreachable in the product flow, which hard-fails on
  not-a-repo before any writes.

Verification: full suite 1211 passed / 1 skipped (python3.12 venv with the
worktree installed editable; `test_bootstrap_script_launch_is_stateless`
fails without an installed coga — pre-existing env artifact, fails on clean
main too, passes with the editable install). End-to-end: real `coga init` in
an identity-less repo exits 2 with the remedy and writes nothing.

## Peer review (2026-07-16)

Native `codex review --base main` found three recovery-guidance defects and a
second-pass identity defect; all must-fixes were applied in commit 3e271403:

- Commit/add failures no longer claim generated files are already staged.
  Recovery now prints shell-safe `git add` and `git commit` commands with the
  exact generated path set (`coga/`, `.gitignore`, `CLAUDE.md`, `AGENTS.md`).
- Failure reporting preserves the failed git phase and stderr, including
  errors from `git add` and the staged-change check rather than only commit.
- The up-front preflight probes both author and committer identity; Git
  resolves them separately, so a committer-only CI environment now fails
  before init writes anything.

The final native re-review reported no actionable regressions. Branch
`init-identity-fail-loud` is clean and rebased onto `origin/main` 5fa969ab;
current commits are eeca2c56 (implementation) and 3e271403 (peer-review fixes).
Final verification: `PYTHONPATH=/home/n/Code/claude/coga-init-identity/src
python -m pytest -q` — 1256 passed, 1 skipped. The two warnings were only
pytest cache writes denied by the read-only feature-worktree mount.

## PR

### Summary

- Fail before writes when Git cannot resolve either author or committer
  identity, with the standard `git config` remedy.
- Surface late init commit failures with Git's phase and stderr instead of
  silently leaving a staged, HEAD-less repository.
- Print complete, shell-safe stage-and-commit recovery commands for every
  path generated by init.

### Test plan

`PYTHONPATH=/home/n/Code/claude/coga-init-identity/src python -m pytest -q` — 1256 passed, 1 skipped.
