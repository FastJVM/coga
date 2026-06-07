This blackboard is the **spool** for the daily Slack digest.

Batchable state-change events append one JSONL record to the `## Spool
(pending)` section below as they happen (see `relay.slack.notify`). The daily
`relay digest` run drains that section, posts one grouped message to Slack, and
empties it back to just the heading. Everything here is plain text in a
git-tracked file on purpose — the pending queue stays legible, never hidden
state.

`relay recurring`'s period ledger lives in this template's `log.md` (never
composed into a run, so it can grow unbounded) — not here in the spool. The
digest flush still parses only valid JSON records and rewrites only the spool
section, so any stray non-JSON line is left untouched.

## Spool (pending)











{"ts":"2026-06-06T21:23","project":"relay","kind":"draft","detail":"created \"stop loading log in conetxt\" (draft)","ticket":"stop-loading-log-in-conetxt","owner":"nick"}
