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























consumed_through: 090e9fa2dbc6
{"id":"090e9fa2dbc6","ts":"2026-09-10T09:55","project":"coga","kind":"done","detail":"claude finished: sweep → done ✅","ticket":"recurring/autoclose-merged","owner":"nicktoper"}
{"id":"65e3f9fdfc73","ts":"2026-09-10T09:55","project":"coga","kind":"done","detail":"claude finished: flush → done ✅","ticket":"recurring/digest","owner":"nicktoper"}
{"id":"1b413db12095","ts":"2026-09-11T10:00","project":"coga","kind":"done","detail":"auto-bumped: review → done — <https://github.com/FastJVM/coga/pull/783|PR #783> merged ✅","ticket":"allow-description-and-owner-on-create","owner":"zach"}
{"id":"6c689b9912a4","ts":"2026-09-11T10:00","project":"coga","kind":"done","detail":"claude finished: sweep → done ✅","ticket":"recurring/autoclose-merged","owner":"nicktoper"}
