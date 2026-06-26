---
slug: marketing/relay-init-git-inits-a-fresh-dir
title: relay init git-inits a fresh dir
status: done
autonomy: interactive
owner: zach
human: zach
agent: claude
assignee: zach
contexts:
- dev/code
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
---

## Description

When `relay init`'s target isn't already a git repo, `_git_commit_relay_os`
returns early and silently skips committing `relay-os/` — no error, no warning —
leaving a git-backed tool untracked and half-set-up. Close the silent skip by
**failing loud** (principle 6): report that the target isn't a git repo and that
the user must run `git init` before re-running, instead of committing nothing in
silence. Do **not** auto-run `git init` — the README already directs users to
`git init` first, and letting the user run it keeps branch naming in their hands
(the `main`/`master` reconciliation is out of scope here, owned by
`fresh-repo-default-branch-mismatch-git-init-master`). Surfaced by the
fresh-directory onboarding path (`marketing/readme-and-docs`).

## Context

- The silent skip lives in `src/relay/commands/init.py` — `_git_commit_relay_os`
  returns early when `target/.git` is absent (`init.py:921`), so `relay-os/` is
  never committed and no "Committed relay-os/" line prints.
- The README's documented path runs `git init` before `relay init`
  (`README.md:42-44`), so this fires only when the user skips that step — the fix
  is a fail-loud guardrail, not a change to the happy path.
- **Decision (with zach): fail loud = hard error / non-zero exit, not a
  warning.** A warning that still exits 0 reads as advisory and is a
  failure-that-returns-success, which principle 6 forbids; the non-zero exit is
  what makes running `git init` non-optional. The message names the missing git
  repo and tells the user to run `git init` here, then re-run `relay init`.
- Note: `relay init` writes `relay-os/` to disk *before* `_git_commit_relay_os`
  runs, so a hard error at the commit step leaves `relay-os/` on disk (harmless —
  re-running after `git init` commits it). Checking git-repo-ness earlier, so a
  failed run leaves nothing behind, is optional and at the implementing agent's
  discretion.

<!-- coga:blackboard -->

## Dev
branch: init-requires-git-repo
worktree: ../relay-init-requires-git
pr: https://github.com/FastJVM/relay/pull/422
ci: no checks configured on this repo (`gh pr checks` reports none) — nothing to wait on
commit: b1634512  "Fail loud when `relay init` target is not a git repo"
commit: 1055a13d  "self-qa: share `_is_git_repo` predicate between init guard and commit step"

## Self-QA
Ran `/code-review` (default effort) and `/simplify` against the branch diff vs main.
- `/code-review`: no findings. Verified the guard handles `.git` as file or dir,
  is placed before any disk writes / clone / venv, doesn't touch the
  `--update`/`--all` paths, and that the bare-`.git` `_make_git_repo` test helper
  is safe (`_git_commit_relay_os` swallows the resulting git error; `.git` is in
  `_INIT_IGNORE` so it doesn't flip `_repo_is_empty`). No stale docs beyond the
  README already fixed.
- `/simplify`: one fix applied — the new guard's `(target/".git").exists()` was
  byte-identical to the skip condition in `_git_commit_relay_os`, and the guard's
  correctness depends on the two matching. Extracted a shared `_is_git_repo(target)`
  predicate so both reference one definition and can't drift. Reviewed reuse /
  simplification / efficiency / altitude; nothing else worth changing.
- Tests: full `python -m pytest` = 838 passed, 1 pre-existing skip. No
  `relay validate` needed (init-time guardrail, validation behavior unchanged).

## Implemented (code committed, not pushed)
- `src/relay/commands/init.py`: precondition in `_do_init` after `--user`
  validation, before `target.mkdir()`/clone/venv — hard error (exit 2, RED
  stderr) when `(target/.git)` is absent, naming the dir + `git init` remediation.
  `_git_commit_relay_os` left intact (defensive; contract unchanged).
- `README.md`: command reference no longer says "if PATH is a git repo" — init
  now requires one (run `git init` first).
- `tests/test_init.py`: added `_make_git_repo(target)` helper; applied to the 17
  successful-init tests; rewrote `test_init_skips_commit_when_target_is_not_git_repo`
  → `test_init_fails_loud_when_target_is_not_git_repo`; rewrote
  `test_init_creates_missing_dir` → `test_init_into_missing_dir_errors_not_git_repo`;
  deleted `test_init_skips_host_gitignore_when_not_git_repo` (premise gone;
  `ensure_host_gitignore` still has its own unit tests).
- Verified: full `python -m pytest` = 838 passed, 1 pre-existing skip.
  No `example/` fixture change needed (init-time guardrail, not task layout).

## Plan (approved 2026-06-22)
Close the silent skip in `_do_init` (`src/relay/commands/init.py`) by failing
loud when the target isn't a git repo, instead of writing `relay-os/` and
skipping the commit.

- Guard placed after `name = _require_user_name(user)`, before `target.mkdir()`
  / clone / venv. Fails before any disk writes ("a bad invocation leaves nothing
  on disk") and before the slow clone/venv. `sys.exit(2)`, RED stderr message
  naming the target + telling the user to `git init` there and re-run.
- Detection mirrors the existing silent-skip condition exactly
  (`(target / ".git").exists()`), so every previously-silent case now errors and
  the happy path is unchanged. `_git_commit_relay_os`'s own internal `.git`
  guard is left intact (defensive; its docstring contract stays honest).

## Decisions
- Placement = early (before writes), not at the commit step — ticket left it to
  discretion; early matches the existing design + better UX. Confirmed w/ Zach.
- Git check runs AFTER `--user` validation so arg-validation errors fire first
  (keeps `test_init_without_user_errors` / `test_init_rejects_invalid_user`
  unaffected).
- `relay init <missing-dir>` now ERRORS (a missing dir can't be a git repo) —
  retires the auto-create-dir convenience. This is the ticket's core "fresh dir"
  case. Flagged to Zach; approved.
- Do NOT auto-run `git init` (per ticket; keeps branch naming with the user).
- `main`/`master` reconciliation is out of scope (owned by
  `fresh-repo-default-branch-mismatch-git-init-master`).

## Tests (tests/test_init.py)
- Add `_make_git_repo(target)` helper; apply to the ~16 successful-init tests
  (bare `.git` dir clears the filesystem check; `.git` is ignored by the
  empty/filled onboarding classification, per
  `test_init_filled_repo_ignores_relay_managed_files`).
- Rewrite `test_init_skips_commit_when_target_is_not_git_repo` → fail-loud
  (exit 2 + message + `relay-os/` not created).
- Rewrite `test_init_creates_missing_dir` → missing dir errors, nothing written.
- Delete `test_init_skips_host_gitignore_when_not_git_repo` (premise gone;
  `ensure_host_gitignore` still has its own unit tests).
- No `example/` fixture change (init-time guardrail, not task layout).
