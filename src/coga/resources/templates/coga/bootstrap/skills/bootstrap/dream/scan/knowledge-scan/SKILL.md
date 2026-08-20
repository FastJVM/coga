---
name: bootstrap/dream/scan/knowledge-scan
description: Scan Dream's corpus in bounded shards and record extract, stale, and gap findings for durable follow-up.
---

# Knowledge Scan

It is the corpus read of the run: across its shards the scan covers every ticket
body and blackboard, and every context, skill, and workflow file, and compares
them. Running it in the decide half, before Phase 4 deletes any done ticket,
means no evidence is lost.

The scan runs as **bounded shards, not one sweep**. Dream partitions the corpus
and launches one subagent per shard; each shard follows
`bootstrap/dream/scan/scan-protocol` for its budget, its append-as-you-go
findings file, its heartbeat, and its required completion line. Read that skill
before you start — it is the delivery contract, and this skill only adds what is
specific to the knowledge scan.

Sharding replaced a single full-corpus read that could not fit. That read
existed so one running delta could de-duplicate across the whole corpus; the
de-duplication now happens in Dream's merge pass over the bounded findings file
instead. The tradeoff is real and accepted: merge-time de-duplication compares
titles, targets, and paragraphs rather than full evidence, which is weaker than
one delta over everything but strictly better than a sweep that returns nothing.
The scan directory's `index.md` carries the full corpus index, so a shard can
still name a target that lives outside its own assignment.

## Shard partition

Dream partitions this scan's corpus into two groups, then chunks each group to
the protocol's budget:

- **tickets** — `coga/tasks/**/*.md`, the bare task files and the `ticket.md` of
  each task directory, bodies and blackboards both.
- **knowledge** — `coga/contexts/**/SKILL.md`, `coga/skills/**`, and
  `coga/workflows/**`.

Keep a task directory's files in one shard. Do not split a single file across
shards.

## Findings

Record only a classified findings list; raw ticket and blackboard contents stay
inside the subagent. Classify each finding as exactly one of:

- `extract` — a done ticket holds durable knowledge that belongs in a context
  or skill. Record the ticket slug and the context/skill area it touches.
- `stale` — an existing context or skill contradicts current repo reality.
  Name the file and state the contradiction.
- `gap` — a repeated pattern (recurring task knowledge, repeated process
  struggle, or an ad-hoc workflow sequence) with no context, skill, or
  workflow to carry it.

Include draft content when a new file is proposed. Set the `area:` field on
every `extract` finding. Group the `extract` findings by the context/skill area
they touch: Dream applies that grouping when it merges the shards into the Dream
task's blackboard `## Findings`, and Phase 4 uses it to batch coherent PRs.
