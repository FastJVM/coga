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

consumed_through:
{"id":"4008976124a6","ts":"2026-06-24T21:13","project":"relay","kind":"done","detail":"auto-bumped: review → done — <https://github.com/FastJVM/relay/pull/421|PR #421> merged ✅","ticket":"cli-extension-model/add-recurring-launch-aliases","owner":"nick"}
{"id":"0316d76d5e68","ts":"2026-06-24T21:13","project":"relay","kind":"done","detail":"auto-bumped: review → done — <https://github.com/FastJVM/relay/pull/418|PR #418> merged ✅","ticket":"fail-loud-on-unrecognized-config-sections-instead","owner":"nick"}
{"id":"8d451f8461dc","ts":"2026-06-24T21:13","project":"relay","kind":"done","detail":"auto-bumped: review → done — <https://github.com/FastJVM/relay/pull/423|PR #423> merged ✅","ticket":"finish-relay-ticket-greet-first-land-pr-417","owner":"zach"}
{"id":"fbe8eec40277","ts":"2026-06-24T21:13","project":"relay","kind":"done","detail":"auto-bumped: review → done — <https://github.com/FastJVM/relay/pull/436|PR #436> merged ✅","ticket":"fix-optioninfo-sentinel-crash-in-on-demand-recurri","owner":"nick"}
{"id":"13e6e459dddc","ts":"2026-06-24T21:13","project":"relay","kind":"done","detail":"auto-bumped: review → done — <https://github.com/FastJVM/relay/pull/422|PR #422> merged ✅","ticket":"marketing/relay-init-git-inits-a-fresh-dir","owner":"zach"}
{"id":"ebbbe8157484","ts":"2026-06-24T21:13","project":"relay","kind":"done","detail":"auto-bumped: review → done — <https://github.com/FastJVM/relay/pull/419|PR #419> merged ✅","ticket":"marketing/remove-relay-draft","owner":"zach"}
{"id":"2c1313039a54","ts":"2026-06-24T21:13","project":"relay","kind":"done","detail":"auto-bumped: review → done — <https://github.com/FastJVM/relay/pull/435|PR #435> merged ✅","ticket":"prevent-autostash-spool-conflicts-on-control-branc","owner":"nick"}
{"id":"ce6818fbc103","ts":"2026-06-24T21:16","project":"relay","kind":"done","detail":"nick finished: review → done ✅","ticket":"launch-prompt/improve-prompt-for-relay-launch","owner":"nick"}
