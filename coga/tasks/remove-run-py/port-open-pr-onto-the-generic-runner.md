---
slug: remove-run-py/port-open-pr-onto-the-generic-runner
title: Port open-pr onto the generic runner
status: draft
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

Port the `open-pr` consumer off its `run.py` script onto the generic runner.
Unlike the recurring jobs, `open-pr` is **not** a thin wrapper: its `run.py` is
~180 lines carrying real seam logic, and its recipe lives in a sibling
`recipe.py`, not a `coga.*` module. So this is a port, not a delete:

1. Promote the open-pr recipe from the packaged sibling `recipe.py` into an
   importable `coga.*` module (a packaged-template change — keep live/packaged
   in sync).
2. Register it in the runner's dispatch table so `coga run open-pr <slug>` works.
3. Preserve the two contracts the `requires: pr` bump gate depends on: the
   `COGA_EXPECTED_TASK`-based ownership proof (the single- vs two-checkout
   `_checkout_mode` gate) and the **bare PR URL on stdout**.
4. Repoint the `coga open-pr <slug>` verb (`aliases.py`) and update the
   `code/open-pr` step body so the agent runs the new verb.

Done: `coga open-pr <slug>` and `coga run open-pr <slug>` both open a PR, emit
the bare URL, and enforce the ownership gate; the `code/open-pr` workflow step
works end-to-end; `test_open_pr_command.py` updated; suite passes.

## Context

**Files:** `src/coga/resources/templates/coga/bootstrap/open-pr/{run.py,recipe.py,ticket.md}`,
`coga/aliases.py` (the `open-pr` → `launch bootstrap/open-pr` rewrite),
`coga/skills/code/open-pr/SKILL.md` (agent step body — note it has **no**
`script:` field; it is an agent step that runs the verb), and the runner +
dispatch table added in ticket A.

**Why open-pr is the hard consumer:** `run.py` holds `_checkout_mode`,
`COGA_EXPECTED_TASK` ownership proof, and `_target_task_arg` — none of which are
in a `coga.*` module today. Do not treat this as a wrapper deletion; if the
ownership proof or bare-URL stdout regresses, the `requires: pr` gate silently
breaks.

**Self-hosting caveat:** this ticket ships on `code/with-review`, whose own
`open-pr` step runs the very verb being rewired. Land the new path and keep the
old seam alive (do not remove `launch_script.py` here — that's ticket C) so the
step still works while this change is in flight.

**Dependency order:** A → **B (this)** → C. Leave `launch_script.py`, the
`script:` field, and `is_script_launch` intact for ticket C.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
