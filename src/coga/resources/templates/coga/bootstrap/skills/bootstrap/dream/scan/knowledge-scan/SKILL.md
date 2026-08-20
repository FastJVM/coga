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
existed so one running delta could compare tickets against knowledge and
de-duplicate across the whole corpus. The tradeoff is real: merge-time
de-duplication compares titles, targets, and paragraphs rather than retaining
all evidence in one context. Area shards preserve the more important
cross-corpus comparison by carrying both ticket and knowledge evidence; a
slightly repeated read over real findings is better than a sweep that returns
nothing.

The scan directory's `index.md` is the bounded routing layer. For every ticket
it includes path, bytes, slug, title, status, context refs, skill refs, and
workflow name. For every context, skill, and workflow it includes path, bytes,
name, description or heading, and namespace. These are compact metadata, not a
replacement for reading the named evidence.

## Shard partition

Dream partitions this scan **by area, with both sides of the comparison in each
shard**. Do not create disjoint ticket-only and knowledge-only shard groups.
Derive an area's first routing key from ticket context/skill/workflow refs and
from knowledge namespaces, then use task paths and titles for tickets with no
refs.

- **Ticket evidence** — every bare task Markdown file and every task
  directory's `ticket.md`, body and blackboard both.
- **Knowledge evidence** — `coga/contexts/**/SKILL.md`, every Markdown file
  under `coga/skills/**`, and `coga/workflows/**`.

Each corpus file has one owning shard, but a relevant knowledge or ticket file
may be duplicated as evidence in another area's assignment. Keep a task
directory's Markdown files together and do not split a single file. The owned
and evidence paths together must stay inside the shared protocol's byte and
file limits.

Before classifying an `extract` or `gap`, compare the ticket evidence with the
matching context, skill, and workflow evidence in that area. For a possible
cross-area target, use the full index to locate it and read a targeted excerpt;
the index entry alone is not evidence that knowledge is present or absent.
Before calling a pattern repeated enough for `gap`, search the indexed ticket
paths and read the matching excerpts from at least two independent tickets.
If the needed comparison cannot fit in this assignment, finish no finding from
that candidate: write `incomplete` with the exact extra evidence paths so Dream
can place them together in a smaller retry shard.

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
