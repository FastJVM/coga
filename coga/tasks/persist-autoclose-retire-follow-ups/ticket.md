---
slug: persist-autoclose-retire-follow-ups
title: Persist autoclose retire follow-ups
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
  - coga/principles
  - coga/architecture
  - coga/codebase
  - coga/recurring
skills: []
workflow:
  name: code/with-self-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: self-qa
    skills:
    - code/self-qa
    assignee: agent
  - name: pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
secrets: null
step: 1 (implement)
---

## Description

Keep autoclose's unfinished `coga retire` follow-ups across recurring runs.
The 2026-09-03 Multiply sweep recorded its cleanup reminder only in
`coga/tasks/recurring/autoclose-merged/ticket.md`. The next period replaces that
completed task, so the reminder disappears even though the checkout or branch
may still need attention. Autoclose only rediscovers tickets it closes in the
current run, so this debt is not reconstructed automatically.

This is a Coga defect observed in a consuming repository. It replaces Multiply
ticket `autofix/persist-autoclose-retire-follow-ups-beyond-the-per` and the
implementation proposed in [Multiply PR #46](https://github.com/FastJVM/multiply/pull/46).
The owner redirected the work upstream on 2026-09-04. The reusable writer,
worklist maintenance, documentation, and regression coverage belong in Coga;
Multiply should consume the shipped fix without a separate maintenance script
or a dependency on an unpushed editable Coga branch.

### Required outcome

1. Give recurring autoclose follow-ups a durable, explicitly documented home
   outside the period task. The existing implementation uses `retires.md`
   beside the recurring template. Resolve the actual template instead of
   hardcoding `autoclose-merged`; retain ordinary non-recurring report surfaces.
2. Make recording idempotent by task ref, preserve unrelated pending entries,
   and define how entries clear once their recorded worktree and branch no
   longer need retirement. Ship that maintenance through Coga's existing
   autoclose/retire surfaces so consuming repositories need no custom Python.
3. Preserve the separation between recording a follow-up and destroying a
   checkout. Autoclose must not remove worktrees or branches; `coga retire`
   remains responsible for its existing safety checks.
4. Reconcile the live and packaged autoclose skill, recurring template, and
   applicable context/documentation with the actual writer and maintenance
   behavior. Document how existing installations adopt the fix, including any
   old local template/workflow overrides; a local editable source checkout is
   not the delivery mechanism.
5. Cover period-task deletion/recreation, reruns and duplicate slugs,
   completed versus still-live cleanup debt, and ordinary non-recurring
   reporting. Recheck parsing and write consistency when integrating the
   preserved patches with current main.

### Existing work to reuse

The old ticket's initial claim that emission was agent-side was incorrect.
`src/coga/autoclose.py::_report_retire_followups` performs the write and uses
`blackboard_from_env`, which points at the ephemeral period ticket. This path
is still present in `/home/n/Code/coga` at handoff inspection.

An implementation and a self-QA correction are already committed in the
separate local checkout `/home/n/Code/claude/coga`, on
`autoclose-retires-durable-home`:

- `fa3880b1` — Write autoclose retire follow-ups to a durable worklist.
- `c5cb1548` — Correct the sweep skill's surfaces and harden worklist parsing.

No PR for that upstream branch was found at handoff. The attached
`coga-existing-implementation.patch` preserves both commits, so resuming does
not require that local checkout to survive. It is a starting point for review
and integration, not evidence that current main passes validation.

`multiply-support.patch` preserves the companion script, tests, worklist seed,
and template/workflow changes from Multiply PR #46. Use its behavior and
regressions as input when completing the upstream implementation; do not add
the Multiply script as a requirement for consumers. The historical seed has 14
entries, of which the old investigation found only four still actionable.
Re-derive current cleanup debt before any backfill or retirement operation.

The earlier review recorded two concerns to resolve during integration: the
durable worklist used a non-atomic read/modify/write, and the companion prune
script resolved relative worktree paths against the process working directory.
Union merges can also resurrect removed entries; the old design relied on an
idempotent daily prune to clear them again. Evaluate these together with the
chosen packaged maintenance path.

## Context

- `multiply-run-log.md` is the captured 2026-09-03 sweep evidence, including the
  follow-up for `v1/persistent-codex-m-managed-checkout`.
- `multiply-ticket-history.md` preserves the original investigation,
  decisions, prior test reports, and Multiply-specific cleanup inventory.
  Its earlier proposal to land changes in both repositories is superseded by
  this ticket's upstream ownership decision.
- `handoff-manifest.md` records the source commit IDs and attachment hashes.
- Previous test counts in the archived history belong to the old checkouts;
  rerun relevant tests against the integrated Coga change.

This ticket captures and relocates the existing defect. Implementation and
review proceed through its normal code workflow; the handoff itself does not
launch that work or dispose of any recorded checkout.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
