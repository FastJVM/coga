This blackboard is the **spool** for the daily Slack digest.

Batchable state-change events append one JSONL record to the `## Spool
(pending)` section below as they happen (see `relay.slack.notify`). The daily
`relay digest` run drains that section, posts one grouped message to Slack, and
empties it back to just the heading. Everything here is plain text in a
git-tracked file on purpose — the pending queue stays legible, never hidden
state.

`relay recurring` also appends one `scaffolded …` ledger line per period below
the spool section (its period ledger); the digest flush parses only valid JSON
records and rewrites only the spool section, so those ledger lines are left
untouched.

## Spool (pending)











{"ts":"2026-06-06T20:45","project":"relay","kind":"done","detail":"→ done (script)","ticket":"digest-dbg-20260606T204523","owner":"nick"}
{"ts":"2026-06-06T20:48","project":"relay","kind":"draft","detail":"created \"Dream validate-drift child of dream-dbg-20260606T204523\" (draft)","ticket":"dream-validate-drift-child-of-dream-dbg-20260606t2","owner":"nick"}
{"ts":"2026-06-06T20:48","project":"relay","kind":"active","detail":"→ active — assignee claude","ticket":"dream-validate-drift-child-of-dream-dbg-20260606t2","owner":"nick"}
{"ts":"2026-06-06T20:48","project":"relay","kind":"done","detail":"→ done (script)","ticket":"dream-validate-drift-child-of-dream-dbg-20260606t2","owner":"nick"}
{"ts":"2026-06-06T20:58","project":"relay","kind":"draft","detail":"created \"Dream cleanup-orphan-markers child of dream-dbg-20260606T204523\" (draft)","ticket":"dream-cleanup-orphan-markers-child-of-dream-dbg-20","owner":"nick"}
{"ts":"2026-06-06T20:58","project":"relay","kind":"active","detail":"→ active — assignee claude","ticket":"dream-cleanup-orphan-markers-child-of-dream-dbg-20","owner":"nick"}
{"ts":"2026-06-06T20:58","project":"relay","kind":"done","detail":"→ done (script)","ticket":"dream-cleanup-orphan-markers-child-of-dream-dbg-20","owner":"nick"}
{"ts":"2026-06-06T21:03","project":"relay","kind":"done","detail":"claude finished → done ✅","ticket":"dream-dbg-20260606T204523","owner":"nick"}
{"ts":"2026-06-06T21:06","project":"relay","kind":"done","detail":"claude finished → done ✅","ticket":"relay-dev-update-dbg-20260606T204523","owner":"nick"}
{"ts":"2026-06-06T21:23","project":"relay","kind":"draft","detail":"created \"stop loading log in conetxt\" (draft)","ticket":"stop-loading-log-in-conetxt","owner":"nick"}
