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


















consumed_through: 648b8acd2a45
{"id":"648b8acd2a45","ts":"2026-09-02T11:59","project":"coga","kind":"done","detail":"claude finished: sweep → done ✅","ticket":"recurring/autoclose-merged","owner":"nicktoper"}
{"id":"d02bd15e6b4e","ts":"2026-09-02T11:59","project":"coga","kind":"done","detail":"claude finished: flush → done ✅","ticket":"recurring/digest","owner":"nicktoper"}
{"id":"da3966f8791e","ts":"2026-09-02T11:59","project":"coga","kind":"done","detail":"claude finished: remind → done ✅","ticket":"recurring/blocker-reminders","owner":"nicktoper"}
{"id":"dc61b2946205","ts":"2026-09-02T12:35","project":"coga","kind":"done","detail":"claude finished: execute → done ✅ — Dream 2026-W36: 10 PRs (#737-#746), 9 draft tickets, 7 period tickets direct-deleted, 57 findings; 22 validate issues + 21 retirement-debt tickets need owner decisions.","ticket":"recurring/dream","owner":"nicktoper"}
{"id":"8719da0cc805","ts":"2026-09-02T13:42","project":"coga","kind":"canceled","detail":"nicktoper canceled — Split into correct-the-v2-known-stale-surfaces-table-and-rout, adjudicate-the-eight-premise-dead-v2-drafts, interview-the-owner-on-the-17-title-only-v2-stubs","ticket":"triage-the-v2-parking-area-empty-descriptions-prem","owner":"nicktoper"}
