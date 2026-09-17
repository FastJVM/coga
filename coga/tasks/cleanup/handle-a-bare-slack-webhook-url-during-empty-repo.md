---
title: Handle a bare SLACK_WEBHOOK_URL during empty-repo init
status: in_progress
owner: nicktoper
agent: claude
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
launch_generation: e916d4af-e084-4042-be6f-d5ee55073298
---

## Description

`coga init` in an empty git repo crashes with a `ConfigError` traceback when
a bare `SLACK_WEBHOOK_URL` is set in the environment. The existing-project init
path handles the same condition with a friendly tip, so the two paths should
agree.

## Context

**Reproduction** (audit, 2026-09-02, check 2 row h): export
`SLACK_WEBHOOK_URL` (any value), `git init` an empty directory, run
`coga init --user tester`. The empty-repo path — the one that seeds
`coga/tasks/coga-build.md` and prints "Run `coga build`" — raises a
`ConfigError` traceback instead of the tip the existing-project path prints
for the identical environment.

**Scope.** Small: find where the existing-project path handles it and apply
the same handling to the empty-repo path, with a test covering both. Edge
case — it only bites someone who already has that variable exported — but a
traceback on the very first command is the worst possible first impression,
and the fix is a few lines.

Source: `marketing/phase-0-audit` step 1 (2026-09-02), triaged by the owner
in step 2 (2026-09-03). This directory holds the work the owner wants done
before the marketing materials ship.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: init-bare-slack-env
worktree: /home/n/Code/claude/coga-init-bare-slack-env

## Findings

- Crash site: `src/coga/commands/init.py` in `_do_init`, the `is_empty` branch
  calls `load_config(coga_os)` solely to hand `logfile.append_log` a `Config`
  for the seeded `coga-build` audit line. The filled-repo path never loads
  config, which is the only reason it "handles" the bare env: it never asks.
- Raise site: `config._resolve_notification_slack_webhook` — a deliberate
  migration guard ("Bare `SLACK_WEBHOOK_URL` is no longer supported") that the
  `coga/sync` context documents as a config-load contract. Not to be loosened.
- Init's atomic rollback already works: the repro leaves no `coga/` behind.

## Implement — what changed (commit 240e6434 on `init-bare-slack-env`)

- `src/coga/commands/init.py`: new `_load_scaffolded_config(coga_os)` pops
  `SLACK_WEBHOOK_URL` from `os.environ` around init's single `load_config`
  call and restores it in `finally`; `_do_init` uses it for the `append_log`
  argument. `Config` is imported for the annotation. The guard in
  `config._resolve_notification_slack_webhook` is untouched.
- `tests/test_init.py`: `test_init_tolerates_bare_slack_webhook_env_on_both_paths`,
  parametrized `empty-repo` / `filled-repo`. Asserts exit 0, no guard text in
  output, the shared opt-in tip, the seeded/pruned `coga-build.md` and log
  line per path, the env var still exported afterwards, and that a plain
  `load_config(target / "coga")` still raises the guard. Failed before the fix
  on `empty-repo` only, matching the audit row.
- `coga/contexts/coga/sync/SKILL.md` + packaged twin under
  `templates/coga/bootstrap/`: one paragraph in "Notifications optional on
  first run" naming init's tolerance and pointing at the helper. Byte-identical.

Decision: hide the variable for one read rather than add a path-based
`append_log`/`log_path` variant (two new shared-infra entry points for one
consumer) or loosen the guard (a documented config-load contract).

Verification: `python -m pytest` in the worktree — 2563 passed. Manual repro
(`git init` empty dir, `SLACK_WEBHOOK_URL=… coga init --user tester`) now
exits 0, prints the tip, seeds `coga-build.md`, writes the log line, commits.
Rebased onto `origin/main` at 4d8734b8 (task/log commits only, no src/tests
diff); touched modules re-run green. No push, no PR.

Adjacent, not fixed: the tip says "Coga runs without them", but with the bare
variable still exported the very next command (`coga status`) exits 2 with the
guard message — a clean error, not a traceback. Pre-existing on both paths;
the wording could say "unset it or declare it before your next command".

## Peer review

- `codex review --base main` **returned**, exit 0: no actionable regressions.
  The reviewer confirmed the init-only scope and environment restoration;
  its 260 targeted init, config, and packaging tests passed. No fixes or
  additional feature commit needed.
- Ran `git fetch origin main` then `git rebase FETCH_HEAD` in the recorded
  feature worktree. Rebase was conflict-free onto `e291585d`; the feature
  commit is now `cb66863f`, one commit ahead. Only task/log state arrived from
  main, so the reviewed product diff is unchanged. `git diff --check
  origin/main...HEAD` passed and the worktree is clean.
- Drove the real CLI in a PTY at **80x24 and 120x40**, with a dummy bare
  `SLACK_WEBHOOK_URL`, for both empty Git repos and repos containing a README
  (four runs). Used the repo's Python 3.12 test environment with the feature
  source pinned via absolute `PYTHONPATH`. Every init exited 0, printed the
  common opt-in tip without a traceback, committed generated state, and
  seeded/pruned the onboarding ticket and audit line appropriately. Each
  subsequent `status` exited 2 with the intentional bare-env guard and no
  traceback. Fixtures: `/tmp/coga-init-peer-review-372ljezn/`.
  Optional managed-skill downloads emitted network warnings in this sandbox;
  they did not prevent init or obscure its final tip. An initial attempt with
  the ambient Python lacked `tomlkit`; the test environment resolved that.
- Post-rebase full suite **passed: 2563 tests**, exit 0 (253.96s):
  `PYTHONPATH=/home/n/Code/claude/coga-init-bare-slack-env/src /home/n/Code/claude/coga/.venv/bin/python -m pytest`.
  One warning: the sandbox could not write the optional pytest cache in the
  feature worktree. No tests failed or were skipped.

## PR

Fix `coga init --user tester` crashing in an empty Git repository when
`SLACK_WEBHOOK_URL` is already exported. Ignore the variable only while
reading the freshly scaffolded config for the onboarding audit entry, then
restore it so both init paths print the existing opt-in tip and later commands
retain the config-load guard.

Add regression coverage for empty and filled repositories and document the
exception in the live and packaged `coga/sync` contexts.

Test plan: `PYTHONPATH=/home/n/Code/claude/coga-init-bare-slack-env/src /home/n/Code/claude/coga/.venv/bin/python -m pytest` — 2563 passed; real-terminal init checks for both repository paths at 80x24 and 120x40 passed.
