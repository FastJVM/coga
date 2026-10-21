---
name: code/implement
description: Agent step for a code change. On the branch launch prepared (or one you set up per `dev/checkouts` when it did not), implement, test, commit, push, and hand off. Stops before the PR — that belongs to a later step.
---

# Implement the change

You are doing the actual code change, in the checkout this session was
launched from. The prompt's **Checkout (runtime)** notice says where you
are: under `coga launch` the feature branch is already created or reused,
its `branch:` linkage is on control, and launch returns the checkout after
you bump. If the notice says no branch was set up, or none was supplied,
follow `dev/checkouts` (its `manual` leaf) for the moves launch would have
made. **Do not open a PR yet** — the later `code/open-pr` step does that,
after review and fixes.

## Order of operations

1. **Read the ticket carefully.** Description, acceptance criteria,
   referenced files. If anything is ambiguous, don't guess: write the
   ambiguity to the blackboard and escalate per your launch mode — ask
   the attending human, or `coga block` in a queue run.

   When adding or revising code facts in the ticket's `## Context`,
   **Cite module plus symbol, never a bare line number.** For example,
   `src/coga/git.py` plus `git.sync_task_state`. If a line range helps
   navigation, name the symbol first and mark the range as an aid. Explain
   the relationship that makes the fact relevant, so the explanation survives
   a refactor. Apply this even to a raw `coga create` ticket that never passed
   through guided authoring or a design step.
2. **Close already-satisfied tickets directly.** If every requested
   checklist item has already landed in other work and there is genuinely
   no diff or PR to create, do not manufacture one and do not
   `coga block` — a blocker is for an unanswered human question, not for
   finished work. A branch launch prepared stays unused; leave it to the
   existing cleanup. Write per-item evidence under `## Already satisfied`
   on the blackboard. Before closing, file every open item the ticket or
   blackboard still records as its own draft (`coga create`) and link it,
   since a closed ticket owns nothing (`coga/workflows`, "Obligations the
   merge does not discharge"). Then run `coga mark done <slug>` and stop.
   Use this only when the evidence is concrete; if a human decision is
   genuinely needed, escalate that ask per your launch mode instead (ask the
   attending human; `coga block` in a queue run).
3. **Confirm the checkout.** Check HEAD against the notice. On a prepared
   branch the only entry dirt is this ticket, projected unstaged from
   control: write your notes and handoff there, and never stage, commit, or
   restore it. A notice that reports kept local commits (ahead or diverged)
   means reconcile them per `dev/checkouts/reconciliation` before pushing.
   Anything unexpected — another branch, other dirt — means stop and follow
   `dev/checkouts/launch-boundary`'s recovery: ask the attending human, or
   `coga block` in a queue run. Without a prepared branch, perform the
   `dev/checkouts` manual start check and branch setup, including publishing
   `branch:` before switching. Work parked for days drifts: start from
   current `main`, not from where the last session left off.

   **Read-only Git: the sandbox clone fallback.** A managed sandbox may
   allow source edits while mounting `.git` read-only, so your first commit
   on the prepared branch is refused. Stop implementation writes and follow
   `dev/checkouts/sandbox-clone` ("First refusal after launch switched"):
   preserve verified copies of all work, keep the prepared branch, and hand
   recovery to the host; do not continue in a new clone, allocate another
   branch, or bump. When the ticket already records a `worktree:` clone,
   the notice names it: change code only there and keep the ticket in this
   checkout. A manual session that cannot create its branch makes the clone
   that topic describes. In every clone, on creation and on each resumed
   session, seed its local config with the ordinary `seed_local_config.py`
   attachment beside this skill:

   ```bash
   python /resolved/code/implement/seed_local_config.py /primary/repo/coga /feature/repo
   ```

   The first argument is the primary directory containing `coga.toml`; the
   second is the clone's Git root. Resolve this skill local-first, falling
   back to the installed bundled skill (`dev/checkouts/sandbox-clone`, "What
   a fresh checkout lacks"). Stop on failure; never synthesize an actor.
4. **Implement on the feature branch.** Match existing code style. Keep changes scoped to the
   ticket — no opportunistic refactors. If you find a real adjacent bug,
   note its symptom, affected code, evidence or reproduction, and any
   existing follow-up ticket reference for the blackboard (write it with the
   handoff in step 11); don't fix it here.
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
8. **Freshen against `main`.** `git fetch origin main && git rebase
   FETCH_HEAD` on the feature branch, preserving the projected ticket as
   `dev/checkouts` describes; if commits came in, re-run the tests and fix
   what broke. Apply `dev/checkouts/reconciliation` when reconciling changes
   or deciding what needs human input. The later `coga open-pr` refuses a
   branch missing material commits from `origin/main`, and as a script it
   has no judgment to rebase with — freshness lands in the agent steps,
   while judgment is available.
9. **Push.** `git push -u origin <branch-name>` (add `--force-with-lease`
   when a rebase rewrote an already-pushed branch). Stay on the branch when
   launch returns the checkout; a manual session performs the
   `dev/checkouts` end-of-step return instead. In the sandbox clone layout,
   push from the clone.
10. **Prepare publication evidence.** Read [coga/internals/pr-publication/preparation](https://github.com/FastJVM/coga/blob/main/docs/contexts/coga/internals/pr-publication/preparation/SKILL.md),
    “Presentation and review-depth rubric” and “Preparation record”. Before the
    handoff, retain the actual implementing agent identity from this session
    (including overrides), exact check commands/results/counts and omission
    reasons, and the full tested head and merge-base OIDs. Do not substitute the
    ticket's configured agent or a planned test command for execution evidence.
    If tests ran on uncommitted changes, establish that the committed tree is
    identical before associating that receipt with the commit. A rebase or later
    fix needs fresh verification; never just change an old receipt's OID.

    Write the structured `## PR` preparation on the live blackboard with the
    handoff below: actual-change title, advisory depth and rationale,
    implementation/deviations/limitations, reasons for every actual diff path,
    and check/review receipts using that topic's schema. This is required even
    when the workflow has no later code review. If review has not run, say so
    and why; design approval does not count as code review. Later judgment
    steps update this record after their fixes and completed reviews. Test
    obligations remain those of this workflow (including step 5 above).
11. **Hand off and bump — this is what ends the step.** Write the handoff
   into the live ticket (the projected copy under launch, `main` in a manual
   session): what changed, decisions, and anything the next step needs.
   Confirm `## Dev` records this attempt's `branch:`. Then run
   `coga bump <slug>`. It publishes the ticket and advances the workflow;
   it is the *only* thing that does so — there is no autobump. Where the
   workflow declares `requires: branch`, `coga bump` refuses to advance
   unless this checkout's ticket copy has a usable `branch:` line under
   `## Dev`; if it refuses, record the line rather than working around it.
   If you stop without bumping, the workflow stalls on `implement`, the
   later steps never start, and your work is invisible even though the
   branch is pushed. If something keeps you from reaching it, escalate per
   your launch mode — ask the attending human, or `coga block` with a reason
   in a queue run.

## Acceptance for this step

- The feature branch is recorded as `branch:` under `## Dev` (plus
  `worktree:` for a sandbox clone), contains the latest `origin/main`, and
  is pushed.
- Tests pass locally.
- No PR yet. The blackboard reflects what changed and any decisions made.
- `coga bump <slug>` ran last — the step is not done until it has. A manual
  session left the checkout on a clean, fast-forwarded `main`.
- Or, for the already-satisfied path only: the blackboard records concrete
  evidence under `## Already satisfied`, and `coga mark done <slug>` has
  closed the ticket. An unused prepared branch needs no commit or PR.

## What this skill does NOT do

- Open a PR — that's `code/open-pr`.
- Self-QA the diff — that's `code/self-qa`.
- Resolve unrelated test failures it didn't cause.

## Gotchas

- If the test suite fails for reasons unrelated to your change, write
  it to the blackboard and escalate per your launch mode rather than
  masking it.
