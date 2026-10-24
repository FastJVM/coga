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
step: 4 (review)
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

pr: https://github.com/FastJVM/coga/pull/1096
branch: coga/make-every-code-workflow-review-with-the-other-a-4c644b


The blackboard is a notepad to be written to often as the human and agent works through a task.

## Design

Approved proposal (owner decision below). Frozen tickets are untouched: only tickets
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

## Peer review

Codex direct review completed (2026-10-23) on head
`f262d07ea0a98cec6ea8bfda21a7f268abe42bbe`, against base
`1b58dfef71d04cf1a97b6e6e6be3925b627f8c81`. Reviewed all 42 changed paths,
the approved design, routing/creation consumers, checkout contracts, shared
prompt extraction, and canonical/package twins. No unresolved must-fix findings.

Findings fixed in `f262d07ea`:

- A legacy `code/with-review` snapshot with `skills: []` follows the new inline
  pointer to `code/peer-review`, but checkout policy checked only the pointer.
  A changed local review skill incorrectly selected `reuse-required`. The
  policy now checks both instruction sources and selects `manual` for custom
  instructions. A regression test failed before the fix and passes for old
  and new snapshots; the owning checkouts topic and packaged twin explain it.
- The workflow audit test counted any `other-agent` step, including design
  evaluation. It now requires peer code review after implementation and before
  publication, or the workflow's explicit exception rationale. A mutation
  check confirmed the original design-only workflow fails this guard.

The implementation follows the owner's decision: the self-review fallback and
non-code exceptions remain, with no new stranding guard or frozen-ticket migration.
Codex independently reviewed Claude's implementation, then authored and
self-reviewed the small checkout fix and regression changes. The final aggregate
review receipt is therefore conservatively classified as self-review; it does
not claim independent review of Codex's fixes.

Checks so far: 34 focused regressions passed; 30 packaging tests passed in a
pristine clone; validation found 0 errors and 47 warnings across 164 tickets;
9 smoke cases passed (legacy/current composition, one/two/three-agent peer
selection, non-first default and directional peer settings, old-workflow
rejection). The final full suite passed: **4077 passed, 10 skipped** in 387.64s on the
final committed head. Exact commands and receipts are in `## PR` below.
The ambient Python initially failed collection for missing `tomlkit`; all
verification uses the prepared checkout venv and an absolute `PYTHONPATH`.

No raw-terminal, pager, TTY prompt, or rendered Slack surface changed. The new
plain-stderr fallback diagnostic is covered by the autofix tests. Checks run
on Linux with Python 3.12.12; no Python 3.11 or other-platform run is claimed.
The rebase was clean (main had only task/log updates); the projected ticket was
backed up outside the repo and restored byte-for-byte, then edited only here.

Final head `f262d07ea` is committed and pushed with an explicit lease against
the previous remote head. Ready for the next frozen step to run `coga open-pr`;
publication and owner review/merge remain. No separate post-merge obligation
was introduced.

## PR

```yaml
title: Add peer code review to design workflows and autofix
author: claude/codex
author_evidence: The implement handoff records Claude (claude-opus-5-5) as the original implementer. Codex
  authored the peer-review correction in f262d07ea during this session.
head: f262d07ea0a98cec6ea8bfda21a7f268abe42bbe
base: 1b58dfef71d04cf1a97b6e6e6be3925b627f8c81
depth: deep
rationale: Changes shipped workflow steps, live instructions for frozen tickets, checkout preparation,
  and unattended autofix routing. Inspect the frozen-ticket compatibility and deliberate single-agent
  fallback; the reviewer authored a small follow-up fix.
implementation: Adds other-agent code review between implementation and publication in code/design-then-implement,
  shares code/peer-review with code/with-review, and selects peer review for autofix when its default
  agent has a resolvable peer. Every remaining workflow explains its intentional exception. Legacy inline
  review steps now check the delegated skill before launch automatically reuses a checkout; the workflow
  audit distinguishes design evaluation from code review.
deviations: No change to the owner-approved design. Peer review fixed the legacy checkout-policy omission
  and strengthened the regression guard; no new stranding guard or frozen-ticket migration was added.
limitations: Existing frozen step lists remain unchanged, so older design-then-implement tickets still
  lack code review. Older with-review snapshots must read the skill referenced by their live inline section.
  Peer selection checks configuration, not executable health. Verification ran on Linux/Python 3.12.12;
  Codex self-reviewed its follow-up corrections.
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
  docs/contexts/coga-dev/current-direction/SKILL.md: Notes both main code workflows peer-review and with-self-review
    is the fallback.
  docs/contexts/coga/checkouts/SKILL.md: Documents design-then-implement peer-review entry and verification
    of the legacy inline pointer plus its delegated skill.
  docs/contexts/coga/recurring/autofix/SKILL.md: Documents the with-review default and no-peer fallback.
  docs/contexts/coga/workflows/SKILL.md: States the code-review shape rule and the body-note convention.
  src/coga/checkout_policy.py: Adds the new review entry rows and checks delegated skill content for old
    skill-less review snapshots.
  src/coga/commands/bump.py: Stranded-code refusal recommends code/with-review first.
  src/coga/commands/mark.py: Stranded-code refusal recommends code/with-review first.
  src/coga/recurring_autofix.py: autofix_workflow selects with-review or the no-peer fallback.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/SKILL.md: Packaged twin of the checkouts
    topic.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/autofix/SKILL.md: Packaged twin
    of the autofix topic.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/workflows/SKILL.md: Packaged twin of the workflows
    topic.
  src/coga/resources/templates/coga/bootstrap/skills/code/open-pr/SKILL.md: Points at code/peer-review;
    old-snapshot example for design-then-implement.
  src/coga/resources/templates/coga/bootstrap/skills/code/peer-review/SKILL.md: New shared peer-review
    step skill.
  src/coga/resources/templates/coga/bootstrap/workflows/brief-for-human.md: Packaged twin of the body
    note.
  src/coga/resources/templates/coga/bootstrap/workflows/code/design-then-implement.md: Adds the other-agent
    peer-review step.
  src/coga/resources/templates/coga/bootstrap/workflows/code/with-review.md: Declares code/peer-review;
    inline section becomes a pointer for old snapshots.
  src/coga/resources/templates/coga/bootstrap/workflows/code/with-self-review.md: Documents it as the
    single-agent fallback.
  src/coga/resources/templates/coga/bootstrap/workflows/draft-for-human.md: Packaged twin of the body
    note.
  src/coga/resources/templates/coga/workflows/autoclose-merged/sweep.md: Packaged twin of the body note.
  src/coga/resources/templates/coga/workflows/blocker-reminders/run.md: Packaged twin of the body note.
  src/coga/resources/templates/coga/workflows/branch-sweep/sweep.md: Packaged twin of the body note.
  src/coga/resources/templates/coga/workflows/build/onboarding.md: Packaged twin of the body note.
  src/coga/resources/templates/coga/workflows/direct/body.md: Packaged twin of the body note.
  src/coga/resources/templates/coga/workflows/phone-home/run.md: Packaged twin of the body note.
  src/coga/resources/templates/coga/workflows/skill-update/run.md: Packaged twin of the body note.
  tests/test_bootstrap_workflow_review_sections.py: Checks the extracted authorship caveat and requires
    code review after implementation and before publication, or an explicit exception rationale.
  tests/test_checkouts.py: Covers new entry rows, old snapshots, and custom review-skill rejection for
    both current and legacy steps.
  tests/test_packaging.py: Registers the new packaged skill.
  tests/test_recurring_autofix.py: Asserts with-review with a peer and the single-agent fallback warning.
review:
  reviewer: codex
  kind: self
  status: passed
  head: f262d07ea0a98cec6ea8bfda21a7f268abe42bbe
  base: 1b58dfef71d04cf1a97b6e6e6be3925b627f8c81
  detail: Direct review completed on all 42 final diff paths with no unresolved must-fix findings. Codex
    independently reviewed Claude's implementation, then authored and re-reviewed the legacy checkout-policy
    fix and test correction; the aggregate is classified as self-review rather than claiming independent
    review of those corrections.
checks:
- command: env PYTHONPATH=/home/n/Code/claude/coga/src .venv/bin/python -m pytest
  status: passed
  head: f262d07ea0a98cec6ea8bfda21a7f268abe42bbe
  base: 1b58dfef71d04cf1a97b6e6e6be3925b627f8c81
  detail: 4077 passed, 10 skipped in 387.64s; complete suite on the final committed head, Linux/Python
    3.12.12.
- command: env PYTHONPATH=/tmp/coga-peer-review-nq_k6gnx/pristine/src /home/n/Code/claude/coga/.venv/bin/python
    -m pytest tests/test_packaging.py
  status: passed
  head: f262d07ea0a98cec6ea8bfda21a7f268abe42bbe
  base: 1b58dfef71d04cf1a97b6e6e6be3925b627f8c81
  detail: 30 passed in 4.89s, run from a fresh clone at /tmp/coga-peer-review-nq_k6gnx/pristine on the
    final head; wheel contents and canonical/package identity passed.
- command: env PYTHONPATH=/home/n/Code/claude/coga/src .venv/bin/python -m coga.cli validate --json
  status: passed
  head: f262d07ea0a98cec6ea8bfda21a7f268abe42bbe
  base: 1b58dfef71d04cf1a97b6e6e6be3925b627f8c81
  detail: 0 errors and 47 warnings across 164 checked tickets; no --fix or external notification check
    requested.
- command: env PYTHONPATH=/home/n/Code/claude/coga/src:/home/n/Code/claude/coga .venv/bin/python /tmp/coga-peer-review-nq_k6gnx/review_smoke.py
  status: passed
  head: f262d07ea0a98cec6ea8bfda21a7f268abe42bbe
  base: 1b58dfef71d04cf1a97b6e6e6be3925b627f8c81
  detail: '9 smoke cases passed: old/current prompt composition, one/two/three-agent routing, non-first
    default, directional explicit peers, and rejection of the original design-only workflow by the audit
    guard.'
- command: git diff --check origin/main...HEAD
  status: passed
  head: f262d07ea0a98cec6ea8bfda21a7f268abe42bbe
  base: 1b58dfef71d04cf1a97b6e6e6be3925b627f8c81
  detail: Passed; all 42 diff paths have preparation explanations, and all 14 changed packaged/canonical
    pairs were separately confirmed byte-identical.
```
