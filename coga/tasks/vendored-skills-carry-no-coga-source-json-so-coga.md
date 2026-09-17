---
title: Correct recurring/skill-update's provenance claim to match how skills are actually
  managed
status: in_progress
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
step: 3 (open-pr)
launch_generation: pending:a57947d5-cafb-41f8-8659-5305d766df81
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

## Dev

branch: docs/skill-attribution
worktree: /tmp/coga-skill-attribution

## Implement plan

- Add one human-readable attribution sentence beside the existing unmanaged
  skill wording in both recurring template copies. Keep the hand-vendored
  Anthropic skill distinct from the package-backed Playwright local override.
- Verified the Anthropic attribution pins `anthropics/skills` at `f458cee3`
  and the Playwright notice names adapted material from
  `microsoft/playwright-cli`. The current templates are identical and still
  lack these attribution pointers.
- Use the existing packaging check and full `python -m pytest` suite for this
  documentation-only change; no new prose-matching test or example change is
  needed. Commit the templates, refresh against `origin/main`, then bump from
  this primary checkout. No implementation push or PR in this step.

## Implementation notes

- Added the attribution sentence to both template descriptions, immediately
  after the existing hand-vendored update-posture sentence. Existing updater
  categories, allowlist guidance, and exit-code paragraphs are unchanged;
  neither provenance JSON nor `skill_manager.py` was modified.
- `git diff --check` and the template `cmp` pass. Initial `python -m pytest`
  could not collect the CLI tests because ambient Python lacks the declared
  `tomlkit` dependency. Installed `.[test]` in
  `/tmp/coga-skill-attribution-venv` (package-index access required escalation
  after sandbox DNS failure). The full suite passed: **2,654 tests in 185.03s**,
  including packaging/twin checks, with
  `PYTHONPATH=/tmp/coga-skill-attribution/src /tmp/coga-skill-attribution-venv/bin/python -m pytest`.

## Implement handoff

- Committed as `c1f3b3aa` (`Clarify skill-update attribution locations`): only
  the live recurring template and its packaged twin changed, by the same
  five-line sentence.
- Post-commit `git fetch origin main && git rebase FETCH_HEAD` completed;
  the branch was already up to date. `git merge-base --is-ancestor origin/main
  HEAD` passed and `git status --short` is empty in the feature checkout.
  The freshness retry required escalation because the sandbox mounted the
  linked worktree's Git metadata read-only.
- No branch push or PR. Ready for the frozen workflow's `peer-review` step;
  the primary checkout holds the authoritative blackboard and will bump.

## Adjacent finding — deferred

The `Hand-vendored upstream skills` bullet in
`coga/contexts/coga/codebase/SKILL.md` still groups Playwright with the
Anthropic import. `src/coga/skill_manager.py`'s `_local_override_result`
identifies a repo copy shadowing a bundled skill, and `_bundled_update_result`
explicitly explains that upgrading the package does not change that installed
repo copy. The ticket's existing refresh-with-package claim and the template's
general bundled-refresh wording merit a separate clarification for local
overrides. This step only adds the requested attribution pointers; it does not
change update behavior or those existing statements. No dedicated follow-up
was found in the current tasks by searching the classification and affected
context terms. Carry this finding into the retro handoff.

## Peer review

- Refreshed the recorded feature worktree with `git fetch origin main && git
  rebase FETCH_HEAD`; the rebase completed without conflicts. The attribution
  commit is now `927d43e6`, based on `origin/main` at `55667b7f`.
- `codex review --base main` from `/tmp/coga-skill-attribution` **returned**
  with exit 0 and no findings. It confirmed the attribution references and
  template parity. Its packaging pytest attempt used ambient Python and hit
  the already-known missing `tomlkit` dependency; its direct parity checks
  passed. No must-fix findings or corrective commit were needed.
- Post-rebase `PYTHONPATH=/tmp/coga-skill-attribution/src
  /tmp/coga-skill-attribution-venv/bin/python -m pytest` completed successfully:
  **2,654 passed in 178.62s**, including the packaging/twin checks.
- Manually checked the added sentence against `ATTRIBUTION.md` and `NOTICE.txt`.
  Both provenance pointers are accurate and the two skill categories remain
  distinct. Post-rebase `git diff --check` and template `cmp` pass; the diff
  still contains only the same five-line addition in the two templates.
  Read the surrounding description to confirm updater categories, allowlist
  guidance, and exit-code paragraphs remain intact. This prose-only change
  affects no terminal, pager, prompt, or rendered Slack surface.
- The feature worktree is clean and contains one committed change ahead of
  fetched `origin/main`. The adjacent local-override documentation finding
  above remains deferred for the retro handoff. The review is complete and
  the PR body below is ready for the next step.

## PR

The weekly skill-update description now names the human-readable attribution
files for hand-vendored `anthropic/skill-creator` and the separate
`browser/playwright` local override. Both live and packaged templates point to
the Anthropic `ATTRIBUTION.md` pin (`anthropics/skills` at `f458cee3`) and the
Playwright `NOTICE.txt` source (`microsoft/playwright-cli`).

Test plan: `PYTHONPATH=/tmp/coga-skill-attribution/src /tmp/coga-skill-attribution-venv/bin/python -m pytest` (2,654 passed); `git diff --check`; `cmp coga/recurring/skill-update/ticket.md src/coga/resources/templates/coga/recurring/skill-update/ticket.md`.
