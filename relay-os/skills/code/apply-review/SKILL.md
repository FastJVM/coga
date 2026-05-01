---
name: code/apply-review
description: Agent step that reads the `## Self-review` blackboard findings and applies fixes. No-ops cleanly when there are no findings.
---

# Apply review feedback

Read the previous step's findings and act on them. If the review found
nothing, this step is a no-op — bump and move on.

## Order of operations

1. **Read `## Self-review` on the blackboard.** If it says "no findings",
   note that under a `## Fix` section ("nothing to apply") and bump.
2. **Apply must-fix and should-fix items.** Skip optional items unless
   the change is trivial and obviously worth it.
3. **Push back** on any finding you disagree with by writing a one-line
   rebuttal under `## Fix` on the blackboard. Don't silently ignore.
4. **Test.** Re-run `python -m pytest`. If validation changed, re-run
   `relay validate --json`.
5. **Commit.** One commit summarizing the review fixes is fine
   ("review: address self-review findings"). Reference the ticket slug
   in the body.
6. **Bump.** Run `relay bump <slug>` to advance to `pr`.

## Acceptance for this step

- Every must-fix and should-fix item is either applied or rebutted on
  the blackboard.
- Tests pass.
- Working tree clean (changes committed) — or no changes if the review
  was empty.

## What this skill does NOT do

- Re-review your own fixes. One review pass is enough — if applying
  fixes uncovers a deeper issue, `relay panic` and let the human
  decide.
- Open or push the PR — that's `code/open-pr`.

## Gotchas

- If a finding turns out to require a much bigger change than expected,
  stop and `relay panic` rather than expanding scope mid-step.
- An empty review is fine. Don't invent findings to "look thorough".
