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











consumed_through: ab124db01254
{"id":"ab124db01254","ts":"2026-08-14T10:58","project":"coga","kind":"done","detail":"→ done (recipe: autoclose)","ticket":"recurring/autoclose-merged","owner":"nicktoper"}
{"id":"ef7ff56aca26","ts":"2026-08-14T10:59","project":"coga","kind":"done","detail":"→ done (recipe: digest)","ticket":"recurring/digest","owner":"nicktoper"}
{"id":"edae68bf07bc","ts":"2026-08-14T10:59","project":"coga","kind":"done","detail":"→ done (recipe: blocker-reminders)","ticket":"recurring/blocker-reminders","owner":"nicktoper"}
consumed_through: fd951ba8b086
{"id":"fd951ba8b086","ts":"2026-08-13T09:41","project":"coga","kind":"done","detail":"→ done (recipe: autoclose)","ticket":"recurring/autoclose-merged","owner":"nicktoper"}
{"id":"9bc506f4be1a","ts":"2026-08-13T09:41","project":"coga","kind":"done","detail":"→ done (recipe: digest)","ticket":"recurring/digest","owner":"nicktoper"}
{"id":"9dcc3202cdde","ts":"2026-08-13T10:09","project":"coga","kind":"done","detail":"claude finished: execute → done ✅ — Dream 2026-W33 complete: 4 PRs opened, 10 tickets direct-deleted, 1 draft ticket, 23 human-needed validation issues reported.","ticket":"recurring/dream","owner":"nicktoper"}
{"id":"ab63d154edb8","ts":"2026-08-13T11:21","project":"coga-v2-premise-dead-drafts","kind":"canceled","detail":"nicktoper canceled — Premise-dead: the ticket is entirely about the mode: frontmatter field (script/auto/interactive), which no longer exists. coga/recurring now documents the surviving constraint (agent work needs a TTY; recipes and complete scripts can be headless). Closing as the ticket's own text directs once the mode story landed.","ticket":"v2/document-interactive-recurring-sweep-hazard-in-rel","owner":"nicktoper"}
{"id":"621e6277d75f","ts":"2026-08-13T11:21","project":"coga-v2-premise-dead-drafts","kind":"canceled","detail":"nicktoper canceled — Premise-dead, and the rewrite condition is not met. The child mode:script orchestration shape it asks to canonize was deleted; Dream now invokes registered recipes directly from the parent task. The surviving phase-list shape has one consumer (Dream), which documents its own convention in its template, so it does not clear the reusable-pattern bar for coga/patterns. Re-open if a second maintenance loop ever needs the shape.","ticket":"v2/document-parent-orchestrates-child-script-tasks-pa","owner":"nicktoper"}
{"id":"5deefabc02e0","ts":"2026-08-13T17:22","project":"coga","kind":"canceled","detail":"nick canceled — Superseded by read-the-recurring-serviced-period-from-the-log-dr: the marker is being deleted rather than protected, so this ticket's scope (preserve last_serviced_period across digest writes) no longer describes the work.","ticket":"digest-can-clobber-recurring-last-serviced-period","owner":"nicktoper"}
{"id":"c0f9d62e7a4b","ts":"2026-08-14T10:56","project":"coga","kind":"done","detail":"codex finished: execute → done ✅ — Prior retirement already direct-deleted in bc94a150, no durable knowledge; owner confirmed no Retro rerun.","ticket":"retire-coga-important-support-second-webhook","owner":"zach"}
