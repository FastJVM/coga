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














consumed_through: 00a447cbf9d8
{"id":"00a447cbf9d8","ts":"2026-08-19T13:50","project":"coga","kind":"done","detail":"→ done (recipe: autoclose)","ticket":"recurring/autoclose-merged","owner":"nicktoper"}
{"id":"1ea67ec85439","ts":"2026-08-19T13:50","project":"coga","kind":"done","detail":"→ done (recipe: digest)","ticket":"recurring/digest","owner":"nicktoper"}
{"id":"e31bde40a7cd","ts":"2026-08-19T13:50","project":"coga","kind":"done","detail":"→ done (recipe: blocker-reminders)","ticket":"recurring/blocker-reminders","owner":"nicktoper"}
{"id":"3ce69e8755b1","ts":"2026-08-21T11:53","project":"coga","kind":"done","detail":"auto-bumped: review → done — <https://github.com/FastJVM/coga/pull/703|PR #703> merged ✅","ticket":"dream-phases-2-3-cannot-complete-scan-subagents-re","owner":"nicktoper"}
{"id":"1885c2276f69","ts":"2026-08-21T11:53","project":"coga","kind":"done","detail":"auto-bumped: review → done — <https://github.com/FastJVM/coga/pull/701|PR #701> merged ✅","ticket":"put-build-back","owner":"nicktoper"}
{"id":"043da5eedd0d","ts":"2026-08-21T11:53","project":"coga","kind":"done","detail":"auto-bumped: review → done — <https://github.com/FastJVM/coga/pull/702|PR #702> merged ✅","ticket":"validate-drift-classifier-misses-17-emitted-kinds","owner":"nicktoper"}
