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
shard subagent along with that shard's assignment. It holds three files:

- `manifest.md` — Dream-written, one line per shard: shard id, the exact paths
  that shard owns, and their total bytes. Dream owns this file; shards read it
  and never write to it.
- `index.md` — Dream-written, the full corpus index for the phase: every
  candidate path and its size, across all shards. A shard reads only its own
  assignment, but the index lets it name a target that lives in another shard.
- `findings.md` — append-only, shared by every shard. This is where findings
  are delivered.
- `progress.md` — append-only, shared by every shard. Heartbeat and completion
  lines.

Append with `>>` and never rewrite these files; concurrent shards share them.

## Shard budget

A shard's assignment is at most **150 KB of Markdown across at most 40 files**.
Dream sizes shards with `find <paths> -type f -name '*.md' -printf '%s %p\n'`
before launching anything.

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

Dream reconciles `manifest.md` against the completion lines in `progress.md`:

- every shard complete → the phase result is `reported`, or `no-op` when the
  total is zero findings;
- any shard missing a completion line, or carrying an `incomplete` line → Dream
  re-shards that assignment into halves and retries it **once**; if it still
  does not complete, the phase result is `partial` and the unread paths and the
  scan directory path go into the run summary as `human-needed`.

Dream then merges `findings.md` into the Dream task's blackboard `## Findings`
section, de-duplicating across shards. Because de-duplication now happens over
the bounded findings file rather than over the raw corpus, two shards can report
the same underlying issue from different evidence; Dream merges those into one
finding and may re-read a specific named file to confirm they are the same.
