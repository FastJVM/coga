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
{"ts":"2026-06-09T21:44","project":"relay","kind":"bump","detail":"claude advanced → step 2 (peer-review) → assigned to codex","ticket":"close-imported-skill-provenance-conflict-and-dream","owner":"nick"}
{"ts":"2026-06-09T21:51","project":"relay","kind":"bump","detail":"codex advanced → step 3 (open-pr) → assigned to claude — Peer review fix committed: 59f3721; tests green.","ticket":"close-imported-skill-provenance-conflict-and-dream","owner":"nick"}
{"ts":"2026-06-09T21:52","project":"relay","kind":"bump","detail":"claude advanced → step 4 (review) → assigned to nick — PR opened: https://github.com/FastJVM/relay/pull/329","ticket":"close-imported-skill-provenance-conflict-and-dream","owner":"nick"}
{"ts":"2026-06-10T05:53","project":"relay","kind":"active","detail":"→ active — assignee nick (auto on launch)","ticket":"slack-webhook-is-env-only-despite-toml-comment-imp","owner":"nick"}
{"ts":"2026-06-10T06:15","project":"relay","kind":"bump","detail":"claude advanced → step 2 (peer-review) → assigned to codex","ticket":"slack-webhook-is-env-only-despite-toml-comment-imp","owner":"nick"}
{"ts":"2026-06-10T09:05","project":"relay","kind":"bump","detail":"codex advanced → step 3 (open-pr) → assigned to claude","ticket":"slack-webhook-is-env-only-despite-toml-comment-imp","owner":"nick"}
{"ts":"2026-06-10T09:07","project":"relay","kind":"bump","detail":"claude advanced → step 4 (review) → assigned to nick — PR opened: https://github.com/FastJVM/relay/pull/330","ticket":"slack-webhook-is-env-only-despite-toml-comment-imp","owner":"nick"}
{"ts":"2026-06-10T11:19","project":"relay","kind":"done","detail":"auto-bumped on merge of PR #329 ✅","ticket":"close-imported-skill-provenance-conflict-and-dream","owner":"nick"}
{"ts":"2026-06-10T11:19","project":"relay","kind":"done","detail":"auto-bumped on merge of PR #330 ✅","ticket":"slack-webhook-is-env-only-despite-toml-comment-imp","owner":"nick"}
{"ts":"2026-06-10T11:25","project":"relay","kind":"active","detail":"→ active — assignee claude","ticket":"add-dev-unit-test-writing-skill","owner":"nick"}
{"ts":"2026-06-10T11:25","project":"relay","kind":"done","detail":"claude finished → done ✅","ticket":"add-dev-unit-test-writing-skill","owner":"nick"}
{"ts":"2026-06-09T21:26","project":"relay","kind":"draft","detail":"created \"Represent autonomy tier in ticket mode field\" (draft)","ticket":"represent-autonomy-tier-in-ticket-mode-field","owner":"nick"}
{"ts":"2026-06-09T21:31","project":"relay","kind":"active","detail":"→ active — assignee claude (auto on launch)","ticket":"wire-autonomy-triage-into-impl-ready-workflows","owner":"nick"}
{"ts":"2026-06-09T21:36","project":"relay","kind":"bump","detail":"claude advanced → step 2 (review-design) → assigned to nick","ticket":"wire-autonomy-triage-into-impl-ready-workflows","owner":"nick"}
{"ts":"2026-06-09T21:36","project":"relay","kind":"bump","detail":"nick advanced → step 3 (implement) → assigned to claude","ticket":"wire-autonomy-triage-into-impl-ready-workflows","owner":"nick"}
{"ts":"2026-06-09T21:42","project":"relay","kind":"bump","detail":"claude advanced → step 4 (open-pr)","ticket":"wire-autonomy-triage-into-impl-ready-workflows","owner":"nick"}
{"ts":"2026-06-09T21:43","project":"relay","kind":"bump","detail":"claude advanced → step 5 (review) → assigned to nick — PR opened: https://github.com/FastJVM/relay/pull/328","ticket":"wire-autonomy-triage-into-impl-ready-workflows","owner":"nick"}
{"ts":"2026-06-09T21:46","project":"relay","kind":"done","detail":"auto-bumped on merge of PR #327 ✅","ticket":"add-dream-skill-update-maintenance-phase","owner":"nick"}
{"ts":"2026-06-09T22:19","project":"relay","kind":"active","detail":"→ active — assignee claude","ticket":"lift-dream-subagent-scan-contract-into-reusable-sk","owner":"nick"}
{"ts":"2026-06-10T05:56","project":"relay","kind":"bump","detail":"codex advanced → step 2 (peer-review) → assigned to claude","ticket":"lift-dream-subagent-scan-contract-into-reusable-sk","owner":"nick"}
{"ts":"2026-06-10T11:18","project":"relay","kind":"draft","detail":"created \"autoclose merged\" (draft)","ticket":"autoclose-merged","owner":"nick"}
{"ts":"2026-06-10T11:35","project":"relay","kind":"active","detail":"→ active — assignee claude","ticket":"add-bootstrap-skill-for-importing-external-skills","owner":"nick"}
{"ts":"2026-06-10T11:40","project":"relay","kind":"draft","detail":"created \"Detect missing skills\" (draft)","ticket":"detect-missing-skills","owner":"nick"}
{"ts":"2026-06-10T14:46","project":"relay","kind":"draft","detail":"created \"Add relay skill search with candidate eval\" (draft)","ticket":"add-relay-skill-search-with-candidate-eval","owner":"nick"}
{"ts":"2026-06-10T11:42","project":"relay","kind":"active","detail":"→ active — assignee nick","ticket":"install-init-skills-via-skill-downloader","owner":"nick"}
{"ts":"2026-06-10T15:09","project":"relay","kind":"bump","detail":"codex advanced → step 2 (peer-review) → assigned to claude","ticket":"install-init-skills-via-skill-downloader","owner":"nick"}
{"ts":"2026-06-10T15:09","project":"relay","kind":"draft","detail":"created \"autocleanup worktree/branche\" (draft)","ticket":"autocleanup-worktree-branche","owner":"nick"}
{"ts":"2026-06-10T15:23","project":"relay","kind":"bump","detail":"claude advanced → step 3 (open-pr) → assigned to codex","ticket":"install-init-skills-via-skill-downloader","owner":"nick"}
{"ts":"2026-06-10T15:24","project":"relay","kind":"bump","detail":"claude advanced → step 3 (open-pr) → assigned to codex","ticket":"lift-dream-subagent-scan-contract-into-reusable-sk","owner":"nick"}
{"ts":"2026-06-10T15:24","project":"relay","kind":"bump","detail":"codex advanced → step 4 (review) → assigned to nick","ticket":"lift-dream-subagent-scan-contract-into-reusable-sk","owner":"nick"}
{"ts":"2026-06-10T15:25","project":"relay","kind":"bump","detail":"codex advanced → step 4 (review) → assigned to nick","ticket":"install-init-skills-via-skill-downloader","owner":"nick"}
{"ts":"2026-06-10T15:32","project":"relay","kind":"done","detail":"nick finished → done ✅","ticket":"lift-dream-subagent-scan-contract-into-reusable-sk","owner":"nick"}
{"ts":"2026-06-10T15:35","project":"relay","kind":"done","detail":"nick finished → done ✅","ticket":"install-init-skills-via-skill-downloader","owner":"nick"}
{"ts":"2026-06-10T15:41","project":"relay","kind":"active","detail":"→ active — assignee claude","ticket":"add-dev-testing-setup-skill","owner":"nick"}
{"ts":"2026-06-09T15:51","project":"relay","kind":"draft","detail":"created \"Document untrusted-tool-output verify-through-ground-truth agent discipline\" (draft)","ticket":"document-untrusted-tool-output-verify-through-grou","owner":"nick"}
{"ts":"2026-06-09T15:51","project":"relay","kind":"draft","detail":"created \"Exclude dev-tree agent-skill symlink views from the wheel build\" (draft)","ticket":"exclude-dev-tree-agent-skill-symlink-views-from-th","owner":"nick"}
{"ts":"2026-06-09T15:52","project":"relay","kind":"draft","detail":"created \"Dream dbg cleanup-orphan-markers\" (draft)","ticket":"dream-dbg-cleanup-orphan-markers","owner":"nick"}
{"ts":"2026-06-09T15:52","project":"relay","kind":"active","detail":"→ active — assignee claude","ticket":"dream-dbg-cleanup-orphan-markers","owner":"nick"}
{"ts":"2026-06-09T15:52","project":"relay","kind":"done","detail":"→ done (script)","ticket":"dream-dbg-cleanup-orphan-markers","owner":"nick"}
{"ts":"2026-06-09T16:31","project":"relay","kind":"draft","detail":"created \"Recurring sweep runs Dream cleanup phase last and consolidates ticket deletion\" (draft)","ticket":"recurring-sweep-runs-dream-cleanup-phase-last-and","owner":"nick"}
{"ts":"2026-06-09T16:45","project":"relay","kind":"active","detail":"→ active — assignee claude","ticket":"recurring-sweep-runs-dream-cleanup-phase-last-and","owner":"nick"}
{"ts":"2026-06-11T11:59","project":"relay","kind":"active","detail":"→ active — assignee claude","ticket":"post-slack-notification-on-mode-script-failures","owner":"nick"}
{"ts":"2026-06-11T11:59","project":"relay","kind":"done","detail":"claude finished → done ✅","ticket":"post-slack-notification-on-mode-script-failures","owner":"nick"}
