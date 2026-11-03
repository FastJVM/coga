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
moves it — resolve that key before globbing) and every repo-authored
`coga/skills/**/SKILL.md`, the `coga/recurring/<name>/ticket.md` templates
(recurring tasks are ticket-format directories), `README.md`, `docs/*.md`, and
the agent instruction files `CLAUDE.md` and `AGENTS.md`.

Which repo this is changes what that surface contains. Read the
`repo-identity:` line at the top of the scan directory's `index.md` — the
protocol's "Repo identity" section defines the test, and Dream evaluates it
once; never re-derive it. In a client repo the index already omits every
Coga-owned path (the protocol's Rule A: the shipped recurring templates,
shipped workflows, and bundled skills and contexts the installed package
placed under `coga/`), so the audit surface is exactly what the index lists,
and the client's own `coga/recurring/*/ticket.md` templates stay in it.

Frozen task artifacts under `coga/tasks/` are historical records, not
contracts — a stale reference inside a retired ticket is not a finding. Audit
only the living contract surface. `coga/log.md` is history too, and is larger
than any shard budget: grep it for an exact term when a claim needs a date or a
slug, never read it whole.

Installer-managed skills are not contract surface either. The upstream trees
that `coga skill install` and `coga skill update` place and refresh wholesale
are not Coga's explanation of itself, and Coga cannot durably edit them: a
`drift` finding against one is reverted by the next refresh. **The test is the
one `gh skill` and `skill_manager.gh_skill_repo()` apply**: a skill is
GitHub-managed exactly when its `coga/skills/**/SKILL.md` frontmatter carries
`metadata.github-repo`. There is no name list — `coga init` installs no packs,
so which trees exist is whatever operators installed explicitly — and the
frontmatter key is the only membership fact. A skill that merely records an
upstream source in `.coga-source.json` is **not** in this class: a `coga skill
install-url` skill such as `coga/skills/clarity/` carries no `github-repo`
key, is locally adapted, and stays in the audit surface. In this repo the
excluded trees are the `google-agents-cli-*` packs, upstream GCP/ADK
documentation large enough to consume whole shard budgets. Exclude them before
globbing so the budget goes to prose this repo authored.

## Shard partition

Dream partitions the surface into groups and chunks each to the protocol's
budget:

- **contexts** — every `SKILL.md` under the configured contexts directory.
  In the Coga source repo also every `SKILL.md` under the package's
  `src/coga/resources/templates/coga/bootstrap/contexts/`: shipped user topics
  are owned there, and a canonical copy under the contexts root is only a
  transitional legacy counterpart.
- **skills** — `coga/skills/**/SKILL.md`, excluding the installer-managed
  trees named above. In the Coga source repo also the package's
  `bootstrap/skills/**/SKILL.md`.
- **templates and docs** — `coga/recurring/*/ticket.md` local definitions,
  `README.md`, `docs/*.md`, `CLAUDE.md`, `AGENTS.md`. In the Coga source repo
  also the package's `recurring/*/` definitions and `bootstrap/workflows/`.
  A `coga/recurring/<name>/ticket.md` that starts with the
  `<!-- coga:recurring-state -->` marker is a state-only carrier (repo state
  for a package-backed job), not prose to audit.
- **single-source ownership** — only in the Coga source repo
  (`repo-identity: coga-source`). The package is the one committed owner of
  every shipped definition; `tests/test_packaging.py` pins the transitional
  legacy live copies in `tests/legacy_removal_inventory.txt` and fails on any
  other live counterpart. Print what the suite derives instead of diffing the
  roots, from the repo root on a single line:

  ```sh
  python -c "import sys; sys.path.insert(0, 'tests'); import test_packaging as t; inv = t._read_inventory(); print('\n'.join(f'{a} {b}' for a, b in t.LIVE_PACKAGED_TWINS if a not in inv and a not in t.SCAFFOLD_COUNTERPARTS))"
  ```

  Any line printed is an unapproved live copy of a package definition: the
  finding is to delete the live copy (or record a reviewed override), never
  to sync the two. Do **not** run a recursive diff between `coga/` and
  `src/coga/resources/templates/coga/`. Because the suite enforces this, a
  green suite means this shard has nothing to report. In a client repo there
  is no packaged source tree: omit this group, and never edit installed
  package resources there; a client's deliberate override is its own file.
  `coga/.agent-skills/` is a generated, gitignored symlink view, not a copy.

## Findings

Check each concrete claim in your shard against three sources of truth:

- **code reality** — a flag, default, command, status value, or path that
  the repo's code no longer implements as described. In the Coga source repo
  that code is `src/coga/`. In a client repo `src/coga/` does not exist, so
  code reality means the client's **own** code, and a claim whose only source
  of truth is Coga's implementation — a `src/coga/` symbol, a `coga` CLI flag
  or exit contract, a packaged template's wording — is **not checkable there
  and not a local finding**. Do not invent a `drift` from a Coga claim you
  cannot verify. Where a client-owned file's claim is plainly Coga-owned and
  worth reporting, write the finding with `owner: coga` (the protocol's
  Rule B); it is routed upstream, never to a local proposal PR.
- **referenced artifacts** — a file, skill, context, or workflow a contract
  names that does not exist on disk.
- **copy divergence** — in the Coga source repo, a live copy of a shipped
  definition that the single-source ownership shard reports (the package is
  the only owner; the fix is removal, not syncing), or a still-inventoried
  legacy copy that drifted from its package owner without a reviewed entry.

Classify each finding as:

- `drift` — a contract claim contradicts code reality, names a missing
  artifact, or a live copy of a package definition is unapproved or drifted. Name the file and line,
  state the contradiction, and name the source of truth.

Findings go to the scan directory's `findings.md` in the protocol's shape, in
the same form as the Phase 2 findings; Dream merges both phases into the Dream
task's blackboard `## Findings`. The audit never repairs anything itself —
Phase 6 routes each `drift` finding to a proposal PR, except an `owner: coga`
finding, which never proposes a local edit and goes to the client checkout's
`coga/upstream-coga.md` instead.
