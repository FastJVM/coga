---
slug: live-and-packaged-twin-pairs-are-edited-together-b
title: Live and packaged twin pairs are edited together by convention but not enforced
  by any test
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: codex
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
step: 2 (peer-review)
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
