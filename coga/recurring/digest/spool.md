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










consumed_through: fd951ba8b086
{"id":"fd951ba8b086","ts":"2026-08-13T09:41","project":"coga","kind":"done","detail":"→ done (recipe: autoclose)","ticket":"recurring/autoclose-merged","owner":"nicktoper"}
{"id":"9bc506f4be1a","ts":"2026-08-13T09:41","project":"coga","kind":"done","detail":"→ done (recipe: digest)","ticket":"recurring/digest","owner":"nicktoper"}
{"id":"9dcc3202cdde","ts":"2026-08-13T10:09","project":"coga","kind":"done","detail":"claude finished: execute → done ✅ — Dream 2026-W33 complete: 4 PRs opened, 10 tickets direct-deleted, 1 draft ticket, 23 human-needed validation issues reported.","ticket":"recurring/dream","owner":"nicktoper"}
{"id":"ab63d154edb8","ts":"2026-08-13T11:21","project":"coga-v2-premise-dead-drafts","kind":"canceled","detail":"nicktoper canceled — Premise-dead: the ticket is entirely about the mode: frontmatter field (script/auto/interactive), which no longer exists. coga/recurring now documents the surviving constraint (agent work needs a TTY; recipes and complete scripts can be headless). Closing as the ticket's own text directs once the mode story landed.","ticket":"v2/document-interactive-recurring-sweep-hazard-in-rel","owner":"nicktoper"}
{"id":"621e6277d75f","ts":"2026-08-13T11:21","project":"coga-v2-premise-dead-drafts","kind":"canceled","detail":"nicktoper canceled — Premise-dead, and the rewrite condition is not met. The child mode:script orchestration shape it asks to canonize was deleted; Dream now invokes registered recipes directly from the parent task. The surviving phase-list shape has one consumer (Dream), which documents its own convention in its template, so it does not clear the reusable-pattern bar for coga/patterns. Re-open if a second maintenance loop ever needs the shape.","ticket":"v2/document-parent-orchestrates-child-script-tasks-pa","owner":"nicktoper"}
{"id":"5deefabc02e0","ts":"2026-08-13T17:22","project":"coga","kind":"canceled","detail":"nick canceled — Superseded by read-the-recurring-serviced-period-from-the-log-dr: the marker is being deleted rather than protected, so this ticket's scope (preserve last_serviced_period across digest writes) no longer describes the work.","ticket":"digest-can-clobber-recurring-last-serviced-period","owner":"nicktoper"}
{"id":"62de761ceb25","ts":"2026-08-14T10:57","project":"coga","kind":"done","detail":"auto-bumped: review → done — <https://github.com/FastJVM/coga/pull/686|PR #686> merged ✅","ticket":"decide-the-fate-of-two-premise-dead-v2-drafts-whos","owner":"nicktoper"}
{"id":"c28c79001c30","ts":"2026-08-14T10:57","project":"coga","kind":"done","detail":"auto-bumped: review → done — <https://github.com/FastJVM/coga/pull/685|PR #685> merged ✅","ticket":"important-alerts-the-task-owner-drop-important-rec","owner":"zach"}
{"id":"e096d8491349","ts":"2026-08-14T10:57","project":"coga","kind":"done","detail":"auto-bumped: review → done — <https://github.com/FastJVM/coga/pull/689|PR #689> merged ✅","ticket":"megalaunch-does-not-set-coga-expected-task","owner":"nicktoper"}
{"id":"f86ab1c1c51f","ts":"2026-08-14T10:57","project":"coga","kind":"done","detail":"auto-bumped: review → done — <https://github.com/FastJVM/coga/pull/677|PR #677> merged ✅","ticket":"process-pr-comments-during-review","owner":"nicktoper"}
{"id":"2935fb8c7128","ts":"2026-08-14T10:57","project":"coga","kind":"done","detail":"auto-bumped: review → done — <https://github.com/FastJVM/coga/pull/687|PR #687> merged ✅","ticket":"recurring-can-only-be-launched-by-owner","owner":"nicktoper"}
