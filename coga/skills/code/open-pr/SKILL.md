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

1. **Find the feature worktree.** Read `branch:` and `worktree:` under
   `## Dev` on the blackboard. Change into that worktree and confirm
   it is on the recorded branch with a clean working tree.
2. **Probe auth before you push.** Run `coga validate --check-github`
   (or, minimally, `gh auth status`) *first*. If git/`gh` auth isn't
   ready, do **not** improvise around it: write the exact failure and the
   suggested fix (set/fix the remote, load your SSH key or credential
   helper, run `gh auth login`) under `## Dev` on the blackboard, then
   `coga block` with a one-line reason so the human can fix auth and
   relaunch. The push and PR cannot succeed without it.
3. **Push** the branch from the feature worktree.
4. **Open the PR** with `gh pr create`. If the `code/self-qa` step
   already opened a draft, run `gh pr ready <PR#>` instead. Title =
   ticket title. Body = short summary + "Closes ticket: `<slug>`" + a
   one-line test plan.
5. **Blackboard the URL from the primary checkout.** Return to the
   primary checkout and add `pr: <url>` under the `## Dev` section on
   the blackboard (see the `dev/code` context).
6. **Bump from the primary checkout.** Run `coga bump <slug>` to
   advance to the next step.

## Acceptance for this step

- A PR exists, links the ticket, and is green on CI (or the failure is
  noted on the blackboard with a reason).
- The blackboard has `branch:`, `worktree:`, and `pr: <url>` under
  `## Dev`.
- `coga bump` has advanced the workflow.

## What this skill does NOT do

- Decide whether to merge — that's the human's job in the next step.
- Make code changes. If CI fails for a real reason, `coga block` and
  let the human relaunch.
- Edit `assignee:` by hand. The workflow's per-step `assignee:` field
  handles the role rewrite on bump.

## Gotchas

- If git/`gh` auth isn't ready, you caught it in step 2: blackboard the
  failure and `coga block` rather than skipping the PR step or
  improvising around missing auth.
- If CI fails for reasons unrelated to your change, write it to the
  blackboard with a link to the failing run, then bump anyway. The
  human decides whether to re-run or rework.
