---
name: coga-dev/internals/recurring-admission
description: The admission machinery that keeps a stale, replaced or concurrently edited recurring period from starting, completing or parking work — period generations and leases, per-child refresh, direct-launch catch-up, the serviced-period ledger read, inactivity gate ordering, ledger freshness at create publication, and strict delegated publication and why delegation exists.
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

## Reading the serviced-period ledger

The user contract is in
[coga/recurring/scheduling](../../../coga/recurring/scheduling/SKILL.md#periods-and-the-serviced-period-ledger).
The scan takes the last firing with `recurring._last_firing` and buckets it
with `_period_key`. One writer and one parser own the line
(`format_serviced_log`, `parse_serviced_period_entries`), pinned by a test.
Records are validated for exact shape and calendar values and compared by
calendar position. Event-aware cross-checkout publication
([spool-merge](../spool-merge/SKILL.md)) can put a newer record above an
older one: `read_serviced_ledger` reads the log **backwards** and stops once
every requested ref has a valid record at or after its target period, and an
older hit never stops the read. The first scan of a new period therefore walks
the whole log; later scans resolve from the tail. Malformed history older than
the stop point is allowed to heal.

## Inactivity gate ordering

The user contract is in
[coga/recurring/scheduling/inactivity](../../../coga/recurring/scheduling/inactivity/SKILL.md).
On an inactive, non-forced sweep each template's frontmatter is read leniently
for `run_when_inactive` and its schedule (`recurring._read_inactivity_fields`),
and a non-exempt template is skipped before strict `Template.load`, period or
ledger handling. The ledger pre-pass applies the same gate, excluding
non-exempt templates before strict loading or ledger reads. Subjects are
classified by `recurring_activity.is_machine_commit`.

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
serviced lines were added or changed externally refuse admission for
the rest of the sweep, even for a same-period change. Deletion alone is benign
only after full reads at both revisions prove unchanged greatest-period and
error state, with no malformed evidence. Other templates stay
serviceable, and audit-only changes invalidate nothing. Both create and
audit-only publishes re-run the check through `publish`'s `guard` at every base
([coga/sync](../../../coga/sync/SKILL.md)).

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

## Why delegation rather than a nested launch

The user rule is in
[coga/recurring/delegation](../../../coga/recurring/delegation/SKILL.md). The
recurring supervisor owns TTY admission only for sessions it spawns: it guards
the session `coga recurring` spawns, never a launch that session makes from its
own tool shell. Two tempting replacements for `delegate:` were rejected for
reasons that still hold:

- **A `ticket.py` that launches the agent.** Deterministic periods are the
  headless class, so a no-TTY sweep would create the period, run the script,
  and only then hit launch's agent TTY refusal — a mid-run failure in place of
  the clean pre-create skip. `recurring-scan` launching agents is no
  precedent: it runs from the operator's shell and re-checks
  `_interactive_stdio_has_tty()` itself.
- **Running the bootstrap runbook inside the period's own session.** Bootstrap
  targets are deliberately stateless (no task per run, no `coga bump` /
  `coga mark`), which fights the period lifecycle, and would fork the runbook
  away from the unchanged on-demand alias (for example `coga resolve-conflicts`).

Implementation: `recurring_runner._run_delegated_task`,
`recurring.delegated_workflow_violation`, `recurring.frozen_task_delegate`.
