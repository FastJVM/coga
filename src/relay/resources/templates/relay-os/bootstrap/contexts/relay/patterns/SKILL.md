---
name: relay/patterns
description: Reusable Relay design patterns built from the core primitives. Currently the spool — a blackboard used as a durable producer/consumer queue. Attach when designing a feature that collects events as they happen and acts on them periodically.
---

# Relay patterns

Compositions of the core primitives (`relay/architecture`) that recur often
enough to be worth naming, so a new feature reaches for the established shape
instead of re-deriving it — or worse, inventing a hidden `.queue` dotfile that
breaks Relay's no-hidden-state rule.

## The spool — a blackboard as a producer/consumer queue

Reach for this when something needs to **collect events as they happen and act
on them periodically**: many writers record events the moment they fire, and
one scheduled reader drains the accumulated records, acts, and empties them.
The blackboard *is* the queue.

```
producer  ──append(record)──▶  recurring/<job>/blackboard.md  ──drain()──▶  consumer
 (many, at event time)           ## Spool (pending)              (one, scheduled)
```

Why a spool rather than a bespoke queue:

- **No hidden state.** The queue is an ordinary, git-tracked, human-readable
  `blackboard.md` — openable mid-flight, never a dotfile or opaque store.
- **No reliance on git history.** Events are captured the moment they fire, so
  nothing depends on scanning `git log` (too slow on a busy task repo) to
  reconstruct what happened.
- **Survives task deletion.** Because the record lands at event time, work
  that's done-and-deleted before the consumer runs is already accounted for.
- **Reuses existing machinery.** The consumer is just a `recurring/` ticket;
  its cadence lives in `schedule:` frontmatter — reproducible from the repo,
  no external cron.

## The `## Spool (pending)` convention

Records are **JSONL** — one self-describing JSON object per line, under a
`## Spool (pending)` heading in the blackboard. JSONL (not a markdown table or
delimited line) because a free-text field can then hold arbitrary characters —
pipes, arrows, emoji — with no escaping, and each line stands alone. Every
record carries enough to be grouped and rendered without re-reading source
state (e.g. the Slack digest's records carry `ts`, `project`, `kind`, `detail`,
and optionally `ticket`, `owner`, `watchers`).

The section lives in a real blackboard, so it can share the file with other
content. The drain rewrites **only** the spool section and ignores any
non-JSON line it finds there — that line is preserved, not drained. The
recurring scaffolder also owns a single `last_serviced_period` high-water line
in the template blackboard; spool drains must preserve it. The JSON-only drain
is still defensive against any stray non-record line.

## The primitive — `relay.spool`

Don't hand-roll the JSONL parsing. `src/relay/spool.py` is the shared,
Slack-agnostic helper:

- `append_record(path, record)` — append one record; creates the file and the
  `## Spool (pending)` section if absent.
- `read_records(path)` — return pending records without modifying the file.
- `drain(path)` — return every pending record in append order, then clear them
  from the section. An absent file or empty spool yields `[]` and touches
  nothing — so the consumer is **idempotent**: a quiet period, or a second run
  the same period, is a silent no-op.

## The consumer is a recurring ticket

Wire the consumer as a `recurring/<job>/` ticket (see `relay/recurring`):

- The spool lives on the **recurring template's persistent blackboard**
  (`relay-os/recurring/<job>/blackboard.md`), which carries across runs — not
  the fresh per-period task blackboard, which is gone next period.
- A `mode: script` step runs a skill whose `script:` drains the spool, acts on
  the records, and exits. The daily Slack digest is the canonical instance:
  see `relay/sync` → "The daily digest — a blackboard producer/consumer", with
  `relay digest` as the consumer.

## Durability and concurrency

`append_record` and `drain` are whole-file read-modify-write through
`atomicio.atomic_write_text`. That rename-based write buys **crash-safety**: a
reader always sees the old or the new complete file, and a crash mid-write
can't truncate the blackboard. It is **not** a lock — two processes appending
at once would both read the same original and the later rename would clobber
the earlier append (a lost record).

What keeps the spool correct today is Relay's single-process model: **one
`relay` CLI process runs at a time**, so appends and drains are already
serialized and never overlap (consistent with `relay/architecture`'s
no-mutex / "status is the signal" design — same reasoning as the git-sync
compare-and-swap being the serialization point). Atomic write covers the only
remaining risk, a crash.

If a future use needs genuinely concurrent producers, or a consumer that must
hold off appends across its read-and-empty, that requires the mutual-exclusion
primitive tracked in the `file-locking-for-concurrent-task-mutation` ticket,
which does not exist yet. Until then, the spool relies on serialization, not a
lock — do not document or design it as lock-guarded.

## What this context does NOT cover

- The primitives this composes (blackboard, recurring tasks, single-process
  model) — see `relay/architecture` and `relay/recurring`.
- The Slack digest's specific records, grouping, and posting — see `relay/sync`.
- File locking — does not exist; see the draft ticket named above.
