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






















consumed_through: 2c04ba02765b
{"id":"2c04ba02765b","ts":"2026-09-09T10:30","project":"coga","kind":"done","detail":"claude finished: sweep → done ✅","ticket":"recurring/autoclose-merged","owner":"nicktoper"}
{"id":"28cbde2305fc","ts":"2026-09-09T10:31","project":"coga","kind":"done","detail":"claude finished: flush → done ✅","ticket":"recurring/digest","owner":"nicktoper"}
{"id":"58966bd52011","ts":"2026-09-09T10:31","project":"coga","kind":"done","detail":"claude finished: remind → done ✅","ticket":"recurring/blocker-reminders","owner":"nicktoper"}
{"id":"76324bdd2669","ts":"2026-09-09T17:01","project":"coga","kind":"canceled","detail":"nicktoper canceled — Duplicate of make-sure-repo-clietn-don-t-edit-coga, which carries the filled ticket.","ticket":"dream-shouldn-t-touch-coga-in-coga-enabled-repo","owner":"nicktoper"}
