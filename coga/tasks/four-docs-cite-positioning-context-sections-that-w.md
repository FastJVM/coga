---
title: Four docs cite positioning-context sections that were never committed
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

Filed by Dream 2026-W39, Phase 6. Route: `drift` — four docs (now `docs/evidence/why-switch-to-coga.md`, `docs/evidence/pitch-evaluation.md`, `docs/evidence/build-vs-adopt.md`, `docs/evidence/adoption-trial.md`) link headings in `docs/contexts/marketing/positioning/SKILL.md` (formerly `coga/contexts/marketing/positioning/SKILL.md`) that were never committed anywhere (checked: every worktree, `git log --all -S`, and open PR #841 which touches positioning but does not add them). The mechanical fix (drop/repoint the dead anchors) would silently erase the docs' claim that positioning is the maintained owner of the pitch statements, so the correction is a human choice: restore the missing sections (if they exist in uncommitted marketing work — `marketing/phase-0-audit` and `marketing/build-the-launch-plan` are in_progress), or repoint the docs to the actual owner, or drop the claims. (The docs-library migration already dropped the dead `#…` anchors from those links, but the docs still name positioning as the maintained owner of those statements, so the choice is still open.)

**F75 — Four docs link positioning-context sections (dated 2026-09-11..14) that were never committed anywhere**  
(Dream 2026-W39 Phase 3, shard ca-06, ca-07, ca-08 (merged 4 blocks); class `drift`; target `docs/why-switch-to-coga.md, docs/pitch-evaluation.md, docs/build-vs-adopt.md, docs/adoption-trial.md → coga/contexts/marketing/positioning/SKILL.md`)

_ca-06 — why-switch-to-coga.md links four positioning-context sections that do not exist:_ The doc states that "The marketing positioning principle and comparative ratings summarize this research" and links four heading anchors in `coga/contexts/marketing/positioning/SKILL.md`: `#current-owner-direction--2026-09-11`, `#competitive-positioning-and-ratings--2026-09-11` (line 32-33), `#two-linked-central-ideas--2026-09-13` (line 40, "chosen delegation and understandable ownership"), and `#message-hierarchy--2026-09-14` (line 93, "uses megalaunch to demonstrate the immediate payoff"). The tracked context (3,408 bytes, last changed 2026-09-10, commit 7a3d56431) has only three headings — `## Earlier directions to consider`, `## Source and claim limits`, `## Where the new message lands` — opens with "Fresh start, owner direction of 2026-09-10 ... The next pitch, audience, central story and tone are still to be decided", and contains none of the phrases "owner direction", "competitive positioning", "two linked central ideas" or "message hierarchy" (`grep -in` over the file returns nothing; a repo-wide grep finds those phrases only in `docs/why-switch-to-coga.md` and `docs/pitch-evaluation.md`). Neither `coga/contexts/marketing/launch-history/positioning-before-reset.md` nor any other file under `coga/contexts/marketing/` carries them either, and `git status` shows no uncommitted change to the context. The doc was committed 2026-09-16 (924412e0c) citing sections dated 09-11 to 09-14 that never landed in the context, so the claim that the positioning context holds the ratings, the two-ideas principle and the message hierarchy is unbacked and all four links are dead. All other referenced artifacts in the file (`docs/{build-vs-adopt,usage-comparison,adoption-trial,pitch-evaluation,continuity-comparison,upkeep-audit}.md` with their cited anchors, `src/coga/{megalaunch,compose}.py`, `src/coga/resources/prompt-megalaunch.md`, `coga/tasks/marketing/phase-0-audit/source-inspection-results.json`, `coga/contexts/coga/{architecture,codebase}/SKILL.md`, `coga/recurring/dream/ticket.md`) exist as named.

_ca-07 — pitch-evaluation links three positioning sections that the positioning context does not contain:_ `docs/pitch-evaluation.md` names `coga/contexts/marketing/positioning/SKILL.md` as the "maintained" owner of three statements and links section anchors that do not exist there: line 13 `#two-linked-central-ideas--2026-09-13` ("the maintained statement"), line 344 `#message-hierarchy--2026-09-14` ("the whole message hierarchy"), and line 615 `#draft-explanation-and-comparative-check--2026-09-13` ("The maintained copy is in positioning"). The positioning context at HEAD has only four headings (`# Coga positioning`, `## Earlier directions to consider`, `## Source and claim limits`, `## Where the new message lands`), and `git log --all -S` for each anchor slug matches only the docs commit `924412e0c` — none of those sections was ever committed to the context, whose last content rewrite is `7a3d56431` (2026-09-10). The doc therefore points readers at a "maintained copy" that lives nowhere on disk; either the positioning context must gain those sections or the doc must stop naming it as their owner. `docs/why-switch-to-coga.md:40` links the same `#two-linked-central-ideas` anchor (outside this shard's owned paths; same cause). Source of truth: `coga/contexts/marketing/positioning/SKILL.md` heading list at HEAD.

_ca-07 — build-vs-adopt links a positioning heading that does not exist:_ `docs/build-vs-adopt.md:28` links "the pitch candidate" to `../coga/contexts/marketing/positioning/SKILL.md#pitch-candidate-your-way-of-working-made-executable` and describes it as centering on "editable work definitions that agents execute and reviewed lessons can improve". No such heading exists: `grep -n "^#" coga/contexts/marketing/positioning/SKILL.md` yields only `# Coga positioning`, `## Earlier directions to consider`, `## Source and claim limits`, and `## Where the new message lands`, and `grep -rin "pitch candidate" coga/contexts/marketing/` matches nothing. `git log --all -S"your way of working, made executable"` shows the phrase only ever entered the repo through the docs commit `924412e0c` (2026-09-16); the positioning context was rewritten in `7a3d56431` (2026-09-10) before the doc was written and never carried that section. `docs/adoption-trial.md:113` links the same missing anchor (outside this shard's owned paths; same cause). Source of truth: `coga/contexts/marketing/positioning/SKILL.md` heading list.

_ca-08 — adoption-trial.md links a positioning-context section that does not exist:_ `docs/adoption-trial.md` ends: "The [positioning context](../coga/contexts/marketing/positioning/SKILL.md#pitch-candidate-your-way-of-working-made-executable) owns the resulting pitch candidate." The file `coga/contexts/marketing/positioning/SKILL.md` exists (3,408 bytes) but has only four headings — `# Coga positioning`, `## Earlier directions to consider`, `## Source and claim limits`, `## Where the new message lands` — and no section titled "Pitch candidate: your way of working made executable"; `grep -i 'way of working made executable'` over `coga/contexts`, `coga/skills`, `docs`, and `README.md` returns nothing, and `git log --all -S'way of working made executable'` shows the heading was never committed anywhere. The context also says at line 61 "No new pitch or campaign is approved by this inventory reset." The doc's ownership claim points at a missing artifact: either the positioning context should carry that pitch-candidate section, or the doc should repoint (e.g. to the `write-the-pitch-and-narrative` plan ticket the context links at line 58) or drop the anchor.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
