---
name: bootstrap/dream/scan/scan-protocol
description: The durable shard protocol both Dream decide-half scans follow — bounded per-shard reading, findings appended to disk as they are decided, and an explicit per-shard completion line.
---

# Scan Protocol

Dream's two decide-half scans — `bootstrap/dream/scan/knowledge-scan` and
`bootstrap/dream/scan/contract-audit` — are read-only sweeps over Coga's own
corpus. Both once specified a single full-corpus read whose entire value arrived
in one final message. That design has two failure modes and hit both: the corpus
outgrew what one subagent can hold, and a subagent that stopped early returned
nothing at all, which Dream could not tell apart from a clean repo.

This protocol is the shared fix and both scans follow it. Work is bounded per
subagent, findings land on disk the moment they are decided, and every shard
ends by stating how many it found — including zero.

## The scan directory

Dream creates one scan directory per phase and passes its absolute path to every
shard subagent along with that shard's assignment. It holds four files:

- `manifest.md` — a Dream-written, append-only assignment log. A shard row
  records its id, attempt number, exact owned paths, any duplicated evidence
  paths, and their total bytes. A supersession row records that a failed parent
  was replaced by one or more retry children. Dream owns this file; shards read
  it and never write to it.
- `index.md` — Dream-written, the full corpus index for the phase: every
  candidate path, its size and kind, plus compact routing metadata when the
  phase skill requires it. The index is a discovery map, not permission to read
  the whole corpus again.
- `findings.md` — append-only, shared by every shard. This is where findings
  are delivered.
- `progress.md` — append-only, shared by every shard. Heartbeat and completion
  lines.

Write `index.md` once before launching. Append every later record with `>>` and
never rewrite the shared files; concurrent shards share them.

Use these manifest record shapes:

```
shard <id> attempt=<1 | 2> bytes=<N> owns: <paths>; evidence: <paths or none>
supersede <parent-id> -> <child-id>[, <child-id> ...]
```

The active manifest is its **leaf assignments**: shard rows whose ids have not
appeared on the left of a `supersede` row. Reconciliation checks only those
leaves. This keeps the log append-only without requiring a failed parent to
later produce an impossible completion line.

## Shard budget

A shard's owned and evidence paths together are at most **150 KB of Markdown
across at most 40 distinct files**. Evidence may appear in more than one shard,
but every corpus file has exactly one owning shard. Dream sizes files portably
before launching anything; for example:

```
find <paths> -type f -name '*.md' -exec wc -c {} \;
```

Do not use GNU-only `find -printf`; Dream must run with the default BSD tools on
macOS too.

A shard fully reads its owned paths and may read the evidence paths named in
its assignment. When a concrete comparison needs another indexed file, use a
targeted grep or range read rather than reading that file whole, and count the
bytes actually read against the same budget. If the comparison cannot fit,
write an `incomplete` line naming the needed evidence so Dream can include it in
the retry assignment. The index alone never substitutes for the comparison.

Two reading rules keep a shard inside its budget:

- **Never read a file over 60 KB whole.** Read it in ranges, or grep it for the
  claims you care about. A single 55 KB context file is a third of a shard.
- **Never read `coga/log.md` whole.** It is the repo-global append-only history
  and is far larger than any shard budget. Grep it for an exact slug or term.

If your assignment turns out to exceed the budget once you size it, do not read
past the budget. Process what fits, then write an `incomplete` line naming the
paths you did not reach so Dream can re-shard them.

## Append findings as you decide them

Write each finding to `findings.md` **the moment you decide it**, before you
read the next file. Never accumulate findings in context to emit at the end —
that is exactly the failure this protocol exists to prevent. A shard that dies
halfway has still delivered everything it decided up to that point.

Each finding is one block:

```markdown
### <short title>

- shard: <shard-id>
- class: <extract | stale | gap | drift>
- target: <file path, or ticket slug for `extract`>
- area: <context/skill area>

<one paragraph describing the change>
```

`area:` is required for `extract` findings — Phase 4 batches coherent PRs by it —
and optional otherwise. When the finding proposes a new file, append the draft
content under the paragraph in a fenced block.

## Heartbeat

After each file you finish reading, append one line to `progress.md`:

```
<shard-id> <ISO-8601 timestamp> read <path> (<bytes>) — <N> findings so far
```

It is a cheap liveness record. A shard that stops mid-sweep leaves a trail
showing exactly how far it got and what it had found.

## Completion line — this is what ends your shard

The last action of every shard is to append its completion line to
`progress.md`:

```
<shard-id> complete — <N> findings
```

**`0 findings` is a real result and the line is still required.** A clean shard
that writes `shard-03 complete — 0 findings` is how Dream learns the shard ran
and found nothing. A shard that writes no line at all is treated as a shard that
never returned, not as a clean one.

If something prevents you from finishing, append this instead and stop:

```
<shard-id> incomplete — <reason>, last read <path>, unread <paths>
```

## Your final message is not the delivery

Dream reads findings from `findings.md` on disk. It does not parse your final
message. Keep that message to one line — the same text as your completion line —
and put everything else on disk. Do not summarize your findings back in the
message; do not hold any finding that is not already in `findings.md`.

## What Dream does with this

Dream reconciles the active leaf assignments in `manifest.md` against the
completion lines in `progress.md`. Leaf completion proves corpus coverage; the
phase's finding total comes from the de-duplicated `findings.md` across **all**
attempts, including durable findings written by a parent before it was
superseded. Supersession changes coverage expectations, never delivery:

- every leaf complete → the phase result is `reported`, or `no-op` only when
  the merged findings total is zero;
- any shard missing a completion line, or carrying an `incomplete` line → Dream
  appends a `supersede` row, appends one or more smaller attempt-2 child rows,
  and retries those children **once**. Use a single child when one indivisible
  file merely needs a fresh attempt. A superseded parent's late completion does
  not satisfy or invalidate its children. If any attempt-2 leaf still does not
  complete, the phase result is `partial` and the unread paths and the scan
  directory path go into the run summary as `human-needed`.

Dream then merges `findings.md` into the Dream task's blackboard `## Findings`
section, de-duplicating across shards. Because de-duplication now happens over
the bounded findings file rather than over the raw corpus, two shards can report
the same underlying issue from different evidence; Dream merges those into one
finding and may re-read a specific named file to confirm they are the same.
