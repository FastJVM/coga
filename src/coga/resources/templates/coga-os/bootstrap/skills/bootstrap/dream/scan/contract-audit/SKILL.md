---
name: bootstrap/dream/scan/contract-audit
description: Audit Dream's living contract surface for drift against code, artifacts, and packaged copies.
---

# Contract Audit

Where the knowledge scan asks what the repo knows that no context captures, the
contract audit asks the opposite: what the contexts, skills, recurring
templates, and shipped docs *claim* that the repo no longer backs up. It is a
consistency pass over Coga's explanation of itself, and it is the decide-half
complement to Phase 1: validate-drift checks deterministic repo hygiene, the
contract audit checks whether the prose still matches the code.

The subagent reads the living contract surface — every
`coga-os/contexts/**/SKILL.md` and `coga-os/skills/**/SKILL.md`, the
`coga-os/recurring/<name>/ticket.md` templates (recurring tasks are
ticket-format directories), `README.md`, `docs/*.md`, and the agent instruction
files `CLAUDE.md` and `AGENTS.md` — and checks each concrete claim against
three sources of truth:

- **code reality** — a flag, default, command, status value, or path that
  `src/coga/` no longer implements as described.
- **referenced artifacts** — a file, skill, context, or workflow a contract
  names that does not exist on disk.
- **copy divergence** — a shipped template under `coga-os/` whose packaged
  counterpart under `src/coga/resources/templates/coga-os/` has drifted,
  where the difference is not documented as intentional.

Frozen task artifacts under `coga-os/tasks/` are historical records, not
contracts — a stale reference inside a retired ticket is not a finding. Audit
only the living contract surface.

The subagent returns only a classified findings list. Classify each finding as:

- `drift` — a contract claim contradicts code reality, names a missing
  artifact, or a live/packaged copy pair has diverged. Name the file and line,
  state the contradiction, and name the source of truth.

Write these findings to the Dream task's blackboard under `## Findings`,
alongside the Phase 2 findings and in the same shape: short title, class,
target file, one paragraph. The audit never repairs anything itself — Phase 7
routes each `drift` finding to a proposal PR.
