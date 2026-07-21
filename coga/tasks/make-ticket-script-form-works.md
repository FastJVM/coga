---
slug: make-ticket-script-form-works
title: make ticket script form works
status: done
owner: nicktoper
human: nicktoper
agent: claude
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

Extend the `bootstrap/ticket` interview skill so it can author **script-backed
tickets**. The launch runtime already fully supports them — `script: inline` (a
fenced block in a `## Script` body section, kept as a single-file task) and
`script: <file>` (a sibling script file in directory form) both resolve and run
today. What's missing is an *authoring path*: `coga create` exposes only title
and workflow, and this interview never asks about scripts, so the only thing
that currently produces a script ticket is recurring templates.

Add an interview step that asks whether the ticket should run a script and, if
so, helps author it: choose **inline vs sibling-file** by the script's
size/nature, set the `script:` frontmatter accordingly, and write the
`## Script` block (inline) or create the sibling script file and convert the
draft to directory form (sibling). Done = running `coga ticket` on a new title
can produce a valid script ticket that `coga launch` then executes as a script.

## Context

**Scope:** interview skill only. We are *not* adding a `coga create --script`
CLI flag — the interview agent edits ticket files directly, so it doesn't need
one. A CLI flag, if ever wanted, is a separate ticket.

**Edit target (source of truth):**
`src/coga/resources/templates/coga/bootstrap/skills/bootstrap/ticket/SKILL.md`.
This skill is a bundled battery — there is **no** live `coga/skills/bootstrap/
ticket/` copy to keep in sync. The `.venv/.../coga/resources/...` copy is an
install mirror; do not edit it.

**Runtime contract to target (already implemented — do not change it):**
- `script:` is three-way (`src/coga/ticket.py:137`, `Ticket.script`):
  `inline` → fenced block in the body's `## Script` section, task stays a single
  `tasks/<slug>.md` file; a filename (`run.sh`, `run.py`) → sibling file in a
  `tasks/<slug>/` directory next to `ticket.md`; `null`/absent → agent task.
- Resolution + dispatch live in `src/coga/commands/launch_script.py`
  (`is_script_launch`, `_resolve_ticket_script`, `_resolve_inline_script`).
- `create.py:145` (`needs_dir`) already branches: an inline script keeps
  file-form, a named script file forces directory-form. `create_task()` accepts
  a `script` arg; the interview agent can mirror that logic by editing files.
- Script command selection (`build_script_command`, launch_script.py:108): a
  `.py` runs under the active interpreter, an executable file runs directly,
  else `sh`. The inline `## Script` fence language should reflect this.

**Inline case needs a new section:** `coga/tasks/_template/ticket.md` has **no
`## Script` section** today, so the skill must instruct the agent to add one to
the body (above the blackboard fence) — that's exactly where
`_resolve_inline_script` reads the fenced block from.

**Directory-conversion subtlety (sibling-file path is the fiddly one):** a draft
scaffolded as a bare `tasks/<slug>.md` must be moved to `tasks/<slug>/ticket.md`
with the script as a sibling when the human picks a sibling-file script. Inline
scripts need no move. Because the interview agent hand-edits files (it does not
reuse `create_task`'s directory logic — that would need the deferred CLI flag),
arm the skill with these safety nets:
- Run `coga validate` after the conversion to catch a malformed move.
- Executable-bit: `build_script_command` runs `.py` under the interpreter and a
  non-executable file under `sh`. A bare `run` file with no extension needs
  `chmod +x` (or it won't dispatch as intended) — call this out.
- The `slug:` frontmatter does **not** change on the bare-file → directory move
  (the id_slug is the leaf either way), so tell the agent not to "fix" it.

**Fit the existing interview shape:** fold this into the current steps (around
the step-3 workflow / step-5 context questions) rather than bolting on a heavy
new phase — the interview is meant to stay short (4–6 questions). Only ask about
scripts when the task actually looks script-shaped.

<!-- coga:blackboard -->

## Already satisfied

This ticket's work already landed on `origin/main` as PR #601 "make ticket
script form works" (commit `1ed07f23`, merged 2026-07-20, including a
"peer-review: apply review findings" pass). This launch started from a stale
local `main` (81f061ff) that predates the merge — discovered while rebasing a
freshly built feature branch, which duplicated the merged change and was then
deleted (worktree removed; no branch/PR needed).

Per-item evidence, all in `1ed07f23`'s version of
`src/coga/resources/templates/coga/bootstrap/skills/bootstrap/ticket/SKILL.md`:

- Conditional interview question: step 3 item 5 "Script execution
  (conditional)" — asked only when the task looks script-shaped; inline vs
  sibling chosen by the script's size/nature.
- `script:` frontmatter set for both forms; agent tasks keep `script: null`.
- Inline: "### Script-backed ticket layout" instructs adding a `## Script`
  section above the `<!-- coga:blackboard -->` fence with one fenced block,
  and documents the `python`/`sh`/`bash` fence-language dispatch.
- Sibling file: bare `tasks/<slug>.md` → `tasks/<slug>/ticket.md` conversion
  with the script beside it; explicit "the frontmatter `slug:` does not change
  when the file moves; do not 'fix' it".
- Safety nets: `chmod +x` for extensionless shebang scripts (dispatch
  semantics spelled out), `coga validate --task <slug>` after the conversion,
  plus a `test -f` check on the sibling script.
- Workflow interplay: requires a one-step, ungated workflow for a
  ticket-level `script:` (suggests `direct/body`); multi-step workflows are
  steered to script-backed step skills instead.
- Beyond the skill text, the PR also updated `src/coga/authoring.py` and
  added `tests/test_bootstrap_ticket_skill_template.py` +
  `tests/test_authoring.py` assertions, so the done-criterion (a `coga
  ticket` interview can produce a valid script ticket that `coga launch`
  executes) is covered with tests.

Note for the owner: this checkout's `main` has diverged from `origin/main`
(merge-base `9022450f`) — local state commits only, none of the recently
merged PRs. Worth a sync so future launches don't start from pre-#601 state.

## Dream Skill: validate-drift

Generated: 2026-07-21T01:21:36+00:00
Command: `coga validate --json --fix`
Task: `make-ticket-script-form-works`

Applied fixes: 1.

- `x`: `missing-file` - created log.md (`coga/tasks/x/log.md`)

Git: committed and pushed `repair-branch`

Result: no remaining validation drift found.

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

pr: https://github.com/FastJVM/coga/pull/601
branch: ticket-script-authoring
worktree: /tmp/coga-ticket-script-authoring-review.C9RLEb

## Plan

- Add a conditional execution-shape question to the existing short interview.
- Document inline and sibling-file authoring, layout conversion, dispatch, and validation in the packaged skill.
- Add a focused contract test, run the suite, commit, and freshen against `origin/main`.

## Implementation

- Added a conditional script-execution question between workflow selection and context attachment; ordinary agent tasks do not get an extra question.
- Documented `script: inline`, the body `## Script` fence, and flat-file preservation.
- Documented sibling filenames, bare-file to directory conversion, unchanged `slug:`, dispatch permissions, and post-move task validation.
- Added script layout/dispatch to evaluator review and the final human summary.
- Extended the existing bundled ticket-skill contract test.

## Verification

- Focused authoring/runtime/create tests after peer-review fixes: 73 passed.
- Full suite after the confirmed live `origin/main` rebase: 1324 passed, 1 skipped (wheel-build check; `hatchling` is unavailable).
- `PYTHONPATH=src python3.12 -m coga.cli validate --task make-ticket-script-form-works --json`: 1 valid task, no issues.
- Commits `d40b8edc` (`Teach ticket interview to author scripts`) and `8b91daf8` (`peer-review: apply review findings`) are clean and two commits ahead of the locally verified control tip `3f37bba9`.

## Follow-up

- Running the full suite inside a live Coga launch exposed an unrelated test-isolation bug: `tests/test_dream_validate_drift.py::test_commit_and_push_main_passes_configured_remote` inherited `COGA_TASK_BLACKBOARD` and appended its fake report to this ticket. All injected fixture sections from the implementation and peer-review test runs were removed; the test should clear or replace launch metadata in a separate ticket.

## Peer review

- Native `codex review --base main` found that ticket-owned scripts must use a compatible one-step workflow; otherwise the ticket-level `script:` fallback runs again on every later workflow step, including human gates.
- Promoting a flat draft to directory form leaves guided authoring's original `TaskRef` stale, causing finalization to mistake the moved ticket for a deletion and skip validation/git sync. The authoring finalizer needs to re-resolve the same task ref after the move.
- `coga validate --task` validates the task shape but does not resolve the declared script. The interview must pair task validation with an explicit script-resolution check instead of claiming validation alone proves the script is runnable.
- These are direct acceptance-path fixes: keep ticket-owned launch dispatch unchanged, require a one-step workflow in the interview, repair guided-authoring re-resolution, and add focused regressions.
- The linked feature worktree's git metadata is read-only in this launch, so the reviewed changes were carried into the independent clone above; rebased review-fix commit: `8b91daf8` (`peer-review: apply review findings`).
- The first `git fetch origin main` attempt hit a transient DNS failure. A later retry succeeded against GitHub, confirmed live `origin/main` at `3f37bba9`, and `git rebase FETCH_HEAD` reported the already-locally-rebased branch up to date; the full suite passed again afterward.

## PR

Summary:
- Teach the guided ticket interview to conditionally author inline or sibling-file script tickets, including layout, interpreter, permission, evaluator, and handoff guidance.
- Keep ticket-owned scripts on one-step ungated workflows and make guided authoring safely validate and git-sync a flat ticket promoted to directory form.

Test plan: `PYTHONPATH=/tmp/coga-ticket-script-authoring-review.C9RLEb/src python3.12 -m pytest` (1324 passed, 1 skipped), plus task-scoped `coga validate`.
