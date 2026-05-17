---
name: code/self-qa
description: Agent QA pass on the implement step's commits. Runs `/review` and `/simplify` against the branch diff and commits fixes in place before the PR is opened.
---

# Self-QA the diff

Independent quality pass over what `code/implement` committed. Runs the
checks **and** commits the fixes in the same step — no separate
findings-then-apply hop. The human reviewer on the PR is the real gate;
this step just makes sure the diff they see is already clean.

## Order of operations

1. **Confirm state.** Read `branch:` and `worktree:` under `## Dev` on
   the blackboard. Change into the feature worktree and confirm it is on
   the recorded branch with a clean working tree (the previous
   `code/implement` step committed). If not, `relay panic` — something
   is off.
2. **Run `/review`.** Invoke the `/review` slash command against the
   branch's diff vs `main`. Note the findings; you'll address them in
   step 4. If `/review` requires a PR, open a draft PR first
   (`gh pr create --draft`) and run `/review <PR#>` against it — keep
   the PR draft until the `code/open-pr` step marks it ready.
3. **Run `/simplify`.** Invoke the `/simplify` slash command against
   the branch. It reviews changed code for reuse, quality, and
   efficiency, then fixes issues it finds. Let it apply its edits.
4. **Apply remaining `/review` fixes.** Address `/review`'s findings
   that `/simplify` did not already cover. Skip optional/nit-level
   findings — leave those for the human reviewer to call out if they
   care. Must-fix and should-fix items are in scope.
5. **Re-run tests.** `python -m pytest` (and `relay validate --json`
   against the example fixture if validation behavior may have
   changed). If anything regressed, fix it before bumping.
6. **Commit.** One commit summarizing the QA pass — e.g. `self-qa:
   apply /review and /simplify findings`. If `/simplify` already
   committed on its own, leave its commits as-is and add one more for
   the residual `/review` fixes (if any).
7. **Bump from the primary checkout.** Return to the primary checkout
   and run `relay bump <slug>` to advance to `pr`.

## Acceptance for this step

- `/review` and `/simplify` have both run against the branch.
- Findings worth acting on are applied, committed, and tested.
- Working tree is clean; tests pass.
- A short `## Self-QA` section on the blackboard notes what was
  changed (or "no findings" if both passes came back clean).

## What this skill does NOT do

- Open or mark the PR ready — that's `code/open-pr`.
- Rework the original change beyond what `/review` + `/simplify`
  surface. If a finding implies a design rethink, write it to the
  blackboard and `relay panic`.
- Reformat unrelated code or sweep adjacent files.

## Gotchas

- Clean output from both passes is a valid outcome. Write "no
  findings" on the blackboard and bump.
- Don't suppress test failures. If a `/simplify` edit broke a test,
  the right move is to fix the edit, not silence the test.
- If `/review` and `/simplify` disagree on a specific edit, the human
  reviewer is one step away — leave the code in the safer state and
  note the disagreement on the blackboard.
