---
name: coga-dev/internals/git-regressions
description: Why `git.publish` refuses to land a Coga state file — the provenance compare-and-swap, `expect` and `guard` hooks, prepared-ticket expectations and their remembered retries, symlink and missing-append-only refusals, pending and released launch-generation rules — the preparation refusal lifecycle commands raise before writing, and the procedure for shipping a stored-ticket schema conversion that the provenance check cannot protect.
---

# Publication refusals and state regressions

Part of `publish` step 3 (`src/coga/git.py` `_guard`); the surrounding flow is
[`coga-dev/internals/state-publication/publish`](../state-publication/publish/SKILL.md).

## The provenance check

For each non-union candidate, control's blob must be one the working copy
derives from (`_provenance`):

- HEAD's blob;
- the merge-base of HEAD and control;
- a blob this worktree itself published (`refs/worktree/coga/published`,
  per-worktree, which lets a feature or detached checkout keep publishing the
  same ticket although its HEAD never advances with control), or one launch's
  checkout preparation verified on control and projected onto the branch
  (`git.record_projected_baseline`, one ticket entry, written strictly and
  read back before spawn), so a resumed branch older than control's ticket
  can still publish its handoff from a later `coga bump` process;
- or the working bytes themselves (an idempotent retry).

`refs/worktree/coga/published` is written after a successful push *and* when
`_publish_locked` finds control already holding the built tree (its
equal-tree `False` return): bytes another process landed from this
checkout's sandboxed write are confirmed publication, so the next bump from
this feature checkout has them as provenance. A failed or unconfirmed
publication never records anything.

A stale checkout therefore cannot overlay a ticket another checkout advanced.
The refusal names the fix: "control copy changed since this checkout last saw
it (control: status=… step=…; here: …); take control's copy with
`git checkout <remote>/<control> -- <path>` and redo the edit".
Before applying that remedy, follow
[reconciliation](../../../../../src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/reconciliation/SKILL.md)
to preserve unique edits and reconcile them with control. A refusal is not
permission to discard the local version wholesale.

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
  pin on it would never be evaluated (`coga-dev/internals/spool-merge`).

- `remember=True` (only the prepared lifecycle path, through
  `sync_task_state(prepared=)` and `mark._publish`) persists each explicit
  expectation in `<coga root>/.coga/pending-publication.json` when the
  attempt fails retryably (`state: pending`) or is refused
  (`state: rejected`). `_pending_expectations` then applies a pending entry
  as that path's exact `expect` for every later publish, including the
  session-teardown retry (`git.retry_session_publication`) and the sweep, so
  a retry cannot fall back to the broader provenance set and land over a
  peer that restored an older published copy. A rejected entry refuses. An
  entry clears when its path lands, when the working copy already equals
  control, or when a new prepared transaction publishes it with its own
  expectation. The file is excluded from publication even where `.coga/`
  is not ignored. A ticket named in `expect` is also a candidate whenever it
  differs from control, even if it equals HEAD.

## Preparing a lifecycle transaction

`git.prepare_ticket` is the read side: under `state_lock` it captures the
local bytes, fetches through `fetch_control_state` (`fresh`, `local` for a
remote-less repo, `missing`, or `failed` — only the first two are read as
current), reads the control copy at the pinned commit, and reconciles
(`_shared_base`, `merge_ticket_bytes`, `lifecycle_winner`). The user contract
is [prepared ticket transactions](../../../coga/state-publication/SKILL.md#prepared-ticket-transactions).
An unreconcilable ticket raises `TicketConflictError` (a
`StateRegressionError`, `status_conflict=True` for an unrankable status pair)
before any write; commands exit 75 through
`commands/common.prepare_lifecycle_ticket`. `write_ticket(..., prepared=)`
raises `TicketChangedError` if the file moved since preparation. Commands
never prompt while holding the lock: `unblock`'s interactive answer
prepares again before writing.

The narrow exception to "refuse and stop" is the unrankable status pair.
Its `TicketConflictError.review` carries a `StatusConflict` (root, rel,
control revision, base/local/control bytes and blob ids, the formatted
`fields`, and `provenance`: the newest control commit that set the ticket
to the base blob, from `_introducing_commit`). `prepare_lifecycle_ticket`
delegates to the non-exiting `reconcile_lifecycle_ticket`, also used by
unblock's post-prompt/batch writes and autoclose. It hands the conflict to
`coga.review_conflict.escalate`, the only GitHub caller on this
path (every `gh` call goes through its `_gh`, which the real-Git tests in
`tests/test_review_conflict.py` stub). Escalation keys the conflict by
`sha256(rel, base, local, control)`, looks up `coga/human-review/<slug>-<key>`
with `gh pr list --state all`, and only when nothing exists builds the head
in a throwaway `GIT_INDEX_FILE` (provenance tree plus the local blob),
`commit-tree`s it onto the provenance commit, and pushes `<oid>:refs/heads/…`
when the remote branch is absent: no local ref, worktree, or index changes,
and never a force-push. It never raises; an `unavailable` outcome is
reported beside the ordinary refusal, which still exits 75. It deliberately
shares nothing with `open_pr` (no `Closes ticket:` footer, no `## Dev`
linkage). `_gh` explicitly selects the configured remote's repository with
`--repo`; its URL parser is shared with PR-assist verification. The remote
must fetch and push one matching repository. OS errors at the GitHub/process
and temporary-index boundaries retain the exit-75 refusal. User contract:
[human review of status conflicts](../../../coga/state-publication/SKILL.md#human-review-of-status-conflicts).

The return path is `prepare_ticket(..., review_base=, on_resolved=)`
(`_prepare_reviewed`): the merged PR's local blob replaces the shared base,
so an unchanged copy adopts control's resolution and later local edits
merge onto it. The merged state comes from the per-worktree
`.coga/human-review.json` record (`review_conflict.merged_record`), or, when
the human kept control's blob, from the unchanged conflict key. Provenance
is deliberately deferred: `PreparedTicket.finish_resolution` runs on the first
prepared write (or at once when the copies already match) and records
control's blob under `PUBLISHED_REF`. Recording it at preparation would let
a command that refuses for another reason leave the unresolved local copy
over a recorded base, which the next preparation would read as a one-sided
local edit and republish over the resolution. A successful ordinary
preparation that adopts or matches control drops the record.
Owner reassignment instead finalizes only after confirmed strict publication;
failed publication restores its original ticket and keeps the review record.
Its successful publication already recorded the new owner, so finalization
must not overwrite that provenance with the older resolution blob.
`_publish_locked` excludes `.coga/human-review.json` even without an ignore
rule, just as it excludes pending publication expectations.

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
  reconciles it (`coga-dev/internals/claim-recovery`).

Other deletions are ordinary candidates: a deleted task file passes the same
provenance check and is removed from the new tree.

Every refusal is collected, logged as `sync refused: …` (except as above),
and raised together as `StateRegressionError` before any push; the file stays
as written. Best-effort callers report and continue; strict callers restore
and retract (`coga-dev/internals/state-publication/publish`). A refused `bump` rewind
exits 75 so the sweep does not republish the retained local rewind.

## Shipping a stored-ticket schema conversion

The provenance check is **not** a schema barrier: an older supervisor still
running and level with control will restore a removed field and pass it. When
a change converts committed `coga/tasks/**` (as `simplify-ticket-format` did;
the no-compatibility-reader decision is recorded in `coga-dev/current-direction`):

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
