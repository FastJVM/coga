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
2. **Branch.** `git checkout -b <task-slug>` from `main`. The branch
   name should match the task directory name.
3. **Implement.** Match existing code style. Keep changes scoped to the
   ticket — no opportunistic refactors. If you find a real adjacent bug,
   write it on the blackboard for a follow-up ticket; don't fix it here.
4. **Test.** Add a regression test before the fix when the ticket is a
   bug. Run `python -m pytest`. If validation behavior changed, run
   `python -m relay.validate --json` against the example fixture.
5. **Update the example fixture** when behavior affects task layout,
   prompt composition, or workflow semantics (per CLAUDE.md).
6. **Commit.** Conventional, present-tense summary line. Reference the
   ticket slug in the body. One commit per logical change is fine; rebase
   to clean up before pushing.
7. **Push** the branch.
8. **Open the PR** with `gh pr create`. Title = ticket title. Body =
   short summary + "Closes ticket: `<slug>`" + a one-line test plan.
9. **Hand off.** Edit the ticket's `assignee:` frontmatter to the
   ticket's `owner:` (the human who created it). Add the PR URL to the
   blackboard with a one-line note.
10. **Advance.** Run `relay bump` to move the workflow to `review`. This
    posts to Slack and logs the handoff.

## Acceptance for this step

You are done when:

- A PR exists, links the ticket, and is green on CI (or the failure is
  noted on the blackboard with a reason).
- The ticket's `assignee` is the human owner.
- The blackboard has the PR URL.
- `relay bump` has advanced the workflow to `review`.

## What this skill does NOT do

- Decide whether to merge — that's the human's `review` step.
- Make breaking changes outside the ticket's scope.
- Resolve unrelated test failures it didn't cause.

## Gotchas

- If the work is too big for one PR, **stop and split the ticket** on
  the blackboard. Don't ship a half-PR.
- If `gh` isn't authed, surface the error to the human on the
  blackboard — don't skip the PR step.
- If the test suite fails for reasons unrelated to your change, write
  it to the blackboard and `relay panic` rather than masking it.
