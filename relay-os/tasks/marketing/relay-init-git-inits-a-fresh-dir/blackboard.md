## Dev
branch: init-requires-git-repo
worktree: ../relay-init-requires-git
pr: (not yet — opens in code/open-pr step)
commit: b1634512  "Fail loud when `relay init` target is not a git repo"

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
