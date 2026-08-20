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

The living contract surface is every `coga/contexts/**/SKILL.md` and
`coga/skills/**/SKILL.md`, the `coga/recurring/<name>/ticket.md` templates
(recurring tasks are ticket-format directories), `README.md`, `docs/*.md`, and
the agent instruction files `CLAUDE.md` and `AGENTS.md`.

Frozen task artifacts under `coga/tasks/` are historical records, not
contracts — a stale reference inside a retired ticket is not a finding. Audit
only the living contract surface. `coga/log.md` is history too, and is larger
than any shard budget: grep it for an exact term when a claim needs a date or a
slug, never read it whole.

## Shard partition

Dream partitions the surface into groups and chunks each to the protocol's
budget:

- **contexts** — `coga/contexts/**/SKILL.md`.
- **skills** — `coga/skills/**/SKILL.md`.
- **templates and docs** — `coga/recurring/*/ticket.md`, `README.md`,
  `docs/*.md`, `CLAUDE.md`, `AGENTS.md`.
- **copy divergence** — one shard for the whole live/packaged comparison. Do not
  read both trees to compare them. Run
  `diff -r coga/ src/coga/resources/templates/coga/` (and `git ls-files` to
  confirm which copies are tracked rather than generated), then read only the
  files the diff actually flags. Note that `coga/.agent-skills/` is a generated,
  gitignored symlink view of the packaged skills, not a copy to compare.

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
