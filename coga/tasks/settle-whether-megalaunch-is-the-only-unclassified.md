---
title: 'Settle whether megalaunch is the only unclassified verb: extension-model vs
  the CLI extension audit'
status: draft
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
step: 1 (implement)
---

## Description

Filed by Dream 2026-W39, Phase 6. Route: `stale` finding spanning `docs/contexts/coga/extension-model/SKILL.md` (formerly `coga/contexts/coga/extension-model/SKILL.md`; after the docs-library split the claim appears only there, no longer in `coga/codebase`), `CLAUDE.md`, `AGENTS.md` and the packaged twin. `extension-model`'s live copy already diverges from its packaged twin on main pending PR #857, and #848 also touches it, so this needs a human decision and a base after those land: either the contexts' "megalaunch is the one unclassified verb" claim is right and `docs/design/cli-extension-audit.md` (formerly `docs/cli-extension-audit.md`) should stop listing `ticket`/`retire` as unsettled, or the audit is right and the contexts (plus CLAUDE.md/AGENTS.md, which restate it) should name all three.

**F19 — `coga/extension-model` and `coga/codebase` call `megalaunch` the only unclassified verb while their own evidence base lists `ticket` and `retire` as unsettled**  
(Dream 2026-W39 Phase 2, shard ks-34; class `stale`; target `coga/contexts/coga/extension-model/SKILL.md`; overlapping open PRs: #857 #848)

`coga/contexts/coga/extension-model/SKILL.md` states twice that `coga megalaunch` "is the one genuinely unclassified in-package implementation" (line 84) and "The one live verb still genuinely under classification is `megalaunch`" (line 270); `coga/contexts/coga/codebase/SKILL.md:113-114`, `CLAUDE.md:19`, `AGENTS.md:19`, and both packaged twins under `src/coga/resources/templates/coga/bootstrap/contexts/coga/{extension-model,codebase}/SKILL.md` repeat it. But `docs/cli-extension-audit.md` — which extension-model names as "the verb-by-verb evidence behind" the rule — records `ticket` as "thin built-in head + `coga.authoring` finalize; package home provisional ... no co-versioning invariant has yet been ratified" (line 77, again at 104 and 211-214: "its permanent package home remains provisional until the residual-command ticket records a co-versioning invariant or moves it to the edge"), and `retire` as retaining "its own task-creation and launch head pending its separate cleanup review" (line 214). Under extension-model's own decision rule a verb is kernel only via the launch closure, the fixed `coga run` table, or a reviewed co-versioning proof, and "Python logic only proves that a verb is not an alias" — yet the audit's sole justification for `show`, `status`, `usage`, `slack`, `secret`, `uninstall`, and `skill` is "built-in ... Logic, not a passthrough" or "Heavy side effects", which the context explicitly rules insufficient. So `ticket` (and by the audit's wording `retire`) are unclassified in exactly the sense the context reserves for `megalaunch`, and the read/report and support verbs have no rule-tier classification at all; the five parked drafts under `coga/tasks/v2/cleanup-core-commands/` exist precisely to supply those. Current reality: `src/coga/cli.py:76-96` registers all of these as Typer commands; `runner.RECIPES` (`src/coga/runner.py:47-54`) contains none of them. Owner of the fact is extension-model (rule + settled table); the fix is either to widen the sentence to name `ticket`/`retire` (and the unclassified read/report/support verbs) alongside `megalaunch` as deferred to the same parked design, or to record their kernel-tier reasons in the audit — and to sync `coga/codebase`, `CLAUDE.md`, `AGENTS.md`, and the packaged twins in the same PR.
Correction (same finding): `coga/current-direction` has **no** packaged twin — `find src/coga/resources/templates -path '*current-direction*' -name SKILL.md` returns nothing — so only the live file needs the edit; disregard the twin sentence above.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
