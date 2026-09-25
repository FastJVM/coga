---
title: Make every code workflow review with the other agent
status: draft
owner: nicktoper
workflow: code/design-then-implement
---

## Description

The owner expects every code-producing workflow to get its code review from
the other agent (`assignee: other-agent`), not from the agent that wrote the
code. Audit every workflow and propose, per workflow, whether to add an
`other-agent` review step, keep it as is on purpose, or retire it. The owner
decides at `review-design`, then `implement` applies the chosen changes.

Done when every workflow under
`src/coga/resources/templates/coga/bootstrap/workflows/` and `coga/workflows/`
either has an `other-agent` step that reviews the code, or says in its own body
why it intentionally doesn't. The owner-approved changes must also be shipped.

## Context

Split out of `where-have-code-review-disappeared`, which fixes the separate bug
where the launch supervisor stops handing off to the other agent after
`coga bump`. This ticket is about workflow *shape*, not that handoff bug.

**Current bundled step owners** (packaged under
`src/coga/resources/templates/coga/bootstrap/workflows/`):
- `code/with-review`, `docs/with-review`: `peer-review` is `other-agent`.
  Already compliant.
- `code/design-then-implement`: only `evaluate-design` is `other-agent`, and
  nothing reviews the code after `implement`. This is the main gap.
- `code/with-self-review`: implement → self-qa → pr are `agent`, and `review`
  is `owner`. No other-agent step by design. Several live tickets use it,
  including `run-the-landed-branch-sweep-daily-from-autoclose`. That is one
  concrete way a ticket ends up with no peer review.
- `docs/create-google-doc`, `brief-for-human`, `draft-for-human`: not
  code-producing. Confirm and leave them alone unless the owner says otherwise.

Repo-local `coga/workflows/` has no `code/` or `docs/` directories today, so a
`code/*` change touches only the packaged copy. If a live copy exists by the
time you edit, keep both byte-identical (`tests/test_packaging.py`).

Also check which workflow ticket authoring steers toward: the `bootstrap/ticket`
skill (packaged under `src/coga/resources/templates/coga/bootstrap/skills/`).
If it nudges authors to `with-self-review`, that is part of the finding.
Changing the workflow definitions doesn't touch existing frozen tickets: only
new or unfrozen tickets pick up the change. Say so in the design.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
