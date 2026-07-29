---
slug: remove-run-py/delete-the-script-seam
title: Delete the script-seam
status: done
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

## Dev

pr: https://github.com/FastJVM/coga/pull/670
branch: delete-script-seam
worktree: /tmp/coga-delete-script-seam

## Already satisfied (2026-07-29 11:12)

Megalaunch re-picked this ticket **eight minutes after PR #670 merged**, from
the primary checkout `/home/n/Code/claude/coga`, which sits on branch
`slack-post-nonfatal-after-transition` — 75 commits behind `origin/main`. The
composed prompt was therefore built from a stale ticket copy (`step: 1
(implement)`, both asks still open) and from stale source that still contained
the seam. Nothing was re-implemented; the ticket file here was refreshed from
`origin/main` before closing.

Verified against `origin/main` (`216db444`; seam deleted in `755e60de`,
squash-merge of PR #670):

- `src/coga/commands/launch_script.py` — gone from the tree.
- `git grep -E 'launch_script|is_script_launch|run_script_mode|current_step_is_script|COGA_ARG|render_show_from_env|finalize_authored_from_env'`
  over `src/`, `tests/`, `docs/` — **zero** hits. The only survivors repo-wide
  are `coga/log.md` history and old ticket prose, which the ticket's Context
  explicitly puts out of scope.
- No `run.py` anywhere except `src/coga/commands/run.py` (the generic runner
  from ticket A). Both vestigial twins (`coga/show`, `coga/ticket/finalize`,
  live and packaged) are deleted.
- No `script: run.py` declaration remains in any `SKILL.md` or `ticket.md`.
- `tests/test_launch_script.py` is deleted; the remaining `*_script*` tests
  (`test_dream_skill_scripts.py`, `test_human_minutes_script.py`) are unrelated.

Workflow record: implement (`0b82f606`) → peer-review (`3f4cac7e`) → open-pr
(#670) → owner merged. Closing with `coga mark done`.

### Follow-up for the human — not fixed here

The primary checkout being 75 commits behind `main` affects the **whole**
megalaunch run, not just this ticket: `coga/log.md` in this checkout is also
stale, so any control-branch sync from here risks writing an old log over
`main`'s. Only this ticket's file was reconciled.

## PR

Delete the launch-integrated script seam. With the generic `coga run` recipe
registry (ticket A) and the open-pr / delete-task ports (ticket B) both landed,
nothing live still dispatches through `script:`, so this removes the mechanism
itself: `commands/launch_script.py`, the `script` field across the ticket, skill,
create, and validation models, the `is_script_launch` / `run_script_mode`
branching in launch, megalaunch, and recurring, and the `COGA_ARG_*` / `COGA_ARGC`
environment plumbing. The two vestigial `run.py` twins (`coga/show`,
`coga/ticket/finalize`) and their seam-only entrypoints (`render_show_from_env`,
`finalize_authored_from_env`) go with it; the real `render_show` and
`finalize_authored` stay and remain wired to their commands. No `run.py` and no
`script:` declaration remains under either the live `coga/` tree or the packaged
templates.

Existing repositories migrate on read: `Ticket.parse` treats a leftover
`script: null` as an absent key, and a non-null leftover survives as an inert
orphan-extension warning rather than a validation error. Architecture, sync, CLI,
and recurring contexts (live and packaged twins), the skill template, product
docs, and the seeded example are updated to describe recipes instead of script
mode.

Test plan: `python -m pytest` (1532 passed, 1 skipped), seeded `example/`
`coga validate --json` clean (ok_count 2, no issues), plus `coga status` /
`coga show` / `--help` smoke checks.

## Peer review (2026-07-29)

Reviewed the branch diff vs `main` with two independent reviewers — one on
production-code correctness, one on live/packaged doc-twin sync and test
coverage. Fixes landed as `3f4cac7e` (`peer-review: apply review findings`):

- **Real defect:** `views.py` lost `from typing import Mapping` along with the
  deleted `render_show_from_env`, but `_terminal_hint(hidden: Mapping[str, int])`
  still referenced it. `from __future__ import annotations` hid it at runtime, so
  it only surfaced under annotation evaluation (`typing.get_type_hints`, autodoc)
  and as a pyflakes/ruff F821. Re-imported from `collections.abc`; verified
  `get_type_hints` now resolves.
- **Dead import / formatting:** dropped the now-unused `load_config` in
  `authoring.py` and restored the blank lines the deletion collapsed.
- **Doc sweep the implementation commit missed** (all stale prose describing the
  deleted mechanism): the skill template's bundled-scripts guidance (live +
  packaged), the packaged CLI context's `recurring promote` passthrough list
  (still advertised `script`, which `_TEMPLATE_PASSTHROUGH` no longer carries),
  the `requires:` gate's "agent- or script-owned" wording (both architecture
  twins), and the README, `docs/vision.md`, `docs/market-thesis.md`,
  `docs/README.md`, and both `docs/cli-extension-*.md` files.
- **Coverage gap:** added `test_validate_tolerates_legacy_non_null_script_key`
  for the `script: run.py` leftover case the ticket's migration requirement names
  but nothing exercised — only the `script: null` path was tested.

Confirmed not defects: no reachable reader of the deleted symbols remains
anywhere in `src/` (grep over `launch_script`, `is_script_launch`,
`run_script_mode`, `current_step_is_script`, `COGA_ARG*`); every live/packaged
twin I touched diffs identical; the unused `os` / `subprocess` imports in
`commands/launch.py` are pre-existing on `main`, not introduced here, so they are
left alone. Deferred as nits: the `coga/scripts/` candidate shape in
`docs/cli-extension-external-surface.md` still proposes launch-called script
targets, and `recurring.py` silently ignores a legacy `script:` key on a template
without a diagnostic.

Rebased onto `origin/main` at `666525a0`; branch is clean, two commits ahead,
unpushed.

## Implementation (2026-07-28)

- Commit `0b82f606` (`Delete the launch script seam`) removes
  `commands/launch_script.py`, all launch/megalaunch/recurring script
  dispatch and argument-environment plumbing, and the `script` field from the
  ticket/skill/create/validation models. `Ticket.parse` strips a legacy
  explicit `script: null`, so existing repositories migrate on read without a
  validation error.
- Deleted the live and packaged `coga/show` and `coga/ticket/finalize`
  executable twins and their seam-only Python entrypoints. No launch-entrypoint
  `run.py` remains under either live `coga/` or packaged Coga templates.
- Updated the live and packaged architecture/sync contracts, CLI and authoring
  templates, recurring/Dream guidance, product docs, seeded example, and
  affected tests. Agent command tickets remain agent-backed; stable headless
  behavior is now exclusively a registered `coga run` recipe.
- Verification on the committed branch:
  - `python -m pytest -q`: `1531 passed, 1 skipped`.
  - Seeded example `coga validate --json`: `ok_count: 2`, no issues.
  - CLI help smoke check, `git diff --check`, legacy-symbol grep, and live /
    packaged `run.py` scan all pass.
  - Repository-wide validation reports the same unrelated pre-existing
    `v2/*` missing-step / unsynthesized-draft errors on both this branch and
    `main`; the behavior-changing example fixture validates cleanly.
- Final fetch found `origin/main` at `c163b7c5`; the required rebase was a
  no-op. The feature checkout is clean and unpushed, with no PR opened.

## Dependency check (2026-07-23)

- Ticket A, `remove-run-py/add-coga-run-generic-runner-and-migrate-recurring`,
  is still at `review-design`; ticket B,
  `remove-run-py/port-hard-consumers-onto-the-generic-runner`, is still
  `active`.
- The destructive precondition is not met: 18 live or packaged `run.py` files
  remain, including recurring jobs, open-pr, and delete-task. There are 19
  live/package `script:` declarations (including instantiated recurring
  tickets with `script: null`), rather than only the two vestigial show/finalize
  twins.
- `src/coga/delete_task.py` still imports `coga.commands.launch_script`, and
  recurring launch code still calls `is_script_launch`. Deleting the seam now
  would break live consumers.
- Decision: do not create a branch or edit implementation files. Retry C only
  after A and B are completed and merged.

## Dependency re-check (2026-07-27)

Re-ran the precondition against a freshly fetched `origin/main` (`3a7eabe3`,
identical to this checkout). The blocker is **half-resolved**:

- **Ticket A is clear.** `remove-run-py/add-coga-run-generic-runner-and-migrate-recurring`
  is `status: done` (merged as PR #650). `coga run` and `runner.RECIPES` are on
  `main`; the recurring jobs no longer own `run.py` files.
- **Ticket B is not.** `remove-run-py/port-hard-consumers-onto-the-generic-runner`
  is still `status: active`. Its own blocker was cleared by the human at
  2026-07-27 11:27 ("proceed with the open-pr and delete-task port"), but the
  port itself has not been written yet — no commit on `main` touches it.
- Concrete evidence that B's two hard consumers are still bound to the seam:
  - `src/coga/delete_task.py:8` still does
    `from coga.commands.launch_script import build_script_command`, still
    requires `skill.script` in frontmatter, and still subprocess-runs
    `skills/bootstrap/delete-task/run.py`.
  - `src/coga/resources/templates/coga/bootstrap/open-pr/` still ships
    `run.py` + `ticket.md` with `script: run.py`, reading its target from
    `COGA_ARG_1` / `COGA_ARGC`.
- The rest of C's precondition *is* met: the only other live `script:` skills
  are the two vestigial twins `coga/show` and `coga/ticket/finalize`, exactly
  as the ticket predicts.

Deleting `launch_script.py` now would break `coga delete` at import time and
strand the packaged `open-pr` command. Decision: re-block on B alone, naming
its path-qualified slug so megalaunch retries C automatically once B lands.
No branch or worktree created; no implementation files touched.

---

## Blockers

- [x] [2026-07-23 07:43] [agent:claude] id=20260723T074319 Precondition failed: remove-run-py/add-coga-run-generic-runner-and-migrate-recurring is still at review-design and remove-run-py/port-hard-consumers-onto-the-generic-runner is still active; live recurring, open-pr, and delete-task script consumers remain. Complete and merge A, then B, before retrying C.
  resolved: [2026-07-28 17:16] [human:nicktoper] Resolved: ticket A merged as PR #650 and ticket B's implementation merged as PR #667 at f6522603. Current origin/main contains the generic runner plus the open-pr and delete-task ports; src/coga/delete_task.py no longer imports launch_script, the packaged open-pr seam is gone, and the only remaining live or packaged run.py plus script: run.py declarers are the vestigial coga/show and coga/ticket/finalize twins. B's ticket is still at its final review bookkeeping step, but its code dependency is fully landed, so C's destructive precondition is met.

- [x] [2026-07-27 14:59] [agent:codex] id=20260727T145920 Precondition still unmet: remove-run-py/port-hard-consumers-onto-the-generic-runner (ticket B) is still status:active and its port has not landed on origin/main (3a7eabe3). Ticket A is now done, so half the original blocker is cleared. But src/coga/delete_task.py:8 still imports build_script_command from coga.commands.launch_script and subprocess-runs skills/bootstrap/delete-task/run.py, and src/coga/resources/templates/coga/bootstrap/open-pr/ still ships run.py + ticket.md with 'script: run.py' reading COGA_ARG_1/COGA_ARGC. Deleting launch_script.py now would break 'coga delete' at import time and strand the packaged open-pr command. Everything else C needs is ready: the only other live script: skills are the two vestigial twins coga/show and coga/ticket/finalize. Land ticket B, then retry C.
  resolved: [2026-07-28 17:16] [human:nicktoper] Resolved: ticket A merged as PR #650 and ticket B's implementation merged as PR #667 at f6522603. Current origin/main contains the generic runner plus the open-pr and delete-task ports; src/coga/delete_task.py no longer imports launch_script, the packaged open-pr seam is gone, and the only remaining live or packaged run.py plus script: run.py declarers are the vestigial coga/show and coga/ticket/finalize twins. B's ticket is still at its final review bookkeeping step, but its code dependency is fully landed, so C's destructive precondition is met.


---

## Blocker reminders

- 28e5bc0cbdb5 last_reminded: 2026-07-24 14:36
