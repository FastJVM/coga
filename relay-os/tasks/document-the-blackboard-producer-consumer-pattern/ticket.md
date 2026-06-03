---
title: Document the blackboard producer/consumer pattern
status: active
mode: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts: []
skills: []
workflow:
  name: dev/with-self-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: self-qa
    skills:
    - code/self-qa
    assignee: agent
  - name: pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
step: 1 (implement)
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
- **Append and drain are lock-guarded.** Many producers append at once;
  the consumer holds the lock across read-and-empty so records produced
  mid-flush are never dropped. (Depends on Relay's file-locking — see
  `file-locking-for-concurrent-task-mutation`.)
- **Drain empties the spool section** back to its seed; an empty spool makes
  the consumer a no-op (safe to run twice).

### Deliverables

- **Document the pattern in a context** so it's discoverable: either a
  section in `relay/architecture` (SKILL.md) or a dedicated
  `relay/patterns` context. Cover: when to reach for it, the JSONL +
  `## Spool (pending)` convention, the lock-guarded append/drain contract,
  and the recurring-ticket-as-consumer wiring. Mirror to the packaged copy
  under `src/relay/resources/templates/relay-os/` if the context ships.
- **(Optional, decide during authoring) extract the primitive.** A small
  `src/relay/spool.py` with lock-guarded `append_record(blackboard, obj)`
  and `drain(blackboard) -> list[obj]`, so callers don't hand-roll JSONL +
  locking. The Slack digest would be its first caller. If this grows beyond
  a thin helper, keep it in the digest ticket and let this one stay
  documentation-only.

### Related

- `stop-overloading-relay-slack` — the motivating first instance (Slack
  digest); this pattern was abstracted out of its design.
- `file-locking-for-concurrent-task-mutation` — the locking this pattern
  depends on for concurrent append / atomic drain.
- `blackboard-for-recurring-task-must-use-the-permant` — the recurring
  consumer must append to / drain the *persistent* blackboard, not a
  per-period copy; this pattern has to land on the same resolution.

### Open questions

- Pattern's home: a section in `relay/architecture` vs a new
  `relay/patterns` context.
- Whether to ship the `spool.py` primitive here or leave it to the digest
  ticket and keep this documentation-only.

## Context

Abstracted from the `stop-overloading-relay-slack` digest design. The
pattern's mechanics lean on `relay/architecture` (blackboard primitive,
recurring tasks, locking) and `relay/sync` (why we avoid hidden state and
git-scan reconstruction).
