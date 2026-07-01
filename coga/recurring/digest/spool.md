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


consumed_through: b4ce33110eaf
{"id":"b4ce33110eaf","ts":"2026-06-29T22:35","project":"coga","kind":"done","detail":"→ done (script)","ticket":"recurring/autoclose-merged","owner":"nick"}
{"id":"dfeadcb6d530","ts":"2026-06-29T22:35","project":"coga","kind":"done","detail":"→ done (script)","ticket":"recurring/digest","owner":"nick"}
{"id":"88272b0eb871","ts":"2026-06-29T22:35","project":"coga","kind":"done","detail":"→ done (script)","ticket":"recurring/skill-update","owner":"nicktoper"}
{"id":"aa970d166610","ts":"2026-06-29T22:41","project":"coga","kind":"done","detail":"→ done (script)","ticket":"dream-validate-drift-w27","owner":"nicktoper"}
{"id":"1fed8b7f4520","ts":"2026-06-30T00:03","project":"coga","kind":"recurring-error","detail":"→ paused (timeout) — liveness watchdog: REPL timed out before signalling done","ticket":"recurring/dream","owner":"nicktoper"}
{"id":"8a41d5cf7c83","ts":"2026-06-30T11:12","project":"coga","kind":"done","detail":"claude finished: execute → done ✅","ticket":"recurring/dream","owner":"nicktoper"}
consumed_through:
{"id":"4008976124a6","ts":"2026-06-24T21:13","project":"relay","kind":"done","detail":"auto-bumped: review → done — <https://github.com/FastJVM/relay/pull/421|PR #421> merged ✅","ticket":"cli-extension-model/add-recurring-launch-aliases","owner":"nick"}
{"id":"0316d76d5e68","ts":"2026-06-24T21:13","project":"relay","kind":"done","detail":"auto-bumped: review → done — <https://github.com/FastJVM/relay/pull/418|PR #418> merged ✅","ticket":"fail-loud-on-unrecognized-config-sections-instead","owner":"nick"}
{"id":"8d451f8461dc","ts":"2026-06-24T21:13","project":"relay","kind":"done","detail":"auto-bumped: review → done — <https://github.com/FastJVM/relay/pull/423|PR #423> merged ✅","ticket":"finish-relay-ticket-greet-first-land-pr-417","owner":"zach"}
{"id":"fbe8eec40277","ts":"2026-06-24T21:13","project":"relay","kind":"done","detail":"auto-bumped: review → done — <https://github.com/FastJVM/relay/pull/436|PR #436> merged ✅","ticket":"fix-optioninfo-sentinel-crash-in-on-demand-recurri","owner":"nick"}
{"id":"13e6e459dddc","ts":"2026-06-24T21:13","project":"relay","kind":"done","detail":"auto-bumped: review → done — <https://github.com/FastJVM/relay/pull/422|PR #422> merged ✅","ticket":"marketing/relay-init-git-inits-a-fresh-dir","owner":"zach"}
{"id":"ebbbe8157484","ts":"2026-06-24T21:13","project":"relay","kind":"done","detail":"auto-bumped: review → done — <https://github.com/FastJVM/relay/pull/419|PR #419> merged ✅","ticket":"marketing/remove-relay-draft","owner":"zach"}
{"id":"2c1313039a54","ts":"2026-06-24T21:13","project":"relay","kind":"done","detail":"auto-bumped: review → done — <https://github.com/FastJVM/relay/pull/435|PR #435> merged ✅","ticket":"prevent-autostash-spool-conflicts-on-control-branc","owner":"nick"}
{"id":"ce6818fbc103","ts":"2026-06-24T21:16","project":"relay","kind":"done","detail":"nick finished: review → done ✅","ticket":"launch-prompt/improve-prompt-for-relay-launch","owner":"nick"}
{"id":"2c94fecc9572","ts":"2026-06-26T20:50","project":"coga","kind":"done","detail":"nick finished: implement → done ✅ — stale migrated task state closed; implementation already merged and live status filtering verified","ticket":"filter-relay-status-by-directory-group","owner":"nick"}
{"id":"2f23bc9129d4","ts":"2026-06-29T15:21","project":"coga","kind":"done","detail":"nick finished: review → done ✅ — Closed after owner review: superseded implementation PR was closed; no revised implementation PR exists.","ticket":"block-unblock-and-megalaunch","owner":"nick"}
{"id":"73dfefc4f19a","ts":"2026-06-30T14:39","project":"coga","kind":"done","detail":"nick finished: review → done ✅","ticket":"trim-blackboard-eval-once-processed","owner":"nick"}
{"id":"4c4b59bc5219","ts":"2026-06-30T14:42","project":"coga","kind":"done","detail":"nick finished: design → done ✅ — Closed stale Coga copy: Relay PR #328 already shipped; no Coga implementation needed.","ticket":"wire-autonomy-triage-into-impl-ready-workflows","owner":"nick"}
{"id":"68f09c0dede9","ts":"2026-07-01T08:58","project":"coga","kind":"done","detail":"zach finished: review → done ✅","ticket":"add-coga-ticket-existing-slug-scan","owner":"zach"}
