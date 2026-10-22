---
name: coga/cli
description: Command index — maps every installed `coga` command and default alias to its contract owner. Attaching it loads only this index, not the linked owners; exact syntax is `coga <command> --help`.
---

# coga CLI — command index

The installed CLI is the syntax authority: run `coga --help` and
`coga <command> --help`. This page only says which file owns each
command's behavior. Attach that topic when a task depends on it.

## Setup

| Command | Owner |
| --- | --- |
| `init` | [coga/init](../init/SKILL.md) (install first: [coga/install](../install/SKILL.md)) |
| `uninstall` | [coga/uninstall](../uninstall/SKILL.md) |
| `build` → `launch coga-build` | [coga/init](../init/SKILL.md) |
| `secret get` | [coga/secrets](../secrets/SKILL.md) |
| `validate` | [coga/first-task](../first-task/SKILL.md) |
| `--version` | [coga/install](../install/SKILL.md) |

## Tickets and state

| Command | Owner |
| --- | --- |
| `create`, `ticket`, `show` | [coga/tickets/authoring](../tickets/authoring/SKILL.md) |
| `owner` | [coga/tickets/ownership](../tickets/ownership/SKILL.md) |
| `mark`, `bump`, `block`, `unblock`, `status` | [coga/lifecycle](../lifecycle/SKILL.md), [coga/workflows](../workflows/SKILL.md) |
| `delete` | [coga/checkout-cleanup](../checkout-cleanup/SKILL.md) |
| `retire` → `launch bootstrap/retire --` | packaged `bootstrap/retire/ticket.md` |
| `open-pr` → `run open-pr` | [coga/pr-publication](../pr-publication/SKILL.md) |
| `resolve-conflicts`, `address-pr-comments` → `launch bootstrap/...` | [coga/checkouts](../checkouts/SKILL.md) |

## Running work

| Command | Owner |
| --- | --- |
| `launch` | [coga/launch](../launch/SKILL.md); script phase: [coga/script-tickets](../script-tickets/SKILL.md) |
| `chat` → `launch bootstrap/orient` | [coga/launch](../launch/SKILL.md) |
| `megalaunch`, `pick` → `megalaunch --pick` | [coga/megalaunch](../megalaunch/SKILL.md) |
| `recurring` (`--force`, `--all`, `launch`, `promote`, `list`) | [coga/recurring](../recurring/SKILL.md) and its children |
| `dream` → `recurring launch dream` | [Dream template](https://github.com/FastJVM/coga/blob/main/coga/recurring/dream/ticket.md) |
| `autoclose` → `recurring launch autoclose-merged` | [coga/recurring/scheduling](../recurring/scheduling/SKILL.md) |
| `skill-update` → `recurring launch skill-update` | [coga/skill-management](../skill-management/SKILL.md) |

## Extension, integrations, and records

| Command | Owner |
| --- | --- |
| `run <recipe>` and `[aliases]` | [coga/extension-model](../extension-model/SKILL.md) |
| `skill` | [coga/skill-management](../skill-management/SKILL.md) |
| `slack` | [coga/notifications](../notifications/SKILL.md) |
| `usage` | [coga/usage](../usage/SKILL.md) |

## Aliases and recipes

This section owns both lists. Default aliases are argv rewrites, not
commands with logic, and dispatch even when `coga.toml` omits them; each
alias row above shows its expansion. A repo adds or overrides aliases in
`[aliases]`; the shipped `coga.toml` comments its entries and optional
examples there.

`coga run` accepts only these fixed recipe names: `autoclose`,
`blocker-reminders`, `branch-sweep`, `validate-drift`,
`cleanup-orphan-markers`, `recurring-scan`, `autofix-analyze`,
`skill-update`, `open-pr`, `delete-task`, `publish-state`, and
`prepare-checkout`. How both mechanisms behave, and why a new command usually
belongs at the edge, is in [coga/extension-model](../extension-model/SKILL.md).

## Picking a command

- Start or resume ticket work: `coga launch <slug>`; ad-hoc session with no
  ticket: `coga chat`.
- Draft work: `coga ticket` (guided) or `coga create` (raw draft).
- Finish a step: `coga bump`; finish a workflow-less ticket:
  `coga mark done`; need a human answer: `coga block`.
- Drain the queue: `coga megalaunch`; choose tasks first: `coga pick`.
- Triage: `coga status`; structure check: `coga validate --json`.
