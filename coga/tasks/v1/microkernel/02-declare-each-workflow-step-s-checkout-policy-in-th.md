---
title: Declare each workflow step's checkout policy in the workflow file
status: in_progress
owner: nicktoper
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
  - name: review-design
    skills: []
    assignee: owner
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
step: 3 (review-design)
contexts:
- coga-dev/microkernel/objectives
- coga-dev/principles
agent: claude
---

## Description

Make a workflow step's checkout policy explicit in its definition and frozen
snapshot. This ticket owns the whole declaration change: schema, freezing,
validation, selection, bundled workflows, compatibility and user guidance.
`launch-decomposition` consumes that policy and does not design a competing one.
This is the refreshed proposal for owner scope review.

### Objectives advanced

Hackability: changing peer review or its skill does not lose branch preparation.
Ticket ownership: the workflow states what each step needs. Simplification:
new definitions no longer rely on a hidden table of names and instruction bytes.

### Premise check against main

Snapshot: `49b34b229` (2026-11-12), physical lines including blanks/comments.

1. The defect remains: `checkout_policy.py` (145 lines) selects a closed
   `_ROWS` table and checks resolved skill or inline-section equality.
2. The surfaces resolve: `WorkflowStep`, `_parse_step`, `Workflow.freeze`
   in `workflow.py` (195 lines), frozen-step validation in `validate.py`,
   `select_checkout_policy`, shared `checkouts.py`, and packaged workflows.
   There is no parsed/frozen `checkout` field yet.
3. Requirements are self-contained here and in the attached objectives;
   the contributor's peer-review example is the acceptance case.
4. Local-first workflow/skill resolution already ships. Declaration-driven
   checkout selection does not. Keep the resolvers; replace the hidden policy
   for new explicit definitions.

### Proposed boundary

Use a step field, proposed spelling `checkout:`, with the existing policy
vocabulary: `control`, `create-or-reuse`, `reuse-required`, and `manual`.
The field is data interpreted by the kernel's existing checkout mechanics.
It neither selects an operator nor authorizes bypassing occupancy, Git or
owner-gate checks.

Parse, validate and freeze the field with the step. An explicit valid value
is authoritative regardless of workflow name, step name, skill content or
local customization. Invalid values fail before checkout effects. Role and
`requires:` remain independent. In a workflow definition, an omitted field
defaults to `manual`; freezing always writes the resulting explicit policy.
New snapshots therefore need no inference from a familiar workflow name.

For old frozen snapshots without the field, retain the current closed table
as a compatibility fallback, including its conservative instruction checks.
Do not rewrite frozen tickets automatically. The distinction is absence in an
already frozen snapshot versus the explicit value emitted by the updated
freezer; no schema-version framework is needed. Document that the fallback can
be retired only after old snapshots have completed or undergone an explicitly
reviewed migration. Do not automatically rewrite those snapshots merely to
delete compatibility code.

Populate the declarations in the package-owned code/docs workflows and any
other workflow whose reviewed step requires automatic preparation. A custom
workflow can then use the same primitives. Compose the actual selection and
its reason in the runtime checkout notice.

### Acceptance criteria

Declared path

- [ ] `WorkflowStep` carries `checkout`; `_parse_step` accepts exactly
      `control`, `create-or-reuse`, `reuse-required`, `manual` and raises
      `WorkflowError` naming the step, the bad value and the vocabulary for
      anything else (non-string, empty, unknown). Omitted parses as `manual`.
- [ ] `Workflow.freeze()` writes `checkout:` on every step, after
      `requires:` when present, including `manual`. `create`, activation in
      `mark.py` and bump's bare-ref freeze all inherit this through `freeze()`.
- [ ] `select_checkout_policy` returns the frozen step's explicit value as
      authoritative, independent of workflow name, step name, step skills,
      skill bytes, inline sections, `assignee:` and `requires:`. Its reason
      names the source, e.g. `step 'peer-review' of workflow 'mine/review'
      declares checkout: reuse-required`. No file resolution happens on this
      path.
- [ ] An invalid frozen value (`checkout: branch`, `checkout: 3`) refuses
      before any checkout effect: `select_checkout_policy` raises, launch
      reports it and stops without reserving, creating or switching a branch,
      and `coga validate` reports a `bad-shape` error for that frozen step.
- [ ] Peer-review acceptance (test): a repo-local workflow copied from
      `code/with-review` under a new name (`team/solo-review`), with
      `peer-review` changed to `assignee: agent` and a locally edited
      `coga/skills/code/peer-review/SKILL.md`, freezes
      `checkout: reuse-required` and launch reuses the recorded branch. The
      same frozen ticket keeps `reuse-required` after the live workflow is
      edited to drop the field or the skill is edited again; a ticket frozen
      after that edit gets the new value.
- [ ] Separate semantics stay separate: `checkout: manual` on a step that
      `requires: branch` still runs manual entry and the bump gate still
      requires the branch; an inherited role does not change the policy;
      an owner-held step reached by an explicit assist uses its frozen value.

Packaged definitions

- [ ] The four code/docs workflows declare the policies the current `_ROWS`
      table selects for them (see the table in Proposed shape). Every other
      packaged workflow omits the field and therefore freezes `manual`,
      which is what it gets today.
- [ ] A fresh ticket frozen from each packaged code/docs workflow selects
      the same kind per step as the table selected before the change
      (parametrized test over workflow × step).

Legacy fallback

- [ ] A frozen step **without** a `checkout` key keeps today's behavior
      exactly: the `_ROWS` lookup, step-skill shape check, resolved skill or
      inline-section comparison, CRLF equivalence and the legacy
      `code/with-review` inline peer-review case. Existing
      `tests/test_checkouts.py` legacy cases pass unchanged.
- [ ] The fallback reason says it came from the legacy table (e.g.
      `... has no frozen checkout: (legacy snapshot); ...`) so a user can tell
      which path ran.
- [ ] No code rewrites a frozen ticket to add `checkout:`.

Shared machinery and notice

- [ ] `checkouts.py` keeps every safeguard (control proof, linkage,
      reservation receipts, projection, occupancy, stranded-ticket guard,
      retry/return). Only the policy *source* changes; the re-check
      `select_checkout_policy(...) != policy` in `plan_ticket_checkout` and
      `confirm_ticket_checkout` still detects a changed frozen step.
- [ ] `ticket_notice` names the selected kind and its reason for every
      action (control, switch, external, manual), not only for manual.

Docs and evidence

- [ ] `coga/workflows` documents `checkout:` in the definition format and the
      frozen snapshot list; `coga/checkouts` replaces the closed-table section
      with "the frozen step declares its entry", lists the packaged values,
      and keeps a short "Legacy snapshots" subsection describing the
      fallback and its retirement condition (below). `src/coga/resources/ticket.md`
      frozen example shows `checkout:`. `coga-dev/microkernel` or
      `coga-dev/codebase` mentions of `checkout_policy.py` stay accurate.
- [ ] The PR reports physical line counts of `checkout_policy.py` and
      `workflow.py` (and `validate.py` delta) at the base and head revisions,
      says the declared path does no name/content inference, and states the
      fallback was retained, not deleted, with its line count.
- [ ] Tests: `tests/test_workflow*.py` (parse/freeze round trip, invalid
      values), `tests/test_validate*.py` (frozen invalid value),
      `tests/test_checkouts.py` (declared, legacy, invalid, notice),
      composition/launch tests that assert notice text or frozen snapshots,
      the seeded fixture. Full Linux `python -m pytest`, `coga validate
      --json`, and a native Windows full-suite receipt per `coga-dev/testing`
      (checkout selection is platform-sensitive: CRLF fallback).

### Proposed shape

1. **`src/coga/workflow.py`.** Add a module constant
   `CHECKOUT_POLICIES: tuple[str, ...] = ("control", "create-or-reuse",
   "reuse-required", "manual")` and `DEFAULT_CHECKOUT = "manual"`. Define
   them here, not in `checkout_policy.py`, because `checkout_policy` imports
   `workflow` and `validate` already imports workflow symbols; keep
   `CheckoutPolicyKind` in `checkout_policy.py` as the `Literal` and assert
   in a test that its args equal `CHECKOUT_POLICIES`. Add
   `checkout: str = DEFAULT_CHECKOUT` to `WorkflowStep`; validate it in
   `_parse_step` next to `requires`; emit it in `Workflow.freeze()`.
   Export the constant in `__all__`.
2. **`src/coga/checkout_policy.py`, `select_checkout_policy()`.** After
   locating the current step: if `"checkout" in step`, validate the value
   against `CHECKOUT_POLICIES` (raise a new `CheckoutPolicyError(ValueError)`
   otherwise) and return `CheckoutPolicy(kind, "<label> declares checkout:
   <kind>", named)`. Otherwise fall through to the existing `_ROWS` code,
   unchanged except the reason prefix marking it legacy. Update the module
   docstring: declared value first, closed table only for snapshots frozen
   before the field. Keep `_changed_skill`, `_lf`, `_changed_section`.
3. **Callers of `select_checkout_policy`.** In `src/coga/launch.py`,
   `_prepare_step_checkout()` calls it before `plan_ticket_checkout`; catch
   `CheckoutPolicyError` there (or move the call inside the existing `try`)
   so the launch stops through the same refusal path, with nothing switched
   (`switched=False`). In `src/coga/checkouts.py` the re-check calls inside
   `plan_ticket_checkout`, `_authoritative_ticket` and
   `confirm_ticket_checkout` should convert `CheckoutPolicyError` into
   `CheckoutPreparationError` at the same stage. Verify that launch's
   earlier preflight does not already reject the ticket; if it does (via
   `assert_task_valid`), the in-selector raise is defense in depth, not the
   primary gate.
4. **`src/coga/validate.py`, `_check_step_shape()`.** Add a `checkout`
   check beside `requires`: if the key is present and the value is not in
   `CHECKOUT_POLICIES`, emit `Issue(kind="bad-shape", ...)` with severity
   error. Absence is valid (legacy snapshot).
5. **`src/coga/checkouts.py`, `ticket_notice()`.** Append
   `Checkout policy: <kind> — <reason>.` to the summaries that do not already
   carry the reason (switch, stay/control, external). Keep the manual text.
6. **Packaged workflows** under
   `src/coga/resources/templates/coga/bootstrap/workflows/`, matching the
   current `_ROWS` selection:

   | Workflow | Step → `checkout:` |
   | --- | --- |
   | `code/design-then-implement` | design, evaluate-design, review-design → control; implement → create-or-reuse; peer-review → reuse-required; open-pr → control; review → reuse-required |
   | `code/with-review` | implement → create-or-reuse; peer-review → reuse-required; open-pr → control; review → reuse-required |
   | `code/with-self-review` | implement → create-or-reuse; self-qa → reuse-required; pr → control; review → reuse-required |
   | `docs/with-review` | implement → create-or-reuse; peer-review → reuse-required; open-pr → control; review → reuse-required |

   Leave recurring/one-step/onboarding workflows without the field. Update
   `tests/fixtures/seeded-repo/coga/workflows/code/*` the same way so the
   fixture stays representative (check `INTENTIONALLY_DIVERGENT_TWINS` in
   `tests/test_packaging.py` if a fixture twin is compared).
7. **Docs** at package owners: `coga/workflows/SKILL.md` (Definition format,
   Frozen snapshot list, a sentence that `checkout:` is metadata, so it is
   frozen and live edits do not reach existing tickets);
   `coga/checkouts/SKILL.md` ("Which checkout a step starts in": declaration,
   default manual, value meanings, the packaged table, "Legacy snapshots"
   with the retirement rule); `src/coga/resources/ticket.md` frozen example
   comment. Check `coga/launch` and `coga/checkouts/manual` for sentences
   that say "shipped step"/"closed table" and point them at the declaration.
8. **Tests**, then run the full suite.

Order: 1 → 4 → 2/3 → 5 → 6 → 7 → tests throughout.

Retirement rule for the fallback (goes in `coga/checkouts`): `_ROWS` and its
content comparison may be deleted only in a reviewed change after no live
ticket in supported repos carries a code/docs snapshot without `checkout:`,
or after an explicitly reviewed migration of those snapshots. Do not
rewrite snapshots merely to delete the fallback.

### Out of scope

- Moving or reshaping CLI command heads, `launch-decomposition`, a new
  agent-session module, locks, hooks or alternative workflow formats.
- Making packaged workflows/skills discoverable or materializing editable
  copies (`make-packaged-behavior-discoverable-and-editable`); this ticket's
  acceptance test copies the workflow by hand.
- Migrating or rewriting existing frozen tickets, or deleting `_ROWS`.
- New policy kinds, or letting `checkout:` change roles, gates, occupancy,
  owner-gate or assist authorization.
- Lints that cross-check `checkout:` against `requires:` or the step role
  (see Open Questions).
- Changing `coga run prepare-checkout` (direct chat), which does not read
  the step policy.

## Context

Read `coga-dev/microkernel/objectives`, `coga-dev/testing` and
`coga-dev/packaging`. The user contract owners are
`src/coga/resources/templates/coga/bootstrap/contexts/coga/workflows/SKILL.md`
and `.../coga/checkouts/SKILL.md`; packaged workflow definitions live under
`src/coga/resources/templates/coga/bootstrap/workflows/`.

This ticket is independent of moving CLI heads and does not need a new
agent-session module. It can be implemented first after the refresh is
accepted. The complete fresh-user acceptance case also needs
`make-packaged-behavior-discoverable-and-editable`. Do not add locks, generic
hooks, alternative workflow representations or automatic frozen-ticket edits.

### Code map (verify by symbol; lines drift)

- `src/coga/checkout_policy.py`: `select_checkout_policy(cfg, ticket)` reads
  `ticket.workflow` and `ticket.current_step()`; `_ROWS` keyed by
  `(workflow name, step name)`; `_changed_skill` compares resolved vs
  `bootstrap_skill_path` bytes with `_lf` CRLF normalization;
  `_changed_section` compares live vs packaged inline sections.
- Callers: `launch.py` `_Launcher._prepare_step_checkout()` selects once and
  passes the policy to `checkouts.plan_ticket_checkout()`; that function and
  `_authoritative_ticket()` / `confirm_ticket_checkout()` re-select and
  refuse on inequality; `ticket_notice()` composes the runtime notice; only
  `_manages_branch_checkout()` launches reach this path (attended, ordinary,
  non-recurring).
- `plan_ticket_checkout()` branches on `policy.kind`: `control`/`manual`
  stay; `reuse-required` without `branch:` refuses (or accepts
  `## Already satisfied`); `create-or-reuse` reserves and creates.
- Freezing: `Workflow.freeze()` is the only snapshot writer, called from
  `create.py`, `mark.py` (activation of a bare ref) and `commands/bump.py`.
- Frozen-step validation: `validate.py` `_check_step_shape()` already checks
  `assignee` and `requires`; no unknown-key rejection exists, so a frozen
  `checkout` key is accepted today and ignored.
- Docs: `coga/checkouts/SKILL.md` "Which checkout a step starts in" holds
  the closed table that this ticket replaces.
- Baseline at `b3ade821e`: `checkout_policy.py` 145, `workflow.py` 195
  physical lines.

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

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Open Questions

1. **Default for an omitted field.** The Description fixes `manual`. An
   alternative is making `checkout:` required in definitions; that breaks
   every existing custom workflow at load. Spec follows `manual`; confirm.
2. **Freeze noise.** Every newly frozen step, including recurring one-step
   period tickets, gains `checkout: manual`. Needed so absence means
   "legacy". Accept, or freeze only for non-manual values and treat absence
   in *new* snapshots as manual (would need a marker to tell new from old,
   which the Description rejects)?
3. **Cross-field lint.** Should `coga validate` warn on a definition step
   with `requires: branch` but `checkout: control|manual`? Left out of
   scope; a cheap follow-up if wanted.
4. **Fallback retirement owner.** Spec records the retirement rule in
   `coga/checkouts`; should a parked follow-up ticket also be created now?

## Evaluator review

Cold review, 2026-11-12. **Not ready as written: settle the refusal boundary
below before implementation.** The declaration/default/freeze/fallback design
otherwise fits the current machinery and is one coherent PR. This is evidence
for owner review, not owner approval. The body and frozen workflow are unchanged.

Reviewed source at `1c8b6b14465416e1ac75f86f852d88f5506ec451`, then fetched
and fast-forwarded to `83a6a9e5fdf6ad26685f93113d5a1ca4fba031bc` before
writing this review. The relevant Python and test files did not change;
intervening workflow/context edits were inspected. No implementation branch,
code, or PR was produced.

### Must resolve before implementation

1. **P2 — Define where, and for which frozen steps, invalid policies must
   refuse.** The acceptance criterion promises refusal before *any* checkout
   effect, with no branch switch. In `src/coga/launch.py`,
   `_Launcher._prepare_target()` calls `_CheckoutBoundary.enter()` before
   reading the authoritative ticket; that boundary may already switch a clean
   feature checkout to control. This ordering is an explicit contract in
   `coga/checkouts/launch-boundary`, “Preparation and return”. A catch added
   to `_prepare_step_checkout()` cannot provide the literal promise without
   changing that contract.

   There is also a concrete gap even when starting on control: the proposed
   selector validates only the **current** step, while
   `_Launcher._publish_startup()` calls `assert_task_valid()` **after**
   `checkouts.plan_ticket_checkout()`. A valid current `create-or-reuse` step
   and a later frozen step with `checkout: branch` therefore allow
   `_reserve_and_create()` to create a branch/receipt before whole-ticket
   validation refuses. `_prepare_agent()`'s composition preflight does not
   validate frozen checkout fields. Thus that earlier preflight cannot be
   assumed to close this gap.

   Recommended disposition: explicitly permit the existing initial control
   normalization; require validation of all frozen checkout values before
   managed feature-branch planning, and retain the selector check as defense
   in depth. State whether refusal also covers exempt launches, since
   `_manages_branch_checkout()` excludes those and they do not all reach
   `_publish_startup()`. Add tests for an invalid current value, an invalid
   later-step value with a valid create step, and invocation from a clean
   feature checkout. If only current-step validation in managed launches is
   intended, narrow the acceptance wording instead. Do not move authority
   reads ahead of control normalization implicitly.

### Recommendations

- **Exercise the legacy path explicitly.** `tests/test_checkouts.py::_frozen`
  calls the live `Workflow.load(...).freeze()`. After this change it will
  emit `checkout:` even in `test_policy_supports_older_frozen_snapshots` and
  the CRLF/edited-skill/inline compatibility cases. Give those cases an
  snapshot helper that removes `checkout`, preserving their existing behavior
  assertions; separately exercise freshly frozen declarations. Otherwise
  unchanged legacy tests either fail against the intentionally authoritative
  declaration or stop exercising `_ROWS`. Existing parse/freeze tests are
  in `tests/test_primitives.py::test_workflow_*`, not a current
  `tests/test_workflow*.py` file.
- **Correct the final re-check call site.** In `src/coga/checkouts.py`,
  `recheck_ticket_checkout()` contains the direct selector call used by
  `_publish_startup()` at stage `startup preflight`. Proposed shape item 3
  omits it. `confirm_ticket_checkout()` instead reaches the selector through
  `_authoritative_ticket()`. Include the actual direct call in the new-error
  translation and refusal tests.
- **Include the kind in legacy manual notices too.**
  `checkouts.ticket_notice()`'s current manual arm includes the reason but
  never says `manual`; the proposed legacy reason prefix does not add it.
  Keeping that arm verbatim misses the all-actions notice criterion for old
  snapshots. Preserve its guidance while adding the same explicit kind/reason
  presentation, and test declared and legacy manual selection.
- **Make the local-definition upgrade consequence visible.** A repo-local
  copy of a code workflow without the new field wins over the updated
  package. Its existing snapshots retain the fallback, but newly frozen
  tickets get explicit `manual`, even if the definition's name and skills
  still match the old table. Document that intentional consequence and the
  remedy of declaring policies in the local definition; no snapshot rewrite
  is needed. The seeded `code/with-review.md` is also a custom four-step
  `implement/pr/approve/merge` workflow using `infra/testing-conventions`,
  not a packaged twin. Assign its intended declarations deliberately rather
  than treating it as the packaged step table.

### Verified conclusions and checks

- All requirements are under `## Description` / `## Context`; none is lost
  to an uncomposed top-level section. The attached objectives and principles,
  the named testing/packaging topics, and this design-review workflow fit.
- All 19 packaged code/docs steps match the proposed policy table. All other
  packaged workflows currently select manual. `Workflow.freeze()` has the
  three named production callers; the constant placement avoids an import
  cycle. Roles, gates, and checkout mechanics can stay separate.
- Physical line counts (including blanks/comments) at both `49b34b229` and
  the reviewed source: `checkout_policy.py` 145, `workflow.py` 195,
  `validate.py` 2,039. Retaining the legacy code is an explicit compatibility
  cost, not a deletion claim. Implementation evidence should also count the
  scoped `launch.py` / `checkouts.py` changes, per the attached objectives.
- Reconciled check at `83a6a9e5fdf6ad26685f93113d5a1ca4fba031bc`,
  Pop!_OS 24.04 LTS (Linux), Python 3.12.12:
  `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest tests/test_checkouts.py tests/test_primitives.py -k 'test_policy or test_notice or test_workflow' --basetemp=/tmp/coga-checkout-design-review-20261112-refresh`
  — **35 passed, 129 deselected, 0 skipped, 0 failed**, 1.78s. This is
  design-review baseline evidence, not an implementation or Windows receipt.
- `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m coga.cli validate --task v1/microkernel/02-declare-each-workflow-step-s-checkout-policy-in-th --json`
  — one valid task, no issues. `git diff --check` passed. A final fetch
  confirmed `HEAD == origin/main` at the reviewed revision before handoff.

## Superseded designs

### 2026-11-12 — Design before the current-main refresh

Superseded by: the refreshed Description and Context above, proposed for owner review.
Reason: source, distribution and caller boundaries changed; the owner clarified
the objectives in `coga-dev/microkernel/objectives`. Historical commands,
paths, approvals and test receipts below are evidence, not current instructions.

#### Description

Hackability defect found on 2026-11-12. src/coga/checkout_policy.py chooses which checkout a step starts in (control, create-or-reuse, reuse-required) from a hidden core table keyed by workflow name and step name, and it requires the step's skills to match the shipped copy byte for byte. Copying a workflow under a new name, editing a step, or overriding its skill locally therefore silently drops the step to manual checkout. A contributor customizing code/with-review's peer review for one-agent repos hit this. Declare the checkout policy on each step in the workflow file, have launch read the declaration, keep the table only as a fallback for frozen snapshots that predate the field, and document the customization path in coga/workflows. A user should be able to copy a bundled workflow into coga/workflows/, change it, and keep its checkout behavior.

#### Context
