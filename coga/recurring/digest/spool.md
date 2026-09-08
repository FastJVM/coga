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
{"id":"332482a269b0","ts":"2026-09-08T16:49","project":"coga","kind":"done","detail":"auto-bumped: review → done — <https://github.com/FastJVM/coga/pull/757|PR #757> merged ✅","ticket":"carry-adjacent-bugs-out-of-a-blackboard-before-ret","owner":"nicktoper"}
{"id":"46db438650f3","ts":"2026-09-08T16:49","project":"coga","kind":"done","detail":"auto-bumped: review → done — <https://github.com/FastJVM/coga/pull/759|PR #759> merged ✅","ticket":"cleanup/add-a-debug-mode-to-init-for-vendoring-from-source","owner":"nicktoper"}
{"id":"b705efce8224","ts":"2026-09-08T16:49","project":"coga","kind":"done","detail":"auto-bumped: review → done — <https://github.com/FastJVM/coga/pull/753|PR #753> merged ✅","ticket":"cleanup/detect-the-current-git-branch-instead-of-hard-codi","owner":"nicktoper"}
{"id":"fb3c6fda4791","ts":"2026-09-08T16:49","project":"coga","kind":"done","detail":"auto-bumped: review → done — <https://github.com/FastJVM/coga/pull/756|PR #756> merged ✅","ticket":"dream-reconciliation-must-count-distinct-shard-ids","owner":"nicktoper"}
{"id":"c113dfa77061","ts":"2026-09-08T16:49","project":"coga","kind":"done","detail":"auto-bumped: review → done — <https://github.com/FastJVM/coga/pull/755|PR #755> merged ✅","ticket":"give-a-ticket-s-superseded-design-one-documented-h","owner":"nicktoper"}
{"id":"931740c6b437","ts":"2026-09-08T16:49","project":"coga","kind":"done","detail":"auto-bumped: review → done — <https://github.com/FastJVM/coga/pull/748|PR #748> merged ✅","ticket":"launch-activates-before-preflight","owner":"nicktoper"}
{"id":"5ee5778c3c45","ts":"2026-09-08T16:49","project":"coga","kind":"done","detail":"auto-bumped: review → done — <https://github.com/FastJVM/coga/pull/758|PR #758> merged ✅","ticket":"live-and-packaged-twin-pairs-are-edited-together-b","owner":"nicktoper"}
{"id":"5518c4fdf427","ts":"2026-09-08T16:49","project":"coga","kind":"done","detail":"auto-bumped: review → done — <https://github.com/FastJVM/coga/pull/747|PR #747> merged ✅","ticket":"megalaunch-activates-picks-before-preflight","owner":"nicktoper"}
{"id":"562286521454","ts":"2026-09-08T16:49","project":"coga","kind":"done","detail":"auto-bumped: review → done — <https://github.com/FastJVM/coga/pull/754|PR #754> merged ✅","ticket":"no-comms-writing-skill-the-process-is-smeared-thro","owner":"nicktoper"}
{"id":"76f0e846690d","ts":"2026-09-08T16:49","project":"coga","kind":"done","detail":"auto-bumped: review → done — <https://github.com/FastJVM/coga/pull/752|PR #752> merged ✅","ticket":"no-skill-exists-for-the-cold-evaluator-review-of-a","owner":"nicktoper"}
{"id":"c36cc0b0efbb","ts":"2026-09-08T16:50","project":"coga","kind":"done","detail":"auto-bumped: review → done — <https://github.com/FastJVM/coga/pull/750|PR #750> merged ✅","ticket":"packaged-repos-ship-recurring-templates-without-th","owner":"nicktoper"}
{"id":"469f5dcc4c29","ts":"2026-09-08T16:50","project":"coga","kind":"done","detail":"auto-bumped: review → done — <https://github.com/FastJVM/coga/pull/751|PR #751> merged ✅","ticket":"retire-never-removes-a-worktree-that-ran-the-tests","owner":"nicktoper"}
{"id":"d77dc7b5b1b9","ts":"2026-09-08T16:50","project":"coga","kind":"done","detail":"auto-bumped: review → done — <https://github.com/FastJVM/coga/pull/749|PR #749> merged ✅","ticket":"service-recurring-from-a-temp-control-worktree-ins","owner":"nicktoper"}
{"id":"f5339d021849","ts":"2026-09-08T16:50","project":"coga","kind":"done","detail":"claude finished: sweep → done ✅","ticket":"recurring/autoclose-merged","owner":"nicktoper"}
