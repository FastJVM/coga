---
name: code/open-pr
description: Agent step that pushes the branch, opens (or marks ready) the PR, hands off to the human owner. Final agent step before human review.
---

# Push and open the PR

Final agent step. Push the branch, open the PR (or mark a draft ready),
hand the ticket back to the human owner.

## Order of operations

1. **Push** the branch.
2. **Open the PR** with `gh pr create`. If the `code/self-review` step
   already opened a draft, run `gh pr ready <PR#>` instead. Title =
   ticket title. Body = short summary + "Closes ticket: `<slug>`" + a
   one-line test plan.
3. **Hand off.** Edit the ticket's `assignee:` frontmatter to the
   ticket's `owner:` (the human who created it).
4. **Blackboard the URL.** Add `pr: <url>` under the `## Dev`
   section on the blackboard (see the `dev/code` context).
5. **Bump.** Run `relay bump <slug>` to advance to the human
   `merge` step.

## Acceptance for this step

- A PR exists, links the ticket, and is green on CI (or the failure is
  noted on the blackboard with a reason).
- The ticket's `assignee` is the human owner.
- The blackboard has `pr: <url>` under `## Dev`.
- `relay bump` has advanced the workflow to `merge`.

## What this skill does NOT do

- Decide whether to merge — that's the human's `merge` step.
- Make code changes. If CI fails for a real reason, `relay panic` and
  let the human relaunch into `fix`.

## Gotchas

- If `gh` isn't authed, surface the error to the human on the
  blackboard — don't skip the PR step.
- If CI fails for reasons unrelated to your change, write it to the
  blackboard with a link to the failing run, then bump anyway. The
  human decides whether to re-run or rework.
