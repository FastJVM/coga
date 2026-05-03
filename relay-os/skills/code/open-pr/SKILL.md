---
name: code/open-pr
description: Agent step that pushes the branch and opens (or marks ready) the PR. Final agent step before human review.
---

# Push and open the PR

Final agent step. Push the branch and open the PR (or mark a draft
ready). The workflow declares the next step's assignee, so the
handoff happens automatically on bump — you don't edit `assignee:`
yourself.

## Order of operations

1. **Push** the branch.
2. **Open the PR** with `gh pr create`. If the `code/self-review` step
   already opened a draft, run `gh pr ready <PR#>` instead. Title =
   ticket title. Body = short summary + "Closes ticket: `<slug>`" + a
   one-line test plan.
3. **Blackboard the URL.** Add `pr: <url>` under the `## Dev`
   section on the blackboard (see the `dev/code` context).
4. **Bump.** Run `relay bump <slug>` to advance to the next step.

## Acceptance for this step

- A PR exists, links the ticket, and is green on CI (or the failure is
  noted on the blackboard with a reason).
- The blackboard has `pr: <url>` under `## Dev`.
- `relay bump` has advanced the workflow.

## What this skill does NOT do

- Decide whether to merge — that's the human's job in the next step.
- Make code changes. If CI fails for a real reason, `relay panic` and
  let the human relaunch.
- Edit `assignee:` by hand. The workflow's per-step `assignee:` field
  handles the role rewrite on bump.

## Gotchas

- If `gh` isn't authed, surface the error to the human on the
  blackboard — don't skip the PR step.
- If CI fails for reasons unrelated to your change, write it to the
  blackboard with a link to the failing run, then bump anyway. The
  human decides whether to re-run or rework.
