---
slug: always-accept-coga-ticket
title: always accept coga ticket
status: in_progress
owner: nick
human: nick
agent: claude
assignee: nick
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
    requires: pr
  - name: review
    skills: []
    assignee: owner
secrets: null
step: 4 (review)
---

## Description

`coga ticket <slug>` refuses to open a `blocked` ticket. `EDITABLE_STATUSES`
in `src/coga/commands/ticket.py` hardcodes six of the seven values in
`lifecycle.VALID_STATUSES`, omitting `blocked`, so the guard bails with a
misleading `unknown status 'blocked'; refusing guided ticket editing` — even
though revising the ticket is exactly how you resolve what blocked it.

Remove the status gate entirely rather than adding `blocked` to the list.
`coga ticket` runs no task work and moves no workflow: it opens an authoring
session over a markdown file the human already owns and can edit by hand.
Gating that on a `status:` value protects nothing and only creates a dead end.
Drop the informational `CAUTION_STATUSES` heads-up in the same pass — the
decision is that `coga ticket <slug>` opens any ticket, with no refusal and no
commentary.

Done looks like: `coga ticket <slug>` launches the authoring interview for a
ticket at **any** status, including `blocked` and an unrecognized/typo status,
printing nothing about the status. The command's own `--help` string
(`ticket.py:69`) already promises "Existing task slug to edit (any status)" —
this change makes that true rather than aspirational.

Note the scope boundary: what's being deleted is the **CLI's** unconditional
stdout/stderr commentary. The `bootstrap/ticket` skill's separate in-session
heads-up — where the interviewing agent notices it is revising a ticket
already in flight and confirms intent on a substantive change — is contextual
judgment, not a mechanical print, and it **stays** (extended to cover
`blocked`).

## Context

### Where the change goes

All the gate logic lives in one file, `src/coga/commands/ticket.py`:

- `EDITABLE_STATUSES` (line ~43) and `CAUTION_STATUSES` (line ~51) — both
  delete, along with the explanatory comment above them.
- `_resolve_existing()` (line ~166) — the only consumer. Its `_bail` on
  unknown status and its `typer.secho` caution block both go; what remains is
  `read_ticket(ref)` and `return ref, ticket, False`. Update its docstring,
  which currently describes "gating on its status" and "the same status guard
  and caution heads-up."

Nothing else in the codebase references either constant (verified by grep).
`_resolve_existing` has exactly two callers, both in `_resolve_or_create_target`
(lines ~149 and ~163). The one non-obvious near-caller is
`megalaunch._author_draft` (`src/coga/megalaunch.py:677`), which runs the same
authoring interview on picked drafts — but it imports `AUTHORING_KICKOFF_EDIT`,
`_authoring_ticket`, and `_run_authoring_session` directly and never goes
through `_resolve_existing`. Megalaunch never had this gate; removing it
changes nothing there.

### Why not keep the unknown-status bail

It is the one thing the guard also caught — a typo in `status:` frontmatter.
That belongs to `coga validate`, which already errors on any value outside
`VALID_STATUSES` (`src/coga/validate.py:573`). Refusing the authoring session
over it is backwards: authoring is the repair path for a malformed ticket.

There is a real cost to pay for that, though. `coga ticket` runs validation
itself on the way out — `_run_authoring_session` → `finalize_authored` →
`validate_authored_task` → `assert_task_valid`, which raises on any
`error`-severity issue, and `invalid-status` is one. So today a typo'd status
fails fast, before the interview; after this change it burns the whole
interview and then bails at the end. The accepted fix is to close that in the
skill rather than in the CLI: add a carve-out to
`bootstrap/ticket/SKILL.md` telling the interviewer that an out-of-vocabulary
`status:` is a defect to repair during the session. This needs an explicit
exception because the skill currently says the opposite at line ~199 ("Do not
change `status:`"). Do not leave the late failure undocumented and unfixed.

### Tests that will break

Two tests in `tests/test_ticket.py` assert on the caution text and must be
updated, not deleted:

- `test_ticket_can_edit_canceled_task_without_reopening` (line ~449) — asserts
  `"already canceled"` appears in the output. Drop that assertion only; the
  test still asserts `status == "canceled"` afterward, which is the point.
- `test_ticket_edits_in_progress_task` (line ~423) — asserts `"in_progress"`
  appears in the output. **This one needs an assertion added, not just one
  removed.** It currently checks only exit code, that substring, and that one
  prompt was spawned; strip the substring and it becomes a duplicate of the
  generic launch tests with no `in_progress`-specific coverage left. Add a
  status-unchanged assertion mirroring the canceled test.

Add a test covering the actual bug: a `blocked` ticket opens, exit code 0, and
its status is still `blocked` afterward. `_allow_ticket_launch` (line ~81) is
the existing helper for stubbing the spawn. The fixture must carry a workflow
— `validate.py:109` puts `blocked` in `_LIVE_WORKFLOW_STATUSES`, so a
workflow-less blocked ticket is an `active-no-workflow` error and
`finalize_authored` would fail the test for the wrong reason. Follow the
neighboring `create_task(..., workflow_name="direct/body", status=...)`
pattern. Validate requires no blocker-ask, so nothing else is needed.

### Prose to keep in sync

Three packaged files repeat the behavior being removed. None has a live
`coga/` mirror, so the usual check-both-copies rule (CLAUDE.md) resolves to a
single edit in each:

1. `src/coga/resources/templates/coga/bootstrap/skills/bootstrap/ticket/SKILL.md`
   — line ~85 enumerates the editable statuses ("at any editable status
   (`draft`, `active`, ...)"); line ~95 is the in-session caution sentence
   (keep the behavior, add `blocked`); line ~352 enumerates non-draft statuses
   for the step-5 cleanup rule and omits `blocked`, so a blocked ticket edited
   today hits that rule with no matching branch. Line ~199 needs the
   status-repair carve-out described above.
2. `src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md`
   lines ~121-125 document `coga ticket` and state the removed behavior almost
   verbatim ("for an `in_progress`, `done`, or `canceled` ticket it prints a
   heads-up first ... but does not refuse"). That sentence goes.
3. The `--help` text at `ticket.py:69` is already correct and needs no edit.

`tests/test_bootstrap_ticket_skill_template.py` does not assert on the status
list — its nearest assertion is the substring `"If editing an existing
non-draft ticket"`, which survives an edit to the enumeration following it —
so it should keep passing.

### Settled decisions — do not relitigate

The evaluator pushed back on dropping the informational `CAUTION_STATUSES`
note, arguing that the "protects nothing, creates a dead end" rationale is
true of the *refusal* but not of a one-line stderr heads-up. The owner
considered that and confirmed removal anyway: the CLI print is unconditional
noise emitted at spawn, and the contextual in-session equivalent in the skill
is the version worth keeping. Both gates go.

### Out of scope

- `coga launch`'s own status handling — it legitimately refuses a `done`
  ticket, and that gate stays.
- Anything that changes a ticket's *lifecycle* status. Editing a blocked
  ticket leaves it blocked; `coga unblock` remains the human's explicit call.
  (Repairing a typo'd, out-of-vocabulary `status:` value is not a lifecycle
  transition and is in scope, per the skill carve-out above.)
- `docs/reference.md` — its `coga ticket` entry (line 40) does not enumerate
  statuses, so it needs no change.
- Trimming the composed prompt. `dev/code` is the largest single layer (7.3
  KiB, ~36%) but is load-bearing: the `open-pr` step declares `requires: pr`
  and reads `branch:`/`worktree:` from the `## Dev` blackboard section it
  defines. It is not a trim candidate.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev
pr: https://github.com/FastJVM/coga/pull/674
branch: codex/always-accept-coga-ticket
worktree: /tmp/coga-always-accept-coga-ticket

## Implementation notes

- Regression reproduced before the fix: the new blocked-ticket test exited 2
  with `unknown status 'blocked'; refusing guided ticket editing`.
- Removed the CLI status refusal and unconditional caution. Guided authoring
  now accepts every lifecycle value while preserving valid status and step
  state.
- The authoring-only prompt projection omits both the launch-only blocker
  preamble and current workflow-step execution layer. Blocker asks remain
  visible as blackboard context without triggering an unblock flow.
- The packaged authoring skill now repairs malformed status metadata as one
  correlated lifecycle shape: terminal repairs clear `step:`, while live
  repairs require a frozen workflow and valid step.
- Updated the packaged CLI/ticket skill prose and matching live/packaged Coga
  behavior contexts. No example fixture change was needed.

## Peer review

- Ran `codex review --base main` against the implementation and again against
  the rebased review fixes.
- Applied all five reported must-fix findings: isolate blocker resolution from
  authoring, clear stale terminal steps during malformed-status repair,
  suppress live execution-step skills, require frozen live workflow repairs,
  and correct the CLI status-preservation contract.
- Commits: `277b0c29` (`Always allow guided ticket editing`), `633d3fa4`
  (`Peer review: preserve authoring lifecycle state`), and `62ebb89f`
  (`Peer review: isolate guided authoring`).

## Verification

- Final post-rebase `python -m pytest` — 1571 passed, 1 skipped.
- `env PYTHONPATH=/tmp/coga-always-accept-coga-ticket/src python -m coga.cli ticket --help`
  — passed; help still says existing tickets may be edited at any status.
- `env PYTHONPATH=/tmp/coga-always-accept-coga-ticket/src python -m coga.cli validate --task always-accept-coga-ticket --json`
  — passed with one valid task and no issues.
- `git diff --check` passed; live and packaged `coga/architecture` copies are
  byte-identical.

## Handoff

- Final `git fetch origin main` + `git rebase FETCH_HEAD` reported the branch
  up to date; it is zero commits behind and three commits ahead of fetched
  `origin/main`.
- Feature checkout is clean. Nothing was pushed and no PR was opened, as
  required before the deterministic open-PR step.

## PR

`coga ticket <slug>` now opens guided authoring for every lifecycle value,
including `blocked` and malformed statuses, without mechanical status
commentary. Valid lifecycle state and blocker asks are preserved; the
authoring-only prompt cannot inherit task-execution or unblock instructions;
and the interview repairs malformed status/workflow/step metadata as one
consistent shape. Regression coverage and shipped behavior documentation are
updated together.

Test plan: `python -m pytest` (1571 passed, 1 skipped); `coga validate --task always-accept-coga-ticket --json`; `git diff --check`.
