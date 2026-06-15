---
name: code/implement
description: Agent step for a code change. Branch, implement, test, commit. Stops before push and PR — those belong to later steps.
---

# Implement the change

You are doing the actual code change. Stop on a clean, committed branch
ready for self-review. **Do not push and do not open a PR yet** — the
later `code/open-pr` step does that, after self-review and fixes.

## Order of operations

1. **Read the ticket carefully.** Description, acceptance criteria,
   referenced files. If anything is ambiguous, write the ambiguity to
   the blackboard and stop — do not guess.
2. **Create a feature worktree.** From the primary checkout on `main`,
   create a feature branch in a separate worktree outside the repo
   directory, for example:
   `git worktree add ../relay-<branch-name> -b <branch-name> main`.
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
   `relay validate --json` against the example fixture. **Make new tests
   conform to the existing suite, not to your own taste** — agents
   reliably skip this because a clean-from-scratch test is easier to
   write than one that matches a quirky neighbor:
   - Read a sibling `tests/test_*.py` first and mirror its naming,
     structure, and fixture style. Match the suite; don't reinvent it.
   - Reuse the project's existing harness and helpers. Do not introduce
     a new test framework, assertion library, or mocking dependency the
     repo doesn't already use.
   - Keep coverage deterministic and low-creating: no real time,
     network, or filesystem nondeterminism; no sprawling mocks where a
     fixture or a plain call would do.
5. **Update the example fixture** when behavior affects task layout,
   prompt composition, or workflow semantics (per CLAUDE.md).
6. **Commit.** Conventional, present-tense summary line. Reference the
   ticket slug in the body. One commit per logical change is fine.
7. **Bump — this is what ends the step.** Return to the primary
   checkout and run `relay bump <slug>`. This advances the workflow to
   the next step and is the *only* thing that does so — there is no
   autobump. If you stop here without running it, the workflow stalls
   on `implement`, the later steps (open the PR, review) never start,
   and your work is invisible even though the code is committed on
   disk. Do not end the session until `relay bump` has run cleanly; if
   something blocks you from reaching it, `relay panic` with a reason.

## Acceptance for this step

- Local branch and feature worktree exist; both are recorded under `## Dev`
  on the blackboard.
- Tests pass locally.
- Changes committed (no working-tree modifications left).
- No push, no PR yet.
- Blackboard reflects what changed and any decisions made.
- `relay bump <slug>` has been run — the step is not done until it has.

## What this skill does NOT do

- Push the branch or open a PR — that's `code/open-pr`.
- Self-QA the diff — that's `code/self-qa`.
- Resolve unrelated test failures it didn't cause.

## Gotchas

- If the work is too big for one PR, **stop and split the ticket** on
  the blackboard. Don't ship a half-implementation.
- If the test suite fails for reasons unrelated to your change, write
  it to the blackboard and `relay panic` rather than masking it.
