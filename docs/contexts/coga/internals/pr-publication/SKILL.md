---
name: coga/internals/pr-publication
description: What `coga open-pr` (the `open-pr` recipe behind the `requires: pr` gate) must prove and in what order — the session ownership witness, checkout gate, cleanliness and non-empty guards, freshness and stranded-ticket checks, the leased push, and where the `pr:` record is published.
---

# PR publication (`coga open-pr`)

The `requires: pr` gate itself is a data check run by `coga bump`
(`coga/lifecycle`): it passes once `## Dev` records `pr:`. This leaf is what
produces that record. `coga open-pr <slug>` is the default alias for the
registered recipe `coga run open-pr <slug>` (`src/coga/open_pr.py`). Stdout
carries only the bare PR URL, so `$(coga open-pr <slug>)` captures it; every
refusal goes to stderr and exits 2, so the gate stays unmet. Exactly one task
argument is accepted.

## Session witness

The launch supervisor pins `COGA_EXPECTED_TASK` and `COGA_EXPECTED_STEP` to
the exact task path and frozen step used to compose the session
([agent spawn](../agent-spawn/SKILL.md)). Nested task re-derivation rewrites
`COGA_TASK_*` but never that pair, so it keeps naming the outer session.
`coga bump` uses both to refuse a stale supervised session after another
worker advanced the ticket; open-pr uses the task half as its ownership
proof.

## Checkout gate (`_checkout_mode`)

- **Single checkout**: `worktree:` is this same checkout, it is not a linked
  worktree, and `COGA_EXPECTED_TASK` names this task. The feature branch's
  ticket is then the live copy.
- **Separate checkout**: otherwise open-pr must run from a checkout on the
  control branch and pushes the recorded branch by name from `worktree:`.
- A same checkout without the witness refuses, so an independent fallback
  clone cannot update its stale ticket copy.

## Checks, in order

1. The ticket is not terminal; `## Dev` has a usable `branch:` (not
   `(`-prefixed) and an existing `worktree:` directory on that branch.
2. Single checkout: publish the pending launch-log append (`sync_log`), then
   leave Coga's task, log, and recurring paths out of the cleanliness check.
   Any other dirt refuses. In a separate checkout, dirt on the live ticket's
   own file gets a restore-don't-commit remediation, since committing it
   strands a duplicate.
3. At least one commit ahead of the base (local ref, else `<remote>/<base>`).
   Single checkout also needs a committed change beyond generated state:
   `merge=union` files and tickets whose authored half (frontmatter minus
   `status`, `step`, `assignee`, `launch_generation`, plus the body above the
   blackboard) is unchanged do not count. Lifecycle-only commits never
   qualify; changed ticket prose does.
4. Freshness: `github_preflight.check_branch_contains_control` fetches
   control into its remote-tracking ref and reads that ref, not `FETCH_HEAD`.
   Only non-overlapping generated Coga state is accepted as drift (single
   checkout also accepts identical Coga-state overlaps), reported on stderr.
5. In a separate checkout, an unsafe overlap on the live ticket's own file is
   reported as a stranded ticket write, not ordinary staleness:
   `stranded_task_state_paths` (run against `FETCH_HEAD` in the recorded
   checkout) says whether control ever absorbed the branch's blob, and the
   remediation restores the merge base's copy on the
   branch and merges control, never a rebase.
6. `gh` auth for the remote host, before anything is pushed.
7. Push with `--force-with-lease` pinned to the remote OID observed just
   before, so a rebased retry publishes but a concurrent remote update is
   refused.
8. Reuse an open PR for the branch (running `gh pr ready` on a draft), or
   `gh pr create --base <control> --head <branch>`.
9. Write `pr:` under `## Dev` with `update_blackboard_under_barrier`, a
   byte splice under the state lock. A replaced stale link is noted on
   stderr.

## Where the record lands

Single checkout: the `pr:` write publishes to control only through
`sync_task_state`. It is reported, never fatal, because the PR is already
open and the live ticket already carries the URL. Coga never commits it on
the feature branch. Separate checkout: the write lands in the control
checkout's live ticket. The successful `requires: pr` bump and the teardown
usage record also land on control only; no gate publishes elsewhere.

## Bump's stranded-write advisory

Before a forward transition, `coga bump` runs the same stranded comparison
between `refs/heads/<control>` and `refs/heads/<branch>`, and prints a
`[bump]` note on stderr. It never blocks, writes, or changes the exit code,
and stays silent when this checkout is on the recorded branch, when
`worktree:` resolves to this checkout, or when any probe fails.
