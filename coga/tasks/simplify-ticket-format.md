---
slug: simplify-ticket-format
title: simplify ticket format
status: active
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
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
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
secrets: null
step: 1 (design)
---

## Description

Simplify ticket frontmatter by removing unused or redundant fields and omitting
empty optional metadata. The human approved the field-removal proposal on
2026-09-09; retain an optional per-ticket agent choice and preserve workflow
routing, human approval gates, ownership, and nonempty contexts/skills/secrets.

### Agreed scope

- Remove `human` from ticket metadata. Human workflow steps go to `owner`;
  stop representing a separate accountable owner and human worker.
- Remove persisted top-level `assignee`. Derive the current operator from the
  workflow and its role inputs, and use that result consistently in launch,
  transitions, status, notifications, and sweeps. Keep workflow-step routing
  declarations; independent manual assignment is no longer a separate surface.
- Remove `slug` from ticket metadata. The existing path-qualified `TaskRef`
  remains the identity used by commands, status, and logs. A file copied away
  from its task path no longer carries its original reference in metadata.
- Remove `watchers` and its per-ticket notification-cc behavior. Preserve owner
  notifications and ownership-based sweep selection.
- Make `agent` optional while retaining explicit per-ticket selection. An
  omitted value uses a documented configured default; main-agent and peer-agent
  selection must remain coherent through the workflow.
- Omit empty `contexts`, `skills`, and `secrets` from newly authored/rendered
  tickets; accept absence as empty. Preserve nonempty values and their existing
  validation, prompt-composition, and scoped-secret behavior. Remove residual
  `script: null` entries; the script field is already retired.

Keep `title`, `status`, `owner`, `workflow`, current `step`, repository extension
support, and conditional system state (`delegate`, `period_generation`, and
`launch_generation`). Drafts may remain workflow-less until they are ready;
activation still requires a workflow.

### Design before implementation

Use `code/design-then-implement` because removal of stored assignment changes
execution, and the mechanics need a written design plus owner review. Resolve
these questions in the design step before implementation:

- Specify routing for omitted step roles, draft/terminal tickets without a
  current step, and existing `human` role tokens. Inventory manual assignment
  mismatches and migrate them intentionally; preserve lifecycle position and
  human gates rather than treating every mismatch as an error.
- Specify when an omitted `agent` default is resolved and whether it is frozen
  at activation. State the consequences if config changes between launches,
  including pause/resume and main-agent -> peer-review -> main-agent rotation.
  Define interaction with `launch --agent`, human assists, and megalaunch's
  override behavior; an ephemeral override is not automatically a persistent
  main-agent choice.
- Cover bootstrap launch targets and recurring templates/instances that
  currently use top-level `assignee`, including targets without workflows.
  Preserve their dispatch and human-assist behavior without retaining a second
  assignment model accidentally.
- Describe the rollout across stored workflow snapshots and existing tickets,
  including parked `v2/` drafts. Preserve workflow step order, completion gates,
  status, ownership and working memory. Workflow renaming, wholesale unfreezing,
  and unrelated cleanup of parked designs are outside this ticket.
  Account for control and feature checkouts so older writers cannot rewrite
  converted tickets. If the coordinated rollout cannot fit one reviewable PR,
  propose a split during design for owner approval.

### Completion criteria

Creation, guided authoring, parsing/rendering, validation, launch, workflow
transitions, status/show, notifications, and recurring/megalaunch paths all use
the approved simplified model. Commands display the derived operator where
useful without writing redundant assignment or identity fields back to tickets.
The removed fields have no supported routing/notification behavior left.

Update affected current tickets, bootstrap/recurring resources, templates,
fixtures, tests, and behavioral documentation together. Keep the live and
packaged twins byte-identical wherever required. Apply the approved format
change in place; do not keep two supported schemas, a permanent deprecation
path, or a standalone frontmatter migration framework. Do not rewrite historical
git revisions or `coga/log.md`.

Add meaningful regressions for operator derivation through activation/bump,
human gates and assists, explicit/default agent selection and peer rotation,
absent optional fields, preserved nonempty skill/secret declarations, both task
file forms, and bootstrap/recurring dispatch. Run `python -m pytest` and
`coga validate --json` against the updated example and real repo. Record any
pre-existing repo validation issues separately and introduce no new ones.

## Context

The audit examined all 207 task files at `e49fc7f9` (81 parked under `v2/`, four
recurring instances), eight historical snapshots from May through September,
and relevant commits/source consumers. The snapshot history is a sample, not
every ticket revision. Evidence behind the accepted cuts:

- `human` equals `owner` on 191 current tickets; the other 16 have
  `owner: nicktoper` / `human: nick`. One historical draft,
  `marketing/auto-width-200` at `b2aaa496`, named Nick and Zach separately but
  its workflow did not use the `human` role.
- Of 89 tickets with an explicit current step role, 79 stored assignments match
  and ten differ (blocked/paused/draft); two additional current steps omit a
  role. `65b52b13` (#779) fixed a real activation bug caused by disagreement
  between stored assignee and the first step's role.
- All 207 `slug` values duplicate the task ref. No current task has `watchers`,
  and HEAD-history searches for its declaration under both `coga/tasks/` and
  the former `relay-os/tasks/` found no commits.
- Current `agent` values are 199 Claude / eight Codex. Historical commit
  `bce4e209` deliberately reassigned seven tickets to Codex. Owner is also
  meaningful: 15 current tickets belong to Zach.
- Empty metadata accounts for 150 `contexts` lists, 201 `skills` lists, 148
  `secrets: null` declarations, and 22 retired `script: null` entries. Three
  marketing drafts actually use `marketing/write-post`; three parked drafts
  incorrectly persist `bootstrap/ticket`. Bootstrap targets also use top-level
  skills. Preserve real skill use while dropping empty scaffolding.

Start with `src/coga/ticket.py` (`CANONICAL_TICKET_KEYS`, `Ticket`), `tasks.py`
(`TaskRef`, discovery), `create.py` (`create_task`), `validate.py`
(`REQUIRED_TASK_KEYS`), `bump.py` (`resolve_role_token`,
`resolve_step_assignee`), `mark.py`, `commands/launch.py`, `megalaunch.py`,
`recurring.py`, `compose.py`, and their consumers. `src/coga/config.py` ->
`Config.default_agent` currently selects the first-declared configured agent;
use that contract as the starting point. Inventory all callers rather than
changing only the template. The current `launch --agent` propagation ends at a
non-`agent` role, including `other-agent`; preserve or explicitly redesign that
contract through the owner-reviewed design.

Read and update the affected contract sources: `docs/spec.md`,
`coga/contexts/coga/architecture/SKILL.md`, the relevant CLI/sync/recurring
contexts, `coga/tasks/_template/ticket.md`, authoring instructions in the
packaged `bootstrap/ticket` skill, and their counterparts under
`src/coga/resources/templates/coga/`. These are editing targets, so their full
bodies are intentionally omitted from `contexts:`. Follow
`coga/contexts/dev/code/SKILL.md` for the later implementation checkout/PR loop.
Keep shared ticket IO/routing in existing core infrastructure; do not introduce
opaque state or a new service to replace visible YAML.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
