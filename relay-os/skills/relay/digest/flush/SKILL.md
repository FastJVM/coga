---
name: relay/digest/flush
description: Flush the daily-digest spool into one Slack post. Drains the recurring/digest blackboard, renders project → person → ticket, posts via the webhook, and empties the spool.
script: run.py
---

# Daily digest flush

This skill is the `mode: script` body of the `recurring/digest/` ticket. It
runs `relay digest`, which:

1. drains the JSONL records spooled under `## Spool (pending)` on the
   `recurring/digest/` blackboard,
2. groups them **project → person → ticket** (owners pinged via `<@ID>`,
   watchers cc'd),
3. posts one sectioned message to the shared Slack channel, and
4. empties the spool section back to its seed.

An empty spool is a silent no-op, so a quiet day or a same-day re-run posts
nothing. The flush honors the `[slack].enabled = false` opt-out exactly as a
live post does (suppressed to stderr).

The script imports `relay.commands.digest.run_digest` and calls it directly, so
it does not depend on `relay` being on `PATH` inside the script environment.
