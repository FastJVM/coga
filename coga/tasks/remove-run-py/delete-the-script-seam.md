---
slug: remove-run-py/delete-the-script-seam
title: Delete the script-seam
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

**Ticket C of 3** in `remove-run-py/`. The destructive one. Runs **only after
tickets A and B** merge. Precondition (verify, don't assume): after A migrated
the recurring jobs and B ported open-pr + delete-task, the *only* skills still
declaring `script: run.py` are the two vestigial twins `coga/show` and
`coga/ticket/finalize` — whose real commands (`commands/show.py` → `render_show`,
the ticket command → `finalize_authored`) already bypass the seam. No *live*
consumer should remain; if grep shows anything else still bound to the seam,
stop — a predecessor ticket is incomplete.

Delete the launch-integrated script-seam entirely:

- Remove the `script:` field from the ticket model and everywhere it is read:
  `launch.py`, `create.py`, `megalaunch.py`, `recurring.py`,
  `recurring_runner.py`, `skill.py`, `tasks.py`, `ticket.py`, `validate.py`,
  `views.py`. (Not `delete_task.py` — ticket B already weaned it off
  `launch_script`. Not `aliases.py`'s open-pr alias — B repointed it; only strip
  any leftover `COGA_ARG` comment/plumbing there.)
- Delete `src/coga/commands/launch_script.py` (~520 lines) and the
  `is_script_launch` / `current_step_is_script` / `run_script_mode` branching
  in `launch.py`, plus the `COGA_ARG_*` / `COGA_ARGC` env plumbing.
- Delete the two vestigial `run.py` twins (`coga/show`, `coga/ticket/finalize`)
  and their `script:` SKILL.md lines (live + packaged), plus their seam-only
  entrypoints: `render_show_from_env` in `views.py` and `finalize_authored_from_env`
  in `authoring.py`. Keep the real functions (`render_show`, `finalize_authored`).
- Sweep any other remaining `run.py` files / `script:` SKILL.md/ticket.md lines
  (live + packaged) as a final catch-all.
- Update docs: the seam section (~line 594) in
  `coga/contexts/coga/architecture/SKILL.md` and the reference in
  `coga/contexts/coga/sync/SKILL.md`, plus their packaged twins under
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/...`.

Done: no `run.py` and no `script:` concept remain anywhere; `coga delete`,
`coga show`, `coga ticket`, and the recurring jobs still work; `coga validate`
passes; the affected test files are updated and green.

## Context

**Model migration:** removing the `script:` field must not break existing
tickets that still carry an explicit `script: null` in frontmatter — tolerate or
strip a leftover `script:` key without a validation error.

**Tests to update:** `test_launch_script.py` (likely deleted), `test_launch.py`,
`test_launch_auto.py`, `test_commands.py`, `test_recurring.py`,
`test_autoclose_sweep.py`, `test_open_pr_command.py`.

**Out of scope:** the ~40 `run.py` mentions in old/done `coga/tasks/*.md` prose
are historical narrative — leave them; editing done tickets changes no behavior.

**Coordination note:** `recurring_runner.py` and `launch.py` are also edited by
ticket A (rerouting recurring launches to `coga run`); here you remove the
now-dead `is_script_launch` import/branching from them. Rebase on A before
starting so you edit the post-A version.

**Dependency order:** A → B → **C (this)**. This ticket assumes A and B are
merged; running it earlier would delete the seam out from under a live consumer
(`coga delete`, open-pr, or a recurring job).

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
