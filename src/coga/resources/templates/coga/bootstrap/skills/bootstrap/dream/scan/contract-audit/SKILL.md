---
name: bootstrap/dream/scan/contract-audit
description: Audit Dream's living contract surface in bounded shards for drift against code, artifacts, and packaged copies.
---

# Contract Audit

Where the knowledge scan asks what the repo knows that no context captures, the
contract audit asks the opposite: what the contexts, skills, recurring
templates, and shipped docs *claim* that the repo no longer backs up. It is a
consistency pass over Coga's explanation of itself, and it is the decide-half
complement to Phase 1: validate-drift checks deterministic repo hygiene, the
contract audit checks whether the prose still matches the code.

Like the knowledge scan, this audit runs as **bounded shards, not one sweep**.
Each shard follows `bootstrap/dream/scan/scan-protocol` for its budget, its
append-as-you-go findings file, its heartbeat, and its required completion line.
Read that skill first; this one only adds what is specific to the audit.

## The contract surface

The living contract surface is every `SKILL.md` under the repo's configured
contexts directory (`coga/contexts/` unless `[layout] contexts` in `coga.toml`
moves it — resolve that key before globbing) and `coga/skills/**/SKILL.md`, the
`coga/recurring/<name>/ticket.md` templates (recurring tasks are ticket-format
directories), `README.md`, `docs/*.md`, and the agent instruction files
`CLAUDE.md` and `AGENTS.md`.

Frozen task artifacts under `coga/tasks/` are historical records, not
contracts — a stale reference inside a retired ticket is not a finding. Audit
only the living contract surface. `coga/log.md` is history too, and is larger
than any shard budget: grep it for an exact term when a claim needs a date or a
slug, never read it whole.

## Shard partition

Dream partitions the surface into groups and chunks each to the protocol's
budget:

- **contexts** — every `SKILL.md` under the configured contexts directory.
- **skills** — `coga/skills/**/SKILL.md`.
- **templates and docs** — `coga/recurring/*/ticket.md`, `README.md`,
  `docs/*.md`, `CLAUDE.md`, `AGENTS.md`.
- **copy divergence** — one shard over actual counterpart pairs only. In the
  Coga source repo, read `IDENTICAL_LIVE_PACKAGED_PAIRS` from
  `tests/test_packaging.py`, confirm both paths in each pair are tracked, and
  compare each pair with `cmp`. Also check an additional pair only when a
  living contract explicitly names it as a synchronized twin. Do **not** run a
  recursive diff between `coga/` and
  `src/coga/resources/templates/coga/`: most of those roots intentionally have
  no counterpart and runtime state such as `coga/log.md` intentionally differs.
  In a downstream repo with no packaged source tree or explicit pair list,
  omit this group. `coga/.agent-skills/` is a generated, gitignored symlink view
  of the packaged skills, not a copy to compare.

## Findings

Check each concrete claim in your shard against three sources of truth:

- **code reality** — a flag, default, command, status value, or path that
  `src/coga/` no longer implements as described.
- **referenced artifacts** — a file, skill, context, or workflow a contract
  names that does not exist on disk.
- **copy divergence** — a shipped template under `coga/` whose packaged
  counterpart under `src/coga/resources/templates/coga/` has drifted,
  where the difference is not documented as intentional.

Classify each finding as:

- `drift` — a contract claim contradicts code reality, names a missing
  artifact, or a live/packaged copy pair has diverged. Name the file and line,
  state the contradiction, and name the source of truth.

Findings go to the scan directory's `findings.md` in the protocol's shape, in
the same form as the Phase 2 findings; Dream merges both phases into the Dream
task's blackboard `## Findings`. The audit never repairs anything itself —
Phase 6 routes each `drift` finding to a proposal PR.
