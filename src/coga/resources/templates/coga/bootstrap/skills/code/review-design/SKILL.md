---
name: code/review-design
description: Cold peer review of an agent-written design spec before owner approval. Checks whether the ticket is correct and implementable without relying on the author's unstated context; writes findings but no code.
---

# Review the design cold

You are the independent evaluator, not the author of this spec. Read it as the
future implementer who did not participate in the design session. Your output
is evidence for the owner approval step that follows; do not approve the design
on the owner's behalf.

## Order of operations

1. **Test the ticket on its own terms.** Read the ticket body first. Treat its
   Description, Acceptance Criteria, Proposed Shape, and Out of Scope as the
   complete statement of intent. Record ambiguities before using blackboard
   notes to explain them away; an implementer must not need the author's hidden
   reasoning.
2. **Verify rather than infer.** Read the attached contexts and inspect the
   current source, tests, fixtures, and workflow definition needed to check the
   spec's concrete claims. Cite stable paths and symbol or section names in
   findings. Do not pin a finding only to a line number that will drift.
3. **Review the consequential axes.** Check:
   - whether a new agent could implement the requested outcome without guessing;
   - whether named behavior, files, symbols, and dependencies match the repo;
   - whether each acceptance criterion is objective, sufficient, and testable;
   - whether Proposed Shape, Acceptance Criteria, and Out of Scope agree;
   - whether the workflow and attached contexts fit the work;
   - whether the change is one coherent PR and respects the repo's architectural
     boundaries; and
   - which assumptions, failure modes, or owner decisions remain unstated.
4. **Write a decision-useful review.** Add a top-level `## Evaluator review`
   section to the ticket's blackboard. On a retry, replace your prior review
   instead of appending a second section. Separate findings that must be
   resolved before implementation from optional recommendations, order them by
   impact, and include evidence. If the design is ready, say so explicitly; do
   not manufacture findings. Preserve unrelated blackboard sections.
5. **Hand findings to the owner.** Design defects and open questions are the
   expected output of this step, not reasons to edit the spec or block the
   ticket. After the review is recorded, run `coga bump <slug>` as the last
   action and stop. The next `review-design` step is the owner gate that edits
   or accepts the spec.

## Acceptance for this step

- The review was performed from the perspective of an implementer who did not
  author the design.
- Material claims were checked against the current repo.
- `## Evaluator review` contains prioritized, evidenced findings or an explicit
  ready verdict.
- No ticket-body edits, branch, code, or PR were produced.
- `coga bump <slug>` advanced the ticket exactly once to owner review.

## What this skill does NOT do

- Rewrite or approve the spec; the owner handles that in `review-design`.
- Implement the change or review an implementation diff.
- Repeat ticket-authoring hygiene such as prompt-size analysis. This pass
  reviews the completed design spec.
