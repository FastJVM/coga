---
name: coga/workflows
description: Workflow definitions and the frozen snapshot — step format, resolution, freezing and what stays live, role routing, activation gating, `requires:` step gates, and rules for editing a shared workflow or step skill.
---

# Workflows

A workflow is an ordered list of steps in a markdown file:
`coga/workflows/<ref>.md` locally, else the package's bundled
`bootstrap/workflows/<ref>.md`; local wins. Shipped workflows, including
`direct/body` (which runs the ticket body's ordered phases), resolve from the
package's `bootstrap/workflows/`; `coga init` copies only the ignored
`workflows/_template.md` authoring starter into the repo.

An existing local entry always wins, including an unreadable file, directory,
or broken symlink: it must be repaired, never bypassed with bundled text. A
file used as a workflow directory is also an error, including on Windows
where the filesystem reports the nested path as missing. A
genuinely absent definition is distinguished from a malformed or unreadable
one, which names its path and cause and refuses launch; only absence composes
the missing-definition placeholder.

## Definition format

A workflow lists ordered steps in Markdown frontmatter. A step names its
role with `assignee:`, can attach `skills:` for judgment work, and can use
`run: <skill-ref>` to run the selected skill directory's `run.py`. The local
directory takes precedence over the packaged copy. Declare an agent role for
a script step. An inherited owner role cannot execute a script.

A step with no script or skill can use an inline `## <step>` section. Owner
steps hand work to the human. See [script tickets](../script-tickets/SKILL.md)
for deterministic dispatch.

## Frozen snapshot, live content

Creation and activation freeze the ordered step names, roles, skills, run
refs and requirements in the ticket. A later workflow edit affects newly
frozen tickets. Attached skills, script files and inline instructions resolve
from current definitions. Older snapshots retain their positions and step
names. Legacy checkout-policy keys are ignored and validation reports them
as obsolete.

When the current definition no longer lists a frozen step, composition and
validation look for an inline `## <old-step-name>` section in the workflow
body. When renaming or removing a step that uses inline instructions, keep
that heading and its instructions until every live ticket using the old step
has finished.

## Roles are the routing

`assignee:` is `owner`, `agent`, or `other-agent`. One pure resolver derives
the operator for every consumer (launch, transitions, script handoffs,
status/show, notifications, sweeps), and nothing is written back:

- `owner` → the ticket's `owner:`, a human handoff.
- `agent` → the ticket's `agent:` main-agent choice.
- `other-agent` → that agent's `[agents.<type>].peer` when set, else the only
  other configured type. Peers are one-directional live configuration, not
  frozen.
- An omitted `assignee:` inherits the nearest preceding declared role in the
  frozen steps; before any declaration it is `owner`.

Human gates are identified by role, never by whether a name is absent from
`[agents.*]`. A live ticket with a missing or inconsistent workflow/step is a
structural error, never a fallback: guessing could skip a human gate. Direct
launch and megalaunch derive routing from the prepared activation before
preflight or any durable write. Validation checks every frozen
`other-agent` step against current config (`unresolvable-step-assignee`),
using the prospective default agent for drafts. Agent types and `peer` are
explained in the shipped `coga.toml` comments ([coga/configuration](../configuration/SKILL.md));
how launch chains across role changes is [coga/launch](../launch/SKILL.md).

## Required at activation, not at draft

A bare workflow reference is accepted on a draft awaiting first activation
and on a canceled ticket, preserving parked intent and terminal history
(revisit if one enters another nonterminal status; activation must freeze
it). A workflow-less draft is valid. `coga mark active` (and launch-time
auto-activation) refuses a ticket without one, pointing at `--workflow` or
`coga ticket`. `coga validate` reports a workflow-less `active`,
`in_progress`, `blocked` or `paused` ticket as `active-no-workflow` (error);
drafts and terminal tickets are left alone. Machine-created one-shots
(recurring periods, `coga retire` tasks) use `direct/body` when their source
declares no workflow: there is no sanctioned workflow-less live task.

## Step completion gates (`requires:`)

A forward `coga bump` checks the current step's requirement. The `branch`
and `pr` gates read the ticket's `## Dev` record. The artifact must be
recorded before the step can advance. See [Git](../git/SKILL.md).

## Code review gate

Code workflows can use a peer or self-review step before the PR workflow
script. Where a final owner gate exists, the owner reviews the PR on GitHub
and decides when to bump and merge. In `code/agent-merge` the final script
verifies the recorded reviewed head and merges the approved change.
[Git](../git/SKILL.md) owns the branch-to-merge sequence.

## Obligations the merge does not discharge

Merge-triggered closure is unconditional: `autoclose-merged` marks a ticket
`done` when it sits on its final step, is `active` or `in_progress`, and its
recorded PR has merged. It never reads Done criteria, acceptance checklists,
or a "still open" list on the blackboard. So, before `git/push-and-open-pr` runs, every obligation the
merge will not discharge — a release publication, an attended or
post-release check, a proof on another platform — is filed as its own draft
(`coga create`) and linked from the handoff, or the work is kept off a
merge-closed workflow such as `code/with-review` or `code/agent-merge`. The
same holds for a manual `coga mark done`: a closed ticket owns nothing, so an open item it records is
an orphan. `code/open-pr` carries the pre-check, and each composed path
that runs `coga mark done` directly (`code/implement` and `code/self-qa` on
the already-satisfied path, `direct/body`) runs the same check before it
closes; `code/address-pr-comments` flags an obligation that surfaces during
review before the owner merges.
