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




















consumed_through: e8dbf814b3f9
{"id":"e8dbf814b3f9","ts":"2026-09-04T11:50","project":"coga","kind":"done","detail":"claude finished: sweep → done ✅","ticket":"recurring/autoclose-merged","owner":"nicktoper"}
{"id":"da2b2ed932e1","ts":"2026-09-04T11:50","project":"coga","kind":"done","detail":"claude finished: flush → done ✅","ticket":"recurring/digest","owner":"nicktoper"}
{"id":"86909c220a4e","ts":"2026-09-04T11:50","project":"coga","kind":"done","detail":"claude finished: remind → done ✅","ticket":"recurring/blocker-reminders","owner":"nicktoper"}
{"id":"9539e6ee86b6","ts":"2026-09-04T12:45","project":"coga","kind":"canceled","detail":"nicktoper canceled — Absorbed by give-a-ticket-s-superseded-design-one-documented-h.","ticket":"v2/document-design-pivot-in-blackboard-convention","owner":"nicktoper"}
{"id":"20bd1c30530f","ts":"2026-09-08T10:40","project":"coga","kind":"done","detail":"claude finished: report-to-coga → done ✅ — Settled model landed in coga/contexts/coga/secrets: one SA, one automation vault; tiers are human-access only; token-inheritance caveat kept pending the scrub ticket.","ticket":"service-account-scoping-single-vault-rule-conflict","owner":"nicktoper"}
{"id":"15b1eae27857","ts":"2026-09-08T11:22","project":"coga","kind":"done","detail":"claude finished: sweep → done ✅","ticket":"recurring/branch-sweep","owner":"nicktoper"}
{"id":"b81f29449248","ts":"2026-09-08T11:24","project":"coga","kind":"done","detail":"→ done (delegate: bootstrap/resolve-conflicts)","ticket":"recurring/resolve-conflicts","owner":"nicktoper"}
{"id":"110ccda0a181","ts":"2026-09-08T16:49","project":"coga","kind":"done","detail":"claude finished: update → done ✅","ticket":"recurring/skill-update","owner":"nicktoper"}
