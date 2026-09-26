---
title: 'Settle whether megalaunch is the only unclassified verb: extension-model vs
  the CLI extension audit'
status: in_progress
owner: nicktoper
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
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
step: 2 (peer-review)
agent: claude
---

## Description

Filed by Dream 2026-W39, Phase 6. Route: `stale` finding spanning `docs/contexts/coga/extension-model/SKILL.md` (formerly `coga/contexts/coga/extension-model/SKILL.md`; after the docs-library split the claim appears only there, no longer in `coga/codebase`), `CLAUDE.md`, `AGENTS.md` and the packaged twin. `extension-model`'s live copy already diverges from its packaged twin on main pending PR #857, and #848 also touches it, so this needs a human decision and a base after those land: either the contexts' "megalaunch is the one unclassified verb" claim is right and `docs/design/cli-extension-audit.md` (formerly `docs/cli-extension-audit.md`) should stop listing `ticket`/`retire` as unsettled, or the audit is right and the contexts (plus CLAUDE.md/AGENTS.md, which restate it) should name all three.

**F19 — `coga/extension-model` and `coga/codebase` call `megalaunch` the only unclassified verb while their own evidence base lists `ticket` and `retire` as unsettled**  
(Dream 2026-W39 Phase 2, shard ks-34; class `stale`; target `coga/contexts/coga/extension-model/SKILL.md`; overlapping open PRs: #857 #848)

`coga/contexts/coga/extension-model/SKILL.md` states twice that `coga megalaunch` "is the one genuinely unclassified in-package implementation" (line 84) and "The one live verb still genuinely under classification is `megalaunch`" (line 270); `coga/contexts/coga/codebase/SKILL.md:113-114`, `CLAUDE.md:19`, `AGENTS.md:19`, and both packaged twins under `src/coga/resources/templates/coga/bootstrap/contexts/coga/{extension-model,codebase}/SKILL.md` repeat it. But `docs/cli-extension-audit.md` — which extension-model names as "the verb-by-verb evidence behind" the rule — records `ticket` as "thin built-in head + `coga.authoring` finalize; package home provisional ... no co-versioning invariant has yet been ratified" (line 77, again at 104 and 211-214: "its permanent package home remains provisional until the residual-command ticket records a co-versioning invariant or moves it to the edge"), and `retire` as retaining "its own task-creation and launch head pending its separate cleanup review" (line 214). Under extension-model's own decision rule a verb is kernel only via the launch closure, the fixed `coga run` table, or a reviewed co-versioning proof, and "Python logic only proves that a verb is not an alias" — yet the audit's sole justification for `show`, `status`, `usage`, `slack`, `secret`, `uninstall`, and `skill` is "built-in ... Logic, not a passthrough" or "Heavy side effects", which the context explicitly rules insufficient. So `ticket` (and by the audit's wording `retire`) are unclassified in exactly the sense the context reserves for `megalaunch`, and the read/report and support verbs have no rule-tier classification at all; the five parked drafts under `coga/tasks/v2/cleanup-core-commands/` exist precisely to supply those. Current reality: `src/coga/cli.py:76-96` registers all of these as Typer commands; `runner.RECIPES` (`src/coga/runner.py:47-54`) contains none of them. Owner of the fact is extension-model (rule + settled table); the fix is either to widen the sentence to name `ticket`/`retire` (and the unclassified read/report/support verbs) alongside `megalaunch` as deferred to the same parked design, or to record their kernel-tier reasons in the audit — and to sync `coga/codebase`, `CLAUDE.md`, `AGENTS.md`, and the packaged twins in the same PR.
Correction (same finding): `coga/current-direction` has **no** packaged twin — `find src/coga/resources/templates -path '*current-direction*' -name SKILL.md` returns nothing — so only the live file needs the edit; disregard the twin sentence above.

## Context

Cited rather than attached: `coga/extension-model`
(`docs/contexts/coga/extension-model/SKILL.md`), especially “The microkernel
rule” and “Choosing a home”, owns placement; the classification table in
`docs/design/cli-extension-audit.md` records implementation evidence.
`src/coga/cli.py`'s `app` registrations expose the disputed command heads;
`src/coga/runner.py`'s `RECIPES` gives none of them a registered-recipe home.
The registration proves current implementation, not permanent placement.

<!-- coga:blackboard -->

## Dev
branch: docs/command-classification

## Implementation plan

- PRs #857 and #848 are merged. Fresh main still claims megalaunch is the
  only unclassified implementation, while the audit and parked cleanup
  reviews leave other command heads unresolved.
- Correct the owning extension-model topic and packaged twin; distinguish
  current package residence from a ratified kernel home. Keep the parked
  cleanup work deferred and preserve runtime behavior.
- Replace the AGENTS.md / CLAUDE.md restatements with an owner pointer and
  align the audit's interpretation and provenance. Codebase and
  current-direction no longer repeat the stale claim; no edit needed there.
- Verify twins and run the full pytest suite, then push and return to main.

## Implementation handoff

- Corrected extension-model and its packaged twin: megalaunch is one of
  several unresolved command placements. The table covers ticket,
  retire/slack, read/report heads, support heads, and skill tooling, and names
  their parked cleanup reviews. Shared infrastructure and launch trust hooks
  keep their independent justification; no commands moved or changed behavior.
- AGENTS.md and CLAUDE.md now point to that owner instead of repeating a
  classification inventory. The audit distinguishes implementation mechanism
  from permanent placement and fixes its obsolete context-home/twin claim.
- No edits to codebase or current-direction: neither still contains the
  disputed statement. No fixture changes or new tests were needed for this
  documentation-only correction.
- Verification: `PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m pytest`
  passed: **2945 passed in 180.84s**. `git diff --check`, `cmp AGENTS.md CLAUDE.md`,
  and `cmp docs/contexts/coga/extension-model/SKILL.md src/coga/resources/templates/coga/bootstrap/contexts/coga/extension-model/SKILL.md`
  passed. The full suite includes packaging/twin coverage.
- Branch pushed; rebased onto latest origin/main. Only an audit-log commit
  arrived after testing; post-rebase twin comparisons and whitespace checks
  passed. Launch checkout returned to clean main before this handoff.
- No PR opened, as required for implement. Peer review should assess the
  placement wording; permanent-home proofs and migrations remain deferred.
