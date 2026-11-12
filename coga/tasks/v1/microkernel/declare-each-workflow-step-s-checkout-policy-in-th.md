---
title: Declare each workflow step's checkout policy in the workflow file
status: draft
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
step: 1 (design)
contexts:
  - coga-dev/microkernel/objectives
  - coga-dev/principles
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

### Acceptance and reduction evidence

- [ ] In a fresh repo, obtain an editable workflow through the customization
      ticket's path, make peer review use one agent, and verify the intended
      branch is reused even with a new workflow name and edited skill.
- [ ] Editing the source workflow affects newly frozen tickets only; changing
      live instructions does not erase an explicit frozen checkout policy.
- [ ] Parse/freeze/read round trips retain values; invalid values fail loud;
      explicit manual, inherited roles, completion gates and owner assists
      retain their separate semantics.
- [ ] Old snapshots retain documented behavior, including CRLF-equivalent
      skills, with a bounded compatibility plan rather than a second policy
      system for newly authored workflows.
- [ ] Existing branch/linkage, projected-ticket, control freshness, occupied
      checkout and retry/return safeguards remain in shared checkout code.
- [ ] Report removal of name/content inference from the normal declared path;
      count the remaining fallback honestly. Do not claim it was deleted.
- [ ] Update `coga/workflows`, `coga/checkouts` and affected launch/validation
      guidance at their package owners. Cover workflow, validation, checkout,
      composition and launch tests, full Linux suite and native Windows receipt.

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

## Superseded designs

### 2026-11-12 — Design before the current-main refresh

Superseded by: the refreshed Description and Context above, proposed for owner review.
Reason: source, distribution and caller boundaries changed; the owner clarified
the objectives in `coga-dev/microkernel/objectives`. Historical commands,
paths, approvals and test receipts below are evidence, not current instructions.

#### Description

Hackability defect found on 2026-11-12. src/coga/checkout_policy.py chooses which checkout a step starts in (control, create-or-reuse, reuse-required) from a hidden core table keyed by workflow name and step name, and it requires the step's skills to match the shipped copy byte for byte. Copying a workflow under a new name, editing a step, or overriding its skill locally therefore silently drops the step to manual checkout. A contributor customizing code/with-review's peer review for one-agent repos hit this. Declare the checkout policy on each step in the workflow file, have launch read the declaration, keep the table only as a fallback for frozen snapshots that predate the field, and document the customization path in coga/workflows. A user should be able to copy a bundled workflow into coga/workflows/, change it, and keep its checkout behavior.

#### Context
