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






consumed_through: f2bbece60922
{"id":"f2bbece60922","ts":"2026-07-27T14:34","project":"coga","kind":"done","detail":"claude finished: execute → done ✅ — W31 sweep: delegated coga resolve-conflicts ran clean — 0 open PRs, nothing to rebase.","ticket":"recurring/resolve-conflicts","owner":"nicktoper"}
{"id":"13d6ee3abb1c","ts":"2026-07-27T14:34","project":"coga","kind":"done","detail":"→ done (recipe: digest)","ticket":"recurring/digest","owner":"nicktoper"}
{"id":"8763a9d458d0","ts":"2026-07-27T14:35","project":"coga","kind":"done","detail":"→ done (recipe: skill-update)","ticket":"recurring/skill-update","owner":"nicktoper"}
{"id":"48968848404b","ts":"2026-07-27T14:35","project":"coga","kind":"done","detail":"→ done (recipe: blocker-reminders)","ticket":"recurring/blocker-reminders","owner":"nicktoper"}
