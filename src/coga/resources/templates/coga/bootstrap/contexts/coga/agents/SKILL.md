---
name: coga/agents
description: Configuring agent types under `[agents.*]`, the shared-versus-local overlay and one-directional `peer` routing, agent instruction files and skill wiring, and who Coga acts as.
---

# Agents

An agent type is a named `[agents.<name>]` table. Tickets name types directly
in `agent:` (no per-user nickname layer), and `Config.agent_type` fails loud
on an undefined name. The first declared type is the default for new tickets
(`Config.default_agent`), so a team lists its default first.

## Keys (`src/coga/config.py` `AgentType`)

| Key | Meaning |
|---|---|
| `cli` (required) | Executable to spawn. Launch fails before any state write when it is not on `PATH`. |
| `file` (required) | The instruction file this CLI reads (`CLAUDE.md`, `AGENTS.md`). Parsed and required; launch does not currently read it. |
| `mode` | Defaults to `local`, the only mode that exists. |
| `name_flag` | Flag that sets the session display name (claude: `-n`); the ticket title follows it. Skipped for discussion launches. |
| `session_id_flag` | Flag that pins the session id (claude: `--session-id`); without it Coga falls back to provider transcript matching for usage. |
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

Agent CLIs look for orientation at the repo root: Claude Code reads
`CLAUDE.md`, Codex reads `AGENTS.md`. `coga init` writes both from one
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
  hosted account and no telemetry identity.
- **Task capability.** A ticket's declared `secrets:` is a declaration of
  intent, not confinement ([coga/secrets](../secrets/SKILL.md)).
