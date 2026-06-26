---
name: coga/patterns
description: Reusable Coga design patterns built from the core primitives. Currently the spool — a human-visible, git-backed producer/consumer queue. Attach when designing a feature that collects events as they happen and acts on them periodically.
---

# Coga patterns

Compositions of the core primitives (`coga/architecture`) that recur often
enough to be worth naming, so a new feature reaches for the established shape
instead of re-deriving it — or worse, inventing a hidden `.queue` dotfile that
breaks Coga's no-hidden-state rule.

## The spool — a human-visible producer/consumer queue

Reach for this when something needs to **collect events as they happen and act
on them periodically**: many writers record events the moment they fire, and
one scheduled reader consumes the accumulated records. The spool is an ordinary,
git-tracked markdown file, not a hidden service or dotfile.

```
producer  ──append(record)──▶  recurring/<job>/spool.md  ──drain()──▶  consumer
 (many, at event time)           ## Spool (pending)          (one, scheduled)
```

Why a spool rather than a bespoke queue:

- **No hidden state.** The queue is a real, git-tracked, human-readable file —
  openable mid-flight, never a dotfile or opaque store.
- **No reliance on git history.** Events are captured the moment they fire, so
  nothing depends on scanning `git log` to reconstruct what happened.
- **Survives task deletion.** Because the record lands at event time, work
  that's done-and-deleted before the consumer runs is already accounted for.
- **Reuses existing machinery.** The consumer is just a `recurring/` ticket;
  its cadence lives in `schedule:` frontmatter — reproducible from the repo,
  no external cron.

## The `## Spool (pending)` convention

Records are **JSONL** — one self-describing JSON object per line, under a
`## Spool (pending)` heading. JSONL (not a markdown table or delimited line)
because a free-text field can then hold arbitrary characters — pipes, arrows,
emoji — with no escaping, and each line stands alone. Every record carries
enough to be grouped and rendered without re-reading source state (e.g. the
Slack digest's records carry `id`, `ts`, `project`, `kind`, `detail`, and
optionally `ticket`, `owner`, `watchers`).

A spool file also carries a fixed `consumed_through: <id>` watermark line under
the heading. The watermark names the newest record the consumer has already
handled. Consumer-specific state that is not part of the producer queue (for
example the digest git high-water mark) belongs in the recurring ticket's
blackboard, not in the union-merged spool file.

## The primitive — `coga.spool`

Don't hand-roll the JSONL parsing. `src/coga/spool.py` is the shared,
notification-agnostic helper:

- `append_record(path, record)` — stamp a unique `id` when absent and append
  one record at the bottom of the section; creates the file section if absent.
- `read_records(path)` — return every JSONL record without modifying the file.
- `read_unconsumed(path)` — return records physically after the anchor named by
  `consumed_through`; with no matching anchor, every record is unconsumed.
- `drain(path)` — return newly consumed records, advance `consumed_through` to
  the newest record, trim the consumed prefix, and keep the newest record in
  place as an anchor. An absent file, empty spool, or already-consumed spool
  yields `[]` and touches nothing.

## The consumer is a recurring ticket

Wire the consumer as a `recurring/<job>/` ticket (see `coga/recurring`):

- The spool lives next to the recurring template as
  `coga/recurring/<job>/spool.md`, so it carries across runs — not in the
  fresh per-period task, which is gone next period.
- A script step runs a skill whose `script:` reads unconsumed records, acts on
  them, drains the spool, and exits. The daily Slack digest is the canonical
  instance: see `coga/sync` → "The daily digest — a blackboard
  producer/consumer", with `coga digest` as the consumer.

## Durability and concurrency

`append_record` and `drain` are whole-file read-modify-write through
`atomicio.atomic_write_text`. That rename-based write buys **crash-safety**: a
reader always sees the old or the new complete file, and a crash mid-write
can't truncate the spool. It is **not** a lock.

Coga allows multiple processes and multiple clones to race on state-plane
writes. The spool stays correct by shape, not by process serialization:

- Producers append only at the bottom, never touching the watermark or existing
  records.
- The consumer drains by deleting only a consumed top prefix, advancing the
  watermark, and keeping the newest record as an untouched anchor.
- `**/spool.md merge=union` handles the pure append-vs-append case by keeping
  both added record lines.

That gives git disjoint hunks for drain-vs-append (top delete vs bottom append,
separated by the anchor) and union-only semantics for append-vs-append, where
there is nothing to resurrect. If a future use needs stronger mutual exclusion,
add an explicit primitive; do not treat atomic file replacement as a lock.

## What this context does NOT cover

- The primitives this composes (recurring tasks, status, git sync) — see
  `coga/architecture` and `coga/recurring`.
- The Slack digest's specific records, grouping, posting, and git scan — see
  `coga/sync`.
- File locking — does not exist; this pattern is merge-by-construction.
