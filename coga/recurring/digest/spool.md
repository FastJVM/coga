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










consumed_through: fd951ba8b086
{"id":"fd951ba8b086","ts":"2026-08-13T09:41","project":"coga","kind":"done","detail":"→ done (recipe: autoclose)","ticket":"recurring/autoclose-merged","owner":"nicktoper"}
{"id":"9bc506f4be1a","ts":"2026-08-13T09:41","project":"coga","kind":"done","detail":"→ done (recipe: digest)","ticket":"recurring/digest","owner":"nicktoper"}
{"id":"9dcc3202cdde","ts":"2026-08-13T10:09","project":"coga","kind":"done","detail":"claude finished: execute → done ✅ — Dream 2026-W33 complete: 4 PRs opened, 10 tickets direct-deleted, 1 draft ticket, 23 human-needed validation issues reported.","ticket":"recurring/dream","owner":"nicktoper"}
{"id":"ab63d154edb8","ts":"2026-08-13T11:21","project":"coga-v2-premise-dead-drafts","kind":"canceled","detail":"nicktoper canceled — Premise-dead: the ticket is entirely about the mode: frontmatter field (script/auto/interactive), which no longer exists. coga/recurring now documents the surviving constraint (agent work needs a TTY; recipes and complete scripts can be headless). Closing as the ticket's own text directs once the mode story landed.","ticket":"v2/document-interactive-recurring-sweep-hazard-in-rel","owner":"nicktoper"}
