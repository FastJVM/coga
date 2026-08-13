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









consumed_through: f4c4a92f773e
{"id":"f4c4a92f773e","ts":"2026-07-31T10:45","project":"coga","kind":"done","detail":"→ done (recipe: autoclose)","ticket":"recurring/autoclose-merged","owner":"nicktoper"}
{"id":"29cf100eb419","ts":"2026-07-31T10:45","project":"coga","kind":"done","detail":"→ done (recipe: digest)","ticket":"recurring/digest","owner":"nicktoper"}
{"id":"0e58d3eb568b","ts":"2026-07-31T10:45","project":"coga","kind":"done","detail":"→ done (recipe: blocker-reminders)","ticket":"recurring/blocker-reminders","owner":"nicktoper"}
{"id":"c757bf711fc7","ts":"2026-08-13T09:38","project":"coga","kind":"done","detail":"→ done (recipe: branch-sweep)","ticket":"recurring/branch-sweep","owner":"nicktoper"}
