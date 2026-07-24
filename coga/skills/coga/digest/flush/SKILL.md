---
name: coga/digest/flush
description: Post the daily Slack digest. Combines Done/Canceled records from the recurring/digest spool with a git scan of merged commits, posts one outcome-focused message, drains the spool, and records the high-water commit.
---

# Daily digest flush

This skill documents the `digest` recipe used by the `recurring/digest/`
ticket. Run it with `coga run digest`; it:

1. reads the unconsumed JSONL Done/Canceled/error records from the dedicated
   `recurring/digest/spool.md` file's `## Spool (pending)` section (de-duping
   the same event recorded by two clones),
2. fetches `origin/main` and scans commits since `### Digest State`
   `last_commit`,
3. renders Done tickets, Canceled tickets, and an "Also merged (no ticket)"
   section,
4. posts one sectioned message to the shared notification channel,
5. drains the spool — advances the `consumed_through` watermark and trims the
   consumed prefix, keeping the newest record as an anchor (so a concurrent
   producer append never conflicts), and
6. records the new high-water commit in the digest ticket's `### Digest State`.

An empty spool can still post when commits merged since the last run. A quiet
run posts nothing only when there are no Done records, no Canceled records, no
recurring errors, and no post-filter new commits. The flush honors the
`[notification.slack].enabled = false` opt-out exactly as a live post does
(suppressed to stderr).
