# Blackboard — github-auth-preflight-and-setup-docs

## Plan (implement step)

Add an opt-in `relay validate --check-github` preflight mirroring `--check-slack`.

1. New module `src/relay/github_preflight.py` — owns subprocess probes, returns
   structured `CheckResult` records:
   - `git remote get-url <cfg.git_remote>` (remote configured)
   - `git ls-remote --heads <remote>` (reachability/auth, non-interactive:
     `GIT_TERMINAL_PROMPT=0` + ssh `BatchMode=yes` so it can't hang on a prompt)
   - `gh --version` (installed)
   - `gh auth status` (authenticated)
   Reachability runs only if the remote exists; gh-auth only if gh is installed.
2. `src/relay/validate.py` — `check_github` param on `run()`, `_github_issues(cfg)`
   mapper (task label `(github)`), exclude `(github)` from ok_count, argparse flag.
3. `src/relay/commands/validate.py` — `--check-github` flag + `--task` guard.
4. Tests in `tests/test_validate.py` — mock subprocess.run: missing remote,
   missing gh, unauth'd gh, success, and default path makes no subprocess call.
5. README "External CLI Tools" — document the preflight, non-`origin` remote,
   SSH vs HTTPS, `gh auth login`.
6. Skills `code/open-pr` + `code/implement-and-pr` — probe `gh auth status`
   before push; on failure write blackboard blocker + `relay panic`.

## Decisions

- Reachability/auth probe failure = `error` severity (confirmed with nick).
  Message enumerates causes (offline / SSH key not loaded / credential helper /
  HTTPS creds) since the probe can't distinguish them. Matches ticket's
  "treat not online as a failed explicit check with a useful message".
- Keep the standard-tool boundary: no PAT store, no GITHUB_TOKEN read, no OAuth.
- `code/` skills are project-local only (no packaged template copy to sync).

## Dev
branch: github-preflight
worktree: /home/n/Code/claude/relay-github-preflight
commit: 97652bf

## Implement step — done

All acceptance criteria addressed:
- `relay validate --check-github` added (opt-in, mirrors `--check-slack`),
  wired into Typer command + argparse module entry, with `--task` guard.
- Probes live in new `src/relay/github_preflight.py`: git remote configured
  (`git remote get-url <cfg.git_remote>`), remote reachable/authed
  (non-interactive `git ls-remote`, `GIT_TERMINAL_PROMPT=0` + ssh BatchMode),
  `gh` installed, `gh` authenticated. Uses cfg.git_remote, not hardcoded origin.
- Failed probes → `(github)` error issues; excluded from ok_count.
- README "External CLI Tools" → new "Git/GitHub auth readiness" subsection.
- `code/open-pr` + `code/implement-and-pr` skills probe auth before push and
  blackboard + panic on failure (no packaged copy to sync — project-local).
- Tests: missing remote / missing gh / unauth gh / success + default-path
  no-subprocess proof. Full suite green (780 passed).
- No PAT store / GITHUB_TOKEN / OAuth introduced.

Verified: `python -m relay.validate --check-github` runs probes (this machine
is ready → no github issues); `--task ... --check-github` exits 2 (guard).

Test runner note: the dev python is 3.9 (too old; relay needs 3.11+). Ran with
the shim venv: `PYTHONPATH=$PWD/src /home/n/Code/relay/relay-os/.relay/.venv/bin/python -m pytest`.

Notes for reviewer / next steps:
- Reachability probe failure is `error` severity (decided with nick): an
  offline machine fails the explicit check with a message enumerating causes.
- Example fixture untouched — change is a CLI flag + check, no task-layout /
  prompt-composition / workflow-semantics impact.
