---
name: coga-dev/current-direction
description: Short, dated product decisions currently in force for Coga, with links to the topics that own each contract; read it to avoid re-litigating closed decisions.
---

# Coga — current direction

Last updated: 2026-10-16.

Each entry is a decision with its date and the topic that owns the resulting
contract. Enduring rules live in those topics, not here. Live execution state
is `coga status` and the ticket bodies; stage posture is
[`coga-dev/project-stage`](../project-stage/SKILL.md). Replaced decisions are in
[`docs/archive/superseded-decisions.md`](../../../archive/superseded-decisions.md).

## In force

- **The microkernel cleanup is v1 scope (2026-10-16).** The six
  `microkernel/*` tickets came back from `_v2/`; v1 ships with
  `coga-dev/microkernel`'s "Open command placements" table empty. The target is the
  current kernel line (launch closure including `mark`/`bump`,
  `block`/`unblock`, `create`, fresh `init`, fixed recipes), not the July
  "only `create` is core" direction. A recorded demo of adding a command at
  the edge follows it (`marketing/demo-hackability-ask-claude-to-add-a-command-live`).
  Contract: [`coga-dev/microkernel`](../microkernel/SKILL.md).
- **Documentation is one library under `docs/` (2026-09-22).** Reusable
  knowledge is `docs/contexts/<ref>/SKILL.md`, read by humans and composed
  into prompts; dated evidence, proposals and history sit outside the
  contexts root. History:
  [`docs/archive/context-migration.md`](../../../archive/context-migration.md).
  Authoring rule: [`coga/knowledge`](../../coga/knowledge/SKILL.md).
- **Marketing planning contexts are retired (2026-10-15).** The README is
  the public presentation; the idea-piece and launch tickets carry their own
  briefs and remaining publication decisions. Do not recreate a permanent
  campaign context library. Revisit only if recurring work needs shared
  guidance beyond those deliverables.
- **PostHog adoption/activity measurement shipped (decided 2026-09-20,
  landed 2026-09-22).** Default-on, opt-out weekly aggregate snapshots; no
  per-command or agent/session/token instrumentation. It reverses the earlier
  instrumentation ban. Contract: [`coga/recurring/phone-home/ticket.md`](https://github.com/FastJVM/coga/blob/main/coga/recurring/phone-home/ticket.md).
- **v2 is a parked wish list (2026-09-20, landed 2026-09-29).** It lives in
  `coga/tasks/_v2/`, outside `coga status`, validation, and Dream; its
  drafts may be stale or contradictory and owe no verdict. Pull one forward
  only by explicit decision, through the premise check in
  [`coga/tasks/_v2/README.md`](../../../../coga/tasks/_v2/README.md); the
  parked-directory rule is [`coga/tickets`](../../coga/tickets/SKILL.md).
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
  entry point. Contracts: [`coga/recurring`](../../coga/recurring/SKILL.md),
  [`coga/recurring/scheduling`](../../coga/recurring/scheduling/SKILL.md),
  [`coga-dev/internals/recurring-admission`](../internals/recurring-admission/SKILL.md).
- **Dream is a recurring template plus an alias; REM is repo-owned recurring
  maintenance; dev hygiene is outside Dream.** Done-ticket cleanup is
  Retro-first, and every processed done ticket is deleted — in a knowledge PR
  when it holds durable knowledge, otherwise directly. Contract:
  [`coga/recurring/dream/ticket.md`](https://github.com/FastJVM/coga/blob/main/coga/recurring/dream/ticket.md).
- **Ticket metadata is cut to what is read; routing is derived.** Operators
  come from the frozen step's role (`owner` | `agent` | `other-agent`) through
  one pure resolver; `agent:` is frozen at activation; overrides are
  ephemeral; removed fields are rejected, not tolerated. Contracts:
  [`coga/tickets`](../../coga/tickets/SKILL.md), [`coga/lifecycle`](../../coga/lifecycle/SKILL.md),
  [`coga/agents`](../../coga/agents/SKILL.md).
- **Delegated recurring periods are bounded to one explicit agent step.**
  Contract: [`coga/recurring/delegation`](../../coga/recurring/delegation/SKILL.md).
- **Thin tickets are designed before they are built.** Use
  `code/design-then-implement` (design → cold evaluation → owner
  `review-design` gate) for one- or two-sentence tickets and
  `code/with-review` when the spec is clear. Contract:
  [`coga/workflows`](../../coga/workflows/SKILL.md).
- **Capability-gap detection stays judgment-based.** Unresolved skill refs are
  already errors (`coga validate` `broken-skill`, composition hard-fails); a
  skill that *should* exist is found at authoring (`bootstrap/ticket`,
  `bootstrap/import`) or by Dream/Retro, not by a lint.
- **`coga create` makes a raw, Slack-silent draft; `coga ticket` runs the
  guided interview** on a new or existing ticket. Contract:
  [`coga/tickets/authoring`](../../coga/tickets/authoring/SKILL.md).
- **Aliases are positional pass-through only** and print their expansion.
  Contract: [`coga/configuration`](../../coga/configuration/SKILL.md).
- **Manual edits stay silent.** Editing a ticket, blackboard or context does
  not post or log; notifications are for agent-driven transitions. Contract:
  [`coga/notifications`](../../coga/notifications/SKILL.md).
- **Control and data planes stay split.** `coga launch` owns
  `active` → `in_progress`; `coga bump` owns `step:`; a human rewind is
  recovery when a step went wrong but the premise holds. When the premise is
  wrong, cancel the ticket with its reason, fix the owning context and start
  a new one. Contract: [`coga/lifecycle`](../../coga/lifecycle/SKILL.md).
- **The `google-agents-cli-*` skill packs stay on purpose.** This repo keeps
  the seven packs as the live target of the GitHub-backed update path; no
  ticket does ADK work. `anthropic/skill-creator/` is the verbatim
  hand-vendored example. Contract:
  [`coga/skill-management`](../../coga/skill-management/SKILL.md).

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
