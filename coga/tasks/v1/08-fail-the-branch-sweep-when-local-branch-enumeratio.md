---
title: Fail the branch sweep when local branch enumeration fails
status: in_progress
owner: nicktoper
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills:
    - code/peer-review
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 2 (peer-review)
agent: claude
launch_generation: 01ce871b-ffe1-4c9f-82d9-0ab3bbe2f4bc
---

## Description

`branchsweep._local_branches` runs `git for-each-ref --format=%(refname:strip=2) refs/heads/` and parses stdout without checking the return code, so a failed local enumeration reads as no local branches. The sweep then proceeds on an empty local inventory, which can let an otherwise authorized remote-only delete run without a known local state, contrary to the rule that an incomplete scan preserves refs. Found during the 2026-10-05 terminal-owner cleanup (PR #963); never exercised. Fix: treat a non-zero exit as a sweep failure, like the worktree probe, with a regression test. Moved from the coga/checkout-cleanup/branch-sweep Known gap note by blocks/02.

## Context

<!-- Ticket guide — keep this comment when filling in or updating the ticket.
It documents field shapes; these are examples, not values to copy into every
ticket. Omit optional fields and sections until needed. Editing rules come
from the base prompt; body regions from coga/tickets; blackboard conventions
(superseded designs, draft cleanup, oversized notes) from coga/blackboard.
Write requirements under ### subheadings of Description or Context; any other
level-two heading above the fence does not reach the launch prompt.

FRONTMATTER
The real values are in this ticket's YAML header. Required ordinary-ticket
keys are title, status, owner, and workflow. A minimal draft has workflow: null.

    title: Fix retry diagnostics           # What the work is called; identity comes from the file path.
    status: draft                          # CLI state: draft, active, in_progress, paused, blocked, done, canceled.
    owner: human-name                      # Accountable human; receives notifications and owner gates.
    agent: codex                           # Optional configured main agent; activation supplies the default if absent.
    contexts:                              # Optional facts to include in every launch; attach only what is needed.
      - service/retries
    skills:                                # Optional ticket-wide procedures, in addition to workflow step skills.
      - infra/testing-conventions
    workflow: code/with-review             # Draft reference or null; live tickets have the frozen mapping below.
    secrets:                               # Optional environment names mapped to references, never credentials.
      - API_TOKEN: env:LOCAL_API_TOKEN
      - SERVICE_KEY: op://automation-vault/service/api-key

The agent choice is not the current operator or the ticket interviewer.
Omit empty contexts, skills, and secrets lists. Each secrets entry has exactly
one unique name (no COGA_ prefix); env: reads the operator's environment and
op:// reads a 1Password item at launch, exposing the value under the left-hand
name. An unavailable reference prevents launch. Never put a literal secret here.

A workflow must be selected before activation. Creation with --workflow, or
activation of a draft reference, freezes its steps. CLI transitions manage step;
do not rewrite a live snapshot or advance it by editing YAML. Frozen example:

    workflow:
      name: code/with-review                # Selected workflow name.
      steps:
        - name: implement                  # Ordered step name.
          skills:                          # Optional procedures for this step; plural, never skill.
            - code/implement
          assignee: agent                  # Role: owner, agent, or other-agent (the configured peer).
          requires: branch                 # Optional completion gate: branch or pr.
    step: 1 (implement)                    # One-based position plus name; CLI removes this on completion.

An omitted step assignee inherits the previous role; the first defaults to
owner. The current step determines who holds the ticket. There is no top-level
assignment field. Removed keys slug, human, assignee, and watchers are invalid.
There is no execution-mode field: a sibling ticket.py supplies a script phase.

Repo extensions are string fields declared under [ticket.fields.<name>] in
coga.toml: description explains the field, values restricts its choices,
default seeds it, and required prevents activation while it is empty. Actual
values live below the extensions marker comment in the YAML header. Preserve
them; do not invent extension fields or change their definitions in config.

Machine-owned fields: delegate freezes a recurring parent's bootstrap/<name>
target; period_generation identifies its materialized run. Both belong only on
period tasks directly under tasks/recurring/. launch_generation is megalaunch's
session claim. Preserve these fields; do not add or clear them yourself.

BLACKBOARD (BELOW THE FENCE)
Keep current decisions and their reasons, verification, next actions, and
blockers here. Update current values in place instead of appending stale copies.

Optional ## Dev: branch: <name> when created; pr: <full /pull/ URL> when opened;
worktree: <path> only for a sandbox clone. One field per line, notes on separate
lines, omit unknown values. For multiple owned branches, the first branch is
the workflow branch.

Optional ## PR: one fenced YAML mapping of PR-preparation receipts (title,
author, head/base OIDs, review depth, files, review, checks). Record only actual
implementation and evidence, never placeholders; coga/pr-publication/
preparation owns the fields and the publishing workflow the review rules.

Optional ## Blockers and ## Blocker reminders are CLI-maintained. Preserve
blocker IDs, timestamps, actor names, resolved answers, and reminder fingerprints
with last_reminded timestamps; use lifecycle commands to block or resolve them.

Recurring parents (coga/recurring/<name>/ticket.md) take schedule and related
template settings owned by coga/recurring/templates; do not add them to an
ordinary ticket.
-->

### Code pointers

- `branchsweep._local_branches` calls `_git(root, "for-each-ref", ...)` and
  iterates `proc.stdout` without looking at `proc.returncode`. `sweep_branches`
  builds `names = local.keys() | remote.keys()` from it, so an empty local
  map turns every remote branch into an apparent remote-only branch.
- Model to copy: `branchsweep._worktree_branches`. On a non-zero exit it sets
  `result.worktree_unavailable` to stderr/stdout (or a fallback string), notes
  "... — sweep skipped: <detail>" via `_note`, and `sweep_branches` returns
  before any delete. Unlike `_remote_branches` (a partial sweep), a local
  enumeration failure stops the whole sweep: no per-branch decision is safe
  without local state. `_local_branches` will need `result` and `echo`
  parameters for this.
- A successful but empty `for-each-ref` (no branches, unborn HEAD) is
  legitimate and is not a failure.
- Failure plumbing to extend: `BranchSweepResult` (add a field such as
  `local_unavailable`), its `failure` property, and `render_sweep_report`,
  which labels `worktree_unavailable` / `state_root_unavailable` as "the sweep
  stopped early". `run_branch_sweep_recipe` exits 2 when `failure` is set.
- Required too: `_local_branches` silently drops a listed branch whose
  `_rev_parse` comes back empty. That branch then looks remote-only, which is
  the same unsafe outcome, so treat it as the same enumeration failure.
  Consider `--format=%(refname:strip=2) %(objectname)` instead: it removes the
  per-branch `rev-parse` and its empty case, and avoids failing the run when a
  branch is deleted between the two calls.
- Placement: the early return in `sweep_branches` goes before `_remote_branches`
  is called. Then no `ls-remote` call is wasted, and `remote_unavailable`
  cannot be reported ahead of the local failure. Add the new field to
  `failure` and to the "stopped early" condition in `render_sweep_report`.
- `checkout_disposal` also calls `sweep_branches(only=...)` and ignores
  `result.failure`. A local failure there only leaves owned branches in place,
  which is acceptable and needs no change.

### Tests

`tests/test_branchsweep.py`. Model the regression test on
`test_worktree_prune_failure_stops_sweep`: monkeypatch `bs._git` so that
`for-each-ref` returns a non-zero `CompletedProcess` while other calls pass
through to the real `_git`. The fake must accept `**kwargs`, because `_git`
takes `input=`; the model test's `fail_prune(root, *args)` does not. Then
assert the new failure field is set and `local_deleted` and `remote_deleted`
are both empty. Ideally, set up a remote-only branch that would otherwise be
deleted (with helpers such as `_merged_at_tip` / `_push_branch`), so the test
shows the delete is refused. Add the new field to the parametrized
`test_recipe_records_a_failed_sweep_on_the_blackboard` cases ("the sweep
stopped early", exit 2).

### Done

The work is done when a failed local enumeration (a non-zero `for-each-ref`
exit, or an unresolvable listed tip) stops the sweep with no local or remote
deletes, sets a named failure that appears in the report as "the sweep
stopped early", and makes the recipe exit 2. A regression test must cover
this, and the user topic and its twin must state the rule.

### Docs (same PR)

The rule is in `coga/checkout-cleanup/branch-sweep`
(`docs/contexts/coga/checkout-cleanup/branch-sweep/SKILL.md`; cited here, not
attached because this ticket edits it). It covers only per-branch failures
today. Add a short
statement that the sweep stops before any delete, records the reason in
`## Branch Sweep`, and exits 2 when it cannot establish local state: local
branch enumeration (new), worktree probe, or Coga root prefix. Keep this
separate from the per-branch paragraph. The packaged twin
`src/coga/resources/templates/coga/bootstrap/contexts/coga/checkout-cleanup/branch-sweep/SKILL.md`
must stay byte-identical (`tests/test_packaging.py`).
`coga-dev/internals/branch-sweep` needs no change.

### Out of scope

The non-UTF-8 decode failure in `branchsweep._git` (the "Known failure mode"
in `coga-dev/internals/branch-sweep`) is a separate, unowned bug. Do not fix
it here.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: fail-sweep-on-local-enumeration

## Implement handoff (2026-11-04)

What changed (commit a65a8e686, pushed):
- `branchsweep._local_branches(root, result, echo)` now lists name and tip in
  one `for-each-ref --format=%(objectname) %(refname:strip=2)` (no per-branch
  `rev-parse`, no delete-between-calls race). A non-zero exit, or an entry it
  cannot split into tip + name, sets new `BranchSweepResult.local_unavailable`
  and notes "could not list local branches — sweep skipped: …". An empty
  successful listing is still fine.
- `sweep_branches` returns right after `_local_branches` on failure, before
  `_remote_branches` (no `ls-remote`, no remote_unavailable masking).
- `failure` includes `local_unavailable` (after state_root, before gh);
  `render_sweep_report` labels it "the sweep stopped early"; recipe exits 2.
- Docs: new paragraph in `coga/checkout-cleanup/branch-sweep` (+ byte-identical
  packaged twin) stating the stop-before-delete rule for local enumeration,
  worktree probe, and Coga root prefix.
- Tests: `test_local_branch_listing_failure_stops_sweep` (merged "feat" that
  would look remote-only stays on both sides), `test_unresolvable_local_branch_entry_stops_sweep`,
  plus `local_unavailable` case in `test_recipe_records_a_failed_sweep_on_the_blackboard`.
  Both new tests fail with the fix reverted.

Decision: an unresolvable entry is detected as an unparseable line from the
combined listing (the `rev-parse`-empty case no longer exists).

Environment note (not this ticket): the primary checkout carries an
uncommitted human edit to `pyproject.toml` (`tmp_path_retention_policy =
"failed"`). It was left untouched and unstaged. With it,
`tests/test_validate.py::test_validate_prunes_skill_dependencies_before_scanning`
errors at teardown (pathlib TypeError); with `-o tmp_path_retention_policy=all`
it passes. Whoever lands that pyproject tweak should fix that interaction.

No independent review yet; the workflow's later steps own review and PR.

## PR

```yaml
title: Stop the branch sweep when local branch enumeration fails
author: claude
author_evidence: Implement session ran as Claude Code (claude-opus-5-5) in a megalaunch queue.
head: a65a8e686aa7b3b141ce26e0f2524400900ad4af
base: 6ea506da11155179f63b8845108b950e887adae6
depth: skim
rationale: Bounded fail-closed change in one sweep helper; read the description for the single-listing parse choice.
implementation: _local_branches lists tip and name in one for-each-ref; a non-zero exit or unparseable entry sets local_unavailable, which stops sweep_branches before the remote listing, reports "the sweep stopped early", and makes the recipe exit 2.
deviations: Replaced per-branch rev-parse with %(objectname) in the listing, as the ticket suggested; the "empty rev-parse" case is now an unparseable-entry case.
limitations: Unrelated local pyproject.toml tweak in the primary checkout causes a teardown error in one test_validate test; not part of this diff.
files:
  src/coga/branchsweep.py: Detect local enumeration failure, record local_unavailable, stop the sweep before any delete, and report it as stopped early.
  tests/test_branchsweep.py: Regression tests for a failed listing and an unresolvable entry, plus the recipe exit-2/report case.
  docs/contexts/coga/checkout-cleanup/branch-sweep/SKILL.md: State that the sweep stops before deleting when local state cannot be established.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/checkout-cleanup/branch-sweep/SKILL.md: Byte-identical packaged twin of the topic.
review:
  reviewer: none
  kind: none
  status: not-run
  detail: Implement step; code review belongs to a later workflow step.
checks:
  - command: .venv/bin/python -m pytest tests/test_branchsweep.py tests/test_packaging.py tests/test_retire_worklist.py -q
    status: passed
    head: a65a8e686aa7b3b141ce26e0f2524400900ad4af
    base: 6ea506da11155179f63b8845108b950e887adae6
    detail: 234 passed (run on the working tree identical to the committed tree).
  - command: .venv/bin/python -m pytest -q
    status: passed
    head: a65a8e686aa7b3b141ce26e0f2524400900ad4af
    base: 6ea506da11155179f63b8845108b950e887adae6
    detail: 4345 passed, 10 skipped, 1 teardown error in test_validate_prunes_skill_dependencies_before_scanning caused by the uncommitted local pyproject tmp_path_retention_policy edit; that test passes with -o tmp_path_retention_policy=all.
```
