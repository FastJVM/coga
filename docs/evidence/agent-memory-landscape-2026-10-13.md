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

## Spec-driven tools, graduated autonomy and team workspaces (checked 2026-10-13)

Added in the README follow-up on PR #1000. Each line was re-read against the
source named; status is given per source. These are close precedents for
individual Coga features, recorded so no feature is presented as the original
part.

- **OpenSpec** (vendor repo and docs). `openspec/specs/` holds the current
  truth ("Specs are the source of truth"); each change is a proposal folder
  under `openspec/changes/`; on archive, each ADDED/MODIFIED/REMOVED delta is
  applied to the main spec and the change moves to `changes/archive/`. Closest
  precedent for "tickets are disposable, what they teach isn't". Planning and
  implementation run as slash commands inside the agent session
  (`/opsx:propose`, `/opsx:apply`, `/opsx:archive`).
- **arXiv 2609.00252** (primary, preprint), Diaz, Gayoso, Cimminio and Perez,
  "Spec-Driven Development for Agentic Software Engineering: Harnessing
  Human-Agent Teamwork", 31 Aug 2026. Harness 8, "Graduated autonomy":
  "Autonomy is calibrated per class of task, explicitly and revisably", and
  "the autonomy level for each class of work is an explicit, versioned
  decision". Closest precedent for per-kind workflows. The authors call it
  conceptual and grounded mostly in gray literature, "a set of falsifiable
  hypotheses" not yet validated empirically. The rest of the paper does not
  contradict Harness 8; it adds that specific autonomy thresholds "date
  quickly" (§8.3) and that a "deliberately lighter discipline" may suit
  exploratory work (§8.2).
- **PyAutoScientist** (vendor docs). Tasks start as Markdown files under
  `<work-type>/<target>/<name>.md` (examples: `feature/`, `bug/`, `refactor/`,
  `docs/`); autonomy is "defined once, in AUTONOMY.md" with a cap per work
  type, and the effective level is the minimum of the prompt's declared level
  and the cap; merge stays human. AUTONOMY.md in the PyAutoBrain repo
  (primary) sets the caps: refactor, test and maintenance `safe`; feature and
  docs `safe` up to medium difficulty, else `supervised`; bug and research
  `supervised`; release `human-required`. Raising a cap is "a doctrine edit"
  citing at least 10 clean calibration-log rows and no rejected ones; any
  rejected row drops the cap one level.
- **Doc-drift checks on a schedule** (precedent for Dream):
  agentpatterns.ai's "Instruction file fact checker" (secondary, pattern
  site) runs Claude Code weekly to verify `CLAUDE.md` claims against the code
  and open correction PRs; Upkeep (primary repo) is a Claude Code plugin and
  CI workflow that reports stale docs and specs on a weekly cron without
  editing; stranske/Workflows PR #2367 (primary, merged 2026-06-14) files a
  monthly docs-drift audit issue that agents turn into fix PRs.
- **The spec-driven category** (all vendor sources): GitHub Spec Kit (slash
  commands in the agent chat; "These are agent skills, not terminal
  commands"), BMAD Method (role personas such as `bmad-agent-pm` and
  `bmad-agent-architect` are skills installed into the coding tool and
  invoked by skill ID), Kiro (its own IDE, plus CLI and
  web; requirements → design → tasks), OpenSpec (slash commands, above) and
  Agent OS by Builder Methods (installed into the project, "designed
  primarily for Claude Code, with slash commands"). Structural difference at
  this date: these run inside the agent session or are the IDE, while Coga
  launches the agent and controls session boundaries and prompt composition
  from outside.
- **Ramp Glass** (vendor launch post, 2026-10-13). A company AI workspace
  with shared skills, multiplayer sessions, connectors (Linear, Notion,
  Google, Slack, Gong and others), a model router and persistent company
  memory edited by employees. The launch post says nothing about who owns or
  reviews shared knowledge or how stale knowledge is handled; that is an
  absence in the post, not proof of absence in the product. The post does not
  state explicitly that it is hosted.
- **Per-step assignees in Coga.** Per-step `assignee:` roles first appeared in
  Coga's workflows on 2026-05-01 (commit `d0e4fcc`, "Declare per-step assignee
  in workflow schema and apply on bump"), before the arXiv preprint above:
  arrived at independently. This is not a priority claim.

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
- OpenSpec: <https://github.com/Fission-AI/OpenSpec>,
  <https://github.com/Fission-AI/OpenSpec/blob/main/docs/concepts.md> (vendor).
- Spec-driven development preprint: <https://arxiv.org/abs/2609.00252>
  (primary).
- PyAutoScientist:
  <https://pyautoscientist.readthedocs.io/en/latest/concepts/workflow.html>
  (vendor), <https://github.com/pyautolabs/pyautobrain/blob/main/AUTONOMY.md>
  (primary).
- Drift checks: <https://agentpatterns.ai/workflows/instruction-file-fact-checker/>
  (secondary), <https://github.com/wei18/Upkeep> (primary),
  <https://github.com/stranske/Workflows/pull/2367> (primary).
- Spec-driven tools: <https://github.com/github/spec-kit>,
  <https://github.com/bmad-code-org/BMAD-METHOD>,
  <https://docs.bmad-method.org/reference/skills-and-agents/>,
  <https://kiro.dev/docs/specs/>, <https://buildermethods.com/agent-os>
  (vendor).
- Ramp Glass: <https://ramp.com/blog/introducing-glass> (vendor),
  <https://www.pymnts.com/news/artificial-intelligence/2026/ramp-1-million-week-spending-leads-glass-ai-tool/>
  (secondary).
