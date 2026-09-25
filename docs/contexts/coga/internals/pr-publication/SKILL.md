---
name: coga/internals/pr-publication
description: What `coga open-pr` (the `open-pr` recipe behind the `requires: pr` gate) must prove and in what order — the checkout gate, the by-name branch and sandbox-clone checks, the non-empty guard, freshness and stranded-ticket checks, the leased push, and where the `pr:` record is published.
---

# PR publication (`coga open-pr`)

The `requires: pr` gate itself is a data check run by `coga bump`
(`coga/lifecycle`): it passes once `## Dev` records `pr:`. This leaf is what
produces that record. `coga open-pr <slug>` is the default alias for the
registered recipe `coga run open-pr <slug>` (`src/coga/open_pr.py`). Stdout
carries only the bare PR URL, so `$(coga open-pr <slug>)` captures it; every
refusal goes to stderr and exits 2, so the gate stays unmet. Exactly one task
argument is accepted.

## Checkout gate (`_checkout_mode`)

open-pr runs from the launch checkout on the control branch, where the live
ticket is, and refuses any other branch. Every code step returns the checkout
to control before its handoff ([dev/checkouts](../../../dev/checkouts/SKILL.md)),
so there is no feature-branch mode, and a sandbox clone's stale ticket copy
can never be updated.

## Checks, in order

1. The ticket is not terminal; `## Dev` has a usable `branch:` (not
   `(`-prefixed). Without `worktree:` (or with one naming this checkout, left
   by the retired single-checkout layout) the branch is checked by name as
   `refs/heads/<branch>`, which must exist locally. With a recorded sandbox
   clone the checks run inside it: the directory must exist, be on that
   branch, and be clean; dirt on the live ticket's own file gets a
   restore-don't-commit remediation, since committing it strands a duplicate.
2. At least one commit ahead of the base (local ref, else `<remote>/<base>`).
3. Freshness: `github_preflight.check_branch_contains_control(head=...)`
   fetches control into its remote-tracking ref and reads that ref, not
   `FETCH_HEAD`. Only non-overlapping generated Coga state is accepted as
   drift, reported on stderr.
4. An unsafe overlap on the live ticket's own file is reported as a stranded
   ticket write, not ordinary staleness: `stranded_task_state_paths` (run
   against `FETCH_HEAD`) says whether control ever absorbed the branch's
   blob, and the remediation restores the merge base's copy on the branch and
   merges control, never a rebase.
5. `gh` auth for the remote host, before anything is pushed.
6. Push with `--force-with-lease` pinned to the remote OID observed just
   before, so a rebased retry publishes but a concurrent remote update is
   refused.
7. Reuse an open PR for the branch (running `gh pr ready` on a draft), or
   `gh pr create --base <control> --head <branch>`.
8. Write `pr:` under `## Dev` with `update_blackboard_under_barrier`, a
   byte splice under the state lock. A replaced stale link is noted on
   stderr.

## Where the record lands

The `pr:` write lands in the control checkout's live ticket, and the CLI exit
sweep publishes it. The successful `requires: pr` bump and the teardown usage
record also land on control only; nothing publishes to the feature branch.

## Bump's stranded-write advisory

Before a forward transition, `coga bump` runs the same stranded comparison
between `refs/heads/<control>` and `refs/heads/<branch>`, and prints a
`[bump]` note on stderr. It never blocks, writes, or changes the exit code,
and stays silent when this checkout is on the recorded branch, when
`worktree:` resolves to this checkout (both left by the retired
single-checkout layout), or when any probe fails.
