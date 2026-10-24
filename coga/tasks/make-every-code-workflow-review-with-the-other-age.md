---
title: Make every code workflow review with the other agent
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
contexts:
- coga/checkouts
- coga/workflows
- coga/recurring/autofix
step: 2 (peer-review)
agent: claude
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
## Dev

branch: coga/make-every-code-workflow-review-with-the-other-a-4c644b


The blackboard is a notepad to be written to often as the human and agent works through a task.

## Design

Proposal (awaiting owner decision). Frozen tickets are untouched: only tickets
created (or bare-ref drafts activated) after merge pick up new step lists.
Live skill/inline text edits do reach frozen tickets, so shared text stays
step-name-agnostic.

Audit facts: create fails loud only if *step 1* can't resolve
(`create.create_task`); a later `other-agent` step surfaces as
`unresolvable-step-assignee` in validate and refuses at that step's routing.
`direct/body` is the only `_NO_PR_WORKFLOWS` member (`mark._NO_PR_WORKFLOWS`):
finishing it with committed product code is refused, steering to `code/*`.

| Workflow | Proposal |
| --- | --- |
| `code/with-review`, `docs/with-review` | Keep; already `other-agent` peer-review. |
| `code/design-then-implement` | **Add** `peer-review` (`other-agent`) between `implement` and `open-pr`; new `checkout_policy` row `reuse-required`; drop "no peer/self-review step" prose here, in `code/open-pr`, `coga/checkouts` table. |
| `code/with-self-review` | **Keep on purpose** as the single-agent fallback (no resolvable peer); body says so and points two-agent repos at `code/with-review`. |
| `direct/body` | Keep; body explains it ships no code (stranding guard), code → `code/*`. |
| `maintenance/with-approval` | Keep; body says it's operational cleanup, not code; code changes → `code/*`. |
| `build/onboarding` | Keep; generates tickets only. |
| `brief-for-human`, `draft-for-human` | Keep; non-code; one-line body note (both twins). |
| one-step recurring (`autoclose-merged/sweep`, `blocker-reminders/run`, `branch-sweep/sweep`, `phone-home/run`, `skill-update/run`, `usage-report/post`) | Keep; one-line body note "deterministic recipe, produces no code" (live+packaged twins). |

Peer-review instructions for design-then-implement: extract the
`code/with-review` `## peer-review` prose into a new bundled skill
`code/peer-review`; design-then-implement and new with-review tickets declare
it; with-review's inline section becomes a short "follow `code/peer-review`"
pointer so old frozen snapshots (skills: []) still compose. Alternative:
duplicate the inline prose (no new skill, two copies to drift).

Autofix: `AUTOFIX_WORKFLOW` → `code/with-review` when `other-agent` resolves
for the ticket's main agent at creation; else fall back to
`code/with-self-review` and say so in the sweep note. `code/implement` already
carries the already-satisfied path, so transient findings still self-close.

Refusal messages in `commands/mark.py`/`commands/bump.py`: recommend
`code/with-review` (or `code/with-self-review` without a peer).

**Owner decision (2026-10-23, attended):** approved all four recommendations —
extract `code/peer-review` skill; keep `code/with-self-review` as the
single-agent fallback; autofix uses `code/with-review` with a no-peer fallback
to `code/with-self-review`; body notes only for non-code workflows (no new
stranding guard).

## Implement handoff

Implemented the approved design in one commit on the branch (pushed).

- New skill `code/peer-review` (bundled + live twin under `coga/skills/code/`),
  extracted verbatim from `code/with-review`'s inline `## peer-review`, made
  step-name agnostic ("the next frozen step"/"PR-opening step").
- `code/with-review`: `peer-review` now declares `skills: [code/peer-review]`;
  its inline section is a short pointer, still composed by older frozen
  snapshots (`skills: []`, e.g. **this ticket**), telling the peer to read and
  follow the skill. `checkout_policy._ROWS` accepts both shapes.
- `code/design-then-implement`: new `peer-review` (`other-agent`,
  `code/peer-review`) between `implement` and `open-pr`; policy row
  `reuse-required`; prose about "no peer/self-review step" replaced.
- `code/with-self-review`: kept; body states it is the single-agent fallback.
- `recurring_autofix.autofix_workflow`: `code/with-review` when
  `bump.resolve_other_agent` succeeds for the prospective default agent, else
  `code/with-self-review` with a stderr warning.
- Non-code workflows (both twins where they exist): appended
  `## No other-agent code review` (a non-step H2, never composed).
- New test `test_every_workflow_has_other_agent_review_or_says_why_not` enforces
  the done criterion over all three workflow roots.
- Refusal messages in `commands/mark.py`/`commands/bump.py`, topics
  `coga/workflows`, `coga/checkouts`, `coga/recurring/autofix` (twins),
  `coga-dev/current-direction`, and the `code/open-pr` skill updated.

Not done / for peer-review: existing frozen tickets keep their old step lists
(by design). No adjacent bugs found. Code review has not run yet; that is the
next frozen step (other-agent).

## PR

```yaml
title: Have every code workflow review with the other agent
author: claude
author_evidence: Implement session ran as Claude (claude-opus-5-5) in this attended launch; no agent override.
head: abf470ffee51d30620bc1e396c14bfe9e20d972e
base: 6e6ad6d34cc8fdc74265dedddacbee0ce4ab925a
depth: deep
rationale: Changes the step shape of a shipped workflow, the live prompt of in-flight code/with-review peer-review steps, checkout entry policy, and unattended autofix routing.
implementation: Extracts the with-review peer-review prose into a code/peer-review skill, adds an other-agent peer-review step to code/design-then-implement, routes autofix to code/with-review with a no-peer fallback to code/with-self-review, and documents in every workflow without an other-agent step why it has none.
deviations: None from the owner-approved design recorded under ## Design.
limitations: Frozen tickets keep their step lists; design-then-implement tickets frozen earlier still skip code review. Older with-review snapshots now compose a pointer section rather than the full instructions, relying on the agent to read the skill file.
files:
  coga/skills/code/open-pr/SKILL.md: Live twin of the open-pr skill wording update.
  coga/skills/code/peer-review/SKILL.md: Live twin of the new peer-review skill.
  coga/workflows/autoclose-merged/sweep.md: Says why this non-code workflow has no other-agent review.
  coga/workflows/blocker-reminders/run.md: Says why this non-code workflow has no other-agent review.
  coga/workflows/branch-sweep/sweep.md: Says why this non-code workflow has no other-agent review.
  coga/workflows/brief-for-human.md: Says why this non-code workflow has no other-agent review.
  coga/workflows/build/onboarding.md: Says why this non-code workflow has no other-agent review.
  coga/workflows/direct/body.md: Says why this no-PR workflow has no other-agent review.
  coga/workflows/draft-for-human.md: Says why this non-code workflow has no other-agent review.
  coga/workflows/maintenance/with-approval.md: Says why this operational workflow has no other-agent review.
  coga/workflows/phone-home/run.md: Says why this non-code workflow has no other-agent review.
  coga/workflows/skill-update/run.md: Says why this non-code workflow has no other-agent review.
  coga/workflows/usage-report/post.md: Says why this non-code workflow has no other-agent review.
  docs/contexts/coga-dev/current-direction/SKILL.md: Notes both main code workflows peer-review and with-self-review is the fallback.
  docs/contexts/coga/checkouts/SKILL.md: Adds design-then-implement peer-review to the entry table.
  docs/contexts/coga/recurring/autofix/SKILL.md: Documents the with-review default and no-peer fallback.
  docs/contexts/coga/workflows/SKILL.md: States the code-review shape rule and the body-note convention.
  src/coga/checkout_policy.py: Entry rows for both peer-review shapes.
  src/coga/commands/bump.py: Stranded-code refusal recommends code/with-review first.
  src/coga/commands/mark.py: Stranded-code refusal recommends code/with-review first.
  src/coga/recurring_autofix.py: autofix_workflow selects with-review or the no-peer fallback.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/SKILL.md: Packaged twin of the checkouts topic.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/autofix/SKILL.md: Packaged twin of the autofix topic.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/workflows/SKILL.md: Packaged twin of the workflows topic.
  src/coga/resources/templates/coga/bootstrap/skills/code/open-pr/SKILL.md: Points at code/peer-review; old-snapshot example for design-then-implement.
  src/coga/resources/templates/coga/bootstrap/skills/code/peer-review/SKILL.md: New shared peer-review step skill.
  src/coga/resources/templates/coga/bootstrap/workflows/brief-for-human.md: Packaged twin of the body note.
  src/coga/resources/templates/coga/bootstrap/workflows/code/design-then-implement.md: Adds the other-agent peer-review step.
  src/coga/resources/templates/coga/bootstrap/workflows/code/with-review.md: Declares code/peer-review; inline section becomes a pointer for old snapshots.
  src/coga/resources/templates/coga/bootstrap/workflows/code/with-self-review.md: Documents it as the single-agent fallback.
  src/coga/resources/templates/coga/bootstrap/workflows/draft-for-human.md: Packaged twin of the body note.
  src/coga/resources/templates/coga/workflows/autoclose-merged/sweep.md: Packaged twin of the body note.
  src/coga/resources/templates/coga/workflows/blocker-reminders/run.md: Packaged twin of the body note.
  src/coga/resources/templates/coga/workflows/branch-sweep/sweep.md: Packaged twin of the body note.
  src/coga/resources/templates/coga/workflows/build/onboarding.md: Packaged twin of the body note.
  src/coga/resources/templates/coga/workflows/direct/body.md: Packaged twin of the body note.
  src/coga/resources/templates/coga/workflows/phone-home/run.md: Packaged twin of the body note.
  src/coga/resources/templates/coga/workflows/skill-update/run.md: Packaged twin of the body note.
  tests/test_bootstrap_workflow_review_sections.py: Skill caveat test and the every-workflow review-or-rationale guard.
  tests/test_checkouts.py: New peer-review rows and legacy-snapshot section behavior.
  tests/test_packaging.py: Registers the new packaged skill.
  tests/test_recurring_autofix.py: Asserts with-review with a peer and the single-agent fallback warning.
review:
  reviewer: none
  kind: none
  status: not-run
  detail: Code review is the next frozen step (other-agent peer-review); owner approval of the design is not code review.
checks:
  - command: python -m pytest
    status: passed
    head: 638a80dc8fdc9c52ed457aff9ed78497f76ed906
    base: 12bde1696235c2bdec2d8d5f3aaf4b23ca6cead8
    detail: 4074 passed, 10 skipped; ran on the working tree committed unchanged as 638a80dc8, before rebasing onto main (main brought only coga/ task and log state).
  - command: python -m pytest tests/test_bootstrap_workflow_review_sections.py tests/test_checkouts.py tests/test_packaging.py tests/test_recurring_autofix.py
    status: passed
    head: abf470ffee51d30620bc1e396c14bfe9e20d972e
    base: 6e6ad6d34cc8fdc74265dedddacbee0ce4ab925a
    detail: 220 passed on the rebased head.
  - command: coga validate --json
    status: passed
    head: 638a80dc8fdc9c52ed457aff9ed78497f76ed906
    base: 12bde1696235c2bdec2d8d5f3aaf4b23ca6cead8
    detail: No error-severity issues (warnings only, pre-existing).
```
