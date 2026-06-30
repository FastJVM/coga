# Daily digest spool

Producer/consumer queue for `coga digest`. Producers append one JSONL record
at the **bottom** of `## Spool (pending)`; the single consumer (`coga digest`)
advances the `consumed_through:` watermark to the newest record and trims the
consumed prefix, always keeping the newest record in place as an *anchor*.

This file is marked `merge=union` (`.gitattributes`) so two clones appending
concurrently merge without conflict. Together with the top-trim/bottom-append
shape (deletes and appends sit in disjoint hunks separated by the anchor), that
makes the spool mergeable by construction with no lock — see the `coga/sync`
context. The git high-water mark lives separately in the digest ticket's
`### Digest State`, not here.

## Spool (pending)


consumed_through: b4ce33110eaf
{"id":"b4ce33110eaf","ts":"2026-06-29T22:35","project":"coga","kind":"done","detail":"→ done (script)","ticket":"recurring/autoclose-merged","owner":"nick"}
{"id":"dfeadcb6d530","ts":"2026-06-29T22:35","project":"coga","kind":"done","detail":"→ done (script)","ticket":"recurring/digest","owner":"nick"}
{"id":"88272b0eb871","ts":"2026-06-29T22:35","project":"coga","kind":"done","detail":"→ done (script)","ticket":"recurring/skill-update","owner":"nicktoper"}
{"id":"aa970d166610","ts":"2026-06-29T22:41","project":"coga","kind":"done","detail":"→ done (script)","ticket":"dream-validate-drift-w27","owner":"nicktoper"}
{"id":"1fed8b7f4520","ts":"2026-06-30T00:03","project":"coga","kind":"recurring-error","detail":"→ paused (timeout) — liveness watchdog: REPL timed out before signalling done","ticket":"recurring/dream","owner":"nicktoper"}
{"id":"8a41d5cf7c83","ts":"2026-06-30T11:12","project":"coga","kind":"done","detail":"claude finished: execute → done ✅","ticket":"recurring/dream","owner":"nicktoper"}
