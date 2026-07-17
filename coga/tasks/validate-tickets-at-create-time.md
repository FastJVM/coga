---
slug: validate-tickets-at-create-time
title: Validate tickets at create time
status: active
owner: nicktoper
human: nicktoper
agent: codex
assignee: codex
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
script: null
step: 1 (implement)
---

## Description

Every Coga-owned command that writes a ticket must run the task-scoped
validation check (`assert_task_valid`, i.e. `coga validate --task <slug>`
semantics) at its write boundary and fail loudly — before reporting success —
if the ticket it just wrote is malformed. Today only `bump` and `mark` do
this; `create`/`create_task`, the `coga ticket` authoring exit, launch-time
transitions, and the recurring/retire scaffolding write tickets unchecked, so
a malformed ticket (bad frontmatter, broken refs, missing fence) sits
undetected until someone happens to run a full `coga validate` by hand. Add
the check to the missing commands and bring the `coga/cli` context's claims
in line with the final behavior.

## Context

Reported by nicktoper (2026-07-09): tickets created during the retest session
were only checked when a full `coga validate` was run by hand, which is how
the legacy install/ schema drift went unnoticed.

Audit (2026-07-16, verified against source):

- **Already validate at their write boundary:** `bump`
  (`src/coga/bump.py:103`, plus the workflow-freeze check in
  `src/coga/commands/bump.py:102`) and all `mark` transitions
  (`src/coga/mark.py` — done/active/in_progress/blocked/paused). Both call
  `assert_task_valid` from `src/coga/validate.py:306`. Launch-time
  transitions (`src/coga/commands/launch.py`, `launch_script.py`) mutate
  tickets only via those `mark_*` functions, so they are transitively
  covered — don't add redundant checks there.
- **Missing the check:** `create_task` in `src/coga/create.py:26` (which
  `coga create`, the recurring scaffold at `src/coga/recurring.py:637`, and
  retire scaffolding all funnel through — one check there covers all three)
  and the `coga ticket` authoring exit (`src/coga/commands/ticket.py`).
  Note the ticket-authoring writes happen inside the spawned session, so the
  real write boundary there is session exit — validate then, and pin what
  failure looks like after the session has already ended (report the issues
  and leave the draft on disk).
- **Context drift:** the bundled `coga/cli` context
  (`src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md`,
  around line 796) claims ticket-authoring exit, launch-time transitions, and
  recurring/retire creation already run the check (they don't), and says raw
  `coga create` "intentionally only scaffolds a draft" — owner decision on
  this ticket: create validates too; a fresh scaffold must be valid by
  construction, and a failure there is a Coga bug worth failing loudly on.
  Update that context wording to match the implemented behavior. There is no
  live-repo copy under `coga/contexts/coga/cli/` — only the packaged one.

Decisions pinned so the implementer doesn't guess:

- On validation failure: fail loudly with the formatted issues
  (`TaskValidationError` / `format_task_issues`) and **leave the file on
  disk** for the human to fix — no rollback. The check is read-only.
- Reuse `assert_task_valid(cfg, ref, action=...)` with a per-command action
  label, matching the existing `bump`/`mark` call sites. Don't invent a new
  validation path.
- First implementation step: confirm a bare freshly-scaffolded draft passes
  `validate_task` clean. The old context wording ("intentionally only
  scaffolds a draft") suggests someone once decided otherwise — if a fresh
  scaffold doesn't validate, fix the scaffold or the schema before wiring
  the check into `create_task`, or `coga create` breaks itself.
- Out of scope: validating human hand-edits (that stays `coga validate
  --task <slug>` run manually), and any repo-wide validation changes.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Production notes

### Evaluator review (pre-launch authoring record)

**1. Description clarity** — Good. States the invariant, names the mechanism (`assert_task_valid`), lists covered vs. missing call sites, and pins failure semantics (fail loud, no rollback, reuse existing path). An agent could start cold.

**2. Workflow fit** — `code/with-review` fits: a multi-file code change with tests and a doc update, ending in a PR. No mismatch.

**3. Contexts** — `dev/code` is right for any branch/PR-producing ticket. Consider also attaching `coga/codebase` (source layout, live-vs-packaged template sync rule) since the ticket edits a packaged context under `src/coga/resources/templates/`; minor, the ticket already flags there is no live copy (verified: `coga/contexts/coga/` has no `cli/`).

**4. Context-vs-inline** — No problem. `dev/code` is narrow (blackboard `## Dev` conventions), and every load-bearing fact (call sites, decisions, out-of-scope) is already copied into `## Context`.

**5. Scope** — Reasonable for one ticket, and likely *smaller* than it reads: `coga create`, recurring, and retire all funnel through the single `create_task` function, so one check there covers three of the listed gaps. Doc update belongs in the same PR per CLAUDE.md.

**6. Assumptions to question (audit spot-check):**
- **Verified correct:** `bump.py:103`, `commands/bump.py:102`, all five `mark.py` transitions, `assert_task_valid` at `validate.py:306`, and the packaged cli context's claims around line 796 read as described.
- **Wrong path:** `create_task` lives in `src/coga/create.py`, not `src/coga/tasks.py`. Likewise the recurring scaffold call is `src/coga/recurring.py:637`, not `src/coga/commands/recurring.py` (which contains no writes).
- **Likely false gap — launch:** `launch.py` and `launch_script.py` mutate tickets exclusively via `mark_active`/`mark_in_progress`/`mark_blocked`/`mark_done`, all of which already call `assert_task_valid`. Launch-time transitions appear transitively covered; the "context drift" claim about launch is therefore also partly wrong. Re-verify before adding redundant checks.
- **Unexamined risk:** the owner decision that raw `coga create` validates assumes a fresh draft scaffold passes task-scoped validation. The old context wording ("intentionally only scaffolds a draft") hints someone once decided otherwise — confirm a bare draft validates clean before wiring the check in, or `create` breaks itself.
- **Fuzzy boundary:** `coga ticket`'s writes happen inside the spawned authoring session, not in `ticket.py`; the "write boundary" there is really session exit, and failure semantics after the session has ended should be pinned down.

*(Authoring note: the wrong-path, launch-transitive-coverage, fresh-scaffold-risk, and session-exit-boundary findings have been folded into `## Context` above.)*
