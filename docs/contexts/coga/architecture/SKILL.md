---
name: coga/architecture
description: Overview of Coga's model — durable files versus transient runtime, the primitives, the correction loop — and a map of every topic by reader need; attaching it does not load any linked child contract.
---

# Coga architecture

Coga manages what an agent works from. Durable state is markdown in git;
runtime is transient. No database, daemon, or hidden memory: each launch
rebuilds its prompt from files.

## Durable files

- **Tickets** under `coga/tasks/`: frontmatter, body, and a blackboard of
  working state composed into the next launch.
  [tickets](../tickets/SKILL.md), [lifecycle](../lifecycle/SKILL.md),
  [blackboard](../blackboard/SKILL.md).
- **Log**: append-only `coga/log.md`, CLI-written, never composed.
- **Contexts**: facts and contracts ("what is true"), attached per ticket.
- **Skills**: process ("how to do it"), attached to workflow steps or tickets.
- **Workflows**: ordered steps with roles and gates, frozen into tickets.
  [workflows](../workflows/SKILL.md).
- **Recurring templates** and stateless **bootstrap targets**.
- **Config**: shared `coga.toml`, machine-local `coga.local.toml`.

Contexts and skills are `SKILL.md` files. They, workflows and bootstrap
targets resolve local-first, then from the package's bundled batteries.
Links never load content; only attached refs compose
([knowledge](../knowledge/SKILL.md)).

## Transient runtime

`coga launch` runs a ticket's `ticket.py` phase, if any, then composes one
prompt ([prompt-composition](../prompt-composition/SKILL.md),
[session-conduct](../session-conduct/SKILL.md)) and supervises one agent
session per step. Status is the signal of who is working; there is no lock.
What a session learns survives only in files.

## The correction loop

An agent errs; the human fixes the owning file and commits; the next launch
composes the fix. Dream proposes corrections as PRs; nothing changes
operating rules without a merge.

## Topic map

- **Start**: [install](../install/SKILL.md), [init](../init/SKILL.md),
  [first-task](../first-task/SKILL.md), [uninstall](../uninstall/SKILL.md),
  [cli](../cli/SKILL.md); purpose: `product/vision`.
- **Understand**: [principles](../principles/SKILL.md), knowledge and the
  model topics linked above.
- **Configure**: [configuration](../configuration/SKILL.md),
  [context-layout](../context-layout/SKILL.md), [agents](../agents/SKILL.md),
  [secrets](../secrets/SKILL.md).
- **Run work**: [launch](../launch/SKILL.md),
  [script-tickets](../script-tickets/SKILL.md),
  [megalaunch](../megalaunch/SKILL.md),
  [launch-internals](../launch-internals/SKILL.md).
- **Recurring and maintenance**: [recurring](../recurring/SKILL.md)
  ([templates](../recurring/templates/SKILL.md),
  [scheduling](../recurring/scheduling/SKILL.md),
  [delegation](../recurring/delegation/SKILL.md),
  [autofix](../recurring/autofix/SKILL.md)),
  [period-task](../period-task/SKILL.md), [dream](../dream/SKILL.md).
- **State and notifications**: [sync](../sync/SKILL.md),
  [notifications](../notifications/SKILL.md),
  [important](../important/SKILL.md),
  [patterns](../patterns/SKILL.md), [usage](../usage/SKILL.md).
- **Develop Coga**: [extension-model](../extension-model/SKILL.md),
  [skill-management](../skill-management/SKILL.md),
  [codebase](../codebase/SKILL.md), [testing](../testing/SKILL.md),
  [packaging](../packaging/SKILL.md), [releasing](../releasing/SKILL.md);
  code-task conventions [dev/code](../../dev/code/SKILL.md)
  ([checkouts](../../dev/checkouts/SKILL.md),
  [dev-record](../../dev/dev-record/SKILL.md),
  [design-history](../../dev/design-history/SKILL.md)).
- **Guarantees** (attach only to change them): `coga/internals/*`, indexed
  by launch-internals, sync, recurring.
- **Browser work**: [api-first](../../browser/api-first/SKILL.md),
  [dom-backed](../../browser/dom-backed/SKILL.md).
- **Posture** (local): `coga/current-direction`,
  `coga/project-stage`, `coga/roadmap`.
