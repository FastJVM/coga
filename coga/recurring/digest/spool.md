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




consumed_through: 8e32b965dc04
{"id":"8e32b965dc04","ts":"2026-07-15T20:14","project":"coga","kind":"done","detail":"→ done (script)","ticket":"recurring/autoclose-merged","owner":"nicktoper"}
{"id":"b99a93978ecd","ts":"2026-07-15T20:14","project":"coga","kind":"done","detail":"→ done (script)","ticket":"recurring/digest","owner":"nicktoper"}
{"id":"bef10e3dc37c","ts":"2026-07-15T20:15","project":"coga","kind":"done","detail":"→ done (script)","ticket":"recurring/blocker-reminders","owner":"nicktoper"}
{"id":"803cb28175e9","ts":"2026-07-15T20:36","project":"coga","kind":"done","detail":"→ done (script)","ticket":"dream-validate-drift-w29","owner":"nicktoper"}
{"id":"88c1b04d9318","ts":"2026-07-15T21:19","project":"coga","kind":"done","detail":"→ done (script)","ticket":"dream-cleanup-orphan-markers-w29","owner":"nicktoper"}
{"id":"462562db3591","ts":"2026-07-16T10:07","project":"coga","kind":"done","detail":"claude finished: execute → done ✅","ticket":"recurring/dream","owner":"nicktoper"}
