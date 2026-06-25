---
name: digest/post
description: One-step script workflow that posts Done tickets plus other merged commits as one Slack digest.
steps:
  - name: flush
    skills:
      - relay/digest/flush
    assignee: agent
---

## flush

Script step. Runs `relay/digest/flush`, which calls `relay digest`: read the
unconsumed records from the dedicated `recurring/digest/spool.md` file, fetch
`origin/main`, render Done tickets plus an "Also merged (no ticket)" section,
post one message to the shared channel, drain the spool (advance the watermark +
trim the consumed prefix, keeping the newest record as an anchor), and update
the digest ticket's `### Digest State` high-water mark. The command posts nothing
only when there are no Done records, no recurring errors, and no post-filter new
commits.
