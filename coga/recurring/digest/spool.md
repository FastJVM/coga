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

















consumed_through: b544ec1432d1
{"id":"b544ec1432d1","ts":"2026-08-25T10:56","project":"coga","kind":"done","detail":"claude finished: sweep → done ✅","ticket":"recurring/autoclose-merged","owner":"nicktoper"}
{"id":"5081af6db1c8","ts":"2026-08-25T10:57","project":"coga","kind":"done","detail":"claude finished: flush → done ✅","ticket":"recurring/digest","owner":"nicktoper"}
{"id":"992d4fdc1da7","ts":"2026-08-25T10:57","project":"coga","kind":"done","detail":"claude finished: remind → done ✅","ticket":"recurring/blocker-reminders","owner":"nicktoper"}
consumed_through: f2582ef9174f
{"id":"f2582ef9174f","ts":"2026-08-24T11:44","project":"coga","kind":"done","detail":"claude finished: execute → done ✅ — W35 sweep: delegated coga resolve-conflicts checked 3 open PRs (#704/#705/#706) — all up-to-date, 0 conflicts, no pushes, no attention needed.","ticket":"recurring/resolve-conflicts","owner":"nicktoper"}
{"id":"c1bdd910a6c4","ts":"2026-08-24T11:44","project":"coga","kind":"done","detail":"→ done (recipe: digest)","ticket":"recurring/digest","owner":"nicktoper"}
{"id":"5d7a8d5c05a4","ts":"2026-08-24T21:57","project":"coga","kind":"done","detail":"claude finished: update → done ✅ — Skill update: 1 updated, 0 follow-up — PR https://github.com/FastJVM/coga/pull/708","ticket":"recurring/skill-update","owner":"nicktoper"}
{"id":"68e2bb6486be","ts":"2026-08-24T21:58","project":"coga","kind":"done","detail":"claude finished: remind → done ✅ — Blocker reminders 2026-08-24: sweep clean, 0 reminders — both blocked tasks (unblock-rewind, verify-the-pr-review-comment-loop) already watermarked.","ticket":"recurring/blocker-reminders","owner":"nicktoper"}
{"id":"58dd9eb67899","ts":"2026-08-24T22:51","project":"coga","kind":"done","detail":"claude finished: execute → done ✅ — Dream 2026-W35: 12 PRs (#710-#721), 14 draft tickets, 4 period tickets deleted, 5 false positives caught. 29 validate issues need owner decisions.","ticket":"recurring/dream","owner":"nicktoper"}
{"id":"02cd1e9058dc","ts":"2026-08-25T11:13","project":"coga","kind":"done","detail":"auto-bumped: review → done — <https://github.com/FastJVM/coga/pull/706|PR #706> merged ✅","ticket":"autoclose-skips-annotated-pr-lines","owner":"nicktoper"}
{"id":"cc12a4337fd2","ts":"2026-08-25T16:29","project":"coga","kind":"done","detail":"claude finished: execute → done ✅ — direct-deleted, no durable knowledge","ticket":"retire-autoclose-skips-annotated-pr-lines","owner":"nicktoper"}
{"id":"93270faa7739","ts":"2026-08-26T21:28","project":"coga","kind":"canceled","detail":"nicktoper canceled — Merged into bumppy-requires-exactly-two-agents — same report, and the peer key must survive this ticket's [agents.*] merge, so they ship as one change.","ticket":"parse-agents-rejects-cogalocaltoml","owner":"nicktoper"}
{"id":"8429c76c8b68","ts":"2026-09-01T17:16","project":"coga","kind":"done","detail":"auto-bumped: review → done — <https://github.com/FastJVM/coga/pull/727|PR #727> merged ✅","ticket":"bumppy-requires-exactly-two-agents","owner":"nicktoper"}
{"id":"934defa2dde5","ts":"2026-09-01T17:16","project":"coga","kind":"done","detail":"auto-bumped: review → done — <https://github.com/FastJVM/coga/pull/724|PR #724> merged ✅","ticket":"fix-the-autofix-analyst","owner":"nicktoper"}
{"id":"59d6f5eb978f","ts":"2026-09-01T17:16","project":"coga","kind":"done","detail":"auto-bumped: review → done — <https://github.com/FastJVM/coga/pull/723|PR #723> merged ✅","ticket":"reconcile-recurring-wrapper-tty-admission-guidance","owner":"nicktoper"}
{"id":"b4599127c6a8","ts":"2026-09-01T17:16","project":"coga","kind":"done","detail":"auto-bumped: review → done — <https://github.com/FastJVM/coga/pull/726|PR #726> merged ✅","ticket":"rewrite-coga-base-prompt-and-agent-mode-block","owner":"nicktoper"}
{"id":"345a3fc92684","ts":"2026-09-01T17:16","project":"coga","kind":"done","detail":"auto-bumped: review → done — <https://github.com/FastJVM/coga/pull/729|PR #729> merged ✅","ticket":"select-session-conduct-instead-of-appending-a-cont","owner":"nicktoper"}
{"id":"4dca8e16207c","ts":"2026-09-01T17:16","project":"coga","kind":"done","detail":"auto-bumped: review → done — <https://github.com/FastJVM/coga/pull/731|PR #731> merged ✅","ticket":"unblock-rewind","owner":"nicktoper"}
{"id":"5593d0b1614f","ts":"2026-09-02T11:57","project":"coga","kind":"done","detail":"claude finished: sweep → done ✅","ticket":"recurring/branch-sweep","owner":"nicktoper"}
{"id":"23f7c213b1f6","ts":"2026-09-02T11:58","project":"coga","kind":"done","detail":"→ done (delegate: bootstrap/resolve-conflicts)","ticket":"recurring/resolve-conflicts","owner":"nicktoper"}
