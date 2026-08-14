---
slug: digest-can-clobber-recurring-last-serviced-period
title: Digest can clobber recurring last_serviced_period
status: canceled
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

It recurred in Magicator on 2026-08-13, this time as an unbounded loop rather
than a one-off: three consecutive `coga recurring` invocations each reported
`digest ... → launch` / `Replaced completed recurring/digest` and posted a
separate Slack digest (7, then 2, then 8 items). The template's git history
shows the two writers alternating on every cycle — a `recurring create` commit
adding `last_serviced_period: 2026-08-13` and the following digest `Sync coga
state` commit removing it. Each erasure sends `create_template` down the
prior-period branch (`recurring.py`: `done` and `not
_period_already_serviced`), which deletes the completed period task, recreates
it, and reruns the recipe. So the defect is not only a lost high-water mark: on
a template whose serviced-period line lands inside `### Digest State`, *every*
`coga recurring` reposts the digest.

Two consequences worth covering in the fix:

- The loop is silent. The scan table prints `ready` / `→ launch`, which is
  indistinguishable from a legitimate first firing, so nothing surfaces that
  the same period is being serviced repeatedly.
- The repeated same-period rewrites of the template blackboard are what the
  2026-08-13 run's committed conflict markers landed in (a single-parent
  `Sync coga state` commit carrying `<<<<<<<` / `=======` / `>>>>>>>` into
  `coga/recurring/digest/ticket.md`). With markers present, `_read_last_commit`
  returns the first `last_commit:` in the region — the older side — so the
  digest also re-reports an already-posted commit range. Whether the sync path
  should have refused to commit a conflicted tree is a separate defect; note it
  here so the two are not conflated.

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
