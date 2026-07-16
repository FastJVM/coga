---
slug: install/warn-loud-when-init-commit-is-skipped
title: Warn loud when init commit is skipped
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: codex
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
step: 2 (peer-review)
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
branch: init-identity-fail-loud
worktree: /home/n/Code/claude/coga-init-identity

## Implemented (implement step, done)

Commit 28820914 "Fail loud when coga init cannot commit coga/" on the branch
above, rebased onto origin/main 517ccd35. The ticket offered two routes
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

## Usage

{"agent":"claude","cache_creation_input_tokens":246170,"cache_read_input_tokens":8919528,"cli":"claude","input_tokens":194,"model":"claude-fable-5","output_tokens":106521,"provider":"anthropic","schema":1,"session_id":"d4e40e9e-d192-412c-a9f4-bb4d055010c5","slug":"install/warn-loud-when-init-commit-is-skipped","step":"implement","title":"Warn loud when init commit is skipped","ts":"2026-07-16T01:22:25.537056Z","usage_status":"ok"}
