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
   referenced files. If anything is ambiguous, don't guess: write the
   ambiguity to the blackboard and escalate per your launch mode — ask
   the attending human, or `coga block` in a queue run.
2. **Close already-satisfied tickets directly.** If every requested
   checklist item has already landed in other work and there is genuinely
   no branch, diff, or PR to create, do not manufacture one and do not
   `coga block` — a blocker is for an unanswered human question, not for
   finished work. Write per-item evidence under `## Already satisfied`
   on the blackboard, then run `coga mark done <slug>` and stop. Use this
   only when the evidence is concrete; if a human decision is genuinely
   needed, escalate that ask per your launch mode instead (ask the
   attending human; `coga block` in a queue run).
3. **Set up the feature checkout.** Two layouts are first-class; pick one
   deliberately, because every later step reads `worktree:` to decide where it
   runs. Either way, pick a short descriptive branch name — it does *not* have
   to match the slug — and write the machine-readable fields
   `branch: <branch-name>` and `worktree: <path>` under a `## Dev` section on
   the blackboard. Keep trailing annotations on a separate line, or
   backtick-delimit the value first (for example,
   ``worktree: `/path with spaces` (other repo)``). See the `dev/code` context
   for the full convention.

   *Separate feature checkout.* From the primary checkout on `main`, create the
   feature branch in a worktree outside the repo directory, for example
   `git worktree add ../coga-<branch-name> -b <branch-name> main`. Then return
   to the primary checkout, on the control branch, to write `## Dev` and to run
   `coga bump` at the end of the step.

   *Single checkout.* When the ticket is run in one checkout — you are already
   in the primary checkout and no second copy will be created — create the
   branch in place (`git switch -c <branch-name>`) and record that checkout's
   own path as `worktree:`. Write `## Dev` there, on the feature branch: it is
   the live ticket copy, and `coga bump` and `coga open-pr` both run from that
   same checkout on that same branch. Do not add a linked worktree in this
   layout — `coga open-pr`'s `_checkout_mode` proves the layout from the
   recorded path plus `COGA_EXPECTED_TASK`, and a stray worktree makes the
   recorded path name a checkout this session cannot claim. Note also that
   generated task/log commits are not implementation work here: `coga open-pr`
   requires at least one committed non-generated path, so a branch carrying only
   task-state churn will not open a PR.

   **Write `## Dev` in the checkout you will bump from.** `coga bump` reads and
   syncs the ticket copy of the checkout it runs in, and nothing else. In the
   separate-checkout layout, writing these lines in the feature checkout and
   bumping from the primary checkout strands them on the feature branch, and
   `coga open-pr` then fails with "No usable `branch:` recorded" even though you
   did record it. Workflows whose implement step declares `requires: branch`
   refuse the bump instead of failing a step later — see step 9.

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
   its required fresh fetch also fails, escalate per your launch mode — ask
   the attending human, or in a queue run
   `coga block --task <slug> --reason "<specific capability or access needed>"`
   instead of merely saying "blocked" and leaving the supervised queue waiting.

   **On a resumed session** where `## Dev` already records a
   `branch:` and `worktree:`, reuse them — and refresh first: from the
   clean feature worktree, `git fetch origin main && git rebase
   FETCH_HEAD`, re-running the tests if new commits came in. Work parked
   for days drifts; start from current `main`, not from where the last
   session left off.
4. **Implement in the feature checkout.** Change into the feature worktree
   (in the single-checkout layout you are already there, on the feature branch)
   and match existing code style. Keep changes scoped to the
   ticket — no opportunistic refactors. If you find a real adjacent bug,
   record its symptom, affected code, evidence or reproduction, and any
   existing follow-up ticket reference on the blackboard; don't fix it here.
   State what remains unresolved. `retro/done-ticket` owns carrying that
   finding into a durable context before deleting this ticket, so the
   blackboard is a handoff, not the bug's final home.
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
   checkout and run `coga bump <slug>`; in the single-checkout layout there is
   nowhere to return to — stay put, on the feature branch, and run it there.
   This advances the workflow to the next step and is the *only* thing that
   does so — there is no
   autobump. Where the workflow declares `requires: branch` on this step,
   `coga bump` refuses to advance unless it reads usable `branch:` and
   `worktree:` lines under `## Dev` in *this* checkout's ticket copy — that
   is the enforcement for step 3. If it refuses, record the lines here (or
   re-run bump from the checkout that already has them) rather than working
   around it, and on a retried implement confirm they describe this attempt. If you stop here without running it, the workflow stalls
   on `implement`, the later steps (open the PR, review) never start,
   and your work is invisible even though the code is committed on
   disk. Do not end the session until `coga bump` has run cleanly; if
   something keeps you from reaching it, escalate per your launch mode —
   ask the attending human, or `coga block` with a reason in a queue run.

## Acceptance for this step

- Local branch and feature checkout (a linked worktree, an independent fallback
  clone, or the primary checkout itself in the single-checkout layout) exist;
  both are recorded under `## Dev`
  on the blackboard, in the ticket copy of the checkout `coga bump` runs from.
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
  it to the blackboard and escalate per your launch mode rather than
  masking it.
