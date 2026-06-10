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
{"ts":"2026-06-09T16:00","project":"relay","kind":"done","detail":"auto-bumped on merge of PR #322 ✅","ticket":"dream-sweeps-done-recurring-period-tickets","owner":"nick"}
{"ts":"2026-06-09T16:00","project":"relay","kind":"done","detail":"auto-bumped on merge of PR #321 ✅","ticket":"rewrite-slack-messages","owner":"nick"}
{"ts":"2026-06-09T16:23","project":"relay","kind":"draft","detail":"created \"Close imported-skill provenance, conflict, and Dream-update gaps\" (draft)","ticket":"close-imported-skill-provenance-conflict-and-dream","owner":"nick"}
{"ts":"2026-06-09T16:29","project":"relay","kind":"draft","detail":"created \"Add Dream skill-update maintenance phase\" (draft)","ticket":"add-dream-skill-update-maintenance-phase","owner":"nick"}
{"ts":"2026-06-09T16:32","project":"relay","kind":"active","detail":"→ active — assignee claude","ticket":"close-imported-skill-provenance-conflict-and-dream","owner":"nick"}
{"ts":"2026-06-09T16:33","project":"relay","kind":"active","detail":"→ active — assignee claude","ticket":"add-dream-skill-update-maintenance-phase","owner":"nick"}
{"ts":"2026-06-09T18:14","project":"relay","kind":"bump","detail":"claude advanced → step 2 (peer-review) → assigned to codex — implement done: Dream sorts last in recurring sweep (branch dream-runs-last); 610 tests pass","ticket":"recurring-sweep-runs-dream-cleanup-phase-last-and","owner":"nick"}
{"ts":"2026-06-09T18:26","project":"relay","kind":"bump","detail":"codex advanced: peer-review → open-pr (step 3/4) → assigned to claude — Peer review clean; tests: 610 passed, 1 skipped","ticket":"recurring-sweep-runs-dream-cleanup-phase-last-and","owner":"nick"}
{"ts":"2026-06-09T18:27","project":"relay","kind":"bump","detail":"claude advanced → step 4 (review) → assigned to nick — PR opened: https://github.com/FastJVM/relay/pull/326","ticket":"recurring-sweep-runs-dream-cleanup-phase-last-and","owner":"nick"}
{"ts":"2026-06-09T18:31","project":"relay","kind":"done","detail":"auto-bumped on merge of PR #326 ✅","ticket":"recurring-sweep-runs-dream-cleanup-phase-last-and","owner":"nick"}
{"ts":"2026-06-09T19:57","project":"relay","kind":"bump","detail":"claude advanced → step 2 (peer-review) → assigned to codex","ticket":"add-dream-skill-update-maintenance-phase","owner":"nick"}
{"ts":"2026-06-09T20:50","project":"relay","kind":"bump","detail":"codex advanced: peer-review → open-pr (step 3/4) → assigned to claude","ticket":"add-dream-skill-update-maintenance-phase","owner":"nick"}
{"ts":"2026-06-09T20:51","project":"relay","kind":"bump","detail":"claude advanced → step 4 (review) → assigned to nick — PR opened: https://github.com/FastJVM/relay/pull/327","ticket":"add-dream-skill-update-maintenance-phase","owner":"nick"}
