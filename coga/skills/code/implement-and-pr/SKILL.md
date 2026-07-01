---
name: code/implement-and-pr
description: Agent step for a code change. Branch, implement, test, commit, push, open PR, hand off to the human reviewer. Used by the `code/with-review` workflow.
---

# Implement and open a PR

You are doing a code change end-to-end. Finish on a clean PR, with the
ticket reassigned to the human owner.

## Order of operations

1. **Read the ticket carefully.** Description, acceptance criteria,
   referenced files. If anything is ambiguous, write the ambiguity to
   the blackboard and stop — do not guess.
2. **Create a feature worktree.** From the primary checkout on `main`,
   create a feature branch in a separate worktree outside the repo
   directory, for example:
   `git worktree add ../coga-<branch-name> -b <branch-name> main`.
   Pick a short descriptive branch name — it does
   *not* have to match the slug. Then return to the primary checkout and
   write `branch: <branch-name>` and `worktree: <path>` under a `## Dev`
   section on the blackboard. See the `dev/code` context for the full
   convention.
3. **Implement in the worktree.** Change into the feature worktree and
   match existing code style. Keep changes scoped to the
   ticket — no opportunistic refactors. If you find a real adjacent bug,
   write it on the blackboard for a follow-up ticket; don't fix it here.
4. **Test.** Add a regression test before the fix when the ticket is a
   bug. Run `python -m pytest`. If validation behavior changed, run
   `coga validate --json` against the example fixture.
5. **Update the example fixture** when behavior affects task layout,
   prompt composition, or workflow semantics (per CLAUDE.md).
6. **Commit.** Conventional, present-tense summary line. Reference the
   ticket slug in the body. One commit per logical change is fine; rebase
   to clean up before pushing.
7. **Probe auth before you push.** Run `coga validate --check-github`
   (or, minimally, `gh auth status`) *first*. If git/`gh` auth isn't
   ready, do **not** improvise around it: write the exact failure and the
   suggested fix (set/fix the remote, load your SSH key or credential
   helper, run `gh auth login`) under `## Dev` on the blackboard, then
   `coga block` with a one-line reason so the human can fix auth and
   relaunch. The push and PR cannot succeed without it.
8. **Push** the branch from the feature worktree.
9. **Open the PR** with `gh pr create`. Title = ticket title. Body =
   short summary + "Closes ticket: `<slug>`" + a one-line test plan.
10. **Hand off from the primary checkout.** Return to the primary checkout
    and edit the ticket's `assignee:` frontmatter to the
    ticket's `owner:` (the human who created it). Add `pr: <url>`
    under the `## Dev` section on the blackboard.
11. **Advance.** Run `coga bump` to move the workflow to `review`. This
    posts to Slack and logs the handoff.

## Acceptance for this step

You are done when:

- A PR exists, links the ticket, and is green on CI (or the failure is
  noted on the blackboard with a reason).
- The ticket's `assignee` is the human owner.
- The blackboard has a `## Dev` section with `branch:`, `worktree:`,
  and `pr:`.
- `coga bump` has advanced the workflow to `review`.

## What this skill does NOT do

- Decide whether to merge — that's the human's `review` step.
- Make breaking changes outside the ticket's scope.
- Resolve unrelated test failures it didn't cause.

## Gotchas

- If the work is too big for one PR, **stop and split the ticket** on
  the blackboard. Don't ship a half-PR.
- If git/`gh` auth isn't ready, you caught it in step 7: blackboard the
  failure and `coga block` rather than skipping the PR step or
  improvising around missing auth.
- If the test suite fails for reasons unrelated to your change, write
  it to the blackboard and `coga block` rather than masking it.
