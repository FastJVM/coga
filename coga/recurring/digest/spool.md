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

















consumed_through: b544ec1432d1
{"id":"b544ec1432d1","ts":"2026-08-25T10:56","project":"coga","kind":"done","detail":"claude finished: sweep → done ✅","ticket":"recurring/autoclose-merged","owner":"nicktoper"}
{"id":"5081af6db1c8","ts":"2026-08-25T10:57","project":"coga","kind":"done","detail":"claude finished: flush → done ✅","ticket":"recurring/digest","owner":"nicktoper"}
{"id":"992d4fdc1da7","ts":"2026-08-25T10:57","project":"coga","kind":"done","detail":"claude finished: remind → done ✅","ticket":"recurring/blocker-reminders","owner":"nicktoper"}
