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












consumed_through: 2e975264dbe5
{"id":"2e975264dbe5","ts":"2026-08-17T14:25","project":"coga","kind":"done","detail":"→ done (recipe: autoclose)","ticket":"recurring/autoclose-merged","owner":"nicktoper"}
{"id":"8703372729a6","ts":"2026-08-17T14:25","project":"coga","kind":"done","detail":"→ done (recipe: digest)","ticket":"recurring/digest","owner":"nicktoper"}
{"id":"882857623215","ts":"2026-08-17T14:25","project":"coga","kind":"done","detail":"→ done (recipe: skill-update)","ticket":"recurring/skill-update","owner":"nicktoper"}
{"id":"7b171e3def41","ts":"2026-08-17T14:26","project":"coga","kind":"done","detail":"→ done (recipe: blocker-reminders)","ticket":"recurring/blocker-reminders","owner":"nicktoper"}
{"id":"1e5227f6db25","ts":"2026-08-17T14:55","project":"coga","kind":"done","detail":"claude finished: execute → done ✅ — Dream 2026-W34: 1 knowledge PR, 10 direct deletes, phases 2-3 human-needed.","ticket":"recurring/dream","owner":"nicktoper"}
{"id":"9938a767199c","ts":"2026-08-17T22:03","project":"coga","kind":"done","detail":"claude finished: execute → done ✅ — W33 sweep: delegated coga resolve-conflicts ran clean — 0 open PRs, nothing to rebase. Prior permission blocker did not recur.","ticket":"recurring/resolve-conflicts","owner":"nicktoper"}
{"id":"2aec4b7a4b90","ts":"2026-08-18T09:56","project":"coga","kind":"done","detail":"claude finished: execute → done ✅ — W34 sweep: delegated conflict resolver completed — 0 open PRs, no branches changed, no human attention needed.","ticket":"recurring/resolve-conflicts","owner":"nicktoper"}
{"id":"8b8272e83457","ts":"2026-08-18T09:57","project":"coga","kind":"done","detail":"auto-bumped: review → done — <https://github.com/FastJVM/coga/pull/694|PR #694> merged ✅","ticket":"autoclose-should-name-the-retire-follow-up","owner":"nicktoper"}
{"id":"c5f1ca951154","ts":"2026-08-18T09:57","project":"coga","kind":"done","detail":"auto-bumped: review → done — <https://github.com/FastJVM/coga/pull/697|PR #697> merged ✅","ticket":"recurring-last-serviced-period-compares-as-a-strin","owner":"nicktoper"}
{"id":"dc853bef99f4","ts":"2026-08-18T09:57","project":"coga","kind":"done","detail":"auto-bumped: review → done — <https://github.com/FastJVM/coga/pull/693|PR #693> merged ✅","ticket":"refuse-recurring-runs-from-a-non-control-branch","owner":"nick"}
{"id":"641c057f4b22","ts":"2026-08-18T09:57","project":"coga","kind":"done","detail":"auto-bumped: review → done — <https://github.com/FastJVM/coga/pull/691|PR #691> merged ✅","ticket":"remove-coga-build-and-project","owner":"nicktoper"}
{"id":"14221b28627a","ts":"2026-08-18T09:57","project":"coga","kind":"done","detail":"auto-bumped: review → done — <https://github.com/FastJVM/coga/pull/692|PR #692> merged ✅","ticket":"remove-legacy-config-compatibility-shims","owner":"nicktoper"}
{"id":"b3439355bbfb","ts":"2026-08-18T09:57","project":"coga","kind":"done","detail":"auto-bumped: review → done — <https://github.com/FastJVM/coga/pull/696|PR #696> merged ✅","ticket":"review-slack-channels","owner":"nicktoper"}
