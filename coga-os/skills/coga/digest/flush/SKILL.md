---
name: coga/digest/flush
description: Post the daily Slack digest. Combines Done records from recurring/digest with a git scan of merged commits, posts one outcome-focused message, drains the spool, and records the high-water commit.
script: run.py
---

# Daily digest flush

This skill is the `mode: script` body of the `recurring/digest/` ticket. It
runs `coga digest`, which:

1. reads the JSONL Done/error records spooled under `## Spool (pending)` on the
   `recurring/digest/` blackboard,
2. fetches `origin/main` and scans commits since `### Digest State`
   `last_commit`,
3. renders Done tickets plus an "Also merged (no ticket)" section,
4. posts one sectioned message to the shared notification channel,
5. empties the spool section back to its seed, and
6. records the new high-water commit in `### Digest State`.

An empty spool can still post when commits merged since the last run. A quiet
run posts nothing only when there are no Done records, no recurring errors, and
no post-filter new commits. The flush honors the `[notification.slack].enabled = false`
opt-out exactly as a live post does (suppressed to stderr).

The script imports `coga.commands.digest.run_digest` and calls it directly, so
it does not depend on `coga` being on `PATH` inside the script environment.
