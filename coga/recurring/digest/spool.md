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













consumed_through: cf39318454c0
{"id":"cf39318454c0","ts":"2026-08-18T09:57","project":"coga","kind":"done","detail":"→ done (recipe: autoclose)","ticket":"recurring/autoclose-merged","owner":"nicktoper"}
{"id":"36d153cc4442","ts":"2026-08-18T09:57","project":"coga","kind":"done","detail":"→ done (recipe: digest)","ticket":"recurring/digest","owner":"nicktoper"}
{"id":"2bd0ff13a7b5","ts":"2026-08-18T11:47","project":"coga","kind":"done","detail":"claude finished: execute → done ✅ — Already satisfied: Retro direct-deleted decide-the-fate-of-two-premise-dead-v2-drafts-whos under Dream at 0de678ef (durable on origin/main), no durable knowledge, no marker, no PR. Closed per owner precedent on retire-coga-important-support-second-webhook; no Retro rerun.","ticket":"retire-decide-the-fate-of-two-premise-dead-v2-drafts-whos","owner":"nicktoper"}
{"id":"ea361c649324","ts":"2026-08-18T11:49","project":"coga","kind":"done","detail":"claude finished: execute → done ✅ — Retro already ran: Dream 2026-W34 direct-deleted recurring-can-only-be-launched-by-owner (commit 59181000, on origin/main) — no durable knowledge, no PR, no marker. Nothing left to retire.","ticket":"retire-recurring-can-only-be-launched-by-owner","owner":"nicktoper"}
