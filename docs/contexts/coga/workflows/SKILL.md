---
name: coga/workflows
description: Workflow definitions and the frozen snapshot — step format, resolution, freezing and what stays live, role routing, activation gating, `requires:` step gates, and rules for editing a shared workflow or step skill.
---

# Workflows

A workflow is an ordered list of steps in a markdown file:
`coga/workflows/<ref>.md` locally, else the package
`bootstrap/workflows/<ref>.md` (`src/coga/paths.py`
`resolve_workflow_path`; local wins). Packaged workflows are the `code/*`
loop and `docs/*`; `direct/body` (run the ticket body's ordered phases) is
seeded into the repo by `coga init`.

## Definition format

YAML frontmatter holds `name`, `description`, and a non-empty `steps:` list
(`src/coga/workflow.py` `Workflow.load`). Each step has a `name` and may
declare `skills:` (a list; singular `skill:` is rejected), `assignee:` (a role
token), and `requires:` (a gate token). The markdown body may carry a
`## <step-name>` section of inline instructions per step.

- A step **with** `skills:` composes those skill files; its inline section is
  never read by the agent (human framing only).
- A step **without** `skills:` composes its inline section, so that prose is
  load-bearing. Adding `skills:` to a formerly skill-less step replaces the
  prose, so restate any limit it carried inside the skill.

## Frozen snapshot, live content

The step list is frozen into the ticket's `workflow:` (name plus each step's
`skills`, `assignee`, `requires`) at `coga create --workflow`, or at
activation when a draft carries a bare-string `workflow:` ref
(`src/coga/mark.py` `_freeze_workflow_ref`, which also seeds `step: 1` and is
a no-op once `workflow:` is a dict). Nothing re-freezes an existing ticket.
So a `steps:` edit reaches only tickets created afterwards and bare-ref drafts
activated afterwards; a draft created with `--workflow` stays on the old
steps however late it is activated.

The freeze covers metadata, not content. Step skills resolve live at every
composition (local `coga/skills/`, then package `bootstrap/skills/`), and a
skill-less step's prose is read live from the current named definition.
Editing a shared skill or prose therefore rewrites the prompt of every frozen
ticket using it, including snapshots whose step sequence predates the edit;
this applies to whichever copy resolves, including a bundled skill. Hence:

- A shared step skill refers to "the next frozen step", never a step by name.
- A newly introduced blackboard section is consumed conditionally ("if an
  `## Evaluator review` section is present"), never required.
- Regression-check a changed shared skill by composing it from a pre-change
  snapshot too.

For live tickets, validation requires the frozen `workflow.name` to still
load and every skill-less frozen step to have non-empty inline instructions;
otherwise launch would compose a "not found" or "no instructions" placeholder.
Deleting or renaming a definition in use is therefore a validation error.
Validation also resolves step skills of recurring templates before any period
exists.

## Roles are the routing

`assignee:` is `owner`, `agent`, or `other-agent`. `src/coga/bump.py`
`resolve_operator` is the one pure resolver every consumer uses (launch,
transitions, script handoffs, status/show, notifications, sweeps), and
nothing is written back:

- `owner` → the ticket's `owner:`, a human handoff.
- `agent` → the ticket's `agent:` main-agent choice.
- `other-agent` → that agent's `[agents.<type>].peer` when set, else the only
  other configured type (`resolve_other_agent`). Peers are one-directional
  and live configuration, not frozen.
- An omitted `assignee:` inherits the nearest preceding declared role in the
  frozen steps; before any declaration it is `owner`.

Human gates are identified by role, never by whether a name is absent from
`[agents.*]`. A live ticket with a missing or inconsistent workflow/step is a
structural error, never a fallback: guessing could skip a human gate. Direct
launch and megalaunch derive routing from the prepared activation before
preflight or any durable write. Validation checks every frozen
`other-agent` step against current config (`unresolvable-step-assignee`),
using the prospective default agent for drafts. Agent configuration is
[coga/agents](../agents/SKILL.md); how launch chains across role changes is
[coga/launch](../launch/SKILL.md).

## Required at activation, not at draft

A workflow-less draft is valid. `coga mark active` (and launch-time
auto-activation) refuses a ticket without one, pointing at `--workflow` or
`coga ticket`. `coga validate` reports a workflow-less `active`,
`in_progress`, `blocked` or `paused` ticket as `active-no-workflow` (error);
drafts and terminal tickets are left alone. Machine-created one-shots
(recurring periods, `coga retire` tasks) use `direct/body` when their source
declares no workflow: there is no sanctioned workflow-less live task.

## Step completion gates (`requires:`)

Before `coga bump` advances **off** a step with `requires: <token>`, it runs
that token's predicate on the blackboard (`src/coga/step_gate.py`
`STEP_GATES`); a miss fails loud with the remediation, regardless of which
agent owns the step. Unknown tokens fail. Human rewinds are never gated.

- `branch`: usable `branch:` **and** `worktree:` under `## Dev`
  (`(`-prefixed placeholders count as absent). Bump sees only the ticket copy
  in its own checkout, and a stale `## Dev` from an earlier attempt passes
  while stranding the current one.
- `pr`: a PR URL under `## Dev`, written by `coga open-pr <ref>`; a skipped
  command cannot be papered over with a bump.

Tokens own their predicate and remediation; bump hardcodes no skill name, and
gate transitions publish only to control. Branch and PR mechanics are
[dev/checkouts](../../dev/checkouts/SKILL.md) and
[coga/internals/pr-publication](../internals/pr-publication/SKILL.md).
