---
slug: live-and-packaged-twin-pairs-are-edited-together-b
title: Live and packaged twin pairs are edited together by convention but not enforced
  by any test
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts: []
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
secrets: null
step: 4 (review)
---

## Description

`CLAUDE.md` instructs: "When changing shipped Coga OS contexts or templates, check both the live
repo copy under `coga/` and the packaged copy under `src/coga/resources/templates/coga/`. Keep them
in sync unless the difference is intentional and documented."

Only some of those pairs are actually enforced. `tests/test_packaging.py::IDENTICAL_LIVE_PACKAGED_PAIRS`
lists 25 pairs and asserts byte-identity. Every other live/packaged twin is kept in sync by
convention alone, and nothing catches a divergence.

Two independent Dream Phase 6 PRs hit this in one run:
- **#719** — `coga/skills/browser/{dochub,playwright}` were fixed live, but their packaged mirrors
  under `src/coga/resources/templates/coga/bootstrap/skills/browser/` carry the same `name:` and
  `$PWCLI` drift. Left untouched to respect PR scope; no test covers them.
- **#721** — three more twin pairs were edited (`coga/contexts/_template`, `docs/gdrive-mcp`,
  `browser/dom-backed`), none of which is in the enforced list.

Decide the rule: either every live/packaged twin belongs in the enforced list, or the list needs a
stated principle for what is in and what is out. Today's boundary looks incidental rather than
designed — which is exactly how a pair silently diverges.

## Context

Found by Dream 2026-08-24, Phase 6, surfaced independently by two PR agents (#719, #721).

Worth noting what did NOT go wrong: Phase 3's dedicated copy-divergence shard (`ca-08`) compared all
25 enforced pairs with `cmp` and found **zero** divergence. The enforcement works where it is
applied. The gap is coverage, not correctness.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

pr: https://github.com/FastJVM/coga/pull/758
branch: derive-twin-sync
worktree: /home/n/Code/codex/coga-derive-twin-sync

## Findings

Derived every live/packaged twin mechanically with two mapping rules:
- `src/coga/resources/templates/coga/X` -> `coga/X`
- `src/coga/resources/templates/coga/bootstrap/{contexts,skills,workflows}/X`
  -> `coga/{contexts,skills,workflows}/X`

69 pairs exist; 64 are already byte-identical. The hand-maintained
`IDENTICAL_LIVE_PACKAGED_PAIRS` covered only 25 of them, so the boundary was
incidental exactly as the ticket claims. The #719 dochub/playwright drift has
since been fixed, and #721's three pairs (`contexts/_template`,
`docs/gdrive-mcp`, `browser/dom-backed`) are identical today.

Only 5 twins diverge, all structurally (repo-local state, not drift):
- `coga/.gitignore` — live copy carries `coga init`'s managed markers
- `coga/coga.toml` — live is this repo's real config; packaged is the seed
- `coga/log.md` — live audit trail vs empty seed
- `coga/recurring/digest/spool.md` — live spool holds consumed events
- `coga/recurring/digest/ticket.md` — live carries owner/assignee + digest state

## Decision

Human chose (attended, this session): derive all twins, keep an explicit
exemption map with a written reason per entry. Keep the exported name
`IDENTICAL_LIVE_PACKAGED_PAIRS` so the Dream contract-audit skill and
`tests/test_dream_worker_templates.py` keep resolving.

Tradeoff accepted: coverage becomes implicit — a new packaged mirror is
enforced automatically, and an intentional divergence now costs an exemption
entry. A live file renamed away silently drops from coverage; a floor-count
assertion is the coarse guard for that.

## What changed

`tests/test_packaging.py`:
- `IDENTICAL_LIVE_PACKAGED_PAIRS` is no longer a literal tuple. It is derived
  from the packaged tree at import (`_discover_live_packaged_twins`), minus the
  documented exemptions. The name is kept because Dream's copy-divergence shard
  and `tests/test_dream_worker_templates.py` both resolve it.
- `LIVE_PACKAGED_TWINS` holds every twin, divergent ones included.
- `INTENTIONALLY_DIVERGENT_TWINS` maps the 5 divergent live paths to reasons.
- `test_live_and_packaged_copies_stay_identical` now covers 64 pairs (was 25),
  and its failure message tells you how to make a difference intentional.
- `test_twin_discovery_still_walks_the_packaged_tree` — floor of 60 plus one
  probe per mapping, so a mapping regression cannot quietly empty the tuple.
- `test_intentional_divergences_stay_real_and_explained` — an exemption that
  names a non-twin, or whose copies have converged, fails. The map self-prunes.

Docs stating the rule: `CLAUDE.md` and `AGENTS.md` (identical twins, edited
together), `coga/contexts/coga/codebase/SKILL.md` + its packaged twin, and
`bootstrap/skills/bootstrap/dream/scan/contract-audit/SKILL.md` (which had to
change: it told the agent to *read* the constant, and a derived tuple has to be
printed instead).

## Verification

- `python -m pytest` in the feature worktree: **2371 passed, 1 failed**.
- The one failure, `tests/test_notification_messages.py::test_recurring_create_is_silent`
  (`IsADirectoryError: .../coga/tasks/work`), is **pre-existing on main** —
  reproduced in the primary checkout with unmodified `tests/`. Not caused by
  this change; worth a follow-up ticket.
- `tests/test_packaging.py` and `tests/test_dream_worker_templates.py`: 20 passed.
- Verified the one-liner now documented in the contract-audit skill actually
  prints the 64 enforced pairs.

Env note: the repo has no venv and `python3` here is 3.9, so the suite was run
from a throwaway 3.12 venv with `pip install -e ".[test]"`. Without hatchling
installed, `test_wheel_includes_bootstrap_batteries` fails for environment
reasons alone.

## Adjacent, not fixed here

- `CLAUDE.md` and `AGENTS.md` are byte-identical twins with no test guarding
  them. Same class of gap as this ticket, different root pair — out of scope
  for this diff; worth its own ticket.
- `test_recurring_create_is_silent` failure above.

## Peer review

Completed on `derive-twin-sync` in the recorded feature worktree. Ran
`codex review --base main` outside the sandbox because its app-server could
not initialize on the sandbox's read-only filesystem. Review log:
`/tmp/coga-derive-twin-sync-peer-review.log`.

The review found one P2 issue: discovery included ignored local installation
artifacts when both roots contained a `.coga/.venv`. Activation scripts embed
their installation paths, so these non-shipped files caused false drift
failures. Fixed in `1dbc7616` (`peer-review: exclude generated local
installation artifacts`): prune installation, agent-tooling, and bytecode
directories before descending, and omit machine-local `coga.local.toml`.
Updated `AGENTS.md`/`CLAUDE.md` and both codebase contexts with that boundary.
The regression passes with the fix and fails against the reviewed pre-fix
discovery; new direct and bundled twins remain covered.

- Independently confirmed 69 discovered pairs, 64 enforced, and byte-identity
  for every enforced pair. Temporary-tree probes show new direct and bundled
  twins are discovered automatically, drift fails for each, and packaged files
  with no live counterpart are excluded.
- Confirmed recurring serviced-period state now lives in `coga/log.md`; it
  does not mutate the newly enforced recurring templates.
- Reproduced `test_recurring_create_is_silent` on unmodified `main`
  (`63da7dfe`) with the same `IsADirectoryError` recorded during implementation.
- Correction to the earlier findings: `docs/gdrive-mcp` currently has only a
  live copy, so it is not among the 69 discovered twins. The `_template` and
  `browser/dom-backed` pairs cited in #721 are covered.

Freshness: ran `git fetch origin main` and `git rebase FETCH_HEAD` in the
feature worktree; rebase onto `63da7dfe` completed without conflicts. Fetched
again after the approval wait and confirmed `origin/main` had not advanced.
The branch has two commits ahead of that base. Both edited documentation
pairs still match byte-for-byte. No unresolved must-fix findings.

Verification (Python 3.12.12 with pytest and hatchling; absolute `PYTHONPATH`
selects the feature source despite the reused test environment):

- `PYTHONPATH=/home/n/Code/codex/coga-derive-twin-sync/src /tmp/coga-dream-review-venv-20260904/bin/python -m pytest tests/test_packaging.py tests/test_dream_worker_templates.py -q`
  — **21 passed**, including the wheel build. Only sandbox cache-write warnings.
- `PYTHONPATH=/home/n/Code/codex/coga-derive-twin-sync/src /tmp/coga-dream-review-venv-20260904/bin/python -m pytest -o cache_dir=/tmp/coga-derive-twin-sync-pytest-cache`
  — **2372 passed, 1 failed** in 161.80 seconds. The sole failure is the
  pre-existing `tests/test_notification_messages.py::test_recurring_create_is_silent`
  fixture mismatch reproduced on `main`; no new failures. Full output:
  `/tmp/coga-derive-twin-sync-pytest.log`.
- `PYTHONPATH=/home/n/Code/codex/coga/src /tmp/coga-dream-review-venv-20260904/bin/python -m pytest tests/test_notification_messages.py::test_recurring_create_is_silent -q`
  — same baseline `IsADirectoryError` on unmodified primary-checkout tests.
- `git diff --check` — passed.
- `PYTHONPATH=/home/n/Code/codex/coga/src /tmp/coga-dream-review-venv-20260904/bin/python -m coga.cli validate --task live-and-packaged-twin-pairs-are-edited-together-b --json`
  — one valid task, no issues or fixes.

## PR

Derive live/packaged twins from the init and bundled-resource paths so new
mirrors enter the identity check automatically. Enforce all 64 synchronized
pairs and document five intentional configuration/runtime differences, with
checks that reject stale or unexplained exemptions.

Exclude generated installation state from discovery so local virtual
environments, agent tooling, bytecode caches, and machine-local config cannot
cause false drift failures. Add a regression covering both mapping rules and
update repository guidance, both codebase contexts, and Dream's audit
instructions to describe the enforced boundary.

Test plan: `PYTHONPATH=/home/n/Code/codex/coga-derive-twin-sync/src /tmp/coga-dream-review-venv-20260904/bin/python -m pytest -o cache_dir=/tmp/coga-derive-twin-sync-pytest-cache` — 2372 passed; one pre-existing `test_recurring_create_is_silent` failure reproduced on `main`. The packaging/Dream subset passed all 21 tests, including the wheel build.
