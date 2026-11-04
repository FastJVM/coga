---
name: coga-dev/internals/spool-merge
description: Event-aware audit publication, guarded log mutation and recovery, retained legacy bytes, retire-worklist union merging, and local writer locking.
---

# Retained state and concurrent writers

Coga lets several processes, worktrees, and clones write state at once. No
lock spans them: `git.state_lock` serializes one checkout only, and
cross-checkout coordination is the push compare-and-swap in
[`coga-dev/internals/state-publication/publish`](../state-publication/publish/SKILL.md). Files that
many writers touch must therefore be correct **by shape**.

**No spool exists.** Outcomes post live ([`coga/notifications`](../../../coga/notifications/SKILL.md)).
There is no hidden queue, drain step, or high-water watermark for
notifications. This page keeps the reusable merge rules that outlived it.

## `merge=union` files

The audit log is no longer a union path. Fresh templates use `/log.md -merge`:
native competing edits conflict with both sides recoverable in Git index
stages. Coga identifies `paths.log_path(cfg)` independently of attributes and
uses the event-aware publisher below. Adoption of that attribute and the
weekly schedule is explicitly staged with compatible writers; the
[operations guide](https://github.com/FastJVM/coga/blob/main/src/coga/resources/templates/coga/recurring/trim-log/operations.md)
owns the two-phase rollout.

`**/retires.md merge=union` remains unchanged. Its healing reader collapses
duplicate slugs and re-applies the discharge rule (`retire_worklist`). Other
union paths still come from `git check-attr merge`; they must tolerate
resurrection or must not carry that attribute.

## One event per log line

New `coga/log.md` events are exactly one
LF-terminated line: `YYYY-MM-DD HH:MM v1 [<ref>] [<actor>] <message>`.
`logfile.append_log` guarantees this centrally; callers pass raw text,
multiline Git stderr included, and never sanitize. It escapes `\` as `\\`
first, then writes LF and CR as the literal two-character text `\n` and
`\r` (CRLF becomes `\r\n`). A literal backslash can never be mistaken for
a line break, so `logfile.decode_log_message` recovers the exact message.
Other control characters, such as tabs and ANSI escapes, pass through
unchanged. Readers therefore split on LF only (`logfile.log_lines`), never on
the wider `str.splitlines` set, and decode only v1-marked messages before
parsing them. The marker precedes the ref tag so it cannot be confused with
legacy message text. The
returned line bytes are exactly what was appended, which is what an exact-byte
retraction removes.

**Legacy bytes stay unchanged while retained.** Events written before this
encoding are not re-encoded. A message that contained a line break left one or
more continuation lines with no leading timestamp, sometimes starting with a
`[<ref>]`-looking prefix. Readers skip such a line rather than misparse it,
and `coga show` (`logfile.task_log_lines`) prints it with the event it
follows. Unmarked legacy messages are read raw, preserving literal backslashes
without guessing the format from parse success. Retraction removes the tagged event and
any continuation lines that follow it, and matches the `[<ref>]` field rather
than a substring, so a peer event that mentions the tag stays. That
whole-event guarantee covers events written under this encoding; an
already-malformed historical event need not retract cleanly.

**Readers outside `logfile` parse the same grammar.** A change to the line
grammar or the escaping must update them in the same PR, and the list is not
obvious from `logfile` alone (the v1 change first missed the telemetry
reader): `usage._LOG_LINE_RE` in `usage.load_records`,
`recurring_runner._CONTROL_LOG_ENTRY_RE` in `_read_control_ledger` and its
incremental diff path, the anchored pattern in `recurring._pause_origins`,
and shared `movement_cursor._ENTRY` for phone-home movement counting. Grep for
`v1 )?` before trusting this list. Accepted limitation: a Coga older than
the v1 header does not parse v1 lines, so an older clone reading a newer log
silently skips the new events rather than failing.

## How `publish` lands the audit log

`logfile.parse_events` returns byte spans, separating malformed timestamp-like
headers, invalid UTF-8, unknown versions, v1 continuations and incomplete tails
conservatively. Legacy continuations belong to their event. Retention pins
opaque data and its attribution boundary so `task_log_lines` cannot attach it
to a different surviving ticket. It never sorts, re-encodes or deduplicates
retained history.

`log_publication.reconcile` preserves control's entire event sequence and
appends new source events in source order. A byte-identical event already on
control keeps control's occurrence count. Missing source events are not delete
instructions. Source HEAD/merge-base provenance is distinct from the landed
`PUBLISHED_REF` blob; the latter must never become a three-way source base.
Whole-file truncation against source HEAD requires a `LogMutation` receipt.

An expired incoming event absent from control can be suppressed only when the
shared selector permits it under pinned control/candidate task/config state
and reachable control history proves those exact canonical event bytes were
archived. Unread movement protection comes from the control snapshot, not
hash absence on incoming replays: a forgotten consumed fingerprint must not
resurrect itself. Genuinely new or unproven backdated input survives. One
transient history traversal includes merge-commit diffs, locates candidates
in patches, then verifies
positives against full blobs (legacy continuation boundaries matter). Failed
inspection never counts as proof. Checkout subsumption and exit diagnostics
use the same reconciliation rule.

Explicit mutation (`git.publish(log_mutation=...)`) requires exact control
preimage and local postimage and removes only named whole-event occurrences.
The trim job first archives pending events, pins decision inputs with `expect`
and `guard`, and publishes cursor migration plus log deletion together.
`log_transaction` pins the intent and attempted commits under the per-worktree
Git ref `refs/worktree/coga/log-mutation`, with a local receipt. It prevents
ordinary publication/checkout return after a crash or uncertain push. Recovery
fetches control, proves accepted commits by ancestry, and either catches up or
restores only unchanged outputs, preserving later appends. Log restoration
precedes cursor restoration. The receipt is transient transaction evidence,
not an archive or distributed tombstone; it is removed only on acknowledged
success or verified restoration. The runbook owns operator recovery.

Before a push, the receipt ref advances to a local merge commit retaining the
intent and every attempted commit; listing OIDs in JSON alone does not protect
them from Git garbage collection. Recovery distinguishes ancestry's negative
result from a failed inspection: an inspection error preserves both outputs
and the receipt, even if fetching control succeeded.

The trim script may have appended a per-run failure report while publication
was withheld. After resolving the receipt, its archive-before-planning phase
can publish that append with the exact control ticket as `expect`. It verifies
the report environment names the existing period and that control's complete
ticket remains a prefix through its blackboard fence. Other inventory edits,
changed lifecycle/body bytes and conflicting reports still refuse; recovery
does not sweep arbitrary task changes.

## How `publish` lands a union path

The retire-worklist contract is unchanged: `_merge_union_bytes` three-way
merges control, merge base and clean-filtered working bytes, then caps
byte-identical line occurrences at control's existing multiplicity. A missing
local union path refuses. It can land explicit line deletions present in the
base; its healing reader handles resurrected worklist rows. The published ref
is never the source base. This generic union contract does not apply to logs.

## Crash-safe replacement is not a lock

Atomic replacement prevents half-written files; it does not serialize writers.
`append_log` acquires the reentrant state lock before opening and holds it
through close. Local replacements, both rollback writers, publication and
landed-byte installation use the same lock and atomic replacement. A local
log whose clean-filtered bytes already equal the published blob is staged
without replacement, preserving the retained spans' original line endings.
Rollback holds the transaction from before-snapshot through refusal, or carries an exact
returned-append identity; a changed prefix refuses visibly. Peer events stay.
A publisher acquires another control checkout's lock non-blockingly before
fast-forwarding, or leaves it for its own locked catch-up. Two checkout locks
are never waited on in opposite order. Manual Git/file writers remain subject
to visible conflicts and exact local-byte comparison failures.
