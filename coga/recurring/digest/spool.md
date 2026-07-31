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








consumed_through: dc09c37d0a0d
{"id":"dc09c37d0a0d","ts":"2026-07-30T10:05","project":"coga","kind":"done","detail":"→ done (recipe: autoclose)","ticket":"recurring/autoclose-merged","owner":"nicktoper"}
{"id":"1864e0e316f2","ts":"2026-07-30T10:05","project":"coga","kind":"done","detail":"→ done (recipe: digest)","ticket":"recurring/digest","owner":"nicktoper"}
{"id":"d345a59f2a36","ts":"2026-07-30T10:06","project":"coga","kind":"done","detail":"→ done (recipe: blocker-reminders)","ticket":"recurring/blocker-reminders","owner":"nicktoper"}
{"id":"249497ad03bf","ts":"2026-07-31T10:45","project":"coga","kind":"done","detail":"auto-bumped: review → done — <https://github.com/FastJVM/coga/pull/674|PR #674> merged ✅","ticket":"always-accept-coga-ticket","owner":"nick"}
{"id":"6216f52464ae","ts":"2026-07-31T10:45","project":"coga","kind":"done","detail":"auto-bumped: review → done — <https://github.com/FastJVM/coga/pull/675|PR #675> merged ✅","ticket":"bump-can-mark-done-too","owner":"nick"}
{"id":"aeb633b7f617","ts":"2026-07-31T10:45","project":"coga","kind":"done","detail":"auto-bumped: review → done — <https://github.com/FastJVM/coga/pull/676|PR #676> merged ✅","ticket":"document-megalaunch-drain-order","owner":"nicktoper"}
{"id":"07fecc9920ab","ts":"2026-07-31T10:45","project":"coga","kind":"done","detail":"auto-bumped: review → done — <https://github.com/FastJVM/coga/pull/672|PR #672> merged ✅","ticket":"retire-a-finished-ticket-s-linked-worktree-and-mak","owner":"nicktoper"}
{"id":"6defd0c5aa89","ts":"2026-07-31T10:45","project":"coga","kind":"done","detail":"auto-bumped: review → done — <https://github.com/FastJVM/coga/pull/673|PR #673> merged ✅","ticket":"scrub-coga-task-in-the-pytest-autouse-guard-so-fix","owner":"nicktoper"}
