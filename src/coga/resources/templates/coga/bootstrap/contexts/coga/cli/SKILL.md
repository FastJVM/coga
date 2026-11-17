---
name: coga/cli
description: Command index — maps every installed `coga` command and default alias to its contract owner. Attaching it loads only this index, not the linked owners; exact syntax is `coga <command> --help`.
---

# coga CLI — command index

The installed CLI is the syntax authority: run `coga --help` and
`coga <command> --help`. This page only says which file owns each
command's behavior. Attach that topic when a task depends on it.

On native Windows, CLI stdout and stderr use UTF-8, including redirected
output. State files follow the [UTF-8 and LF contract](../state-publication/SKILL.md).

## Setup

| Command | Owner |
| --- | --- |
| `init` | [coga/init](../init/SKILL.md) (install first: [Get started](https://github.com/FastJVM/coga/blob/main/README.md#get-started)) |
| `uninstall` | [coga/uninstall](../uninstall/SKILL.md) |
| `build` → `launch coga-build` | [coga/init](../init/SKILL.md) |
| `secret get` | [coga/secrets](../secrets/SKILL.md) |
| `validate` | [coga/first-task](../first-task/SKILL.md) |
| `--version` | The installed package version (`unknown` without package metadata); one CLI serves every repo, so there is no per-repo version |

## Tickets and state

| Command | Owner |
| --- | --- |
| `create`, `ticket`, `show` | [coga/tickets/authoring](../tickets/authoring/SKILL.md) |
| `owner` | [coga/tickets](../tickets/SKILL.md#owner-and-relationships) |
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
| `megalaunch` → `launch bootstrap/megalaunch --`; `pick` → `launch bootstrap/megalaunch -- --pick` | [coga/megalaunch](../megalaunch/SKILL.md) |
| `recurring` (`--force`, `--all`, `launch`, `promote`, `list`) | [coga/recurring](../recurring/SKILL.md) and its children |
| `dream` → `recurring launch dream` | [Dream template](https://github.com/FastJVM/coga/blob/main/src/coga/resources/templates/coga/recurring/dream/ticket.md) |
| `autoclose` → `recurring launch autoclose-merged --rerun` | [coga/recurring/scheduling](../recurring/scheduling/SKILL.md) |
| `skill-update` → `recurring launch skill-update` | [coga/skill-management](../skill-management/SKILL.md) |

## Extension, integrations, and records

| Command | Owner |
| --- | --- |
| `run <recipe>` and `[aliases]` | [coga/extension-model](../extension-model/SKILL.md) |
| `skill` | [coga/skill-management](../skill-management/SKILL.md) |
| `slack` → `launch bootstrap/slack --` | [coga/notifications](../notifications/SKILL.md); packaged `bootstrap/slack/ticket.md` |
| `usage` | [coga/usage](../usage/SKILL.md) |

## Stateless command completion

`coga mark done bootstrap/<name>` ends a stateless agent-backed command's
supervised session; it is that command's only completion signal (`coga
slack` is a non-terminal FYI for every target). It writes no ticket, runs no
workflow or completion gate, and posts no notification: the command's own
roll-up FYI is the notification. It appends one `done (stateless command)`
audit line, credited as `agent:<name>` from the command ticket's `agent:` or
the configured default (the FYI rule; a lifecycle exception, since no
supervised task identity exists to verify). With Git enabled the line must be
confirmed on control before the done marker is requested; otherwise the line
is kept, the sweep is withheld, the command exits 75 with the
`coga run publish-state <log>` recovery. The session can still exit normally
or reach a configured idle or max-session limit. With Git disabled the local
append suffices.
`--message` and `--force` exit 2 before any effect, as do the other `mark`
verbs on a bootstrap ref.

`coga slack --task <ref> --message --help` exits 2 without posting: the
launch help marker makes the script refuse a `--help` its `--message` option
consumed. `coga slack --help` prints the script's usage.

## Aliases and recipes

This section owns both lists. Default aliases (the `→` rows above) are argv
rewrites that dispatch even when `coga.toml` omits them; a repo adds or
overrides them in `[aliases]`.

`coga run` accepts only these fixed recipe names: `autoclose`,
`blocker-reminders`, `branch-sweep`, `validate-drift`,
`cleanup-orphan-markers`, `recurring-scan`, `autofix-analyze`,
`skill-update`, `open-pr`, `delete-task`, `publish-state`, and
`prepare-checkout`. How both mechanisms behave, and why a new command usually
belongs at the edge, is in [coga/extension-model](../extension-model/SKILL.md).
