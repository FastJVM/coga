---
name: coga/current-direction
description: Short, dated product decisions currently in force for Coga, with links to the topics that own each contract; read it to avoid re-litigating closed decisions.
---

# Coga — current direction

Last updated: 2026-09-25.

Each entry is a decision with its date and the topic that owns the resulting
contract. Enduring rules live in those topics, not here. Live execution state
is `coga status` and the ticket bodies; sequencing is
[`coga/roadmap`](../roadmap/SKILL.md); stage posture is
[`coga/project-stage`](../project-stage/SKILL.md). Replaced decisions are in
[`docs/archive/superseded-decisions.md`](../../../archive/superseded-decisions.md).

## In force

- **Documentation is one library under `docs/` (2026-09-22).** Reusable
  knowledge is `docs/contexts/<ref>/SKILL.md`, read by humans and composed
  into prompts; dated evidence, proposals and history sit outside the
  contexts root. Ticket:
  [`redo-documentation-dir-and-merge-it-with-context-b`](../../../../coga/tasks/redo-documentation-dir-and-merge-it-with-context-b.md).
  Authoring rule: [`coga/knowledge`](../knowledge/SKILL.md).
- **V1 marketing is one idea piece, then Show HN (2026-09-21).** See
  [`marketing/plan`](../../marketing/plan/SKILL.md) and
  [`marketing/positioning`](../../marketing/positioning/SKILL.md).
- **PostHog adoption/activity measurement is approved work (2026-09-20,
  confirmed 2026-09-21), not shipped.** It reverses the earlier
  instrumentation ban; the ticket
  [`marketing/add-telemetry`](../../../../coga/tasks/marketing/add-telemetry.md)
  owns scope and must update [`coga/principles`](../principles/SKILL.md) §5
  when it lands. Until then the principle stands.
- **`coga/tasks/v2/` is to be parked out of `coga status` (2026-09-20).**
  The parking follow-up is not yet a ticket; see
  [`coga/roadmap`](../roadmap/SKILL.md) for the inventory and accepted
  validation baseline.
- **Recurring runs are ordinary tickets with a stable identity (by
  2026-09-02).** One `recurring/<name>` task per template, the serviced
  period recorded in `coga/log.md`, completed runs cleaned up by Dream,
  `--force` as a real forced run, and `--all <path>` as the one scheduler
  entry point. Contracts: [`coga/recurring`](../recurring/SKILL.md),
  [`coga/recurring/scheduling`](../recurring/scheduling/SKILL.md),
  [`coga/internals/recurring-admission`](../internals/recurring-admission/SKILL.md).
- **Dream is a recurring template plus an alias; REM is repo-owned recurring
  maintenance; dev hygiene is outside Dream.** Done-ticket cleanup is
  Retro-first, and every processed done ticket is deleted — in a knowledge PR
  when it holds durable knowledge, otherwise directly. Contract:
  [`coga/dream`](../dream/SKILL.md).
- **Ticket metadata is cut to what is read; routing is derived.** Operators
  come from the frozen step's role (`owner` | `agent` | `other-agent`) through
  one pure resolver; `agent:` is frozen at activation; overrides are
  ephemeral; removed fields are rejected, not tolerated. Contracts:
  [`coga/tickets`](../tickets/SKILL.md), [`coga/lifecycle`](../lifecycle/SKILL.md),
  [`coga/agents`](../agents/SKILL.md).
- **Delegated recurring periods are bounded to one explicit agent step.**
  Contract: [`coga/recurring/delegation`](../recurring/delegation/SKILL.md).
- **Thin tickets are designed before they are built.** Use
  `code/design-then-implement` (design → cold evaluation → owner
  `review-design` gate) for one- or two-sentence tickets and
  `code/with-review` when the spec is clear. Contract:
  [`coga/workflows`](../workflows/SKILL.md).
- **Capability-gap detection stays judgment-based.** Unresolved skill refs are
  already errors (`coga validate` `broken-skill`, composition hard-fails); a
  skill that *should* exist is found at authoring (`bootstrap/ticket`,
  `bootstrap/import`) or by Dream/Retro, not by a lint.
- **`coga create` makes a raw, Slack-silent draft; `coga ticket` runs the
  guided interview** on a new or existing ticket. Contract:
  [`coga/tickets`](../tickets/SKILL.md).
- **Aliases are positional pass-through only** and print their expansion.
  Contract: [`coga/configuration`](../configuration/SKILL.md).
- **Manual edits stay silent.** Editing a ticket, blackboard or context does
  not post or log; notifications are for agent-driven transitions. Contract:
  [`coga/notifications`](../notifications/SKILL.md).
- **Control and data planes stay split.** `coga launch` owns
  `active` → `in_progress`; `coga bump` owns `step:`; a human rewind is
  recovery for understood work and a normal move for unknown work. Contract:
  [`coga/lifecycle`](../lifecycle/SKILL.md).

## Open intent, not live direction

- **`workflow` → `playbook` rename.** Parked as
  `v2/rename-workflow-primitive-to-playbook`. It touches a reserved
  frontmatter key, so it needs a design pass (alias versus migration) before
  any mechanical rename. Until it merges, `workflow` is the canonical term;
  do not hand-edit the `workflow:` key ahead of the code change.

## Deliberately deferred

- Inbound Slack → ticket creation (`v2/use-slack-as-a-sync-channel-for-tickets`)
  and an enriched outbound inbox (`v2/issue-inbox-slack`).
- Multi-workspace Slack; one workspace is assumed.
- Real-time sync through a server. Git push/pull is the sync layer through
  about five people; revisit at ten or more.
- `coga update-workflow` to re-snapshot a workflow into in-flight tickets;
  edit frontmatter by hand.
- A scheduler wrapper; operators run `coga recurring` themselves.
