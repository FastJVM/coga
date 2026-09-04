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



















consumed_through: 2a1781e508f8
{"id":"2a1781e508f8","ts":"2026-09-03T11:00","project":"coga","kind":"done","detail":"claude finished: sweep → done ✅","ticket":"recurring/autoclose-merged","owner":"nicktoper"}
{"id":"14e2f7ac91c2","ts":"2026-09-03T11:01","project":"coga","kind":"done","detail":"claude finished: flush → done ✅","ticket":"recurring/digest","owner":"nicktoper"}
{"id":"d08aac562f91","ts":"2026-09-03T11:01","project":"coga","kind":"done","detail":"claude finished: remind → done ✅","ticket":"recurring/blocker-reminders","owner":"nicktoper"}
{"id":"06d53450a1f7","ts":"2026-09-03T11:43","project":"coga","kind":"canceled","detail":"nicktoper canceled — Premise-dead: all three motivating drafts are parked in v2 (not on the current execution path), the named stale coga/secrets op:// claim already shipped fixed in #714, and the live v1 headless facts are already homed in coga/recurring + coga/secrets. Residual missing-user preflight work is covered by v2/fail-validation-when-local-user-is-required-for-ex. Full premise check on the blackboard.","ticket":"no-durable-runbook-covers-running-coga-headless","owner":"nicktoper"}
{"id":"e8dbf814b3f9","ts":"2026-09-04T11:50","project":"coga","kind":"done","detail":"claude finished: sweep → done ✅","ticket":"recurring/autoclose-merged","owner":"nicktoper"}
