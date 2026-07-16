---
slug: install/init-does-not-persist-user-then-blocks-on-reinit
title: relay init doesn't persist user on first run, then wedges on re-init
status: done
owner: zach
human: zach
agent: claude
assignee: claude
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
---

## Description

Greg's first `relay init` failed partway without persisting his `user`. Re-running
`relay init` then reported the directory was already initialized and recommended
`--update`, but `--update` complained the user wasn't set — leaving him wedged
between "already initialized" and "user missing" with no clear path forward. Make
first-run user capture atomic/recoverable (or let `--update` set a missing user),
so a partially-failed init isn't a dead end requiring manual config editing.

## Context

Reported by Greg. The partial failure was triggered by the pip hash-checking
issue (`install/pip-hash-requirement-breaks-editable-install`). Related in-flight
init hardening: `marketing/relay-init-git-inits-a-fresh-dir` (fail loud when the
target isn't a git repo) and `fresh-repo-default-branch-mismatch-git-init-master`.
Name capture itself is `relay-init-captures-name-via-user-param` (done). Init code
is in `src/relay/commands/` (init) and `src/relay/config.py`.

<!-- coga:blackboard -->

## Already satisfied

Every arm of the ask has already landed on main; there is no diff to make.

1. **Partial init can no longer strand a half-built repo (the wedge itself).**
   PR #449 (`a1044363`, 2026-06-25, "init: roll back a partial relay-os/ on
   failure (fixes the re-init wedge)") wrapped the whole init body in
   `try/except BaseException` → `shutil.rmtree(coga_os)` → re-raise
   (`src/coga/commands/init.py:432-482`). Any failure after `coga/` is created —
   including the `sys.exit(2)` path Greg hit when pip failed in `install_venv`,
   and Ctrl-C — removes the partial `coga/`, so re-running `coga init` starts
   clean instead of hitting "already exists" over a missing `user`. The
   regression test `test_failed_init_rolls_back_partial_coga_os`
   (`tests/test_init.py:513`) cites this ticket's slug in its docstring and
   covers both a normal exception and KeyboardInterrupt.

2. **User capture is atomic — validated before any writes.**
   `_require_user_name` runs before the clone/venv/template work
   (`src/coga/commands/init.py:379`), so a missing/invalid `--user` exits with
   nothing on disk, and `coga.local.toml` with the `user` line is written inside
   the rollback-protected block. (Name capture via `--user` itself was
   `relay-init-captures-name-via-user-param`, already done per this ticket's
   context.)

3. **The `--update` arm is moot.** `coga init --update` was removed entirely in
   PR #461 (`03fd0c37`). The "already exists" refusal
   (`src/coga/commands/init.py:353-359`) no longer recommends `--update`, and
   the missing-user config error (`src/coga/config.py:304-311`) points at
   `coga init --user <name>` / adding `user = "..."` to `coga.local.toml` —
   which with rollback in place can only be reached from a *complete* init or a
   teammate's clone, not a partial first run.

Verification: `python3.12 -m pytest tests/test_init.py -q` — 94 passed
(includes the rollback regression test and the user-capture tests).

Adjacent finding (not fixed here, per scope rules): `src/coga/cli.py:321` has a
stale comment still describing "`coga init` (fresh or `--update`)" — `--update`
was removed in #461. One-line comment cleanup for a follow-up or drive-by.
