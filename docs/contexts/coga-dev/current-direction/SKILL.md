---
name: coga-dev/current-direction
description: Short, dated product decisions currently in force for Coga, with links to the topics that own each contract; read it to avoid re-litigating closed decisions.
---

# Coga — current direction

Last updated: 2026-11-12.

Each entry is a decision with its date and the topic that owns the resulting
contract. Enduring rules live in those topics, not here. Live execution state
is `coga status` and the ticket bodies; stage posture is
[`coga-dev/project-stage`](../project-stage/SKILL.md). Replaced decisions are in
[`docs/archive/superseded-decisions.md`](../../../archive/superseded-decisions.md).

## In force

- **Two linked-worktree exceptions (2026-10-14).** Ticket work creates no
  linked worktrees, except the recurring runner's temporary control worktree
  for a parked checkout ([recurring temp worktrees](../internals/recurring-temp-worktrees/SKILL.md))
  and Retro's isolated checkout, created and removed for one Retro pass so
  Retro runs while the operator keeps working in the main tree. Revisit if
  those worktrees leak or become operator-visible noise. Contract:
  [`coga/checkouts`](../../../../src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/SKILL.md).
- **V1 ships for first users and ships hackable (2026-10-27, amended 2026-11-12).**
  The owner requires easy installation and working first-task paths on macOS
  and native Windows, a finished README with matching user documentation, and
  the existing release and PostHog evidence. Usage reporting and commit/log
  work remain in scope. The [numbered execution queue](../../../../coga/tasks/v1/README.md)
  owns the retained tickets and order. On 2026-11-12 the owner pulled the
  microkernel cleanup and the recurring-recipes refactor back into v1
  (`coga/tasks/v1/microkernel/`), reversing their 2026-10-27 deferral:
  hackability is a base promise of the open-source release, and a contributor
  could not customize the peer-review step without finding a package-only
  workflow and a hidden core checkout table. The open-command-placements table
  must be empty before v1 again. Its hackability demo, further context
  restructuring, and Dream fixes stay parked under `coga/tasks/_v2/`. The
  implemented kernel boundary remains owned by
  [`coga-dev/microkernel`](../microkernel/SKILL.md). The owner clarified the
  target as a ticket-centred microkernel with accessible, editable behavior
  and a simpler program; [microkernel objectives](../microkernel/objectives/SKILL.md)
  owns that direction, including customization of wheel-delivered behavior.
- **Documentation is one library under `docs/` (2026-09-22).** Reusable
  knowledge is `docs/contexts/<ref>/SKILL.md`, read by humans and composed
  into prompts; dated evidence, proposals and history sit outside the
  contexts root. History:
  [`docs/archive/context-migration.md`](../../../archive/context-migration.md).
  Authoring rule: [`coga/knowledge`](../../../../src/coga/resources/templates/coga/bootstrap/contexts/coga/knowledge/SKILL.md).
- **Marketing planning contexts are retired (2026-10-15).** The README is
  the public presentation; the idea-piece and launch tickets carry their own
  briefs and remaining publication decisions. Do not recreate a permanent
  campaign context library. Revisit only if recurring work needs shared
  guidance beyond those deliverables.
- **README demo accuracy (2026-10-26).** The July 18, 2026
  [demo](https://www.youtube.com/watch?v=iwnewxJvRPc) is removed from the
  README's onboarding path: its visible top-level `assignee` edits and
  linked-worktree recovery instructions no longer match the current ticket
  and checkout contracts. A generic command-name caveat did not explain
  those differences. Reconsider the link after those scenes are corrected;
  a new recording is not a launch prerequisite. Current reader path:
  [README](https://github.com/FastJVM/coga/blob/main/README.md) and
  [first task](../../../../src/coga/resources/templates/coga/bootstrap/contexts/coga/first-task/SKILL.md).
- **PostHog adoption/activity measurement shipped (decided 2026-09-20,
  landed 2026-09-22).** Default-on, opt-out weekly aggregate snapshots; no
  per-command or agent/session/token instrumentation. It reverses the earlier
  instrumentation ban. Contract: [`coga/recurring/phone-home/ticket.md`](https://github.com/FastJVM/coga/blob/main/src/coga/resources/templates/coga/recurring/phone-home/ticket.md).
- **v2 is a parked wish list (2026-09-20, landed 2026-09-29).** It lives in
  `coga/tasks/_v2/`, outside `coga status`, validation, and Dream; its
  drafts may be stale or contradictory and owe no verdict. Pull one forward
  only by explicit decision, through the premise check in
  [`coga/tasks/_v2/README.md`](../../../../coga/tasks/_v2/README.md); the
  parked-directory rule is [`coga/tickets`](../../../../src/coga/resources/templates/coga/bootstrap/contexts/coga/tickets/SKILL.md).
- **Reliability before convenience (since 2026-09-02).** Bugs that block
  installation, launch, state sync or review take precedence over new
  convenience surfaces. Marketing and documentation work proceed
  independently when they do not change the core task model. (The former
  `coga/roadmap` is archived at
  [`docs/archive/roadmap.md`](../../../archive/roadmap.md).)
- **Recurring runs are ordinary tickets with a stable identity (by
  2026-09-02).** One `recurring/<name>` task per template, the serviced
  period recorded in `coga/log.md`, completed runs cleaned up by Dream,
  `--force` as a real forced run, and `--all <path>` as the one scheduler
  entry point. Contracts: [`coga/recurring`](../../../../src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/SKILL.md),
  [`coga/recurring/scheduling`](../../../../src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/SKILL.md),
  [`coga-dev/internals/recurring-admission`](../internals/recurring-admission/SKILL.md).
- **Dream is a recurring template plus an alias; REM is repo-owned recurring
  maintenance; dev hygiene is outside Dream.** Done-ticket cleanup is
  Retro-first, and every processed done ticket is deleted — in a knowledge PR
  when it holds durable knowledge, otherwise directly. Contract:
  [`coga/recurring/dream/ticket.md`](https://github.com/FastJVM/coga/blob/main/src/coga/resources/templates/coga/recurring/dream/ticket.md).
- **Ticket metadata is cut to what is read; routing is derived.** Operators
  come from the frozen step's role (`owner` | `agent` | `other-agent`) through
  one pure resolver; `agent:` is frozen at activation; overrides are
  ephemeral; removed fields are rejected, not tolerated. Contracts:
  [`coga/tickets`](../../../../src/coga/resources/templates/coga/bootstrap/contexts/coga/tickets/SKILL.md), [`coga/lifecycle`](../../../../src/coga/resources/templates/coga/bootstrap/contexts/coga/lifecycle/SKILL.md),
  [`coga-dev/internals/agent-config`](../internals/agent-config/SKILL.md).
- **Delegated recurring periods are bounded to one explicit agent step.**
  Contract: [`coga/recurring/delegation`](../../../../src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/delegation/SKILL.md).
- **Thin tickets are designed before they are built.** Use
  `code/design-then-implement` (design → cold evaluation → owner
  `review-design` gate) for one- or two-sentence tickets and
  `code/with-review` when the spec is clear, or `code/agent-merge` when the
  owner has opted out of the PR gate and audits after the merge. All three
  have the other agent review the code; `code/with-self-review` is the
  single-agent fallback. Contract:
  [`coga/workflows`](../../../../src/coga/resources/templates/coga/bootstrap/contexts/coga/workflows/SKILL.md).
- **Capability-gap detection stays judgment-based.** Unresolved skill refs are
  already errors (`coga validate` `broken-skill`, composition hard-fails); a
  skill that *should* exist is found at authoring (`bootstrap/ticket`,
  `bootstrap/import`) or by Dream/Retro, not by a lint.
- **`coga create` makes a raw, Slack-silent draft; `coga ticket` runs the
  guided interview** on a new or existing ticket. Contract:
  [`coga/tickets/authoring`](../../../../src/coga/resources/templates/coga/bootstrap/contexts/coga/tickets/authoring/SKILL.md).
- **Aliases are positional pass-through only** and print their expansion.
  Contract: [`coga/extension-model`](../../../../src/coga/resources/templates/coga/bootstrap/contexts/coga/extension-model/SKILL.md).
- **Manual edits stay silent.** Editing a ticket, blackboard or context does
  not post or log; notifications are for agent-driven transitions. Contract:
  [`coga/notifications`](../../../../src/coga/resources/templates/coga/bootstrap/contexts/coga/notifications/SKILL.md).
- **Control and data planes stay split.** `coga launch` owns
  `active` → `in_progress`; `coga bump` owns `step:`; a human rewind is
  recovery when a step went wrong but the premise holds. When the premise is
  wrong, cancel the ticket with its reason, fix the owning context and start
  a new one. Contract: [`coga/lifecycle`](../../../../src/coga/resources/templates/coga/bootstrap/contexts/coga/lifecycle/SKILL.md).
- **Init offers selected missing supporting CLIs (owner reversal,
  2026-09-30).** Users read a missing `gh` as a broken, unprofessional
  install and churn. Interactive `coga init` offers `git` and `gh`; it notes
  `op` without installing it, installs no Python package or skill, and runs
  nothing without a yes. Agent CLI installation offers and links were removed
  2026-11-05, and 2026-11-07 made the remedy a `coga.toml` fix: a missing
  agent CLI points at `cli` in the agent's `[agents.*]` table, while init may
  offer an already-installed CLI as the default. Contract:
  [`coga/init`](../../../../src/coga/resources/templates/coga/bootstrap/contexts/coga/init/SKILL.md).
- **Native Windows is supported (2026-11).** The core port (2026-10-23)
  runs non-interactive commands and deterministic work;
  `v1/14-interactive-coga-launch-on-native-windows` adds attended agent
  sessions through an inherited console and a Job Object, with no
  idle-timeout. Windows Server 2025 is the tested version.
  User-facing contracts: [README "Get started"](../../../../README.md#get-started),
  [`coga/launch`](../../../../src/coga/resources/templates/coga/bootstrap/contexts/coga/launch/SKILL.md#phases-and-routing).
- **The `google-agents-cli-*` skill packs stay on purpose.** This repo keeps
  the seven packs as the live target of the GitHub-backed update path; no
  ticket does ADK work. `anthropic/skill-creator/` is the verbatim
  hand-vendored example. Contract:
  [`coga/skill-management`](../../../../src/coga/resources/templates/coga/bootstrap/contexts/coga/skill-management/SKILL.md).
- **No branch freshness guard at bump (2026-10-06).** The proposed
  branch/worktree freshness check predates ordinary tickets' move to the
  launch checkout; branch existence cannot tell a wrong old branch from a
  legitimate resumed one, and `open-pr` already checks existence and commits
  ahead of the base. Revisit on a concrete wrong-branch handoff under the
  current ordinary-ticket workflow; recurring worktrees are outside it.
  Contract: [`coga/workflows`](../../../../src/coga/resources/templates/coga/bootstrap/contexts/coga/workflows/SKILL.md).
- **The code review step stays a human gate (2026-09-13).** Rather than
  auto-launching `code/address-pr-comments` or blocking merges on unresolved
  threads, `autoclose-merged` reports unanswered threads after the merge.
  Contract: [`coga/workflows`](../../../../src/coga/resources/templates/coga/bootstrap/contexts/coga/workflows/SKILL.md) ("Code review
  gate", "Obligations the merge does not discharge"). Evidence for the
  obligations rule (Dream 2026-W43): three tickets closed with recorded,
  unowned obligations — `marketing/fix-installer/release-0-4-1-so-new-context-files-publish`
  auto-closed on the merge of PR #998 with its PyPI publication and
  clean-install checks owed, `marketing/readme-top` marked done with a "Still
  open" list, and
  `marketing/fix-installer/add-an-attended-coga-build-step-to-the-clean-insta`
  leaving the macOS walk without a build passthrough. Retro W43 proposed
  them as known gaps, but only PR #1046 (macOS harness) merged; #1058 and
  #1059 closed unmerged. 0.4.1 has since published, with its attended gate
  skipped by owner decision (`coga/releasing`). The remaining README checks
  were assigned to a follow-up on 2026-10-26; retiring `marketing/readme-top`
  did not discharge them. First-task claims still need the authenticated
  install evidence, not just an install/init smoke.
  When measuring this queue, a ticket still on `review` with a merged PR is not backlog
  (autoclose closes it next run); count only open PRs as the live queue, and
  gate a measurement over retired tickets and merged PRs on a closed time
  window, never on an empty live queue.

## Open intent, not live direction

- **`workflow` → `playbook` rename.** Parked as
  `_v2/rename-workflow-primitive-to-playbook`. It touches a reserved
  frontmatter key, so it needs a design pass (alias versus migration) before
  any mechanical rename. Until it merges, `workflow` is the canonical term;
  do not hand-edit the `workflow:` key ahead of the code change.

## Deliberately deferred

- Inbound Slack → ticket creation (`_v2/use-slack-as-a-sync-channel-for-tickets`)
  and an enriched outbound inbox (`_v2/issue-inbox-slack`).
- Multi-workspace Slack; one workspace is assumed.
- Real-time sync through a server. Git push/pull is the sync layer through
  about five people; revisit at ten or more.
- `coga update-workflow` to re-snapshot a workflow into in-flight tickets;
  edit frontmatter by hand.
- A scheduler wrapper; operators run `coga recurring` themselves.
- A ticket-split contract (owner decision 2026-09-25): no split skill,
  `## Split` roster, or `Split from` cross-link convention (#889 closed), and
  no oversized-ticket instruction in the `code/*` step skills (#899, removed
  in `2ffcd4f8b`). The rationale, sibling practice, and criterion for revisiting
  the decision belong to
  [coga/tickets/discovery](../../../../src/coga/resources/templates/coga/bootstrap/contexts/coga/tickets/discovery/SKILL.md).
