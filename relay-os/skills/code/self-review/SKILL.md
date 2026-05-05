---
name: code/self-review
description: Agent step that runs `/review` against the current branch's diff and writes findings to the blackboard for the next step to apply.
---

# Self-review the diff

Run an independent review pass over the work the previous step
committed. The output is a list of findings the next step (`code/apply-review`)
will read and act on. You are **not** fixing anything in this step.

## Order of operations

1. **Confirm state.** Read `branch:` and `worktree:` under `## Dev` on
   the blackboard. Change into that feature worktree and confirm it is
   on the recorded branch with a clean working tree (the previous
   `code/implement` step committed). If not, `relay panic` — something
   is off.
2. **Run `/review`.** Invoke the `/review` slash command against the
   branch's diff vs `main`. If `/review` requires a PR, open a draft PR
   first (`gh pr create --draft`) and run `/review <PR#>` against it —
   keep the PR draft until the `code/open-pr` step marks it ready.
3. **Capture findings on the blackboard** in the primary checkout under
   a top-level `## Self-review` section. Verbatim is fine; don't
   summarize. Group as:
   - **Must fix** — correctness, security, broken tests, missing
     acceptance criteria.
   - **Should fix** — clarity, naming, small structural issues.
   - **Optional** — nits, stylistic preferences. The next step may skip
     these.
4. **Bump from the primary checkout.** Run `relay bump <slug>` to
   advance to `fix`.

## Acceptance for this step

- `## Self-review` section exists on the blackboard with at least one
  of the three groups (or "no findings" stated explicitly).
- Working tree is still clean — you did not edit code.
- If a draft PR was opened, its URL is on the blackboard.

## What this skill does NOT do

- Apply fixes — that's `code/apply-review`.
- Mark the PR ready for human review — that's `code/open-pr`.

## Gotchas

- An empty review is a valid outcome. Write "no findings" on the
  blackboard so the next step knows to no-op.
- Don't filter aggressively — surface findings even if you disagree.
  The next step decides what to apply.
