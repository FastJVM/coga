---
title: Activation does not resolve step 1's assignee role token
status: done
owner: nicktoper
agent: claude
contexts:
- coga/launch-internals
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills: []
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
---

## Description

There are two paths that can land a ticket on step 1 of a frozen workflow, and
they disagree about whether the step's `assignee:` role token is applied.

`create_task` (`coga.create`) resolves it: when `--workflow` is passed it
freezes the snapshot, reads `wf.steps[0].assignee`, and resolves the role
token (`owner` / `human` / `agent` / `other-agent`) against the ticket's
matching role field before writing `assignee:`.

`_freeze_workflow_ref` (`coga.mark`) does not. It converts a bare-string
`workflow:` ref into the frozen dict and seeds `step: 1 (<name>)`, but never
touches `assignee:`. So a hand-authored or guided-authored draft — which
carries `workflow:` as a plain name — activates onto an agent-owned step still
wearing whatever `assignee:` creation defaulted to, normally the human owner.

The result is a ticket that cannot be launched at all. `coga launch`
classifies the target from the ticket's literal `assignee:` field, sees a name
that is not a key in `[agents.*]`, and refuses as a human handoff — on a step
whose own frozen `assignee: agent` says the opposite. `coga bump` is no escape:
it requires `status: in_progress`, which only launch can set. The task is
wedged until a human hand-edits the frontmatter.

Observed on `reuse-the-existing-control-worktree-for-recurring`: hand-authored
draft, auto-activated on launch (`activated (draft -> active) - auto on
launch` in `coga/log.md`), frozen onto `1 (implement)` whose step declares
`assignee: agent`, but left at `assignee: nick`. Both `coga bump` and
`coga launch` refused. Repaired by hand.

Note the asymmetry is invisible until launch time, and the failure names the
wrong cause: the error says "this is a human handoff", which the frozen
workflow contradicts.

Done looks like: activating a draft that carries a bare `workflow:` string and
no `step:` resolves step 1's role token exactly as `create_task` does, so
`coga launch` starts it without a hand-edit; a step-1 role token that cannot
resolve (e.g. `other-agent` with one configured agent) fails loud at
activation with the same message `create_task` gives, rather than deferring a
confusing refusal to launch; a ticket already carrying a step is untouched
(the documented no-op in `coga/architecture` still holds - nothing re-freezes
an existing ticket); and the resolution logic is shared between the two call
sites rather than copied.

## Context

- `coga/architecture` documents `_freeze_workflow_ref` as "a documented no-op
  once `workflow:` is already a dict carrying a step" and describes per-step
  `assignee:` role tokens as resolving "on bump". Whether seeding step 1 at
  activation should also resolve that step's token is the gap this ticket
  closes; update the context in the same PR if the answer changes what is
  written there.
- Existing tickets in the repo that carry `assignee: <human>` on an
  agent-owned step are the same defect and may need a sweep - check before
  deciding whether a migration is in scope.
- Per `ticket-specs-should-cite-symbols-not-line-numbers`, cite symbols.

<!-- coga:blackboard -->

## Dev

pr: https://github.com/FastJVM/coga/pull/779
branch: resolve-step-one-assignee
worktree: /home/n/Code/claude/coga-resolve-step-one-assignee

## Implemented and reviewed

- Creation and activation share `resolve_first_step_assignee`, backed by
  `resolve_role_token` in `coga.bump`. `resolve_step_assignee` delegates to the
  same primitive, preserving bump's role and peer semantics.
- `_freeze_workflow_ref` resolves the first-step role only when seeding a
  missing step. A frozen workflow carrying a step keeps its assignee. Failed
  resolution raises `WorkflowError` before any durable activation; existing
  activation callers already render that exception. Creation and activation
  share the resolver's failure text.
- `codex review --base main` reported one P2: launchers cached routing before
  preparation changed the assignee. Confirmed failures included direct launch
  rejecting a human-default draft, CLI preflight checking the wrong agent and
  leaving an unstarted ticket `in_progress`, and megalaunch spawning the old
  agent while recording the resolved one.
- Fixed `commands.launch._launch` to refresh routing and override continuation
  after preparation. Megalaunch defers stepless ticket routing until its
  prepared view exists, rechecks human gates in the selection and final
  preflight, and selects the agent from that same view. Blocker classification
  remains tied to the original snapshot; the routing check adds no blocker
  reread or lifecycle write.
- Regressions cover activation success/failure/no-op, direct draft launch,
  missing resolved-agent CLI, all four first-step roles in megalaunch with
  and without an override, and override continuation after draft activation.
  Both architecture context copies document the behavior and match exactly.
- Rebased without conflicts onto fetched `origin/main` at `6d1ed844`.
  Feature commits: `5c0528ea` (implementation), `63c530ea` (review fixes).
  The feature checkout is clean and two commits ahead of that base.

## Migration scope

The implementation sweep found ten live tickets with a human assignee on an
agent-owned step: `run-recurring-agent-templates-off-the-control-bran` and
`v2/acceptance-criteria`, `v2/automerge-ticket`, `v2/gh-merge-requirement`,
`v2/identify-blocking-issues`,
`v2/implement-accepted-ticket-interview-improvements`, `v2/issue-inbox-slack`,
`v2/overload-ticket-locally-easily`, `v2/relay-design-repositories`, and
`v2/use-worktree-when-starting-a-dev-task`. All already have a step, so this
prospective fix deliberately leaves them alone. Their one-field repairs remain
outside this product PR: they are control-branch task state, and including them
would collide with routine task syncs. No migration machinery was added.

## Verification

- Native review completed; its must-fix finding is addressed.
- Final full suite on the rebased commits: **2335 passed, 1 confirmed
  pre-existing failure**, with no skipped or deselected tests. Exact command
  from the feature checkout:
  `TMPDIR=/tmp/coga-step-one-final-tests PATH=/tmp/coga-step-one-review-venv/bin:$PATH python -m pytest`.
  The disposable environment was installed with the declared `[test]` extra,
  including pip and hatchling; all packaging tests passed, including the wheel
  build. Full output: `/tmp/coga-step-one-tests-final.log`.
- The first full run exposed an extra blocker read, fixed above; then
  `/tmp/coga-step-one-review-venv/bin/python -m pytest tests/test_megalaunch.py -q -p no:cacheprovider`
  passed all 113 tests. A subsequent full run passed all routing tests but hit
  a transient unrelated worktree in the cleanup test's shared `/tmp` glob;
  that directory subsequently vanished. The private-temp full rerun passed
  that cleanup test without changing product code or deleting other worktrees.
- Confirmed baseline failure on an untouched archive of `origin/main` at
  `6d1ed844`: `tests/test_notification_messages.py::test_recurring_create_is_silent`
  passes a directory-form task as `TaskRef(file_form=True)`, causing
  `IsADirectoryError`. Reproduced with
  `/tmp/coga-step-one-review-venv/bin/python -m pytest tests/test_notification_messages.py::test_recurring_create_is_silent -q -p no:cacheprovider`.
- From feature `example/coga`:
  `env -u SLACK_WEBHOOK_URL /tmp/coga-step-one-review-venv/bin/coga validate --json`
  reports 3 valid tasks and no issues. The inherited webhook variable is
  removed for this fixture's notification-disabled config only.
- From primary: `coga validate --task activation-does-not-resolve-step-1-s-assignee-role --json`
  reports 1 valid task and no issues.
- `git diff --check origin/main...HEAD` passes. A direct diff of the live and
  packaged architecture contexts is empty after rebase.

## PR

Activating a draft with a bare `workflow:` reference now resolves step 1's
assignee through the same resolver used by task creation. Unresolvable roles
fail before activation is written, and tickets with an existing step retain
their assignment.

Direct launch and megalaunch select and preflight the resolved agent, preserving
human handoffs and explicit agent overrides. Adds activation and launcher
regressions and updates both architecture context copies.

Test plan: `python -m pytest` — 2335 passed; the existing `tests/test_notification_messages.py::test_recurring_create_is_silent` failure also reproduces on untouched `main`. `coga validate --json` from `example/coga` — 3 valid tasks, no issues.
