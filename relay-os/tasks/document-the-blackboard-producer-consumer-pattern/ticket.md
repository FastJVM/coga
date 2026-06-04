---
title: Document the blackboard producer/consumer pattern
status: done
mode: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts: []
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
---

## Description

Relay keeps reinventing the same shape: something needs to **collect events
as they happen and act on them periodically**, without hiding state or
relying on slow git scans. The Slack digest (`stop-overloading-relay-slack`)
is the first concrete instance, but the shape is general and deserves to be
named as a first-class Relay pattern so future work reaches for it instead
of re-deriving it (or worse, inventing a hidden `.queue` file).

**This ticket documents the pattern.** Code is out of scope except, perhaps,
extracting the tiny reusable primitive it depends on — the actual digest
implementation lives in its own ticket.

### The pattern: a blackboard as a durable producer/consumer queue

A **producer** appends records to a blackboard as events occur; a
**consumer** drains that blackboard on a schedule (a recurring ticket),
acts, and empties it. The blackboard *is* the queue.

Why this fits Relay rather than a bespoke queue:

- **No hidden state.** The queue is an ordinary, git-tracked, human-readable
  `blackboard.md` — openable mid-flight, never a dotfile or opaque store.
- **No reliance on git history.** Events are captured the moment they fire,
  so nothing depends on scanning `git log` (too slow on a busy task repo)
  to reconstruct what happened.
- **Survives task deletion.** Because the record lands at event time, work
  that's done-and-deleted before the consumer runs is already accounted for.
- **Reuses existing machinery.** The consumer is just a `recurring/` ticket;
  the cadence lives in its `schedule:` frontmatter — reproducible from the
  repo, no external cron.

### Shape

```
producer  ──append(record)──▶  recurring/<job>/blackboard.md  ──drain()──▶  consumer
 (many, concurrent)              ## Spool (pending)               (one, scheduled)
```

- **Records are JSONL** — one self-describing JSON object per line under a
  `## Spool (pending)` section. Chosen over tables/delimited lines because a
  payload field can hold arbitrary text (pipes, emoji, arrows) with no
  escaping, and each record stands alone. Still plain text in a visible
  blackboard.
- **Append and drain rely on single-process serialization, not a lock.**
  Relay runs one CLI process at a time, so appends and the consumer's
  read-and-empty never overlap. Writes go through `atomic_write_text` for
  crash-safety (a reader sees the old or new complete file; a crash can't
  truncate it) — that is *not* mutual exclusion. Genuinely concurrent
  producers would need the not-yet-built primitive in
  `file-locking-for-concurrent-task-mutation`; until it lands, do not
  document the spool as lock-guarded.
- **Drain empties the spool section** back to its seed; an empty spool makes
  the consumer a no-op (safe to run twice).

### Deliverables

- **Document the pattern in a context** so it's discoverable: either a
  section in `relay/architecture` (SKILL.md) or a dedicated
  `relay/patterns` context. Cover: when to reach for it, the JSONL +
  `## Spool (pending)` convention, the serialized (not lock-guarded)
  append/drain contract, and the recurring-ticket-as-consumer wiring. Mirror
  to the packaged copy under `src/relay/resources/templates/relay-os/` if the
  context ships.
- **The primitive already exists — no extraction needed here.**
  `src/relay/spool.py` shipped with the Slack digest (#275): `append_record`,
  `read_records`, `drain` over a `## Spool (pending)` JSONL section via
  `atomic_write_text`. So this ticket is documentation-only; the doc points at
  the existing module rather than hand-rolling JSONL + serialization.

### Related

- `stop-overloading-relay-slack` — the motivating first instance (Slack
  digest); this pattern was abstracted out of its design.
- `file-locking-for-concurrent-task-mutation` — the not-yet-built primitive
  the spool would need *only if* it ever has genuinely concurrent producers;
  today it relies on single-process serialization instead.
- `blackboard-for-recurring-task-must-use-the-permant` — the recurring
  consumer must append to / drain the *persistent* blackboard, not a
  per-period copy; this pattern has to land on the same resolution.

### Open questions (resolved during implement)

- Pattern's home: **new `relay/patterns` context** (keeps `architecture`
  lean; gives future patterns a home). A pointer from `relay/architecture`'s
  "does NOT cover" list makes it discoverable.
- Ship `spool.py` here? **No — it already exists** (shipped in #275). This
  ticket stays documentation-only and points at the existing module.

## Context

Abstracted from the `stop-overloading-relay-slack` digest design. The
pattern's mechanics lean on `relay/architecture` (blackboard primitive,
recurring tasks, single-process serialization) and `relay/sync` (why we
avoid hidden state and git-scan reconstruction).
