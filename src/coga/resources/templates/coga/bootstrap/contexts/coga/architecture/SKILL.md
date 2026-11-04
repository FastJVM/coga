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
  working state composed into the next launch; disposable once done.
- **Log**: CLI-written `coga/log.md`, never composed; the [retention job](https://github.com/FastJVM/coga/blob/main/src/coga/resources/templates/coga/recurring/trim-log/ticket.md) expires eligible old events.
- **Contexts**: facts and contracts ("what is true"), attached per ticket.
- **Skills**: process ("how to do it"), attached to workflow steps or tickets.
- **Workflows**: ordered steps with roles and gates, frozen into tickets.
- **Recurring templates** and stateless **bootstrap targets**.
- **Config**: shared `coga.toml`, machine-local `coga.local.toml`.

Contexts and skills are `SKILL.md` files. They, workflows and bootstrap
targets resolve local-first, then from the package's bundled batteries.
Links never load content; only attached refs compose.

## Transient runtime

`coga launch` runs a ticket's `ticket.py` phase, if any, then composes one
prompt and supervises one agent session per step. Status is the signal of
who is working; there is no lock. What a session learns survives only in
files.

## The correction loop

An agent errs; the human fixes the owning file and commits; the next launch
composes the fix. Dream proposes its corrections as PRs and never edits
operating rules on control itself; a human's edit inside the Coga roots
publishes directly ([coga/state-publication](../state-publication/SKILL.md)).

## Who Coga acts as

Coga acts as the OS user, through tools they already authenticate (`git`
and its remote, `gh`); it stores no GitHub token and has no hosted account.
A missing login fails with a setup hint. The optional weekly snapshot
identifies the repo by a committed UUID, not a person; the
[phone-home ticket](https://github.com/FastJVM/coga/blob/main/coga/recurring/phone-home/ticket.md)
owns it. A ticket's `secrets:` declares intent, not confinement
([secrets](../secrets/SKILL.md)).

## Topic map

- **Start**: [install](../install/SKILL.md), [init](../init/SKILL.md),
  [first-task](../first-task/SKILL.md), [uninstall](../uninstall/SKILL.md),
  [cli](../cli/SKILL.md).
- **Model**: [knowledge](../knowledge/SKILL.md),
  [tickets](../tickets/SKILL.md), [lifecycle](../lifecycle/SKILL.md),
  [blackboard](../blackboard/SKILL.md), [workflows](../workflows/SKILL.md),
  [prompt-composition](../prompt-composition/SKILL.md).
- **Configure**: [configuration](../configuration/SKILL.md),
  [context-layout](../context-layout/SKILL.md),
  [secrets](../secrets/SKILL.md).
- **Run work**: [launch](../launch/SKILL.md),
  [script-tickets](../script-tickets/SKILL.md),
  [megalaunch](../megalaunch/SKILL.md),
  [human-assist](../human-assist/SKILL.md),
  [recurring](../recurring/SKILL.md),
  [period-task](../period-task/SKILL.md).
- **State**: [sync](../sync/SKILL.md),
  [notifications](../notifications/SKILL.md),
  [important](../important/SKILL.md),
  [state-publication](../state-publication/SKILL.md),
  [usage](../usage/SKILL.md).
- **Extend and ship code**: [extension-model](../extension-model/SKILL.md),
  [skill-management](../skill-management/SKILL.md),
  [edge-code](../edge-code/SKILL.md), [sandboxes](../sandboxes/SKILL.md),
  [checkouts](../checkouts/SKILL.md),
  [checkout-cleanup](../checkout-cleanup/SKILL.md),
  [pr-publication](../pr-publication/SKILL.md).

Each topic links its own children.
