---
slug: validate-tickets-at-create-time
title: Validate tickets at create time
status: in_progress
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
step: 3 (open-pr)
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

## Dev

branch: validate-ticket-create
worktree: /tmp/coga-validate-ticket-create

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

## Implementation notes

- Live-source recheck on 2026-07-16 found that both requested boundaries
  already run equivalent task-scoped checks, but through duplicated
  `validate_task_dir` / error-filtering code: `create_task` raises `ValueError`
  after writing and `validate_authored_task` raises `AuthoringError` after the
  authoring session exits. The remaining implementation gap is to route both
  through the required `assert_task_valid` contract and pin its action labels,
  not to add a second validation pass.
- Fresh-scaffold baseline passed:
  `tests/test_create.py::test_create_minimal` and the existing ticket
  post-exit validation regression both pass on `main`. A raw draft already
  returns only after its generated ticket passes task-scoped validation.
- Proposed scope: standardize the two checks, preserve clean command-level
  error reporting and the malformed file on disk, add focused regression
  coverage, update the packaged `coga/cli` wording, and leave launch-time
  transitions alone because `mark_*` already covers them.

### Implemented

- Commit `a8df64a5` on `validate-ticket-create` replaces the duplicated create
  and authoring validators with `assert_task_valid`, using action labels
  `create` and `ticket authoring`. Raw create, recurring, retire, interactive
  ticket authoring, and the script-backed authoring finalizer now surface the
  shared formatted failure cleanly while leaving the written ticket in place.
- The packaged `coga/cli` context now states that all `create_task` paths and
  guided authoring validate at their write boundary; direct human edits remain
  a manual `coga validate --task <slug>` responsibility. Launch received no
  redundant check because its mutations already route through `mark_*`.
- Verification: affected modules `74 passed`; recurring module `112 passed`;
  full suite `1273 passed, 1 skipped`; example fixture
  `coga validate --json` reported `ok_count: 1` with no issues or fixes.
- Final `git fetch origin main && git rebase FETCH_HEAD` reported the branch
  up to date at `fd67a069`; the feature worktree is clean and one commit ahead.

### Peer review (2026-07-16, reviewer agent)

Ran `/code-review` (default effort) against the branch diff vs main:
8 finder angles, each surviving candidate independently verified.

Must-fix findings, applied in commit `42bf21c3`
(`peer-review: apply review findings`):

- **Live/packaged skill drift (confirmed):** the implement step updated the
  packaged finalize skill but missed the live copy
  `coga/skills/coga/ticket/finalize/run.py`, which still caught only
  `AuthoringError` — a `TaskValidationError` from a guided `coga ticket`
  session in *this* repo would have escaped as a raw traceback (exit 1)
  instead of the `[ticket-finalize]` message (exit 2). Synced the live copy
  per CLAUDE.md's live/packaged sync rule.
- **Recurring except too narrow (confirmed, pre-existing escape):** the new
  `except TaskValidationError` in `_create_at_slug` left create_task's plain
  `ValueError` modes (unknown contexts, slug collision, ...) crashing the
  whole recurring sweep past scan_due's per-template `except RecurringError`.
  Widened to `(TaskValidationError, ValueError)` and added a regression test.
- **Doc drift (confirmed):** `docs/cli-extension-audit.md` still said
  create/draft does no validation; updated the row to match the new behavior.

Skipped as nits/design (recorded for a future ticket, not this PR):
re-parenting `TaskValidationError` onto `ValueError` (verified safe by grep
today, but it touches ~15 pre-existing catch sites — separate decision);
the last hand-rolled validate/format copy in `commands/project.py:138`;
an exact-string assertion in `tests/test_recurring.py`. Refuted claims:
sweep-2 adoption of a retained malformed task is caught loudly at launch by
`mark_in_progress`; the `--force` path crash is pre-existing, not new.

Verification after fixes + unconditional rebase onto origin/main
(`fd67a069..f601bc24`): full suite `1274 passed, 1 skipped` (via
`PYTHONPATH=src python3.12 -m pytest`; the bare `python` here is 3.9 and one
launch-script test needs coga importable in a spawned process — environment,
not code). Branch is clean, two commits ahead of main.

## PR

Validate tickets at their create-time write boundaries.

Every Coga-owned command that writes a ticket now runs the shared task-scoped
check (`assert_task_valid`) before reporting success. `create_task` (covering
`coga create`, recurring scaffolds, and retire) and the `coga ticket`
authoring exit previously did this through duplicated hand-rolled
`validate_task_dir` blocks raising `ValueError`/`AuthoringError`; both now
route through `assert_task_valid` with action labels `create` and
`ticket authoring`, matching the existing `bump`/`mark` call sites. On
failure the command reports the formatted issues, exits 2, and leaves the
written ticket on disk for correction. Launch-time transitions needed no
change — they already validate via `mark_*`. The recurring sweep now converts
create-time failures (validation and plain `ValueError`) into per-template
skip-and-report instead of aborting the whole sweep. The packaged `coga/cli`
context, its live finalize-skill sibling, and `docs/cli-extension-audit.md`
are updated to match.

Test plan: `python -m pytest` (1274 passed, 1 skipped), including new
regression tests for create/retire/recurring/authoring failure reporting;
`coga validate --json` on the example fixture reports no issues.
