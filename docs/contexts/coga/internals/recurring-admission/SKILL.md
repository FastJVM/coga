---
name: coga/internals/recurring-admission
description: The admission machinery that keeps a stale, replaced or concurrently edited recurring period from starting, completing or parking work — period generations and leases, per-child refresh, direct-launch catch-up, ledger freshness at create publication, and strict delegated publication.
---

# Recurring admission and period generations

A period lives at a stable path, so "the same task" across time needs a
discriminator. The creator stamps each new materialization with a
`period_generation` token (a UUID; template or ordinary-task copies are
rejected). A **lease** (`recurring.PeriodLease`) is that token plus the exact
ticket bytes; `same_period_lease` requires both to match, ignoring CRLF versus
LF. The token stays stable across the child's own edits and audit appends but
changes on every rematerialization, so it never requires rereading the global
log.

## Sweeps and named launches

A sweep or `coga recurring launch <name>` performs full public admission once at
its outer boundary (branch, owner, `git.refresh` catch-up — a warning for bare
and named interactive single-repo scans), freezes each remote-backed period's
lease, then launches through an internal typed seam. Immediately before each
ordinary child, the seam refreshes again, resolves only the exact ref (a removed
ref cannot alias a prefix sibling), and rechecks branch, owner and the frozen
generation. A task removed, replaced, or moved to `done`, `canceled` or `paused`
while an earlier child ran is skipped. An unverifiable remote-backed refresh
fails closed. A checkout with no remote freezes that local-only class at
admission; a remote appearing to vanish later refuses rather than silently
switching class.

Every ordinary launch returns an exact lease: the admission lease for a
`ticket.py` child, or one recaptured immediately before each agent spawn only
if token, launchable status and full ticket still match the composed prompt —
a parked, closed, advanced or edited ticket cannot run a stale prompt. If a
child exits unfinished, only the same generation gets a fresh lease and the
pause is rendered from those bytes (preserving concurrent same-generation
edits); a replacement refuses teardown rather than parking the new task.

**Direct `coga launch recurring/<name>`** has no outer admission: with a remote
configured it requires a verified control catch-up *before* resolving the ref or
reading dispatch, and refuses if fetch or integration fails; without a remote,
local `HEAD` is control. It then reloads config and resolves the refreshed
period so remote materialization, completion or replacement wins.

## Create publication and ledger freshness

The create is one `publish` of the period task, the template's cursors and the
log, with `expect` pinned to control's exact ledger and template copies read at
the same fetch. A peer that serviced the period in between makes the publish
refuse; the create re-reads control and adopts the peer's period, publishing
only its own log line if the period is already handled.

The pre-create ledger read is bound to the caught-up revision and reused while
the fetched revision matches. A different revision before the first successful
create refreshes the snapshot for the complete target set (also on a
non-fast-forward retry). After a successful own publication — whose revision is
read from the remote-tracking ref that push advanced, including audit-only
pushes — a later control advance is diffed on `coga/log.md`: templates whose
serviced lines were added, removed or changed externally refuse admission for
the rest of the sweep, even for a same-period change; other templates stay
serviceable, and audit-only changes invalidate nothing. Both create and
audit-only publishes re-run the check through `publish`'s `guard` at every base
([coga/sync](../../sync/SKILL.md)).

Freshness refusals are admission errors, not best-effort sync failures. A
rejected local create is restored to control's task or its absence, never left
as a local-only orphan; peers and their generations are preserved; the audit
lines stay. Reused tasks validate the ledger too. `--force` and named launches
bypass period dedup but still validate the observed ledger and honor
task/generation guards; a forced reuse keeps operator edits.

This is an **observed-revision boundary, not exactly-once execution**: a rival
can still advance after a successful publication (per-child checks then guard),
and a byte-identical competing record or a net-zero change cannot be attributed.

## Delegated periods

For a frozen `delegate:` the runner preflights push access, then verifies the
exact ticket plus generation against freshly fetched control at start, final
spawn, completion and timeout (`_verify_period_on_control`). Start publishes
`in_progress` strictly (its provenance check is the compare-and-swap) before
announcing; launch then reloads config and redoes every preflight and
composition, because that publish may fast-forward control. Immediately before
spawn the runner requires the same lease, `in_progress` and the frozen
delegate, and freezes the exact parent template named by the period's state
snapshot; completion verifies it and publishes it with `done`, so a concurrent
cursor edit refuses and a child's cursor update cannot stay local. Every
lifecycle publication is strict: a refused or definitely failed one restores the
leased bytes and retracts its audit lines; a lost push reply with unreadable
control retains local state and refuses for reconciliation. The live completion
notification waits for durable publication; a sweep continues after a timeout
only once its guarded pause publishes.
