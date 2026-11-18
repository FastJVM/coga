---
title: 'Recipe migration, part 5 (parked): move branch-sweep and autofix replay adapters'
status: blocked
owner: nicktoper
contexts:
- coga-dev/microkernel/objectives
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
    checkout: control
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
    checkout: control
  - name: review-design
    skills: []
    assignee: owner
    checkout: control
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
    checkout: create-or-reuse
  - name: peer-review
    skills:
    - code/peer-review
    assignee: other-agent
    checkout: reuse-required
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
    checkout: control
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
    checkout: reuse-required
step: 1 (design)
agent: claude
---

## Description

Part 5 of the recipe migration, **parked**. Remove the `branch-sweep` and
`autofix-analyze` entries from `runner.RECIPES`, leaving five, by moving each
thin adapter to a command or script ticket while the shared implementations
stay in core:

- `branch-sweep`: the recurring branch-sweep job calls the recipe wrapper,
  while `checkout_disposal._sweep_owned_branches` calls `sweep_branches`
  with an owned-branch restriction and skill-management reuses patch-ID
  support. Keep those shared primitives.
- `autofix-analyze`: recurring scans and named runs use live analysis; this
  recipe independently replays saved records. Keep the shared analysis and
  ticketing; move only the replay adapter.

**Activation condition.** This ticket stays a draft until a generic stateless
publication contract for ticket-run commands exists (expected from
`v1/microkernel/06-read-report-commands-as-ticket-workflows` or its
successor). Before activating, confirm which ticket delivered it, and update
this description. Also requires parts 1–4 (`04`–`04d`) to have merged.

Done when both adapters run from tickets with unchanged behavior, both names
exit 2, and the design step's acceptance criteria hold.

## Context

Rules from `coga-dev/microkernel` (cited, not attached): core keeps shared
infra with at least two real consumers or a reviewed co-versioned command
contract; production `src/coga/` never imports `coga_edge`; count callers of
one symbol, not copies of one body. Read its "Edge packaging invariants"
section, plus `coga-dev/packaging`, `coga-dev/testing` and the package-owned
`coga/edge-code`, `coga/script-tickets` and `coga/state-publication` under
`src/coga/resources/templates/coga/bootstrap/contexts/`.

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
          checkout: create-or-reuse        # Entry checkout: control, create-or-reuse, reuse-required, manual.
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

## Design step status (2026-11-16)

Not started: the ticket's own activation condition is unmet at main 299e14222.

- Parts 1–4: `v1/microkernel/04-gigantic-refactor-move-recurring-recipes-out-of-co`
  is at step 6 (review), PR #1245 open; it introduces `runner.run_entry`,
  `RECIPE_ROOTS` and `state_sweep`, which this migration would build on.
  `04b`, `04c`, `04d` are all blocked waiting on that merge.
- Publication contract: `v1/microkernel/06-read-report-commands-as-ticket-workflows`
  is at step 7 (review), PR #1240 open; not yet on main.

Designing against unmerged PR heads would cite symbols that may change, so the
spec waits. When both merge: confirm 06 delivered the generic stateless
publication contract, update the Description's activation paragraph, then write
the spec against main.

---

## Blockers

- [ ] [2026-11-16 22:20] [agent:claude] id=20261116T222004 Activation condition unmet: design needs v1/microkernel/04-gigantic-refactor-move-recurring-recipes-out-of-co (PR #1245; 04b-04d also wait on it) and v1/microkernel/06-read-report-commands-as-ticket-workflows (PR #1240, stateless publication contract) merged to main first. Unblock once both merge, or tell me to design against the open PR heads instead.

## Coordination: branch-sweep simplification first (2026-11-17)

`v1/why-is-the-code-so-big` is the pilot that simplifies
`src/coga/branchsweep.py` (~1,730 lines, proposed target ≤ 300). Move the
branch-sweep recipe only after that ticket lands, so this migration moves the
small module instead of code that is about to be cut. Its spec also moves
`discharge_owned_followups` to `autoclose.py` and drops
`--publish-and-release-local`, which changes what this ticket would migrate.

---

## Blocker reminders

- d09c90ff76bd last_reminded: 2026-11-18 09:02
