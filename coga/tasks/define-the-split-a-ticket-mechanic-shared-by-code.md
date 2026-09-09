---
slug: define-the-split-a-ticket-mechanic-shared-by-code
title: Define the split-a-ticket mechanic shared by code design and implement
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
secrets: null
step: 1 (implement)
---

## Description

`v2/skill-for-split-into-sibling-ticket-discipline` was raised by the Dream
W22 knowledge scan and re-raised from a different repo in Dream W31, and it is
still a parked `draft`. Half of it has since shipped without the draft being
updated: `retro/done-ticket/SKILL.md` now carries the adjacent-finding contract
end to end — an "Unresolved adjacent bugs" section, a disposition-table row, a
pre-deletion verification step, and a required report line — so a source ticket
can no longer be deleted as the only copy of an accepted adjacent finding.

The other half is untouched. `coga/skills/code/implement/SKILL.md` still says
only "If the work is too big for one PR, **stop and split the ticket** on the
blackboard", and `coga/skills/code/design/SKILL.md` only says "recommend a split
rather than writing a spec you know is oversized". Neither defines the mechanic,
and grepping the live and packaged skill trees finds no `## Split` or
`## Sequencing` heading convention anywhere.

So an agent told to split has no answer for what filename the siblings get,
which blackboard section records the split, how siblings cross-link, or how an
ordered sequence differs from a co-equal split — and every split invents its own
shape.

## Context

The fix is a short "Splitting a ticket" contract shared by `code/implement`
and `code/design`: sibling slug convention, one named blackboard heading, the
cross-link form, and the sequenced-versus-co-equal distinction. Both skills are
twin pairs — keep the live and packaged copies byte-identical.

Dispose of the parked draft as part of this: narrow
`v2/skill-for-split-into-sibling-ticket-discipline` to the split mechanic alone,
since its adjacent-finding acceptance criterion is already met, or cancel it
with a pointer to this ticket.

This also interacts with `ticket-relationships-and-ownership-have-no-mechani`
(ticket-to-ticket dependency ordering has no mechanism): an ordered split needs
a way to record the order. Decide whether the split contract adopts whatever
that ticket settles, or defines its own heading and stays prose-only.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
