---
title: "Recipe migration, part 4: move Dream's validate-drift and orphan-marker workers to the edge"
status: draft
owner: nicktoper
contexts:
  - coga-dev/microkernel/objectives
workflow:
  name: code/with-review
  steps:
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
step: 1 (implement)
---

## Description

Part 4 of the recipe migration. Move Dream's two Python workers,
`validate-drift` (847-line `dream_validate_drift.py`) and
`cleanup-orphan-markers` (336-line `dream_cleanup_orphan_markers.py`), into
`coga_edge.validate_drift` and `coga_edge.cleanup_orphan_markers`, and remove
both `runner.RECIPES` entries. Dream's packaged `ticket.md` phases call
`coga run validate-drift` and `coga run cleanup-orphan-markers` today.

Done when Dream's phases invoke the edge workers, both names exit 2 through
`coga run`, and the checklist below holds.

### Invocation (owner decision 2026-11-16)

Dream stays agent-backed. Its ordered phases invoke the workers as
`python -m coga_edge.<worker>`, with the same flags they pass today. Do not
add a Dream `ticket.py`, a child task, or general attachment copying. A full
local Dream fork copies the worker module beside its ticket and points its
phase text at that local file; document that passage in the edge-code
upgrade procedure. These workers never bump, but still get 04's exit
publication. Their `--cwd` cross-root parsing supplies the root resolver.

### Behavior to preserve

Drift repair and full classifier coverage; the orphan-marker scan stays
report-only.

### Surfaces to update in the same PR

Dream's packaged `ticket.md` Phase 1/5 passages; skills
`bootstrap/dream/tasks/validate-drift` and
`bootstrap/dream/tasks/cleanup-orphan-markers`; plus the shared list below.
The migration fixtures must include frozen Dream Phase 1/5 instructions and
parked or customized Dream copies.

### Acceptance

- [ ] Both entries removed; names exit 2; no core stub.
- [ ] Classifier/repair and report-only scan tests pass against the edge modules.
- [ ] Both private `append_report` copies are deleted in favor of
      `blackboard.append_blackboard_report`.
- [ ] Old and new Dream passages are covered by fixtures against the
      installed wheel and a complete local fork.
- [ ] The shared migration rules below are satisfied.

### Shared migration rules (from the group record in 04)

Depends on `v1/microkernel/04-gigantic-refactor-move-recurring-recipes-out-of-co`
(shared reporting/publication infra) being merged; that ticket also holds the
registry disposition table and the owner decisions of 2026-11-16. Start from
current main after that merge.

- **Edge home.** The job moves to `src/coga_edge/<recipe_name>.py`. Its
  packaged definition selects it; core never imports or path-loads it.
  It imports only stdlib and shared `coga.*`, never sibling edge modules, so
  a copied module is a complete local fork.
- **Remove the registry name.** Delete the `runner.RECIPES` entry and the
  core module. The removed name takes the existing unknown-recipe exit-2 path
  in `commands/run.py`; add no forwarding entry or core stub.
- **Entry sequence.** Use 04's shared report → publish → bump sequence.
  Scheduled runs bump exactly once after success and propagate bump failure;
  manual runs never advance the outer task.
- **Reporting.** Report through `blackboard.append_blackboard_report` and
  delete the job's private `append_report` copy, if any. Supply the job's own
  root resolver to `runner.run_reported`.
- **Shared helpers stay.** A helper with another production consumer stays in
  core; audit individual symbols with `grep`, not modules.
- **Old callers.** Follow the package-owned
  `coga/edge-code/edge-code-upgrades.md`. Inventory old template/period
  shims (and, where relevant, frozen Dream passages), including parked and
  customized copies. Ship concrete old/new invocation passages and fixtures
  that test stock, customized and parked callers against the read-only
  installed wheel and a complete local fork, preserving state bytes. Do not
  overwrite running code, frozen workflow/lifecycle state, recurring parent
  blackboards or unknown customizations. Adopting the migration on this
  repo's own periods is a separate rollout: record its plan on this ticket's
  blackboard; do not perform it in the implementation PR.
- **Same-PR owner updates.** Rewrite every surface naming the removed
  spelling or core module (listed per ticket below), plus the `coga/cli`
  recipe index, `coga-dev/microkernel`, `coga-dev/codebase` and the AGENTS.md
  `runner.RECIPES` text. Edit package copies under `src/coga/resources/`;
  keep `coga-dev/` topics local. Packaging checks require one owner, no live
  twins.
- **Verification.** Report production code before/after at named revisions
  as a per-file table (core / edge / scripts, physical lines via `wc -l`),
  marking deleted code and removed duplicates separately from moved code. Run
  the job's suites plus runner/recurring/shared-consumer suites, packaging
  checks and the per-change Linux receipt in `coga-dev/testing` (native
  Windows/macOS receipts are release-only; record them as deferred), plus
  `coga validate` in a disposable fixture.

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
