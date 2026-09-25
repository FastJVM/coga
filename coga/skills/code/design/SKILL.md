---
name: code/design
description: Agent step that turns a thin ticket into an implementable spec — problem, acceptance criteria, proposed shape, out of scope — written under the ticket sections that actually compose into the next step. Writes no code.
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
3. **Cite symbols, not line numbers.** Apply this to code claims anywhere
   in the spec. Write the file and the symbol — `src/coga/git.py`,
   `sync_task_state()` — never a bare `git.py:597-640`. Line citations
   can drift before the ticket is implemented.
   - When a range helps navigate a long module, name the symbol first
     and mark the range as a navigational aid that is
     expected to drift, not as a fact the spec rests on.
   - For each code claim, state the *relationship* that makes the fact
     load-bearing, such as which caller passes a value to which callee.
     This gives the implementer something to verify after the code moves.

   See "Citing code in `## Context`" in `bootstrap/ticket` for the full
   citation rule and examples.
4. **Write the spec where the next step will read it.** Only three
   regions of the ticket compose into a launched agent's prompt:
   `## Description`, the inline `## Context`, and the blackboard.
   Composition takes one `##` heading and stops at the next one, so a
   sibling `## Acceptance Criteria`, `## Proposed Shape`, or
   `## Out of Scope` is legible to a human reading the file and
   invisible to the implement agent. Replace or extend the body so it
   has:
   - `## Description` — the problem and why it matters, in prose,
     followed by the spec itself as `###` subsections beneath it:
     - *Acceptance criteria* — a checklist an implementer and a
       reviewer can both verify objectively. This step is the only
       author of that checklist. The ticket interview may already have
       put a done sentence in the `## Description` prose; treat it as
       the seed to expand and reconcile, not a competing version to
       argue with.
     - *Proposed shape* — the intended approach: which files change,
       the key functions or data structures, the order of work.
       Concrete enough to implement, not so rigid it forbids better
       ideas found mid-build.
     - *Out of scope* — what this ticket deliberately does *not* do,
       so the implement step doesn't scope-creep.
   - `## Context` — codebase facts, file paths, and references the
     implementer needs that are not the spec itself.

   Do not park spec content in a fourth `##` section and assume the
   next step will see it. If it isn't under `## Description`,
   `## Context`, or on the blackboard, it is not in the prompt.
5. **Record open questions on the blackboard.** Anything you could not
   resolve from the codebase — a genuine product or design choice —
   goes under an `## Open Questions` section in the ticket's blackboard region. The
   owner answers them in `review-design`; when the frozen workflow includes an
   independent evaluator, that evaluator first tests whether they are complete.
6. **Bump — this is what ends the step.** Run `coga bump <slug>`. It
   advances the workflow to its next frozen step and is the only thing that
   does so — there is no autobump. If you stop without running it, the
   workflow stalls here and the spec never reaches its next reviewer.

## Acceptance for this step

- `ticket.md` states the problem, acceptance criteria, a proposed
  shape, and what is out of scope, all specific to this codebase — and
  all of it under `## Description` or `## Context`, not in sibling `##`
  sections the implement step never composes.
- Every source citation in the spec names a file and a symbol. No claim
  rests on a bare line number.
- Any unresolved design questions are on the blackboard under
  `## Open Questions`.
- No branch, no code, no PR.
- `coga bump <slug>` has been run — the step is not done until it has.

## What this skill does NOT do

- Write or commit code, create a branch, or open a PR — that is
  `code/implement` and `code/open-pr`.
- Review or approve its own spec. A later evaluator may review it; the owner
  decides in `review-design`.
- Invent answers to genuine product decisions — surface them as open
  questions instead.

## Gotchas

- A vague spec defeats the point of the step. "Refactor the config
  loader" is not a Proposed Shape; naming the functions and the new
  signature is.
- Don't gold-plate. The spec should be the smallest design that meets
  the ticket — the Out of Scope section is where ambition goes to wait
  for its own ticket.
