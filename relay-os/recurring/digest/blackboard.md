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







[2026-06-06 09:24] scaffolded digest-2026-06-06
{"ts":"2026-06-06T14:47","project":"relay","kind":"done","detail":"→ done (script)","ticket":"digest-dbg-20260606T144723","owner":"nick"}
