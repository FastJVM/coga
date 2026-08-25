---
slug: live-and-packaged-twin-pairs-are-edited-together-b
title: Live and packaged twin pairs are edited together by convention but not enforced
  by any test
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
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
step: 1 (implement)
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
