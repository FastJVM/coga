# Agent memory and scoping landscape — 2026-10-13

**Scope.** A quick check, made during the README positioning review, of how
Claude Code, Codex CLI and Kiro persist and scope project knowledge. It is not
an exhaustive survey. Several sources are secondary write-ups rather than
vendor documentation: re-verify against the vendor docs before reusing any
line in a public claim. These facts change fast.

| Tool | Human-written knowledge | Tool-written memory | How knowledge is scoped |
|---|---|---|---|
| Claude Code | `CLAUDE.md` at project, personal, local (gitignored) and managed-organization scopes | Auto memory: Claude's own notes under `~/.claude/projects/<project>/memory/`, local to the machine and not synced; reported on by default since v2.1.59 | By file location and imports; skills load on demand when relevant |
| Codex CLI | `AGENTS.md`, read from the Git root down to the working directory, with `AGENTS.override.md` taking precedence; reported 32 KiB ceiling | Memories under `~/.codex/memories/`, per user, no team sharing; framed as Codex-managed state, with `AGENTS.md` as the supported place to edit | By directory walk; skills in the `SKILL.md` format |
| Kiro | Steering files in `.kiro/steering/`; `AGENTS.md` also read, always included | — (not checked) | Steering inclusion modes: always, `fileMatch` when a matching file enters context, or manual when the user cites it in chat. Specs run requirements → design → tasks with user approval between stages; autonomy modes include Autopilot |

## Observations at this date

- Scoping is by location (nested files, directory walk, `fileMatch`) or by a
  manual mention in chat. The manual mention is per session and not recorded.
- Tool-written memory lives outside the repository, per machine or per user.
- No per-fact ownership rule and no check of stored knowledge against the
  code were found in the sources read. Community guides recommend verifying
  memory against current code by hand.
- Kiro is the closest conceptually (files for specs, approval gates, autonomy
  modes); its spec process is fixed and its autonomy mode is chosen per
  session rather than per kind of work.

These are dated observations, not "first" or "only" claims; see
[`marketing/positioning`](../contexts/marketing/positioning/SKILL.md) for the
claim limits.

## Sources (read 2026-10-13)

- Claude Code memory: <https://blog.memoryplugin.com/claude-code-memory/>,
  <https://ai-workshop.dometrain.com/docs/getting-started/first-steps/memory>,
  <https://mer.vin/2026/05/claude-code-memory-architecture-explained-for-beginners-with-claude-md-and-auto-memory/>
  (secondary).
- Codex CLI: <https://mem0.ai/blog/how-memory-works-in-codex-cli> (secondary),
  <https://docs.rs/crate/agent-config/0.3.3/source/docs/agents/codex.md>
  (secondary, links the vendor pages under `developers.openai.com/codex`).
- Kiro: <https://kiro.dev/docs/steering/> (vendor), plus secondary summaries of
  the spec workflow.
