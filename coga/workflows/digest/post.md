---
name: digest/post
description: One-step lifecycle for the digest recurring task's deterministic half.
steps:
  - name: flush
    skills:
      - coga/digest/flush
    assignee: agent
---

## flush

Script-backed recurring task. `coga launch` runs the period task's reserved
`ticket.py`: read the unconsumed Done/Canceled/error records from the dedicated
`recurring/digest/spool.md` file, fetch `origin/main`, render Done tickets,
Canceled tickets, and an "Also merged (no ticket)" section, post one message to
the shared channel, drain the spool (advance the watermark + trim the consumed
prefix, keeping the newest record as an anchor), and update the digest ticket's
`### Digest State` high-water mark. The command posts nothing only when there
are no Done records, no Canceled records, no recurring errors, and no post-filter
new commits.
