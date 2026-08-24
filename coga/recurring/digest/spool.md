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















consumed_through: 24f3b7c532a5
{"id":"24f3b7c532a5","ts":"2026-08-21T11:53","project":"coga","kind":"done","detail":"→ done (recipe: autoclose)","ticket":"recurring/autoclose-merged","owner":"nicktoper"}
{"id":"9531275abd24","ts":"2026-08-21T11:53","project":"coga","kind":"done","detail":"→ done (recipe: digest)","ticket":"recurring/digest","owner":"nicktoper"}
{"id":"a6ec0c97bcea","ts":"2026-08-21T11:54","project":"coga","kind":"done","detail":"→ done (recipe: blocker-reminders)","ticket":"recurring/blocker-reminders","owner":"nicktoper"}
{"id":"415405e3360b","ts":"2026-08-24T11:42","project":"coga","kind":"done","detail":"→ done (recipe: branch-sweep)","ticket":"recurring/branch-sweep","owner":"nicktoper"}
{"id":"0f53b647eaf6","ts":"2026-08-24T11:42","project":"coga","kind":"done","detail":"auto-bumped: review → done — <https://github.com/FastJVM/coga/pull/700|PR #700> merged ✅","ticket":"recurring-recipe-question","owner":"nicktoper"}
