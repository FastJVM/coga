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
2. **Close already-satisfied tickets directly.** If every requested
   checklist item has already landed in other work and there is genuinely
   no branch, diff, or PR to create, do not manufacture one and do not
   `coga block` — a blocker is for an unanswered human question, not for
   finished work. Write per-item evidence under `## Already satisfied`
   on the blackboard, then run `coga mark done <slug>` and stop. Use this
   only when the evidence is concrete; if a human decision is genuinely
   needed, `coga block` with that ask instead.
3. **Create a feature worktree.** From the primary checkout on `main`,
   create a feature branch in a separate worktree outside the repo
   directory, for example:
   `git worktree add ../coga-<branch-name> -b <branch-name> main`.
   Pick a short descriptive branch name — it does
   *not* have to match the slug. Then return to the primary checkout and
   write the machine-readable fields `branch: <branch-name>` and
   `worktree: <path>` under a `## Dev` section on the blackboard. Keep trailing
   annotations on a separate line, or backtick-delimit the value first (for
   example, ``worktree: `/path with spaces` (other repo)``). See the `dev/code`
   context for the full convention.

   **Read-only Git fallback.** A managed agent sandbox may allow source edits
   while mounting the primary checkout's `.git` metadata read-only. If
   `git worktree add` fails for that reason, do not stop at a conversational
   request for the human to create it. Use ordinary Git to make an independent
   writable clone under `/tmp`, refresh it from the real remote, and create the
   feature branch there:

   ```bash
   feature_clone_dir=$(mktemp -d /tmp/coga-feature.XXXXXX)
   git clone --no-hardlinks "$(git rev-parse --show-toplevel)" "$feature_clone_dir/repo"
   git -C "$feature_clone_dir/repo" remote set-url origin "$(git remote get-url origin)"
   git -C "$feature_clone_dir/repo" fetch origin main
   git -C "$feature_clone_dir/repo" switch -C main FETCH_HEAD
   git -C "$feature_clone_dir/repo" switch -c <branch-name>
   ```

   Record that clone's repo path as `worktree:`; downstream `coga open-pr`
   accepts any clean recorded feature checkout. If the independent clone or
   its required fresh fetch also fails, run
   `coga block --task <slug> --reason "<specific capability or access needed>"`
   instead of merely saying "blocked" and leaving a supervised queue waiting.

   **On a resumed session** where `## Dev` already records a
   `branch:` and `worktree:`, reuse them — and refresh first: from the
   clean feature worktree, `git fetch origin main && git rebase
   FETCH_HEAD`, re-running the tests if new commits came in. Work parked
   for days drifts; start from current `main`, not from where the last
   session left off.
4. **Implement in the worktree.** Change into the feature worktree and
   match existing code style. Keep changes scoped to the
   ticket — no opportunistic refactors. If you find a real adjacent bug,
   write it on the blackboard for a follow-up ticket; don't fix it here.
5. **Test.** Add a regression test before the fix when the ticket is a
   bug. Run `python -m pytest`. If validation behavior changed, run
   `coga validate --json` against the example fixture. **Make new tests
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
6. **Update the example fixture** when behavior affects task layout,
   prompt composition, or workflow semantics (per CLAUDE.md).
7. **Commit.** Conventional, present-tense summary line. Reference the
   ticket slug in the body. One commit per logical change is fine.
8. **Freshen against `main` before handing off.** From the clean feature
   worktree, `git fetch origin main && git rebase FETCH_HEAD`; if commits
   came in, re-run the tests and fix what broke. The later `open-pr`
   `coga open-pr` refuses a branch missing material commits from
   `origin/main`, and as a script it has no judgment to rebase with —
   freshness lands in the agent steps, while judgment is available.
9. **Bump — this is what ends the step.** Return to the primary
   checkout and run `coga bump <slug>`. This advances the workflow to
   the next step and is the *only* thing that does so — there is no
   autobump. If you stop here without running it, the workflow stalls
   on `implement`, the later steps (open the PR, review) never start,
   and your work is invisible even though the code is committed on
   disk. Do not end the session until `coga bump` has run cleanly; if
   something blocks you from reaching it, `coga block` with a reason.

## Acceptance for this step

- Local branch and feature checkout (linked worktree or independent fallback
  clone) exist; both are recorded under `## Dev`
  on the blackboard.
- Tests pass locally.
- Changes committed (no working-tree modifications left).
- The branch contains the latest `origin/main`.
- No push, no PR yet.
- Blackboard reflects what changed and any decisions made.
- `coga bump <slug>` has been run — the step is not done until it has.
- Or, for the already-satisfied path only: no branch/worktree is required,
  the blackboard records concrete evidence under `## Already satisfied`,
  and `coga mark done <slug>` has closed the ticket.

## What this skill does NOT do

- Push the branch or open a PR — that's `code/open-pr`.
- Self-QA the diff — that's `code/self-qa`.
- Resolve unrelated test failures it didn't cause.

## Gotchas

- If the work is too big for one PR, **stop and split the ticket** on
  the blackboard. Don't ship a half-implementation.
- If the test suite fails for reasons unrelated to your change, write
  it to the blackboard and `coga block` rather than masking it.
