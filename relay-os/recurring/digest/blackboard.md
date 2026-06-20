This blackboard is the **spool and git high-water state** for the daily Slack
digest.

Done outcomes and recurring scan errors append one JSONL record to the
`## Spool (pending)` section below as they happen (see `relay.notification.notify`).
The daily `relay digest` run combines those records with a git scan of
`origin/main`, posts one outcome-focused message to Slack, empties the spool
back to just the heading, and updates `### Digest State`. Everything here is
plain text in a git-tracked file on purpose — the pending queue and high-water
mark stay legible, never hidden state.

`relay recurring` keeps the serviced-period high-water mark here and append-only
human history in this template's `log.md` (never composed into a run, so it can
grow unbounded). The digest flush still parses only valid JSON records and
rewrites only the spool section, so any stray non-JSON line is left untouched.

last_serviced_period: 2026-06-17

### Digest State

last_commit: 8fe393be8ee3fd7f0e8b76ad237c144227baafa4
range: last 24h..8fe393b (123 commit(s), 16 reported)
posted: yes
## Spool (pending)












{"ts":"2026-06-18T14:53","project":"relay","kind":"done","detail":"→ done (script)","ticket":"dream-debug-validate-drift","owner":"nick"}
{"ts":"2026-06-18T15:13","project":"relay","kind":"done","detail":"→ done (script)","ticket":"dream-debug-cleanup-orphan-markers","owner":"nick"}
