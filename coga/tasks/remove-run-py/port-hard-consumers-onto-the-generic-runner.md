---
slug: remove-run-py/port-hard-consumers-onto-the-generic-runner
title: Port open-pr and delete-task onto the generic runner
status: active
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
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
step: 1 (implement)
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
