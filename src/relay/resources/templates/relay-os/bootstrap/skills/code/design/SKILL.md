---
name: code/design
description: Agent step that turns a thin ticket into an implementable spec. Fleshes out the ticket body — Description, Acceptance Criteria, Proposed Shape, Out of Scope. Writes no code.
---

# Design the change

You are turning a thin ticket into something an implementer can pick up
without guessing. The output is a *written spec on the ticket itself* —
no branch, no code, no PR. The later `code/implement` step does the
build, and it should not have to re-derive intent.

## Order of operations

1. **Read the ticket and its contexts.** Whatever the human wrote in
   the Description is the seed. Read the referenced files and the
   composed contexts so the spec fits the codebase as it actually is.
2. **Investigate before you write.** Locate the real files, functions,
   and call sites the change touches. A spec that names the wrong
   module is worse than no spec.
3. **Write the spec into `ticket.md`.** Replace or extend the body so
   it has these sections:
   - `## Description` — the problem and why it matters, in prose.
   - `## Acceptance Criteria` — a checklist an implementer and a
     reviewer can both verify objectively.
   - `## Proposed Shape` — the intended approach: which files change,
     the key functions or data structures, the order of work. Concrete
     enough to implement, not so rigid it forbids better ideas found
     mid-build.
   - `## Out of Scope` — what this ticket deliberately does *not* do,
     so the implement step doesn't scope-creep.
4. **Record open questions on the blackboard.** Anything you could not
   resolve from the codebase — a genuine product or design choice —
   goes under an `## Open Questions` section on `blackboard.md`. The
   `review-design` step exists for the owner to answer them.
5. **Split the ticket if it is too big.** If the honest Proposed Shape
   is more than one PR's worth of work, say so on the blackboard and
   recommend a split rather than writing a spec you know is oversized.
6. **Bump — this is what ends the step.** Run `relay bump <slug>`. It
   advances the workflow to `review-design` and is the only thing that
   does so — there is no autobump. If you stop without running it the
   workflow stalls here and the owner is never asked to review.

## Acceptance for this step

- `ticket.md` has Description, Acceptance Criteria, Proposed Shape, and
  Out of Scope sections, all specific to this codebase.
- Any unresolved design questions are on the blackboard under
  `## Open Questions`.
- No branch, no code, no PR.
- `relay bump <slug>` has been run — the step is not done until it has.

## What this skill does NOT do

- Write or commit code, create a branch, or open a PR — that is
  `code/implement` and `code/open-pr`.
- Approve its own spec. The owner does that in `review-design`.
- Invent answers to genuine product decisions — surface them as open
  questions instead.

## Gotchas

- A vague spec defeats the point of the step. "Refactor the config
  loader" is not a Proposed Shape; naming the functions and the new
  signature is.
- Don't gold-plate. The spec should be the smallest design that meets
  the ticket — the Out of Scope section is where ambition goes to wait
  for its own ticket.
