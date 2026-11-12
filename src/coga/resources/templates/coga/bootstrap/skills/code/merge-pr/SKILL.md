---
name: code/merge-pr
description: Agent step that merges the reviewed PR with no owner gate. Re-checks that the PR is open, ready, conflict-free, unchanged since the recorded peer review, and passing the repo's required verification, merges it pinned to that head with the repo's merge method, then bumps to close the ticket. Any failed check is a refusal and an escalation, never a forced merge.
---

# Merge the reviewed PR

This step replaces the owner's PR gate: the configured peer agent's review is
the review, and you merge the PR yourself. The owner audits after the merge and
can revert. That trade only holds while the PR you merge is exactly the change
the peer reviewed and still passes what the repo requires. Every check below
re-establishes that; a check you cannot establish is a refusal, not a judgment
call.

Under `coga launch` this step starts on the recorded `branch:` (reused, never
reset), with this ticket projected unstaged from control as the only entry
dirt; the **Checkout (runtime)** notice says so. Otherwise perform the
`coga/checkouts` manual start and switch to the recorded branch yourself. You
make no commits here: never stage, commit, or restore the projected ticket,
and never rebase or push the branch.

## Refuse rather than force

Whenever a check below fails, do not merge. Write a `## Merge` note on the
blackboard naming the failed check and what you observed, then escalate per
your launch mode — ask the attending human, or
`coga block --task <slug> --reason "<the specific reason>"` in a queue run.
Do not bump. The owner decides what happens next: fix and re-run this step,
send the work back to an earlier step, or move the ticket to a workflow with
an owner gate. Never repair the PR here — no rebase, no fix commit, no
conflict resolution, no new review — because any of those produces a head
nobody reviewed.

Refuse for the same reason when the change needs a decision only the owner
can make: a must-fix finding the owner deferred, an open question on the
blackboard, an obligation the merge would leave without an owner, or anything
the ticket says the owner must approve.

## Order of operations

1. **Read the record.** From `## Dev`, read `branch:` and `pr:`. Missing
   `pr:` is an earlier-step gap (the `requires: pr` gate should have held
   it); refuse. Read the `## Peer review` note and the `## PR` preparation
   record the earlier steps left on the blackboard.
2. **Confirm the review finished and its findings are resolved.** The
   `## Peer review` note must record which review form ran, that it
   **completed** (direct) or **returned** (tool), what it found, and the
   head/base it covered. A review recorded as started but not completed or
   returned is still in flight (`code/open-pr`, "Refuse to publish ahead of a
   review in flight"). Every must-fix finding must be recorded as fixed on
   the branch; a finding deferred to the owner, or one whose resolution you
   cannot find, is an owner decision. Note what the record says about
   independence; peer selection alone does not prove independent authorship,
   and a self-review recorded as such is not the independent review this
   workflow relies on.
3. **Read the PR's live state and recover a completed merge first.** Run
   `gh pr view <pr-url> --json state,isDraft,baseRefName,headRefName,headRefOid,mergeable,mergeStateStatus,reviewDecision,mergedAt,mergeCommit`.
   In every state, require `baseRefName` to be the configured control branch
   and `headRefName` to be the recorded `branch:`.

   If `state` is `MERGED`, a previous session or a merge queue may have
   completed the merge before the ticket closed. Require a nonempty
   `mergedAt` and `mergeCommit.oid`, then perform the reviewed-head and
   verification checks in steps 4 and 5. Fetch the configured remote control
   branch and prove that `mergeCommit.oid` is an ancestor of that fetched
   control tip. Missing or mismatched evidence is a refusal. With that proof,
   go directly to step 10: record the existing merge and close the ticket
   once, without attempting another merge. The open-PR gates below and
   steps 6–9 apply only when a merge remains to be performed.

   Otherwise require all of:
   - `state` is `OPEN` and `isDraft` is false;
   - `baseRefName` is the configured control branch (`[git].control_branch`,
     default `main`) and `headRefName` is the recorded `branch:`;
   - `mergeable` is `MERGEABLE` and `mergeStateStatus` is `CLEAN` (or
     `HAS_HOOKS`). `DIRTY` is a conflict, `BEHIND` a branch the repo requires
     to be current, `BLOCKED` a required review or check that has not
     passed, `UNSTABLE` a failing non-required check, and `UNKNOWN` a state
     GitHub has not computed yet: re-read it once after a short wait, then
     refuse if it is still not clean;
   - `reviewDecision` is not `CHANGES_REQUESTED`.
4. **Confirm the head is the reviewed head.** Capture `headRefOid` as the
   verified head. It must equal the head the `## Peer review` note says the
   review covered, and `git rev-parse HEAD` in this checkout must equal it.
   A head that moved after the review — a fix commit, a rebase, a push by
   someone else — is unreviewed, even when the diff looks small. If the
   note records its receipt as covering an older revision, refuse.
5. **Run the repo's required verification at that head.** Run every check
   the repo's agent instructions (for example `AGENTS.md`, `CLAUDE.md`, the
   testing topic they link) and the ticket require before a merge, from this
   checkout at the verified head. Where the repo has hosted CI, also confirm
   with `gh pr checks <pr-url> --required` that every required check passed
   on that head. A step-3 state of `CLEAN` is not a substitute where the repo
   has no required checks. Record the exact commands and results under
   `## Merge`. A failure, a check you cannot run here, or a receipt that does
   not cover the verified head is a refusal.
6. **Re-check obligations.** `code/open-pr` already filed every obligation
   the merge will not discharge (`coga/workflows`, "Obligations the merge
   does not discharge"). Read the blackboard for anything that surfaced
   since; if a new open item has no draft of its own, file it with
   `coga create` and link it, or refuse if you cannot tell whether it is
   owed.
7. **Choose the repo's merge method.** Use the method the repo's
   instructions or contributing guide name (merge commit, squash, or rebase).
   If they name none, use GitHub's default for this repository:
   `gh repo view --json viewerDefaultMergeMethod`. Never pick a method the
   repository disallows, and never pass `--admin` to bypass protection or a
   merge queue.
8. **Merge, pinned to the verified head.** Run
   `gh pr merge <pr-url> --<merge|squash|rebase> --match-head-commit <verified-head>`.
   Do not pass `--auto` or `--delete-branch`: the ticket closes on a merged
   PR, not a scheduled one, and the feature branch is disposed of by the
   shared checkout proofs (`coga retire`, the `branch-sweep` and
   `autoclose-merged` sweeps), not by hand. If GitHub rejects the merge
   because the head moved, refuse; never drop the flag or retry with a newer
   head.
9. **Confirm the merge landed.** Re-read
   `gh pr view <pr-url> --json state,mergeCommit` and require `state` to be
   `MERGED`. A repository whose control branch uses a merge queue may
   enqueue the PR instead: then do not bump. Record that it is queued under
   `## Merge` and escalate per your launch mode; once the queue lands it,
   `autoclose-merged` (when scheduled) closes the ticket, or a relaunch of
   this step follows the already-merged recovery path in step 3.
10. **Record and bump.** Under `## Merge`, record the PR URL, the verified
    head, the merge method, the merge commit, and the verification
    receipts. For recovery, identify the existing merge and use its recorded
    method if known; do not invent one. Re-read the ticket's current control
    copy before bumping. If it is already `done`, report the verified outcome
    without another bump. If its current step is no longer this merge step,
    refuse and reconcile the lifecycle change. Otherwise run
    `coga bump <slug> --message "merged <pr-url> as <merge-commit>; owner audits post-merge"`.
    This is the final step, so the bump marks the ticket `done` and posts
    the message to the owner. Launch returns the checkout to a clean,
    current control branch afterwards; in a manual session, perform the
    `coga/checkouts` end-of-step return and reconcile per
    `coga/checkouts/reconciliation`.

## Acceptance for this step

- The peer review completed or returned, covered the merged head, and its
  must-fix findings were fixed on the branch.
- A new merge passed the open, ready, conflict-free and clean-control gates;
  recovery instead proved the existing merge on current control.
- The repo's required verification passed at the merged head.
- A new merge used `gh pr merge` with `--match-head-commit` set to the
  verified head and the repo's merge method. Recovery did not attempt another
  merge. In both cases the PR reads `MERGED`.
- `## Merge` records the evidence, and `coga bump <slug>` closed the ticket.

## What this skill does NOT do

- Fix, rebase, or re-review the branch. Those belong to the earlier steps; a
  PR that needs them goes back through them, not around them.
- Override GitHub. Branch protection, required reviews, required checks,
  and merge queues all stand; a merge they block is an owner decision.
- Clean up the branch. Retire and the sweeps run the shared checkout proofs
  (`coga/checkout-cleanup`).
- Hand-edit routing metadata. Who holds a ticket is derived from the current
  workflow step's `assignee:` role every time it is read.
