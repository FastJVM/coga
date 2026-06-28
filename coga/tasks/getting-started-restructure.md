---
slug: getting-started-restructure
title: getting-started-restructure
status: draft
autonomy: interactive
owner: lilfedor
human: lilfedor
agent: claude
assignee: lilfedor
contexts: []
skills: []
workflow: code/with-review
secrets: null
script: null
---

## Description

Restructure the **Getting Started** section of the repo-root `README.md` so the
primary onboarding path reads top-to-bottom without digressions. Remove the
over-explaining sentence "That puts `coga` on your PATH." from the install step.
Keep the main flow in this order: install via `pip` → `coga init --user` (set up
a project) → `coga build` (bootstrap) → launch first ticket and the "From there"
other-commands list. Extract the source-checkout / "developing coga itself"
material (the `git clone`, `pip install -e .`, periodic `git pull`, and `pipx
install` from a branch/tag) **out** of the install step — where it currently
interrupts the onboarding flow — and fold it into the existing `## Development`
section at the bottom of the README, which already covers installing from
source and running tests.

## Context

- Edits **only** the repo-root `README.md` — the coga source repo's front-door
  doc. It is not mirrored by a packaged template under
  `src/coga/resources/templates/`, so no sync is required.
- Current layout (`## Getting Started`, ~lines 29–103): step 1 ("Install the
  CLI") embeds the source-checkout block between the `pip install coga` lines
  and step 2 ("Set up a project"). That embedded block is exactly what moves
  out. Steps 2 (`coga init --user`), 3 (`coga build`), and 4 (launch first
  ticket + the "From there" list and the "First run vs. ongoing authoring"
  callout) are already in the desired order — they just need to follow the
  install step without the source-checkout interruption.
- This is essentially a **reorder plus one-sentence deletion**, not a content
  rewrite. Preserve the install commands, the "From there" list, and the callout
  verbatim. Minimal transitional rewording **is** expected where the source
  block is lifted out: it currently opens "To work against a source checkout
  instead —", which only reads correctly next to the `pip` step, so give it a
  fresh lead-in once it lives under `## Development`.
- The moved material lands in the **existing `## Development` section** (~line
  862) — not a new section. That section already covers install-from-source +
  tests and is the conventional home for contributor setup; merge the
  source-checkout steps into it (above the existing `python -m pytest` / `coga
  validate` block).
- Line 864 of `## Development` currently reads `Install from source as in
  [Getting Started](#getting-started), then:`. Once the steps live in
  `## Development` itself, that cross-reference is redundant — drop or reword it
  so the section reads cleanly with the install steps inline.
- A prior uncommitted one-line edit that removed the PATH sentence was reverted
  on 2026-06-28 so this ticket starts from a clean base; redo that removal as
  part of the restructure.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Decisions

- 2026-06-28 (human): the source-checkout / "developing coga" block **folds
  into the existing `## Development` section** at the bottom of the README — not
  a new section near the top. Rationale: that material serves contributors and
  PR-branch testers (a small, technical audience), so it belongs in the
  conventional bottom-of-README dev section, keeping the main install flow
  clean. This resolves the evaluator's "overlapping existing section" + "stale
  cross-reference" findings below; both are now folded into the ticket Context.

## Evaluator review

**Description clarity / target order — good.** The intended final order is unambiguous: install (`pip`) → set up project (`coga init --user`) → bootstrap (`coga build`) → launch first ticket + "From there" list, with the source-checkout material extracted into its own section placed after the Getting Started flow (between `## Getting Started` and `## Principles`). An agent with no prior context could execute this correctly. The one-sentence deletion is precisely identified.

**Context facts — verified accurate, with one omission.** I checked every factual claim against the live README:
- The source-checkout block *does* sit between the `pip install coga` lines (lines 33–38) and "Set up a project" (line 58) — specifically lines 40–56. Correct.
- Steps 2 (`coga init --user`, line 58), 3 (`coga build`, line 70), and 4 (launch, line 80) plus the "From there" list and the "First run vs. ongoing authoring" callout are already in the desired order. Correct.
- "That puts `coga` on your PATH." is on line 37, and the ticket correctly scopes the deletion to that sentence only (the adjacent "Upgrade later…" sentence stays). Correct.
- No packaged README template exists under `src/coga/resources/templates/`, so the "no sync required" claim holds.

**Missing fact (the important one):** the ticket overlooks two things tied to moving the source-install material out of Getting Started:
1. **A stale cross-reference.** Line 864, in the existing `## Development` section, reads: `Install from source as in [Getting Started](#getting-started), then:`. Once the source-checkout instructions leave Getting Started, this link sends readers to a section that no longer contains them. The agent must repoint it to the new section's anchor (e.g. `#developing-coga-from-source`).
2. **An overlapping existing section.** There is already a `## Development` section (line 862) whose entire premise is installing from source and running tests. Creating a separate "Developing coga from source" section near the top will sit awkwardly beside it and partially duplicate its theme. The ticket should instruct the agent to reconcile the two — either fold the moved material into the existing `## Development` section, or explicitly note why a second near-the-top section is preferred. As written, the ticket appears unaware that `## Development` exists.

**Workflow fit.** `code/with-review` (implement → peer-review by the other agent → open-pr → human review) is heavier than this work warrants — it's a docs-only reorder plus a one-sentence deletion. It's not a *mismatch* (conservative is fine for a front-door doc), but the peer-review step adds a round-trip for very low-risk content. Acceptable; just know it's on the heavy end.

**Contexts.** Attaching none and inlining the facts in `## Context` is the right call here — the facts are local to this one README and not reusable. The one context that could have been relevant (`codebase/SKILL.md`'s live-copy/template-sync rule) is preemptively neutralized by the accurate "no packaged template" note. No missing context.

**Scope.** Appropriately sized for one ticket — a single-file reorder plus a deletion. The cross-reference fix and Development-section reconciliation noted above are part of the same edit, not separate tickets.

**Assumptions to question before launch:**
- The ticket asserts the restructure is "a reorder plus one-sentence deletion, not a rewrite," and says to preserve commands and prose verbatim. But cleanly lifting the source block out will require *some* connective rewording (the moved block opens with "To work against a source checkout instead—" which only makes sense adjacent to the pip step; as a standalone section it needs a fresh lead-in). Flag that minimal transitional rewording is expected, not forbidden.
- "Pick a fitting heading level/title" leaves the heading level open while specifying placement before `## Principles`. Given the existing `## Development` section, the agent should default to `##` and consciously decide between a new heading and merging — see the omission above.
- Confirm the prior reverted PATH edit (noted as reverted 2026-06-28) is in fact absent from the working tree before starting, so the deletion isn't a no-op or a double-removal.
