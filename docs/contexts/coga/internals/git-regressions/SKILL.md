---
name: coga/internals/git-regressions
description: Why `git.publish` refuses to land a Coga state file — the provenance compare-and-swap, `expect` and `guard` hooks, symlink and missing-append-only refusals, pending and released launch-generation rules — and the procedure for shipping a stored-ticket schema conversion that the provenance check cannot protect.
---

# Publication refusals and state regressions

Part of `publish` step 3 (`src/coga/git.py` `_guard`); the surrounding flow is
[`coga/internals/state-publication`](../state-publication/SKILL.md).

## The provenance check

For each non-union candidate, control's blob must be one the working copy
derives from (`_provenance`):

- HEAD's blob;
- the merge-base of HEAD and control;
- a blob this worktree itself published (`refs/worktree/coga/published`,
  per-worktree, which lets a feature or detached checkout keep publishing the
  same ticket although its HEAD never advances with control);
- or the working bytes themselves (an idempotent retry).

A stale checkout therefore cannot overlay a ticket another checkout advanced.
The refusal names the fix: "control copy changed since this checkout last saw
it (control: status=… step=…; here: …); take control's copy with
`git checkout <remote>/<control> -- <path>` and redo the edit".

## Hooks

- `expect={path: bytes | None}` replaces the provenance set with the exact
  bytes the writer read (`None`: must not exist). Megalaunch's claim,
  admission, and released-witness reconciliation, and the recurring create's
  ledger read use it. On a `merge=union` path it adds a check that path
  otherwise lacks — but only while the path is a candidate.
- `guard=callable(base)` runs before each attempt with the commit that attempt
  builds on (refetched after a rejected push, so a retry never decides on a
  stale tip), whether or not there are candidates, and refuses by raising.
  It exists for decisions `expect` cannot express: the recurring create must
  not land once control's content records the period as serviced, and after
  the first publish on a control checkout `coga/log.md` is clean, so a blob
  pin on it would never be evaluated (`coga/internals/spool-merge`).

## Other refusals

- **Symlink** — refused outright; publishing would land the target's bytes,
  possibly from outside the repo, as a regular file.
- **Missing append-only file** — a `merge=union` path absent from the working
  tree while control has it is refused rather than published as a deletion,
  naming `git checkout <remote>/<control> -- <path>`. That refusal is not
  appended to a missing `coga/log.md`, which would recreate it truncated;
  stderr carries it.
- **Stale launch generation** (`ticket_regression_reason`) — a control ticket
  whose `launch_generation` is `pending:<uuid>` is sealed while megalaunch
  holds the child: the only accepted replacement is the identical ticket with
  the generation admitted. A working copy carrying a `released:` generation
  is a local recovery witness and is never published; `coga launch`
  reconciles it (`coga/internals/claim-recovery`).

Other deletions are ordinary candidates: a deleted task file passes the same
provenance check and is removed from the new tree.

Every refusal is collected, logged as `sync refused: …` (except as above),
and raised together as `StateRegressionError` before any push; the file stays
as written. Best-effort callers report and continue; strict callers restore
and retract (`coga/internals/state-publication`). A refused `bump` rewind
exits 75 so the sweep does not republish the retained local rewind.

## Shipping a stored-ticket schema conversion

The provenance check is **not** a schema barrier: an older supervisor still
running and level with control will restore a removed field and pass it. When
a change converts committed `coga/tasks/**` (as `simplify-ticket-format` did;
the no-compatibility-reader decision is recorded in `coga/current-direction`):

1. **One PR carries everything** — code, converted tickets, fixtures, and
   context edits. A split merge leaves CLI and stored tickets disagreeing with
   no reader to bridge them.
2. **Open a writer quiet window before merge.** Stop the recurring and
   megalaunch dispatchers, let old supervisors finish teardown and sync,
   suspend scheduled entry points and writers on other machines, and
   inventory running processes, clones, and installed or editable entry
   points — registered worktrees are not live processes.
3. **Rebuild the conversion on the exact control tip you merge**, and re-verify
   the allowed per-ticket diff; control moves under long-running PRs.
4. **Rebase a converted ticket control has since advanced** by taking
   control's copy wholesale, then re-applying only the mechanical conversion.
   Prove it with `git diff origin/main -- <path>` showing only the allowed
   field and token changes.
5. **Never run a mutating Coga command from the converting checkout**: its
   exit sweep would publish converted tickets before the code lands. Verify
   with a source-pinned `python -m coga.validate --json` and a direct
   `compose_prompt_report` call, comparing findings by task and kind.
6. **Keep dispatch stopped until merged writers are verified.** Update the
   control checkout and every installed or editable writer, confirm import
   paths, reconcile other checkouts before allowing writes, rerun read-only
   validation, then resume with fresh processes. Never replay an old
   supervisor's finalizer after merge.
