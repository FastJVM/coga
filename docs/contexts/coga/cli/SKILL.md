---
name: coga/cli
description: Command index — maps every installed `coga` command and default alias to the topic that owns its contract. Attaching it loads only this index, not the linked topics; exact syntax is `coga <command> --help`.
---

# coga CLI — command index

The installed CLI is the syntax authority: run `coga --help` and
`coga <command> --help`. This page only says which topic owns each
command's behavior. Attach that topic when a task depends on it.

## Setup

| Command | Owner |
| --- | --- |
| `init` | [coga/init](../init/SKILL.md) (install first: [coga/install](../install/SKILL.md)) |
| `uninstall` | [coga/uninstall](../uninstall/SKILL.md) |
| `build` → `launch coga-build` | [coga/init](../init/SKILL.md) |
| `secret get` | [coga/secrets](../secrets/SKILL.md) |
| `validate` | [coga/testing](../testing/SKILL.md), [coga/first-task](../first-task/SKILL.md) |
| `--version` | [coga/install](../install/SKILL.md) |

## Tickets and state

| Command | Owner |
| --- | --- |
| `create`, `ticket`, `show`, `owner` | [coga/tickets](../tickets/SKILL.md) |
| `mark`, `bump`, `block`, `unblock`, `status` | [coga/lifecycle](../lifecycle/SKILL.md), [coga/workflows](../workflows/SKILL.md) |
| `delete`, `retire` | [dev/checkout-cleanup](../../dev/checkout-cleanup/SKILL.md) |
| `open-pr` → `run open-pr` | [coga/internals/pr-publication](../internals/pr-publication/SKILL.md), [dev/dev-record](../../dev/dev-record/SKILL.md) |
| `resolve-conflicts`, `address-pr-comments` → `launch bootstrap/...` | [dev/checkouts](../../dev/checkouts/SKILL.md) |

## Running work

| Command | Owner |
| --- | --- |
| `launch` | [coga/launch](../launch/SKILL.md); script phase: [coga/script-tickets](../script-tickets/SKILL.md) |
| `chat`, `claude`, `codex` → `launch bootstrap/orient` | [coga/launch](../launch/SKILL.md) |
| `megalaunch`, `pick` → `megalaunch --pick` | [coga/megalaunch](../megalaunch/SKILL.md) |
| `recurring` (`--force`, `--all`, `launch`, `promote`, `list`) | [coga/recurring](../recurring/SKILL.md) and its children |
| `dream` → `recurring launch dream` | [coga/dream](../dream/SKILL.md) |
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

Default aliases are argv rewrites, not commands with logic; each alias row
above shows its expansion (`aliases.DEFAULT_ALIASES`). A repo adds or
overrides them in `[aliases]`. `coga run` accepts only the fixed names in
`runner.RECIPES` — the recurring jobs, `open-pr` and `delete-task`. Both
mechanisms, and why a new command usually belongs at the edge, are in
[coga/extension-model](../extension-model/SKILL.md).

## Picking a command

- Start or resume ticket work: `coga launch <slug>`; ad-hoc session with no
  ticket: `coga chat`.
- Draft work: `coga ticket` (guided) or `coga create` (raw draft).
- Finish a step: `coga bump`; finish a workflow-less ticket:
  `coga mark done`; need a human answer: `coga block`.
- Drain the queue: `coga megalaunch`; choose tasks first: `coga pick`.
- Triage: `coga status`; structure check: `coga validate --json`.
