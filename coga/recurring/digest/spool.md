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
















consumed_through: f2582ef9174f
{"id":"f2582ef9174f","ts":"2026-08-24T11:44","project":"coga","kind":"done","detail":"claude finished: execute → done ✅ — W35 sweep: delegated coga resolve-conflicts checked 3 open PRs (#704/#705/#706) — all up-to-date, 0 conflicts, no pushes, no attention needed.","ticket":"recurring/resolve-conflicts","owner":"nicktoper"}
{"id":"c1bdd910a6c4","ts":"2026-08-24T11:44","project":"coga","kind":"done","detail":"→ done (recipe: digest)","ticket":"recurring/digest","owner":"nicktoper"}
