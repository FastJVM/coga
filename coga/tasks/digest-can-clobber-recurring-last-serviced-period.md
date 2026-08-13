---
slug: digest-can-clobber-recurring-last-serviced-period
title: Digest can clobber recurring last_serviced_period
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
- coga/recurring
- coga/codebase
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills: []
    assignee: owner
secrets: null
step: 1 (implement)
---

## Description

The digest recipe can delete the recurring scheduler's
`last_serviced_period` high-water mark from the digest template blackboard.
That loses the scheduler's proof that the current period already ran and can
make a same-period recurring sweep fire the digest again.

The collision is structural:

1. `set_last_serviced_period_text` appends a missing
   `last_serviced_period: <key>` line at the end of the blackboard.
2. `_STATE_RE` in `commands/digest.py` treats `### Digest State` as extending
   until the next Markdown heading or EOF.
3. `_write_digest_state` replaces that entire match. On a freshly installed
   digest template, the scheduler-appended high-water line sits after the
   digest section with no intervening heading, so the replacement consumes it.

This happened in the Magicator repository on 2026-07-27. The run restored the
line by hand, but the same layout is reproducible from the packaged template:
the template starts without a serviced-period line and the first recurring
create appends it after `### Digest State`.

### Scope

- Make the digest state writer preserve every blackboard line it does not own,
  including `last_serviced_period`, regardless of whether that line appears
  before or after `### Digest State`.
- Keep recurring's high-water writer position-independent; do not rely on a
  one-time manual relocation in a live template.
- Add regressions for a newly materialized template, both relative orderings of
  the two state blocks, and repeated digest/recurring writes.
- Verify that a digest write followed by `read_last_serviced_period` returns the
  same period key.

### Acceptance criteria

- `_write_digest_state` changes only the digest-owned state.
- A successful digest cannot cause a current-period template to become due
  again.
- Existing digest state, recurring merge, and template-sync tests remain green.


## Context

- `src/coga/commands/digest.py` — `_STATE_RE` and `_write_digest_state`.
- `src/coga/recurring.py` — `set_last_serviced_period_text` and the recurring
  high-water read/write contract.
- `src/coga/resources/templates/coga/recurring/digest/ticket.md` — fresh
  template ordering that exposes the collision.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
