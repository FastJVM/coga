---
name: coga/workflows
description: Workflow definitions and the frozen snapshot — step format, resolution, freezing and what stays live, role routing, activation gating, `requires:` step gates, and rules for editing a shared workflow or step skill.
---

# Workflows

A workflow is an ordered list of steps in a markdown file:
`coga/workflows/<ref>.md` locally, else the package
`bootstrap/workflows/<ref>.md` (`src/coga/paths.py`
`resolve_workflow_path`; local wins). The package's fallback workflows live
under `src/coga/resources/templates/coga/bootstrap/workflows/`; the workflows
`coga init` seeds into the repo (including `direct/body`, which runs the
ticket body's ordered phases) live under
`src/coga/resources/templates/coga/workflows/`.

An existing local entry always wins, including an unreadable file, directory,
or broken symlink: it must be repaired, never bypassed with bundled text.
`Workflow.load` distinguishes genuine absence (`WorkflowNotFoundError`, also a
`WorkflowError`) from malformed definitions and read failures (`WorkflowError`
with the source path and cause). Resolution also reports inspection failures
(such as an unsearchable directory or a non-directory parent) as `WorkflowError`,
without trying the bundled fallback. Inline prompt composition preserves only the
documented missing-definition placeholder; other load failures refuse launch.

## Definition format

YAML frontmatter holds `name`, `description`, and a non-empty `steps:` list
(`src/coga/workflow.py` `Workflow.load`). Each step has a `name` and may
declare `skills:` (a list; singular `skill:` is rejected), `assignee:` (a role
token), and `requires:` (a gate token). The markdown body may carry a
`## <step-name>` section of inline instructions per step.

`_parse_inline_sections` uses the shared `taskfile.body_sections` parser:
closed backtick and tilde examples retain their `##` lines and subsequent
prose inside the current section. Fenced headings cannot supply instructions
for another step. A real H2 ends the current section even when its name is
not a step; only headings matching a step name supply instructions. Headings
may be indented up to three spaces and have a closing `#` run. Unmatched
fence openers are ordinary text, so they cannot hide later real step headings.

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

**validate-drift: unfrozen-workflow.** Bare workflow references are accepted
on drafts intentionally awaiting first activation and on canceled tickets.
This preserves parked intent and terminal history without activating work
merely to clear a warning. Revisit this decision if an affected ticket enters
a nonterminal status other than draft; activation must freeze its workflow.

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

- `branch`: a usable `branch:` under `## Dev` (`(`-prefixed placeholders
  count as absent); `worktree:` is recorded only for the sandbox-clone
  fallback and is not checked. Bump sees only the ticket copy
  in its own checkout, and a stale `## Dev` from an earlier attempt passes
  while stranding the current one.
- `pr`: a PR URL under `## Dev`, written by `coga open-pr <ref>`; a skipped
  command cannot be papered over with a bump.

Tokens own their predicate and remediation; bump hardcodes no skill name, and
gate transitions publish only to control. Branch and PR mechanics are
[dev/checkouts](../../dev/checkouts/SKILL.md) and
[coga/pr-publication](../pr-publication/SKILL.md).

Gates are exit checks only: no gate, role, or step name says where a step
starts. Launch selects entry checkouts from a closed table of shipped
workflow steps whose consumed instructions match the packaged ones, and
gives every other step manual guidance; that table belongs to
[dev/checkouts](../../dev/checkouts/SKILL.md#which-checkout-a-step-starts-in).
Workflow definitions and frozen snapshots carry no checkout field.

## Branch gate scope

Decision (2026-10-06, owner): do not add the proposed branch/worktree freshness
guard at bump. Its cross-checkout premise predates ordinary tickets' move to
the launch checkout. Branch existence cannot distinguish a wrong old branch
from a legitimate resumed branch; `open-pr` already checks existence and
commits ahead of the base. Revisit on a concrete wrong-branch handoff under
the current ordinary-ticket workflow. Recurring worktrees are outside this
decision.

## Code review gate

`code/with-review` and its siblings freeze `code/address-pr-comments` on an
owner-assigned `review` step: the owner merges and resolves threads, and the
skill is an on-demand assist that never resolves or bumps. Coga does not own
GitHub merge policy, so an unresolved bot thread does not block a merge.
Decision (2026-09-13, owner): keep the human gate; rather than auto-launching
the assist or blocking merges, add post-merge detection. When
`autoclose-merged` closes a ticket it fetches that PR's `reviewThreads` once
and names every unresolved, non-outdated, reply-less thread in the closure's
`coga/log.md` line, its sweep report, and one Slack line, report-only
(`coga/autoclose/sweep` skill, "The unanswered-thread follow-up").

### Obligations the merge does not discharge

Merge-triggered closure is unconditional: `autoclose-merged` marks a ticket
`done` when it sits on its final step, is `active` or `in_progress`, and its
recorded PR has merged (`coga.autoclose._candidate` plus the merged-state
check). It never reads Done criteria, acceptance checklists, or a "still open"
list on the blackboard. So, before `coga open-pr` runs, every obligation the
merge will not discharge — a release publication, an attended or
post-release check, a proof on another platform — is filed as its own draft
(`coga create`) and linked from the handoff, or the work is kept off a
merge-closed workflow such as `code/with-review`. The same holds for a manual
`coga mark done`: a closed ticket owns nothing, so an open item it records is
an orphan. `code/open-pr` carries the pre-check, and each composed path
that runs `coga mark done` directly (`code/implement` and `code/self-qa` on
the already-satisfied path, `direct/body`) runs the same check before it
closes; `code/address-pr-comments` flags an obligation that surfaces during
review before the owner merges.

Worked case (Dream 2026-W43): three tickets closed with recorded, unowned
obligations. `marketing/fix-installer/release-0-4-1-so-new-context-files-publish`
was auto-closed on the merge of PR #998 while its PyPI publication and
post-PyPI clean-install checks were still owed; `marketing/readme-top` was
marked done with a "Still open" list; and
`marketing/fix-installer/add-an-attended-coga-build-step-to-the-clean-insta`
left the macOS walk without a build passthrough. Retro W43 kept them only as
known gaps in PRs #1058, #1059, and #1046.

Reading rules: a ticket still on `review` with a merged PR is not backlog
(autoclose closes it on its next run); count only open PRs as the live queue.
A measurement over retired tickets and merged PRs should gate on a closed time
window, never on an empty live queue, which normal throughput never produces.
