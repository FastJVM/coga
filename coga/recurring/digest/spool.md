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



consumed_through: 4f676e9ca380
{"id":"4f676e9ca380","ts":"2026-07-15T12:32","project":"coga","kind":"done","detail":"→ done (script)","ticket":"recurring/skill-update","owner":"nick"}
{"id":"701102bd50d8","ts":"2026-07-15T12:32","project":"coga","kind":"done","detail":"→ done (script)","ticket":"recurring/digest","owner":"nick"}
{"id":"64832a75819d","ts":"2026-07-15T12:33","project":"coga","kind":"done","detail":"→ done (script)","ticket":"recurring/blocker-reminders","owner":"nick"}
{"id":"c2166e860b5b","ts":"2026-07-15T20:01","project":"coga","kind":"done","detail":"claude finished: open-pr → done ✅ — PR merged; task complete.","ticket":"remove-megalaunch-token-budget-guard-and-usage-pro","owner":"nicktoper"}
