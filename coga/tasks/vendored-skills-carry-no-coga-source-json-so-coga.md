---
title: Correct recurring/skill-update's provenance claim to match how skills are actually managed
status: active
owner: nicktoper
agent: claude
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
step: 1 (implement)
---

## Description

Narrowed 2026-09-16 (`adjudicate-parked-and-active-tickets-whose-premise`):
the template rewrite this ticket originally asked for has already landed, and
one sentence remains.

The weekly `recurring/skill-update` template (`coga/recurring/skill-update/ticket.md`
and its packaged twin) now describes every skill category it services —
GitHub-backed packs delegated to `gh skill`, URL installs carrying
`.coga-source.json`, `install-local` directories, twins of bundled skills, and
hand-vendored packs "outside every updater path" with "the same unmanaged
update posture". What it still does not say is **where human-readable
attribution lives**: the deliberately unmanaged, hand-vendored
`anthropic/skill-creator` carries
`coga/skills/anthropic/skill-creator/ATTRIBUTION.md`, pinning `anthropics/skills`
at `f458cee3`; separately, the package-backed `browser/playwright`
`local-override` carries `coga/skills/browser/playwright/NOTICE.txt`, naming
`microsoft/playwright-cli` as the source of its adapted material.

Add that one statement to the template's `## Description`, next to the
existing hand-vendored sentences, in both copies, keeping the hand-vendored
and local-override categories distinct. Do not backfill `.coga-source.json`
for either skill (see Context), and do not touch `skill_manager.py`.

## Context

### What already shipped, and where

- `.coga-source.json` provenance is no longer hypothetical for this repo:
  `coga/skills/clarity/.coga-source.json` is a real URL install, and the
  template's `include`-allowlist paragraphs describe its shape.
- PR #743 rewrote the template around `gh skill` delegation, and #776, #796,
  and #804 added the `include` allowlist, per-skill `gh` outcomes, and the
  runner resync — all after this ticket was last edited. Re-read the current template before writing; the categories
  and the four exit-code paragraphs are correct and must stay.
- Live and packaged twins are derived, not registered: `tests/test_packaging.py`
  discovers every `templates/coga/<path>` ↔ `coga/<path>` pair and requires
  byte-identity, so editing only one copy fails the suite. There is no list to
  add the pair to.

### Do not backfill

Only `anthropic/skill-creator` is a genuine hand-vendored external import, and
it has no install-url source to record — writing a `.coga-source.json` for it
would be inventing machine provenance for a hand-copied tree, and would then
make the weekly job try to "update" it from a URL nobody installed it from.
`browser/playwright` looks vendored but reports `local-override`: it shadows a
bundled package-backed skill and refreshes with the package. Its `NOTICE.txt`
is still the right human-readable provenance to name.

### Provenance

Found by Dream 2026-08-24 — Phase 2 shards 13, 14, 15 (merged), corroborated by
Phase 3 shards ca-04 and ca-05. The original framing ("walks nothing",
"no `.coga-source.json` exists anywhere") was overtaken by PRs #743–#804 and
by the `clarity` install; the residue above is what survived re-verification.

### Split out of this ticket

Two follow-ups that arrived here from Dream Phase 6 have their own tickets:

- `guard-the-browser-dochub-and-playwright-live-vs-pa` — packaging-test coverage
  for the `browser/{dochub,playwright}` mirrors (done 2026-09-13, since retired).
- `validate-that-committed-skill-scripts-with-a-sheba` — validator check for
  committed scripts that carry a shebang but not the executable bit.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
