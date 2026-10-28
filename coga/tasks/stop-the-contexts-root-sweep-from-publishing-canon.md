---
title: Stop the contexts-root sweep from publishing canonical topics without their
  packaged twins
status: in_progress
owner: nicktoper
contexts:
- coga-dev/principles
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
agent: claude
launch_generation: pending:36473822-b74f-46d8-89a4-1779d701e9e3
---

## Description

Coga keeps hand-maintained twins of shipped resources in the package and in this repo's live Coga roots. A feature-branch state sweep can publish the live half to control before the packaged half merges, leaving main's packaging tests red. Remove that duplication by making `src/coga/resources/` the single committed source of shipped content, read from the installed package at runtime, with deliberate repo overrides taking precedence.

Owner decision: shipped definitions live **only in the package** and runtime consumers treat them as read-only. An editable install reads the source tree; an installed wheel reads its resources. Repos, including this one, retain their own overrides, real state, and the explicitly justified physical scaffolding described below. Upgrades should update fallback content without re-copying it into each repo. Recurring parents need this fallback too, with their writable state kept in the repo or clone, never in the package.

Rejected alternatives: excluding twin paths from the sweep, or publishing both halves together. Both treat the symptom and keep the duplication that produces drift.

The ticket is done when this repo has no unapproved live copies of shipped content, every removed copy resolves from the package in editable and fresh-wheel installations, and recurring discovery and execution work without local parents while preserving overrides and writable state. Fresh initialization must use fallbacks for reusable shipped definitions while creating the necessary repo-owned scaffolding; existing installations need a documented migration that preserves customization and state. Packaging tests must enforce the single-source rule and local-only `coga-dev/` audience, and a feature-branch sweep regression must prove that editing packaged content cannot publish half of that change to control or break control's packaging checks. The owning topics, agent instructions, indexes, and links must describe and navigate the new layout, with context navigation checks green.

## Context

### Background

The twins grew from init vendoring (e8fac886f), survived package fallbacks (340ef8033), and became mandatory for user topics in #875 (5c917004d). The owner authorizes the `design` step to read `docs/archive/` for a recorded twin rationale only; raise any conflict with the owner decision at `review-design` rather than deviating.

Observed failures on 2026-10-21: 001aad66f published topic deletions/architecture edits; e9a88b970 published topic edits during `coga create`. Test the publication boundary, not those historical commits.

### Facts the design depends on (verified 2026-10-28)

- `paths.resolve_skill_path`, `resolve_workflow_path`, and `resolve_context_path` fall back only to package `bootstrap/{skills,workflows,contexts}/`. Init seeds outside `bootstrap/`, including `skills/direct/body/SKILL.md` and recurring workflows, need fallback support before deletion. `commands.update.copy_fresh_templates` currently copies everything except `bootstrap/`.
- `paths.recurring_dir` is repo-local; `recurring.scan_due`, `scan_clone_due`, `create_named`, and `list_templates` read it directly. Discovery, validation, status, and named launch must agree on effective parents. Separate definition lookup from writable-state paths; never redirect writers or publication into the package.
- `period_state.parent_ticket_path`, phone-home's `period_state`, and `retire_worklist.template_worklist_path` / `worklist_for_period_task` depend on local parents. Preserve parent blackboard keys, state snapshots, and worklists. Keep the shared serviced-period ledger in `coga/log.md` and clone ledgers local; `branch-sweep` is clone-scoped with no period task.
- `paths.packaged_template_path` reads `files("coga.resources")`; editable installs read `src/coga/` directly. Runtime read-only behavior does not forbid normal source authoring.
- Inventory the entire mapping in `tests/test_packaging.py` (`_live_counterparts`, `_discover_live_packaged_twins`): also include `coga/bootstrap/{address-pr-comments,resolve-conflicts}/ticket.md`, scripts/runbooks, starter templates, and `docs/contexts/.gitignore`. Preserve repo-only content.
- Git needs a physical `coga/.gitattributes` even when identical to its seed. `INTENTIONALLY_DIVERGENT_TWINS` currently exempts `coga/{.gitignore,coga.toml,context.md,log.md}` and `coga/recurring/phone-home/ticket.md`. Preserve their state or approve a state-preserving replacement. Phone-home counters alone should not force a permanently stale definition; every remaining scaffold/override needs an explicit reason.
- `coga-dev/` stays local. Hatch walk / force-include collisions can appear only on a pristine tree; build and install the verification wheel from a fresh disposable clone, outside the editable source import path.

### Scope and verification

- Exercise all shipped parents: `autoclose-merged`, `branch-sweep`, `blocker-reminders`, `dream`, `phone-home`, `skill-update`, `address-pr-comments`, `resolve-conflicts`. Cover discovery, dependency resolution, period/clone execution, overrides, and repeated state updates without package writes; stub outward effects in isolated repos.
- Cover fresh init, customized existing repos with saved state, disabled jobs, and existing frozen periods/workflows. A local state-only directory must not shadow a packaged definition.
- Packaging tests must reject unapproved live counterparts while retaining justified exceptions and required-resource checks. Exercise all resource types in editable and fresh-wheel smoke coverage. The feature-branch regression must prove packaged edits stay off control while ordinary local task/state edits still publish.
- Update `docs/README.md`, `AGENTS.md`, `coga-dev/{packaging,testing,codebase}`, and affected user contracts/shipped instructions. Fix links, including local development topics' links into moved user topics; extend `test_context_navigation_has_no_broken_links` to the new owning tree.

### Rollout constraint

The first deletion is also subject to the sweep: `tests/test_packaging.py` (`_context_distribution_problems`) currently requires live counterparts, and `git._state_areas` includes their root. Design and verify the transition so intermediate state publications, including live-copy deletions, keep control functional and packaging checks green. A steady-state packaged-edit test alone is insufficient. Land fallback/state support and compatible checks before dependent removals; do not bypass publication guards or reintroduce the rejected sweep exclusions.

### Open for the `design` step

- Choose recurring-state storage and override granularity, including sibling scripts/supporting files. Malformed overrides must fail visibly, not silently select package defaults.
- At `review-design`, approve migration of old seeds versus intentional overrides, preservation of state/customizations, `_name` parking and explicit disabling, and defaults for newly bundled jobs. Do not silently re-enable deleted/parked jobs. A documented operator migration is acceptable; automatic migration tooling is not presumed.
- Classify retained init scaffolds and exceptions. Keep one cohesive design; propose sibling implementation tickets at `review-design` if the dependency/rollout plan needs them, per `coga/tickets/discovery`.

### Cited, not attached

- `coga-dev/packaging` (`docs/contexts/coga-dev/packaging/SKILL.md`): read "Where bundled resources live", "Distribution states for a context", "Canonical copies and twins", "Wheel packaging".
- `coga/context-layout` (`docs/contexts/coga/context-layout/SKILL.md`): read "Context audiences" and "Local first, then bundled".
- `coga/recurring/templates` (`docs/contexts/coga/recurring/templates/SKILL.md`): read "Fields", "The template-to-period transform", "First firing is retroactive", "Cross-run state surfaces". `coga/period-task` (`docs/contexts/coga/period-task/SKILL.md`): read "Persistent state lives in the parent's blackboard".
- `coga/recurring/scheduling` (`docs/contexts/coga/recurring/scheduling/SKILL.md`): read "Periods and the serviced-period ledger", "Repo scope and clone scope", "What a sweep does per template", "Variants".
- `coga/init` (`docs/contexts/coga/init/SKILL.md`): read "Fresh repo" and "Clone of a repo that already uses Coga".

These are editing targets, cited rather than attached. Paths above are pre-migration; user-topic owners move to `src/coga/resources/templates/coga/bootstrap/contexts/` and must be updated in the same change.

Sweep mechanics, for the failure only: `git.coga_root_paths` and `git._state_areas` publish the Coga root and `cfg.contexts_root`.

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
