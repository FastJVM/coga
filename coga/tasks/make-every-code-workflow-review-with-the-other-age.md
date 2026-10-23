---
title: Make every code workflow review with the other agent
status: draft
owner: nicktoper
workflow: code/with-review
contexts:
  - coga/checkouts
  - coga/workflows
  - coga/recurring/autofix
---

## Description

The owner expects every code-producing workflow to get its code review from
the other agent (`assignee: other-agent`), not from the agent that wrote the
code. Audit every workflow and propose, per workflow, whether to add an
`other-agent` review step, keep it as is on purpose, or retire it. Include what
`recurring_autofix` should use, given that unattended runs may have no peer,
and what happens when `other-agent` can't resolve a peer.

This ticket runs under `code/with-review`, which has no design gate. The
`implement` step therefore works in two phases. First it writes the per-workflow
proposal to the blackboard under `## Design` and gets the owner's explicit
decision on it. In an attended session, ask and wait. Otherwise block with the
proposal as the ask. Only then does it apply the approved changes. The
`peer-review` step then reviews that diff against the recorded decision.

Done when every workflow under
`src/coga/resources/templates/coga/bootstrap/workflows/`,
`src/coga/resources/templates/coga/workflows/`, and `coga/workflows/` (except
the `_template.md` starters) either has an `other-agent` step that reviews the
code, or says in its own body why it intentionally doesn't. The owner-approved
changes are shipped when their PR is merged with `tests/test_packaging.py`
passing, and the coupled code and topics listed under Context are updated in
that same PR.

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
  is `owner`. No other-agent step by design. The live ticket `fix-git-sync-failure` uses it, and so does
  every autofix ticket (see below). That is one concrete way a ticket ends up
  with no peer review.
- `brief-for-human`, `draft-for-human`: not
  code-producing. Confirm and leave them alone unless the owner says otherwise.

**Repo-local `coga/workflows/`** has no `code/` or `docs/` directories, so a
`code/*` change touches only the packaged copy. If a live copy exists by the
time you edit, keep both byte-identical (`tests/test_packaging.py`). It does
hold other workflows that the done criterion also covers. Classify each one in
the design: `brief-for-human`, `draft-for-human` (live twins of the bundled
ones), `maintenance/with-approval`, `build/onboarding`, `direct/body`, and the
one-step recurring/scripted workflows `autoclose-merged/sweep`,
`blocker-reminders/run`, `branch-sweep/sweep`, `phone-home/run`,
`skill-update/run`, and `usage-report/post`. Most are probably not
code-producing. The ones that can produce code, such as `direct/body` and
`maintenance/with-approval`, need an explicit decision. Packaged twins under
`src/coga/resources/templates/coga/workflows/` exist for `build/onboarding`,
`direct/body`, `autoclose-merged/sweep`, `blocker-reminders/run`,
`branch-sweep/sweep`, `phone-home/run`, and `skill-update/run`. An edit to one
of them touches both copies.

**Code coupled to these workflow names.** Changing a workflow's step list
changes behavior here too:
- `checkout_policy` keeps a per-(workflow, step) table (`_CODE` and the step
  entries). A new review step needs its own entry there, which decides whether
  it reuses the implementation checkout. Read the `coga/checkouts` topic before
  adding one.
- `recurring_autofix.AUTOFIX_WORKFLOW` hard-codes `code/with-self-review` for
  unattended autofix tickets, and `docs/contexts/coga/recurring/autofix`
  documents it. Changing or retiring `with-self-review` affects autofix, so the
  design must say which workflow autofix should use. An unattended run may
  have no peer agent available.
- The refusal messages in `commands/mark.py` and `commands/bump.py` recommend
  `code/with-self-review or code/with-review`. Update them if the
  recommendation changes.
- `templates/coga/workflows/build/onboarding.md` steers generated tickets to
  `code/design-then-implement`.
- `code/open-pr` (bundled skill) and the `coga/checkouts` and
  `coga-dev/current-direction` topics mention these workflows by name. Fix
  them in the same PR as any rename or retirement.

The `bootstrap/ticket` skill itself names only `code/with-review` as its
example. It does not nudge authors toward `with-self-review`.

Changing the workflow definitions doesn't touch existing frozen tickets: only
new or unfrozen tickets pick up the change. Say so in the design.

**Questions the design must answer** (from the pre-launch cold review):
- Should every code workflow have a peer, or is `with-self-review` still
  wanted for single-agent installs where `other-agent` can't resolve? Today a
  missing or ambiguous peer fails loud (`unresolvable-step-assignee`). Say what
  each proposed workflow does in that case.
- Do `direct/body` and `maintenance/with-approval` actually produce code? Check
  before adding a review step to them.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
