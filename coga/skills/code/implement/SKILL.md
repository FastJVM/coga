---
name: code/implement
description: Agent step for a code change. From a clean `main`, branch, implement, test, commit, push the branch, and return the checkout to `main`. Stops before the PR — that belongs to a later step.
---

# Implement the change

You are doing the actual code change, in the checkout this session was
launched from. Start on a clean `main`, do the work on a feature branch,
push it, and end back on a clean `main` (`dev/checkouts`). **Do not open a
PR yet** — the later `code/open-pr` step does that, after review and fixes.

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
   no branch, diff, or PR to create, do not manufacture one and do not
   `coga block` — a blocker is for an unanswered human question, not for
   finished work. Write per-item evidence under `## Already satisfied`
   on the blackboard, then run `coga mark done <slug>` and stop. Use this
   only when the evidence is concrete; if a human decision is genuinely
   needed, escalate that ask per your launch mode instead (ask the
   attending human; `coga block` in a queue run).
3. **Start check, then branch.** Follow `dev/checkouts` ("Start, work,
   end"). From the launch checkout, `git fetch origin main`, then require
   HEAD on `main`, `git status --porcelain --untracked-files=all` empty (Coga
   state included), and `git merge --ff-only origin/main` to succeed. If any
   of that fails — dirty files, another ticket's branch, a diverged `main` —
   stop: ask the attending human, or `coga block` in a queue run. Do not work
   around it with a linked worktree, a control checkout, a stash, or a
   switch. (`origin`/`main` stand for the configured `[git].remote` and
   `[git].control_branch`.)

   Pick a short descriptive branch name — it does *not* have to match the
   slug — and create it without leaving `main`: `git branch <branch-name>`.
   Still on `main`, write `branch: <branch-name>` under a `## Dev` section on
   the blackboard (keep trailing annotations on a separate line, or
   backtick-delimit the value first; see the `dev/dev-record` context), plus
   any plan notes worth keeping. Publish these edits using `dev/checkouts`
   ("Publish pre-branch ticket edits") and require a clean tree; writing on
   `main` alone does not publish them. Then `git switch <branch-name>`. From here
   until you return to `main`, edit code only: ticket and blackboard edits
   made on the branch are not published, and the end-of-step return refuses
   to discard them.

   **Read-only Git: the sandbox clone fallback.** A managed agent sandbox may allow source edits
   while mounting the checkout's `.git` metadata read-only. If creating the
   branch fails for that reason, do not stop at a conversational request for
   the human to create it. Use ordinary Git to make an independent writable
   clone under `/tmp`, refresh it from the real remote, and create the
   feature branch there:

   ```bash
   feature_clone_dir=$(mktemp -d /tmp/coga-feature.XXXXXX)
   git clone --no-hardlinks "$(git rev-parse --show-toplevel)" "$feature_clone_dir/repo"
   git -C "$feature_clone_dir/repo" remote set-url origin "$(git remote get-url origin)"
   git -C "$feature_clone_dir/repo" fetch origin main
   git -C "$feature_clone_dir/repo" switch -C main FETCH_HEAD
   git -C "$feature_clone_dir/repo" switch -c <branch-name>
   ```

   Record that clone's repo path as `worktree:` next to `branch:` in the
   launch checkout's ticket, publish that record using the same pre-branch
   procedure, and require a clean primary tree before working in the clone;
   the launch checkout stays on `main` and keeps
   the ticket, `coga bump`, and `coga open-pr`. If the independent clone or
   its required fresh fetch also fails, escalate per your launch mode — ask
   the attending human, or in a queue run
   `coga block --task <slug> --reason "<specific capability or access needed>"`
   instead of merely saying "blocked" and leaving the supervised queue waiting.

   **Seed local config in the clone** before the first Coga command there,
   with the ordinary `seed_local_config.py` attachment beside this skill:

   ```bash
   python /resolved/code/implement/seed_local_config.py /primary/repo/coga /feature/repo
   ```

   The first argument is the primary directory containing `coga.toml`; the
   second is the clone's Git root. Any `python` works: when it cannot import
   `coga` (a `uv tool install` or pipx install keeps the package in its own
   environment) the helper re-runs itself under the interpreter named by the
   `coga` console script's shebang, and fails loud if no `coga` is on PATH.
   Resolve this skill local-first, falling back to the installed bundled
   skill (see `dev/checkouts`, "What a fresh checkout lacks"). Stop on failure;
   never synthesize an actor.

   **On a resumed session** where `## Dev` already records a `branch:`, reuse
   it: after the start check, `git switch <branch-name>`, then
   `git fetch origin main && git rebase FETCH_HEAD`, re-running the tests if
   new commits came in. Work parked for days drifts; start from current
   `main`, not from where the last session left off.
4. **Implement on the feature branch.** Match existing code style. Keep changes scoped to the
   ticket — no opportunistic refactors. If you find a real adjacent bug,
   note its symptom, affected code, evidence or reproduction, and any
   existing follow-up ticket reference for the blackboard (write it after
   returning to `main`); don't fix it here.
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
8. **Freshen against `main`.** On the clean feature branch,
   `git fetch origin main && git rebase FETCH_HEAD`; if commits came in,
   re-run the tests and fix what broke. The later `coga open-pr` refuses a
   branch missing material commits from `origin/main`, and as a script it
   has no judgment to rebase with — freshness lands in the agent steps,
   while judgment is available.
9. **Push and return to `main`.** `git push -u origin <branch-name>` (add
   `--force-with-lease` when a rebase rewrote an already-pushed branch).
   Then run the `dev/checkouts` end-of-step return: discard dirty Coga
   state only after proving it already matches `origin/main`, `git switch
   main`, and `git merge --ff-only origin/main`. If a dirty Coga-state path
   is not already on `origin/main`, or any other path is dirty, stop and
   escalate — never discard unpublished state. In the
   sandbox clone layout, push from the clone; the launch checkout never left
   `main`.
10. **Hand off and bump — this is what ends the step.** On `main`, write
   the blackboard handoff: what changed, decisions, and anything the next
   step needs. Confirm `## Dev` records this attempt's `branch:`. Then run
   `coga bump <slug>`. It publishes the ticket and advances the workflow to
   the next step; it is the *only* thing that does so — there is no
   autobump. Where the workflow declares `requires: branch` on this step,
   `coga bump` refuses to advance unless it reads a usable `branch:` line
   under `## Dev` in this checkout's ticket copy. If it refuses, record the
   line rather than working around it. If you stop here without running it,
   the workflow stalls on `implement`, the later steps (review, open the PR)
   never start, and your work is invisible even though the branch is
   pushed. Do not end the session until `coga bump` has run cleanly; if
   something keeps you from reaching it, escalate per your launch mode —
   ask the attending human, or `coga block` with a reason in a queue run.

## Acceptance for this step

- The feature branch exists, is recorded as `branch:` under `## Dev` (plus
  `worktree:` for a sandbox clone), contains the latest `origin/main`, and
  is pushed.
- Tests pass locally.
- The launch checkout is back on `main`, fast-forwarded and clean.
- No PR yet.
- Blackboard reflects what changed and any decisions made.
- `coga bump <slug>` has been run — the step is not done until it has.
- Or, for the already-satisfied path only: no branch is required,
  the blackboard records concrete evidence under `## Already satisfied`,
  and `coga mark done <slug>` has closed the ticket.

## What this skill does NOT do

- Open a PR — that's `code/open-pr`.
- Self-QA the diff — that's `code/self-qa`.
- Resolve unrelated test failures it didn't cause.

## Gotchas

- If the work is too big for one PR, **stop and escalate** per your
  launch mode, naming the separable pieces on the blackboard. The owner
  decides the scope; don't create tickets yourself or ship a
  half-implementation.
- If the test suite fails for reasons unrelated to your change, write
  it to the blackboard and escalate per your launch mode rather than
  masking it.
