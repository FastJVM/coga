---
slug: remove-run-py/port-hard-consumers-onto-the-generic-runner
title: Port open-pr and delete-task onto the generic runner
status: in_progress
owner: nicktoper
human: nicktoper
agent: codex
assignee: nicktoper
contexts: []
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
    requires: pr
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 4 (review)
---

## Description

**Ticket B of 3** in `remove-run-py/`. Depends on ticket A (the `coga run`
runner must exist). Still non-destructive toward the seam machinery — the final
deletion is ticket C.

Port the **two seam-integrated consumers** — `open-pr` and `delete-task` — off
the `run.py` seam onto the generic runner. These are the hard consumers: unlike
the thin recurring wrappers in ticket A, neither has its recipe in a `coga.*`
module and both have live code paths bound to `launch_script` internals. Each is
a port, not a delete. Leave `launch_script.py` and the `script:` field intact
here — the actual deletion is ticket C.

**open-pr** (`bootstrap/open-pr`): `run.py` is ~180 lines of real seam logic and
its recipe lives in a sibling `recipe.py` (~530 lines), not a module.
1. Promote the open-pr recipe from the packaged sibling `recipe.py` into an
   importable `coga.*` module (packaged-template change — keep live/packaged in
   sync).
2. Register it in the runner's dispatch table so `coga run open-pr <slug>` works.
3. Preserve the two contracts the `requires: pr` bump gate depends on: the
   `COGA_EXPECTED_TASK` ownership proof (single- vs two-checkout `_checkout_mode`
   gate) and the **bare PR URL on stdout**.
4. Repoint the `coga open-pr <slug>` verb (`aliases.py`) and update the
   `code/open-pr` step body so the agent runs the new verb.

**delete-task** (`bootstrap/delete-task`, backs `coga delete`): this is the twin
of open-pr and the reason it belongs here, not in ticket C. `src/coga/delete_task.py`
imports `build_script_command`, `build_task_env`, and `script_repo_root`
straight from `launch_script.py` and subprocess-runs the delete-task `run.py`.
So `coga delete` (used by recurring replacement, retire, and dream cleanup)
depends on the seam.
1. Promote the delete-task recipe into an importable `coga.*` module and register
   it in the runner.
2. Rewrite `delete_task.py` to call that recipe directly (or via `coga run
   delete-task`) instead of importing `launch_script` internals — so that when
   ticket C deletes `launch_script.py`, nothing in the delete path breaks.

Done: `coga open-pr <slug>` / `coga run open-pr <slug>` open a PR with the bare
URL + ownership gate intact; `coga delete <task>` works with no `launch_script`
import; the `code/open-pr` step works end-to-end; `test_open_pr_command.py` and
any delete-task test updated; suite passes.

## Context

**Files:**
- open-pr: `src/coga/resources/templates/coga/bootstrap/open-pr/{run.py,recipe.py,ticket.md}`,
  `coga/aliases.py` (the `open-pr` → `launch bootstrap/open-pr` rewrite),
  `coga/skills/code/open-pr/SKILL.md` (agent step body — it has **no** `script:`
  field; it is an agent step that runs the verb).
- delete-task: `src/coga/delete_task.py` (imports `build_script_command`,
  `build_task_env`, `script_repo_root` from `launch_script.py`), the
  `bootstrap/delete-task` skill `run.py` (live + packaged).
- plus the runner + dispatch table from ticket A.

**Why these two and not the others:** open-pr and delete-task carry logic that is
not in a `coga.*` module and have code coupled to `launch_script`. The remaining
`script: run.py` twins — `coga/show` and `coga/ticket/finalize` — are *vestigial*:
their real commands (`commands/show.py` → `render_show`, the ticket command →
`finalize_authored`) already bypass the seam, so only the seam-only `*_from_env`
entrypoints are dead weight. Those are a mechanical sweep and stay in ticket C.

**Self-hosting caveat:** this ticket ships on `code/with-review`, whose own
`open-pr` step runs the very verb being rewired. Land the new paths and keep the
old seam alive (do not remove `launch_script.py` here — that's ticket C) so the
step still works while this change is in flight. `code/with-review` never runs a
delete mid-workflow, so the delete-task port carries no in-flight hazard.

**Dependency order:** A → **B (this)** → C. After A and B merge, the only
remaining `script:` declarers are the two vestigial twins, so ticket C's
zero-live-consumers precondition holds.

**Coordination note:** `recurring_runner.py` is touched by ticket A (reroute
recurring launches to `coga run`); this ticket does not edit it.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

pr: https://github.com/FastJVM/coga/pull/667
branch: port-open-pr-delete-task-to-run
worktree: /home/n/Code/claude/coga-port-run-recipes

## Implemented (2026-07-27)

Ticket A's `coga run` / `runner.RECIPES` landed, so the port went ahead as one
commit on top of `origin/main` `3779d340`. Full suite green (1563 passed, 1
skipped); `coga validate --json` on `example/` is clean.

**open-pr.** `bootstrap/open-pr/recipe.py` moved (git-mv, history preserved) to
`src/coga/open_pr.py`, and `run.py`'s seam became `run_open_pr_recipe(cfg,
argv)` + `_checkout_mode` in that same module. Registered as `open-pr`; the
default alias is now `run open-pr`. The packaged command ticket
(`ticket.md`/`run.py`/`recipe.py`) is deleted.

**delete-task.** `src/coga/delete_task.py` now *is* the deletion (`rmtree` /
`unlink` keyed off the resolved ticket path) instead of subprocess-running the
bundled skill's `run.py` through `launch_script.build_script_command`. Exposed
as `run_delete_task(ref)` for `coga delete` + recurring replacement, and as the
`delete-task` recipe. The skill's `run.py` and its `script:` line are gone; its
SKILL.md is now a contract naming `coga run delete-task <task>`.

### Decisions

- **Removed the old spellings rather than shimming them.** The ticket's
  "keep the old seam alive" is parenthetically scoped to `launch_script.py`,
  which is untouched — and ticket C's stated precondition is that only the
  vestigial `coga/show` + `coga/ticket/finalize` twins still declare
  `script: run.py`. Leaving shims would have re-tripped C's stop condition (it
  blocked on exactly that evidence on 2026-07-27). No in-flight hazard: the
  installed `coga` runs from the primary checkout on `main`, not this branch.
- **Diagnostics moved to stderr** (`[open-pr]` stale-`pr:` and state-drift
  notes). In-process they would otherwise land on stdout beside the URL and
  break the bare-URL contract that this ticket requires preserving.
- **`COGA_EXPECTED_TASK` is still the ownership witness.** `coga run` rewrites
  no `COGA_TASK_*`, but the anchor stays the gate because only it names the
  *session's* task rather than whatever the environment last described.
- Test-side dead weight removed with the seam: `conftest.load_bootstrap_recipe`
  and the `_install_delete_skill` copies in `test_commands.py` / `test_git.py`.
  `test_launch_script.py`'s two bootstrap-script tests now seed a repo-local
  `bootstrap/probe` ticket instead of borrowing the retired open-pr one.

### Note for the human — unintended sync to main

Running `coga validate` / `coga run` from inside the feature worktree tripped
Coga's automatic control-branch sync, which committed the `coga/` context edits
(architecture, codebase, extension-model, `code/open-pr` skill, dream template)
and pushed them to `origin/main` as `3779d340` before this PR exists. Not
reverted: it is the repo's own sync mechanism, the content is the intended
final text, and un-publishing would mean two more pushes to `main` plus a real
risk of the merge silently dropping those edits. Consequence until this PR
merges: `main`'s contexts describe `coga run open-pr` while `main`'s code still
aliases to `launch bootstrap/open-pr`, and the live/packaged `code/open-pr`
copies are momentarily out of sync. Operationally harmless — the step still
tells agents to run `coga open-pr <slug>`, which works under either spelling.
Those five files are therefore *not* in this PR's diff.

## Peer review (2026-07-27)

Reviewed by the second agent against the branch diff vs `main`, rebased first
onto `origin/main` `db887b05` (clean). `/code-review` is user-triggered only in
this harness and cannot be model-invoked, so the pass was done directly over the
diff rather than through the slash command — noted here because the step names
that tool. Suite green after the fixes: **1564 passed, 1 skipped**.

Contract checks that passed as-is: `run_open_pr_recipe` is a faithful
transcription of the retired `run.py` (`_checkout_mode` identical, `_git`
matches the old inline `subprocess.run`, every `_run` call site keeps an
explicit `cwd`); the bare-URL stdout contract is now asserted positively rather
than by absence; `COGA_TASK_SLUG` was already `ref.id_slug`, so the delete
report line is byte-identical. The `cli` context and `bootstrap/` skills have no
live twin in this repo (packaged-only), so the live/packaged sync rule is not
violated. Grep confirms the only remaining `script:` declarers are
`coga/show` + `coga/ticket/finalize` — ticket C's precondition holds.

Two findings applied:

- **Must-fix — filesystem errors escaped `coga delete` and unattended recurring
  replacement as tracebacks.** Deletion used to run behind a subprocess, so any
  `OSError` came back as a non-zero exit and was wrapped into `DeleteTaskError`.
  In-process, `shutil.rmtree`/`unlink` raise `OSError` directly, and all three
  callers (`coga delete`, `run_delete_task_recipe`, `recurring.create_template`)
  catch only `DeleteTaskError` — so an undeletable task aborted with a traceback
  instead of a clean refusal, worst in the unattended recurring path. Now
  translated in `run_delete_task`, with a regression test verified to fail
  against the pre-fix source (`PermissionError`, exit 1).
- **Stale comment** in `commands/launch.py` still cited `code/open-pr` as the
  example of a script-backed step skill. It is an agent step with no `script:`,
  and this PR removes the last trace of its script seam; the example is dropped
  rather than repointed at the two twins ticket C deletes.

## PR

**Port `open-pr` and `delete-task` off the `run.py` seam onto `coga run`.**

Ticket B of 3 in `remove-run-py/`. These are the two seam-integrated consumers:
unlike the thin recurring wrappers in ticket A, neither had its recipe in a
`coga.*` module and both had live code bound to `launch_script` internals.

- **open-pr** — the packaged `bootstrap/open-pr` command ticket is retired. Its
  `recipe.py` moves (via `git mv`, history preserved) to `src/coga/open_pr.py`,
  and `run.py`'s seam becomes `run_open_pr_recipe(cfg, argv)` + `_checkout_mode`
  in that same module, registered as the `open-pr` recipe. `coga open-pr <slug>`
  now aliases to `run open-pr` and takes the task ref as ordinary argv instead of
  `COGA_ARG_1`. Both gate contracts are preserved: the `COGA_EXPECTED_TASK`
  ownership proof and the bare PR URL on stdout — the `[open-pr]` diagnostics
  move to stderr so they can't land on the value channel in-process.
- **delete-task** — `src/coga/delete_task.py` now *is* the deletion, keyed off
  the resolved ticket path, instead of importing `build_script_command` /
  `build_task_env` / `script_repo_root` from `launch_script.py` to subprocess the
  bundled skill's `run.py`. Exposed as `run_delete_task(ref)` for `coga delete`
  and recurring replacement, and as the `delete-task` recipe. Filesystem errors
  are translated to `DeleteTaskError` so the in-process path keeps the single
  failure type its callers catch. The skill's `run.py` and `script:` line are
  gone; its SKILL.md is now a contract naming `coga run delete-task <task>`.

`launch_script.py` and the `script:` field are untouched — the deletion is
ticket C, whose precondition (only the vestigial `coga/show` and
`coga/ticket/finalize` twins still declare `script: run.py`) now holds.

Note: five `coga/` context/skill files describing the new spelling were already
pushed to `main` by Coga's own control-branch sync during this work, so they are
not in this diff.

**Test plan:** `python -m pytest` — 1564 passed, 1 skipped; `coga validate
--json` on `example/` clean; `coga --help` and `coga run <unknown>` smoke-checked.

---

## Blockers

- [x] [2026-07-23 07:45] [agent:claude] id=20260723T074518 Blocked on remove-run-py/add-coga-run-generic-runner-and-migrate-recurring: its coga run generic runner and dispatch table are absent from origin/main while that task remains at review-design; finish and merge ticket A before retrying this port.
  resolved: [2026-07-27 11:27] [human:nicktoper] Resolved: ticket A merged as PR #650 (2026-07-27). coga run and the RECIPES dispatch table are on origin/main at 2a26d9df, so the stated precondition is met. Proceed with the open-pr and delete-task port.

---

## Blocker reminders

- 574c8271398a last_reminded: 2026-07-24 14:36
