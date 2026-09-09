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





















consumed_through: f5339d021849
{"id":"f5339d021849","ts":"2026-09-08T16:50","project":"coga","kind":"done","detail":"claude finished: sweep → done ✅","ticket":"recurring/autoclose-merged","owner":"nicktoper"}
{"id":"32fb0bde78b8","ts":"2026-09-08T16:50","project":"coga","kind":"done","detail":"claude finished: flush → done ✅","ticket":"recurring/digest","owner":"nicktoper"}
{"id":"1bc90357c816","ts":"2026-09-08T16:50","project":"coga","kind":"done","detail":"claude finished: remind → done ✅","ticket":"recurring/blocker-reminders","owner":"nicktoper"}
{"id":"98b21d3da867","ts":"2026-09-08T17:31","project":"coga","kind":"done","detail":"claude finished: execute → done ✅ — Dream run complete: 6 phases, 13 proposal PRs, 18 draft tickets, 7 done tickets reaped.","ticket":"recurring/dream","owner":"nicktoper"}
