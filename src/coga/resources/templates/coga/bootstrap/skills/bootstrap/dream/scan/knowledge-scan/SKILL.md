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
shard**. Do not create disjoint ticket-only and knowledge-only shard groups: a
shard that owns no ticket path cannot reach `extract` or `gap` at all, since
both classes are defined by a ticket-to-knowledge comparison, and it silently
degrades to a knowledge-only consistency check that can only ever report
`stale`. A shard with one empty side is a mis-partition, not a shard kind.
Derive an area's first routing key from ticket context/skill/workflow refs and
from knowledge namespaces, then use task paths and titles for tickets with no
refs.

- **Ticket evidence** — every bare task Markdown file and every task
  directory's `ticket.md`, body and blackboard both.
- **Knowledge evidence** — every `SKILL.md` under the repo's configured
  contexts directory (`coga/contexts/` unless `[layout] contexts` in
  `coga.toml` moves it — resolve that checkout-root-relative key before
  globbing), every repo-authored Markdown file under `coga/skills/**`, and
  `coga/workflows/**`.

Installer-managed skills are **outside the corpus**. `coga/skills/` mixes
repo-authored skills with upstream trees that `coga skill install` and
`coga skill update` place and refresh wholesale. **The manifest's `ref` list in
`src/coga/resources/managed-skills.toml` is the whole test.** Exclude those
trees before globbing.

Do *not* widen that to "any skill whose recorded metadata names a non-local
source". Provenance is not management: a skill installed with
`coga skill install-url` also carries a `.coga-source.json` naming an upstream
source, but it is an ordinary project-local skill that the repo adapts and that
Coga can durably edit. `coga/skills/clarity/` is the live case — `source_type:
url`, absent from the manifest, and carrying real `local_adaptation_notes`.
Excluding it would drop repo-specific knowledge from the corpus for no reason
beyond it having once been downloaded. Today they are the seven `google-agents-cli-*` trees: 286,169 bytes
across 34 Markdown files, about 61% of all Markdown under `coga/skills/` and
roughly two full shard budgets. The content is upstream GCP/ADK documentation
carrying no Coga repo reality, and Coga cannot durably edit it — a `stale`
finding against it is reverted by the next refresh, and no `extract` can ever
target it. Spend the budget on knowledge this repo authored.

Each corpus file has one owning shard, but a relevant knowledge or ticket file
may be duplicated as evidence in another area's assignment. Keep a task
directory's Markdown files together. The owned and evidence paths together must
stay inside the shared protocol's byte and file limits.

A few contexts are large enough that pricing them at full length costs a shard
on its own — `coga/contexts/coga/architecture/SKILL.md` is ~74 KB,
`coga/contexts/coga/sync/SKILL.md` ~67 KB, and
`coga/contexts/coga/recurring/SKILL.md` ~54 KB against a 150 KB budget — and
that is what forces the knowledge-only shards this partition forbids. The
protocol already refuses to read a file over 60 KB whole, so sizing one whole
charges a shard for bytes it will never read. **Own an oversized context as a
ranged path**, using the shared protocol's "Ranged ownership" rules: pair it
with its area's ticket set and record it in the manifest as
`<path>@<allowance>`, so it is priced at the bytes the shard will actually
spend rather than at its full length. The shard covers it by grepping and
range-reading the sections its tickets touch. A context over the whole-read
limit is the only file this phase may own that way; every other file is owned
whole or not owned, and a ranged file still has exactly one owning shard.

Before classifying an `extract` or `gap`, compare the ticket evidence with the
matching context, skill, and workflow evidence in that area. For a possible
cross-area target, use the full index to locate it and read a targeted excerpt;
the index entry alone is not evidence that knowledge is present or absent.
Before calling a pattern repeated enough for `gap`, search the indexed ticket
paths and read the matching excerpts from at least two independent tickets.
Then check whether the gap already has an owner: grep every task Markdown file
under `coga/tasks/` — bare `.md` files and each `ticket.md`, titles and bodies,
not only your shard's paths — for the target path and two or three of the
finding's distinctive terms, and read each hit's title and description. An open
ticket (any status but `done` or `canceled`) that already covers the same gap
is its owner; earlier Dream runs file gaps as drafts and name the run, phase,
and shard in the description, so an owned gap usually greps on its own target.
Still write the finding — the count must stay honest — but add
`owner: <slug>` so Phase 6 reports "already ticketed" instead of filing a
duplicate. A `done` ticket is evidence to inspect, not an open owner: verify
the promised change in the current corpus or an open PR before treating the
gap as covered, and cite that evidence. If the ticket instead holds
unextracted durable knowledge, emit `extract` with the `source:` and `area:`
fields below. If the promised change is still missing, keep the `gap` and
continue the open-owner search; `status: done` alone must not suppress it.
If the needed comparison cannot fit in this assignment, finish no finding from
that candidate: write `incomplete` with the exact extra evidence paths so Dream
can place them together in a smaller retry shard.

## Findings

Record only a classified findings list; raw ticket and blackboard contents stay
inside the subagent. Classify each finding as exactly one of:

- `extract` — a done or canceled ticket holds durable knowledge that belongs
  in a context or skill. Record the ticket slug and the context/skill area it
  touches, and add a `source:` line that says who can consume it:
  - `source: done` — `status: done` and the blackboard's `## Dev` section has
    no real `branch:` or `worktree:` value (absent, empty, or a placeholder
    such as `(not yet created)`). Phase 4 Retro extracts it this run.
  - `source: done+checkout` — `status: done` with a real `## Dev` checkout.
    This is retirement debt: Retro does not touch it, and `coga retire <slug>`
    is what will. Phase 6 lists it under retirement debt instead of losing it.
  - `source: canceled` — `status: canceled`. Retro refuses non-done tickets,
    so Phase 6 opens the knowledge PR itself. A canceled ticket's abandoned
    design is not durable knowledge; only a reusable fact it discovered along
    the way — a gotcha, a verified behavior, a measured limit — qualifies.

  Read `status:` and `## Dev` from the ticket itself; the index entry alone is
  not evidence. A ticket in any other status holds working state, not
  extractable knowledge.
- `stale` — an existing context or skill contradicts current repo reality.
  Name the file and state the contradiction.
- `gap` — a repeated pattern (recurring task knowledge, repeated process
  struggle, or an ad-hoc workflow sequence) with no context, skill, or
  workflow to carry it. Add `owner: <slug>` when the owner search above found
  an existing ticket for it.

Include draft content when a new file is proposed. Set the `area:` and
`source:` fields on every `extract` finding. Group the `extract` findings by
the context/skill area they touch: Dream applies that grouping when it merges
the shards into the Dream task's blackboard `## Findings`, and Phase 4 uses it
to batch coherent PRs.
