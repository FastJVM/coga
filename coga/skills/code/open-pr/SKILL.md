---
name: code/open-pr
description: Agent step that runs `coga open-pr` to push the branch and open (or ready) the PR, then bumps. The deterministic push/open/record work lives in the command; the step gates on a recorded `pr:`, so it cannot complete without a real PR.
---

# Push and open the PR

This is an agent step, but the mechanical work — push, open (or ready) the PR,
record the URL — is done by a single deterministic command, `coga open-pr`. You
run it, confirm it recorded the PR, then bump. The *judgment* (what the PR says,
whether the branch is mergeable) belongs to the earlier implement / peer-review
steps; this step just turns the recorded branch into a PR.

(Mechanism note: `coga open-pr <slug>` is a default alias for `coga run
open-pr <slug>` — the registered `open-pr` recipe. It is an ordinary command,
not a nested launch, so it never touches your session's done sentinel.)

The step declares `requires: pr`, so `coga bump` refuses to advance until a
`pr:` line is recorded under `## Dev`. That is a **data check**: skipping
`coga open-pr` and bumping anyway fails loud — the recorded artifact is the
gate, not your say-so.

## Order of operations

1. **Confirm the handoff state.** Run the `dev/checkouts` start check: the
   launch checkout is on `main`, clean, and fast-forwarded to `origin/main`.
   If it is not, stop and ask the attending human, or `coga block` in a queue
   run; do not switch or stash your way past it. Then read the
   machine-readable `branch:` field (and `worktree:`, present only for a
   sandbox clone) under `## Dev` on the blackboard. A trailing annotation
   must follow a backtick-delimited value or live on a separate line; bare
   values consume the whole remainder of the line. The implement / review
   steps must have created the feature branch, recorded it, and left it
   committed and ahead of the base branch. If `branch:` is missing, that is
   an earlier-step gap — do not improvise a branch here; escalate per your
   launch mode by asking the attending human, or by using `coga block` with
   a one-line reason in a queue run. Those steps are also not finished while
   a review they ordered is still running — see *Refuse to publish ahead of a
   review in flight* below before you run anything.
2. **Run `coga open-pr <slug>` from `main`.** Never switch to the feature
   branch for this step: the command checks and pushes it by name, and
   refuses to run on any branch other than `main`. **Never hand-open the PR
   with `gh pr create` to route around a refusal** without explicit human
   approval: the recorded `pr:` line is what the `requires: pr` gate reads,
   and a hand-opened PR leaves the ticket ungated.

   It resolves the ticket first and:
   - reads `branch:` (and `worktree:`) from `## Dev`,
   - confirms the branch exists here as `refs/heads/<branch>` — or, for a
     recorded sandbox clone, that the clone is on that branch and clean —
     is ahead of the base (`[git].control_branch`, default `main`), and has
     no unsafe material drift from the latest `<remote>/<base>`
     (non-overlapping generated task/log drift is safe),
   - pushes the branch by name (using an explicit force-with-lease when a safe
     retry follows a rebase),
   - opens the PR with `gh pr create` — or `gh pr ready` if a draft already
     exists, or reuses an already-open PR (idempotent on re-run),
   - writes `pr: <url>` back under `## Dev` in this checkout's ticket, which
     the command's exit sweep publishes to control.

   It **fails loud** (non-zero, nothing pushed/opened) on: no usable
   `branch:`, a branch this checkout does not have, a missing, off-branch,
   or dirty sandbox clone, **no commits ahead of base** (the incident case —
   no empty PR), a stale branch, or a `git push` / `gh` auth failure *before*
   the PR exists.

   **PR title** = the ticket title. **PR body** comes, in order, from: a `## PR`
   section (blackboard first, then ticket body), else the ticket's
   `## Description`, else the title; a `Closes ticket: <slug>` line is always
   appended. So author a `## PR` section in the earlier steps if you want a
   curated summary + test plan; omitting it is fine.
3. **Bump.** Once `coga open-pr` reports the URL and `pr:` is recorded under
   `## Dev`, run `coga bump <slug>` from `main` to hand off to the next step.
   The bump's `requires: pr` gate will pass because the URL is now recorded.
   The checkout never left `main`, so there is nothing to return from.

## Refuse to publish ahead of a review in flight

Alongside the "never hand-open the PR" guard in step 2, this step carries a
second refusal: **a step must not be bumped, and `coga open-pr` must not run,
while the review that step ordered is still in flight.** Mergeability belongs to
the earlier implement / peer-review step, and that step is not complete when a
review has been *started* — it is complete when the review has returned and its
must-fix findings are addressed, or explicitly deferred by the owner. A green
`python -m pytest` is not a substitute — `code/self-qa` already records why.

**The wait itself belongs to the preceding step, not here.** By the time this
step's agent is composed, the `self-qa` / `peer-review` session that ordered the
review has already bumped and exited, so this step cannot hold a review open —
it can only refuse to publish. `code/self-qa` and the `with-review`
`peer-review` section therefore carry the wait-before-bump rule at the point it
can still be obeyed. What reaches this step is their durable evidence: a
`## Self-QA` or `## Peer review` blackboard note stating which review form ran,
that it **returned**, and what it found. Read that note before running
`coga open-pr`. If it is absent, or records a review as started without
recording that it returned, treat the review as still in flight and escalate per
your launch mode instead of publishing.

`reconcile-recurring-wrapper-tty-admission-guidance` is the worked case. PR #723
was opened, advanced through this mechanical step, and merged as `5243dfd5`
while a required independent `codex review --base origin/main` was still
running. The review then returned six actionable regressions in the merged code,
including two P1 stale-period races: a period start that was not an observable
compare-and-set, and completion/timeout that never re-leased the period
generation after the child exited. Repairing that cost a 19-commit follow-up
branch, a second PR (#725), and sixteen further review rounds — every one of
them against code already on `main`.

The recovery the owner chose is the precedent for a review that lands after the
merge: **hold the owner-controlled review gate and authorize a separate
follow-up fix PR from current `main`.** Do not rewind or replay the merged
ticket's implementation flow, and do not close the review gate while must-fix
findings are unresolved. Record the owner's authorization on the blackboard so
the corrective branch and PR are traceable to it; that authorization covers the
follow-up work, not a workflow bump or task closure.

**A blackboard note does not hold that gate — park the status.** The ticket is
on its final step and its `## Dev` `pr:` still names the merged PR, which is
exactly `autoclose`'s close predicate (`autoclose.py::_candidate`: final step
plus `status` in `active`/`in_progress`). The next `autoclose-merged` sweep
would therefore close the gate you meant to keep open, within 24h, and no
amount of recorded authorization changes that. `paused` and `blocked` are the
two statuses the sweep does not consider, so make the hold real:

- `coga block --task <slug> --reason "post-merge review findings unresolved:
  <specifics>"` when the gate is genuinely waiting on the owner. This is the
  better fit — the ask shows up in `coga status --blocked` and the
  `blocker-reminders` job keeps re-notifying until it is answered.
- `coga mark paused <slug>` when the repair is already authorized and tracked
  elsewhere, and the original only needs to stop being swept.

Do the repair itself on its own ticket against current `main`; the merged
ticket's `pr:` linkage stays pointed at the merged PR and is not rewritten.

## If `coga open-pr` fails

Fix the cause and re-run it — it is idempotent:

- Missing `branch:` → an earlier step didn't record it; escalate per your
  launch mode if you can't recover it here.
- Branch not in this checkout → the implement step pushed it; fetch it
  (`git fetch origin <branch>:<branch>`) and re-run.
- Nothing ahead of base → implement/review produced no change. Build the
  requested change rather than opening an empty PR, escalating per your
  launch mode if that needs human direction.
- Refused because the checkout is not on `main` → an earlier step did not
  return it. If it is this ticket's branch and clean apart from Coga state
  already on `origin/main`, run the `dev/checkouts` end-of-step return and
  re-run. Anything else — another ticket's branch, unpublished dirt — stop
  and escalate; do not commit, stash, or discard it.
- Stranded ticket write (the refusal names this ticket's own file and says
  not to rebase) → switch to the branch, inspect the diff it prints,
  preserve anything still needed in the `main` ticket (after returning),
  then restore the merge base's copy and commit exactly as the message
  spells out, push, and return to `main`. The branch then contributes no
  change to the ticket and the gate passes. If the message also names other
  overlapping paths, drop the ticket write first and bring control in with
  `git merge origin/main`, not a rebase.
- Stale branch → switch to the branch, rebase onto `origin/main`, re-run
  `python -m pytest`, commit, and push with `--force-with-lease`; then run
  the `dev/checkouts` end-of-step return and re-run `coga open-pr` from
  `main`.
- `git` / `gh` auth failure → follow the setup hint the command prints (fix the
  remote, load your SSH key / credential helper, `gh auth login`), then re-run.
- Dirty sandbox clone → inspect the diff. The refusal names this ticket's
  own file apart from any other dirt and tells you not to commit it. For an
  accidental edit to this task's `## Dev` or blackboard, preserve any
  missing text in the launch checkout's ticket, then discard only confirmed
  duplicate hunks in the clone (`git restore --staged --worktree -- <path>`).
  Do not commit or stash confirmed duplicates to satisfy the gate.
  Intentional ticket-body or `ticket.py`/attachment changes can belong to the
  implementation and stay in the feature diff. See the `dev/dev-record`
  context.

## Acceptance for this step

- Any review the preceding step ordered has returned, and its must-fix findings
  are addressed or explicitly deferred by the owner.
- `coga open-pr <slug>` has been run and `pr: <url>` is recorded under `## Dev`.
- `coga bump <slug>` has advanced the workflow (its `requires: pr` gate passed).

## What this skill does NOT do

- Decide whether to merge — that's the human's job in the next step.
- Make code changes or resolve CI failures. If CI fails for a real reason,
  escalate per your launch mode — ask the attending human, or `coga block`
  in a queue run — and let the human redirect or relaunch as appropriate.
- Resolve merge conflicts with the base — the peer-review / self-qa step handles
  mergeability before this step runs.
- Hand-edit routing metadata. There is none to edit: who holds a ticket is
  derived from the current workflow step's `assignee:` role every time it is
  read.
