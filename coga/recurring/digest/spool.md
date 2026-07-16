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





consumed_through: 5395a45530c4
{"id":"5395a45530c4","ts":"2026-07-16T10:15","project":"coga","kind":"done","detail":"→ done (script)","ticket":"recurring/autoclose-merged","owner":"nicktoper"}
{"id":"c74322881d74","ts":"2026-07-16T10:15","project":"coga","kind":"done","detail":"→ done (script)","ticket":"recurring/digest","owner":"nicktoper"}
{"id":"8f2a92e28596","ts":"2026-07-16T10:15","project":"coga","kind":"done","detail":"→ done (script)","ticket":"recurring/blocker-reminders","owner":"nicktoper"}
{"id":"a24c6c948452","ts":"2026-07-16T10:30","project":"coga","kind":"done","detail":"claude finished: implement → done ✅","ticket":"install/retest-ssh-https-and-init-reclone-on-fresh-machine","owner":"nicktoper"}
