---
name: coga/agents
description: Configuring agent types under `[agents.*]`, the shared-versus-local overlay and one-directional `peer` routing, agent instruction files and skill wiring, and who Coga acts as.
---

# Agents

An agent type is a named `[agents.<name>]` table. Tickets name types directly
in `agent:` (no per-user nickname layer), and `Config.agent_type` fails loud
on an undefined name. Which type new tickets get is the default agent,
described [below](#the-default-agent).

## Keys (`src/coga/config.py` `AgentType`)

| Key | Meaning |
|---|---|
| `cli` (required) | Executable to spawn. Launch fails before any state write when it is not on `PATH`. |
| `file` (required) | The instruction file this CLI reads (`CLAUDE.md`, `AGENTS.md`). Parsed and required; launch does not currently read it. |
| `mode` | Defaults to `local`, the only mode that exists. |
| `name_flag` | Flag that sets the session display name (claude: `-n`); the ticket title follows it. Skipped for discussion launches. |
| `session_id_flag` | Flag that pins the session id (claude: `--session-id`); without it Coga falls back to provider transcript matching for usage. |
| `launch_args` | Extra argv tokens (a string, `shlex`-split; default `""`) inserted right after `cli` in every interactive spawn, positional and discussion shapes alike: launch, megalaunch, `coga ticket`, and `coga chat`. Not applied to `analyze`. The shipped template sets `--no-daemon` for codex; see [Launch environment inheritance](#launch-environment-inheritance). |
| `discussion` | argv template for `coga chat` / `coga ticket`, with `{prompt}` replaced, so the prompt rides as system or developer context. Empty uses built-in defaults for known CLIs, then positional. |
| `analyze` | One-shot argv for the recurring autofix analyst, with a `{prompt}` token. `claude` and `codex` have built-in defaults; an unknown CLI with no override skips the analysis loudly. |
| `peer` | The reviewer type an `other-agent` workflow step selects. |

The shipped `coga.toml` declares `claude` and `codex`. Removed keys (`auto`,
`skip_permissions`, `skip_permissions_argv`) raise a migration error naming
the file that holds them; launches are interactive-only
([coga/configuration](../configuration/SKILL.md)).

## Shared policy, local overlay

`[agents.*]` is machine capability, so unlike `[layout]` it may appear in
both files. `_parse_agents` merges at the **key** level: a local table
overrides individual keys of the shared one (for example a different `cli`
path) and inherits the rest, and a local-only table appends a type installed
only on this machine. Required-key and type checks run on the merged result.
An explicit local `launch_args = ""` clears a shared value.

## Launch environment inheritance

A supervised session works only if the agent's **shell commands** inherit
the environment Coga hands the agent process: `COGA_SUPERVISED`,
`COGA_EXPECTED_TASK`, `COGA_EXPECTED_STEP`, `COGA_DONE_SENTINEL`, and
`COGA_TASK_*` ([coga/internals/agent-spawn](../internals/agent-spawn/SKILL.md)).
Without them, an in-session `coga bump` is credited `human:<user>` rather than
`agent:<type>`, the stale-step guard in `coga bump` does not run, and the done
sentinel never fires. The session then stays open after the bump until the
human exits it.

**Codex remedy.** By default the interactive Codex TUI (observed in
codex-cli 0.162.x) attaches to a shared, long-lived `codex app-server`
daemon. That daemon spawns the model's shell commands with *its own*
environment, not the launching TUI's, so nothing Coga sets reaches them.
`codex --no-daemon` runs the app server in-process and restores inheritance.
Disabling the `daemon_auto_start` feature is not enough while a daemon is
already running. The shipped `coga.toml` therefore sets, with a comment:

```toml
[agents.codex]
launch_args = "--no-daemon"
```

Core adds no built-in default. **Existing repositories** created before the
template change must add that line to `[agents.codex]` in `coga/coga.toml`,
or per machine in `coga.local.toml`. Remove it only for a Codex that predates
the flag (Codex rejects it only with `--remote` and with the `agents`,
`queue`, and `remote-control` subcommands, none of which Coga uses). The
one-shot `analyze` argv (`codex exec`) already inherits the environment.

**Advisory warning.** After a supervised session ends, `coga launch` and
`coga megalaunch` compare the ticket's `(status, step)` frozen immediately
before spawn with its post-session state. If they differ and the supervisor
observed no matching done signal, they print a yellow stderr warning naming
the task and pointing here. Missing `COGA_*` is the likely cause, but the
warning says only that it *may* be. A human or another session could also
have moved the ticket, so the observation never establishes who did.
Observation limits:

- Launch reads state after its checkout return and reload, so an advance
  published from elsewhere is seen. It skips the check when the return or
  reload refuses, the target was removed, or the ticket cannot be read or
  parsed. Exempt checkouts read their current copy. Megalaunch uses its
  existing post-session read.
- A session whose unresolved blocked resume launch reblocks itself is not
  diagnosed, so the supervisor's own write is never attributed to the agent.
  Megalaunch observes before its reblock.
- The warning appears only after the session ends. It never changes exit
  codes, chaining, or result handling. Bump-time detection (sniffing vendor
  environment markers) is deliberately out of scope: it would put vendor
  knowledge in core and misfire on unsupervised sessions.

## The default agent

`Config.default_agent()` is the type a ticket's `agent:` is stamped with at
first activation (or at a create straight into a live status), and the
fallback for `coga retire`, the autofix analyst, and the authoring
interviewer. Precedence:

1. top-level `default_agent = "<type>"` in `coga.local.toml`;
2. top-level `default_agent` in `coga.toml`;
3. the first-declared table in the merged `[agents.*]`.

With the key unset in both files, the third term applies, which is the
behaviour from before the key existed. Changing the default never needs a
table reorder. The key is local-capable on purpose, unlike shared-only
`[autofix]`: which vendor a machine can run right now (an exhausted quota, a
missing install) is an operator fact, so one clone can switch to `codex`
without editing committed config. A local table also cannot reorder the shared
ones, so before the key existed a machine had no way to change its default.

Each value present must be a non-empty string naming a type in the
**merged** `[agents.*]` table. Otherwise config load fails, naming the file
that supplied it and listing the known types. Both values are checked even
when the local one wins. As with `[autofix] agent`, a shared value naming a
type that some clone declares only locally breaks other clones on their next
command. That failure is loud, not a silent fallback.

The default is resolved once, then frozen. Activation writes it into `agent:`
([coga/tickets](../tickets/SKILL.md)), so changing it later affects only
tickets activated afterwards. A recurring period ticket that already exists
keeps its agent even when a forced rerun in the same period reactivates it.
The new default applies from the next newly materialized period. Read-only
surfaces (status, show, compose, validate) report the default that activation
*would* stamp, and the `other-agent` peer of an unactivated ticket is derived
from it.

More specific knobs win over it. A recurring agent-backed launch uses
`--agent`, else the period ticket's `agent:`. The autofix analyst uses
`--agent`, else `[autofix] agent`, else the default
([coga/recurring/autofix](../recurring/autofix/SKILL.md)). The authoring
interviewer reaches the default only as its last term, after
`[authoring] agent`, `COGA_AUTHORING_AGENT`, and any ticket's own `agent:`
([coga/tickets](../tickets/SKILL.md)). The packaged `bootstrap/ticket`,
`bootstrap/orient`, and onboarding tickets pin `agent: claude`, and that pin
outranks the default. So `default_agent = "codex"` does not by itself move
`coga ticket` or `coga chat`. Use `[authoring] agent` or `--agent` for those.
Interactive `coga init` sets the key in the `coga.toml` it creates, behind an
explicit confirm, when the agent CLI it installed or found is not the packaged
default ([coga/init](../init/SKILL.md)).

## `peer` routing

- The target must be another configured type; naming itself or an unknown
  type fails config load.
- It is global and one-directional per agent type. `claude.peer = "codex"`
  says nothing about codex's reviewer, and it cannot vary by ticket or
  workflow. A per-ticket reviewer was deferred as unneeded policy surface.
- With no `peer`, "other" means the single configured type that is not the
  ticket's main agent. That is zero-config for two-agent repos. With three or
  more types and no `peer`, resolution fails loud asking for one
  (`src/coga/bump.py` `resolve_other_agent`).
- The asymmetry: the ticket freezes its main `agent:`, but `peer` is read
  from **live** config at each handoff or launch. A `peer` set only in
  `coga.local.toml` therefore picks a different reviewer on that machine
  without rewriting ticket routing. That is accepted, so a machine can use a
  third agent teammates do not have. A repo wanting one policy for everyone
  sets `peer` in shared `coga.toml`.

Step roles and handoff mechanics belong to
[coga/workflows](../workflows/SKILL.md) and
[coga/lifecycle](../lifecycle/SKILL.md).

## Instruction files and skill discovery

Agent CLIs look for orientation at the repo root: Codex reads `AGENTS.md`;
Claude Code reads `CLAUDE.md`, or `AGENTS.md` when no `CLAUDE.md` or
`CLAUDE.local.md` exists in the working directory or above it (Claude Code
v2.1.277 or later). A clone that keeps a `CLAUDE.local.md` must start it with
`@AGENTS.md` or it loses the repo guide. `coga init` writes both from one
template (`AGENT_GUIDE_TEMPLATE`) only where missing and never overwrites a
hand-edited guide. Keep compatibility with both names. `coga uninstall`
removes unmodified guides and backs up edited ones.

Skills reach agents through `coga/.agent-skills/`, a generated view of local
plus bundled skills, which init symlinks into `.claude/skills/coga` and
`.codex/skills/coga`. Both links and the view are gitignored, so each clone
creates them with `coga init --user` ([coga/init](../init/SKILL.md)). Launch
also rebuilds the view.

## Who Coga acts as

- **Operator.** The OS user plus tools they already authenticate: `git`, SSH
  agent or credential helper, `gh`. Coga stores no GitHub token. Git transport
  uses your remote, GitHub API work uses `gh` auth, and a missing login fails
  with a setup hint (`gh auth login`, fix your remote).
- **Repo.** Identified by its Git checkout and `coga/` config. There is no
  hosted account. For the optional weekly snapshot, a UUID v4 lives as
  committed state in the phone-home recurring parent blackboard and is shared
  by synced clones; it is not a human account.
  [phone-home ticket](https://github.com/FastJVM/coga/blob/main/coga/recurring/phone-home/ticket.md) owns its lifecycle and concurrency
  limits.
- **Task capability.** A ticket's declared `secrets:` is a declaration of
  intent, not confinement ([coga/secrets](../secrets/SKILL.md)).
