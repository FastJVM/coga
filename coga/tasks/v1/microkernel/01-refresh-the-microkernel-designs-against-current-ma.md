---
title: Refresh the microkernel designs against current main
status: done
owner: nicktoper
workflow:
  name: draft-for-human
  steps:
  - name: agent-produces
    skills: []
    assignee: agent
  - name: human-owns-and-finishes
    skills: []
    assignee: owner
  - name: report-to-coga
    skills: []
    assignee: agent
agent: claude
contexts:
- coga-dev/principles
- coga-dev/microkernel/objectives
---

## Description

The microkernel tickets returned to v1 on 2026-11-12 because hackability is a
base promise of the open-source release: a contributor got lost changing peer
review. Apply the four-question premise check in `coga/tasks/_v2/README.md`
against current main, refresh every child's inventory and proposed boundary,
identify delivered/obsolete work, and propose ownership and execution order.
The owner decides the refreshed scope before any child implementation resumes.

Judge every design against the attached `coga-dev/microkernel/objectives`
context, linked from the group's README. For each child, state which objective
it advances and drop or defer work that advances none.

### Owner clarification — 2026-11-12

The owner asked to establish the objectives in a standing Coga-dev context
before continuing the design refresh. Its owner is
`docs/contexts/coga-dev/microkernel/objectives/SKILL.md`. The refreshed designs
will apply that direction, including access to editable wheel-delivered
behavior; detailed scope and execution order still need review.

### Parent premise check

Snapshot: `main` at `49b34b229` (2026-11-12), reconciled with the subsequent
draft-creation state at `1cc548c63`; production source is unchanged between them.

1. The subject still exists: the group retained stale plans after returning
   to v1. Establishing the objectives alone did not refresh those designs.
2. All eight original child paths resolve. Their current bodies now identify
   relocated/removed surfaces; the new accessibility draft adds the missing
   objective owner at the task level.
3. The children carry their requirements and retained review evidence on disk.
   No retired task or archived audit is required to supply missing substance.
4. Several implementations shipped, but no complete group refresh had. This
   deliverable removes that already-delivered work from proposed implementation
   scopes and makes the remaining owner decisions visible.

### Proposed architecture for review

Use one ticket execution model. A stateless command ticket carries a script
or agent procedure and receives ordinary operands; persistent work carries its
state and workflow in its ticket. Aliases provide the familiar command names.
Scripts stay deterministic. No stateful task is manufactured merely to print
a report or execute a stateless command.

The kernel interprets the generic file model and supplies process execution,
prompt composition, shared configuration/IO, checked transitions and
publication. Procedure defaults, queue/report policy and single-job work move
to the ticket that owns them. Keep the actual invariants in shared operations
while reconsidering their user-facing wrappers. A package location, registered
recipe or Python implementation does not establish a permanent kernel home.

Recommend preserving the execution/bootstrap entry points and guarded
state/completion primitives for this pass. Keep the specifically justified
publication, recurring-admission and chat-receipt contracts in the recipe
audit; retain uninstall's recovery entry unless its replacement works with
broken config. These are proposed bounded exceptions with named reasons,
not an exemption for every current command. The recipe design proposes five
job moves first, then two adapter moves after their contracts are proven.

Expose the owning files and complete editable local implementations through
one customization path. The wheel remains the source of defaults; deliberate
local overrides are the user's copies. This introduces a real tradeoff:
defaults follow package upgrades, while a full local fork becomes the user's
maintenance responsibility. Copying an import shim alone does not meet the goal.

### Scope and dependency decisions proposed

- The existing checkout declaration ticket owns the step field, freezing,
  validation, runtime selection and legacy fallback. The launch ticket consumes
  that result. New snapshots always carry an explicit policy, with `manual`
  as the default; only old snapshots use the compatibility table.
- The new `make-packaged-behavior-discoverable-and-editable` draft owns access
  to defaults and complete local copies. It joins checkout declaration in
  the first end-to-end acceptance case: customize peer review for one agent.
- `launch-decomposition` now targets remaining session/caller boundaries;
  its originally proposed CLI/service split is already delivered. It owns the
  minimal generic stateless contract required by read and write command tickets.
- `residual-command-surfaces` additionally owns the previously unassigned
  `recurring promote` classification. Read/report owns `recurring list`;
  the recipe ticket owns `recurring-scan` and registry contraction.

The group [README](README.md#proposed-execution-order) owns the proposed order
and child scope map. It removes the blanket "all work waits for the full
launch decomposition" dependency. Each child's body owns its detailed proposal.

### Known design risks to resolve before implementation

Read commands currently skip publication and can load config without an
operator; ordinary launch does not provide that complete contract. A blind
alias would change observable behavior. Prefer a small generic execution/
publication seam, shared by real consumers, over a command-name exception list.
The exact interface remains design work in the launch ticket.

Nested script launch clears the outer supervisor's expected-task/step and
done-marker environment. Session-ending `block`/completion and bootstrap
`slack` therefore cannot be moved unchanged behind a script alias. Preserve
the direct primitive until a narrow verified completion boundary exists;
copying ambient supervisor authority is not the proposed solution.

Full local copies must include the actual implementation and necessary
siblings while preserving recurring state and frozen/running periods.
Removing recipes requires reconciliation of old shims and Dream instruction
passages as well as new wheel contents. The existing upgrade procedure supplies
the starting contract; this refresh does not authorize an external rollout.

### Refresh acceptance

- [x] Every original child and the new accessibility draft has the ordered
      premise check, source inventory, remaining boundary, objective contribution
      and concrete simplifications; abandoned designs remain on disk.
- [x] The group owns a proposed execution order and every open placement row
      has a scope owner. Shipped work is removed from the implementation plan.
- [x] CLI-owned child fields, owner gates and existing review evidence are
      preserved. No child implementation or workflow advance occurs here.
- [x] Reconcile against current main, validate the edited tickets and context
      references, and prepare the handoff to the owner's next workflow step.

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

<!-- coga:blackboard -->

## Report to Coga — 2026-11-12

Produced: refreshed premise checks, inventories, boundaries, objective
contributions and simplifications for all eight original microkernel children;
a new draft child `05-make-packaged-behavior-discoverable-and-editable`; and
the standing objectives context. Superseded designs are kept on disk.

Human decisions: the owner first required the objectives as a standing
context, then accepted the whole refresh ("yes to all"): scope map, execution
order, the new 05 draft, the bounded core exceptions and the full-local-fork
tradeoff. No child was activated or advanced.

Where it landed (all on `main`):

- Objectives: `docs/contexts/coga-dev/microkernel/objectives/SKILL.md`
- Scope map and order: `coga/tasks/v1/microkernel/README.md`
  (`## Child scopes proposed for review`, `## Proposed execution order`)
- Per-child proposals: `coga/tasks/v1/microkernel/02-…` through `10-…`
- Open-row ownership pointer: `docs/contexts/coga-dev/microkernel/SKILL.md`

Next: each child proceeds through its own lifecycle and launch, starting with
checkout declaration (02) and the accessibility draft (05) for the fresh-repo
one-agent peer-review case.

## Refresh handoff — 2026-11-12

The owner first clarified the objectives, then asked to continue with the
designs and tickets. The standing objectives are published and attached.
All eight original children now carry refreshed proposals; the CLI created
the ninth, `make-packaged-behavior-discoverable-and-editable`, as a draft with
the design/review workflow. The group README owns the scope map and proposed
order. The original child designs and review receipts are retained under
Superseded designs and excluded from normal prompt composition.

Source evidence is pinned to `49b34b229`; the later `1cc548c63` commit only
created the new draft and its CLI audit. Relevant shipped changes were proved
from main's content and history: launch API separation (`b3007ef2e`), retire's
command ticket (`953d14094`), wheel edge delivery (`bc46823c4`) and the recurring
package catalog (`d0f4e2c6f`). No archive was read or edited.

Main proposals for owner review:

- Checkout policy stays with its dedicated declaration ticket, independently
  of the full launch decomposition. The new accessibility ticket joins it in
  the fresh-repo one-agent peer-review acceptance case.
- Launch owns the generic stateless read/write and verified completion seams.
  Ordinary reads must not inherit launch's state sweep; nested script commands
  must not silently lose or inherit another session's completion authority.
- Recipe scope starts with five remaining job moves, then proposes moving
  the branch-sweep and saved-autofix adapters while keeping their shared code.
  The five remaining registered contracts have individual reasons; the earlier
  owner-approved open-pr exception is preserved pending any explicit revision.
- Residual command scope now includes `recurring promote`; the standing open
  table names that proposed owner. Authoring-only finalization can move with
  its ticket while shared publication and agent selection remain shared.
- Keep bounded state/completion and uninstall recovery primitives until an
  equivalent edge path is demonstrated. Avoid turning a head-count target
  into a new mutation language or recovery framework.

Only planning state and the open-row ownership pointer changed. No production
code, child status/step/workflow, configuration or manually edited log is part
of this refresh. Owner acceptance of the proposal does not advance child gates;
use each child's existing lifecycle/launch when the scope is accepted.

## Owner decision — 2026-11-12

The owner accepted the refresh as proposed ("yes to all"):

- the child scope map and the proposed execution order in the group README
- the new `05-make-packaged-behavior-discoverable-and-editable` draft
- the bounded core exceptions with their named reasons
- the full-local-fork maintenance tradeoff

Acceptance does not activate or advance any child; each proceeds through its
own lifecycle/launch.

## Verification

- `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m coga.cli validate --task <slug> --json`
  for all ten tickets in this group — all exit 0. The same four pre-existing
  `unfrozen-workflow` warnings remain on the read/report, residual, support and
  orchestration drafts; no new issue was introduced and their CLI-owned
  workflow fields were preserved.
- `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m coga.cli validate --json`
  — exit 0, 96 tasks OK, no errors; repo-wide warnings: 11 unfrozen workflows,
  four large blackboards and two stuck-in-progress records.
- Read-only `compose_prompt_report` checks for all ten tickets — current
  objectives/premise checks compose; historical design bodies are excluded.
- Read-only comparison against `1cc548c63` — all CLI-owned frontmatter
  unchanged, attached context refs resolve, exactly one fence per ticket.
  Compared the eight originals with their retained history; prior design and
  review substance is present on disk.
- `git diff --check` — clean. No behavioral test suite was run for this
  planning-only change; each child names its implementation verification.
- Final reconciliation: fetched `origin/main` at `0e9b189b1`; only three audit
  additions had landed since draft creation. Backed up and byte-verified all
  12 edited files, restored the local baseline, fast-forwarded, and reapplied
  verified copies. Production source and the edited file baselines were unchanged.
  Publish the prepared state, then bump this parent once to owner review.
