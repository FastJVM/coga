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
step: 2 (peer-review)
launch_generation: 7ab37cdc-0dc3-43fa-ab3c-b8e173f599a5
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
