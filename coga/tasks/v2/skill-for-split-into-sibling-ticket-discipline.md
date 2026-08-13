---
slug: v2/skill-for-split-into-sibling-ticket-discipline
title: Skill for split-into-sibling-ticket discipline
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
- coga/architecture
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
  - name: review
    skills: []
    assignee: owner
step: 1 (implement)
---

## Description

Surfaced by Dream W22 Phase 2 knowledge scan (G9).

The done `move-automerge-out-of-relay-status` ticket and its sibling
`remove-the-post-merge-automerge-git-hook` (since subsumed by the
standalone-automerge retirement) show a repeated
discipline: when a design grows beyond one PR's worth, the agent splits it
into ≥2 sibling tickets and records the split in the blackboard under a
`## Split` heading, cross-linking the siblings.

The `code/implement` and `code/design` skills both say "stop and split the
ticket on the blackboard" but neither defines the split mechanic — what
filename, what blackboard section, what cross-link convention, when to
sequence (`## Sequencing`) vs co-equal split.

Dream W31 in the Magicator repository exposed the complementary failure mode:
`code/implement` tells an agent to write a real adjacent bug on the source
ticket's blackboard for a follow-up rather than fix it opportunistically, but
no later step is required to carry that finding out. Four docs-migration
tickets followed that instruction. Their adjacent findings existed only in
the disposable source tickets until Dream rescued them immediately before
Retro deleted those tickets.

Planned decomposition and incidental findings are different decisions, but
they need the same durable carrier. Creating a draft records a finding; it does
not decide that the work should be scheduled. The owner can still reject or
cancel it later.

Draft outline:

- Open a packaged `code/split-ticket` skill (or extend `code/design` and
  `code/implement` with one shared "Splitting a ticket" contract).
- Bullets covering: when to split (PR too big, two concerns coupling); how
  (create sibling drafts, point at each other under `## Sequencing` /
  `## Split`); the cross-link convention.
- Define the adjacent-finding path: before the source ticket can reach review
  or be retired, every real out-of-scope finding must be copied into a draft
  ticket or an appropriate durable context. A PR-body note or source-ticket
  blackboard entry alone is not durable.
- Put the check at the narrowest reliable lifecycle point. Avoid making every
  reviewer re-audit arbitrary prose if a structured heading or Retro gate can
  carry the same contract legibly.
- Add fixtures covering both a planned multi-ticket split and an incidental
  adjacent bug whose source ticket is subsequently deleted.

### Acceptance criteria

- A source ticket can be deleted without deleting the only copy of an accepted
  adjacent finding.
- Sibling tasks are cross-linked and distinguish ordered sequencing from a
  co-equal split.
- Recording a draft does not silently activate it or take scheduling judgment
  away from the owner.
- The packaged and live copies of every changed workflow skill remain in sync.

## Context

- Magicator source finding:
  `coga/carry-adjacent-findings-out-of-a-ticket-before-it` (Dream 2026-W31).
- `src/coga/resources/templates/coga/bootstrap/skills/code/implement/SKILL.md`
  — current adjacent-bug instruction.
- `src/coga/resources/templates/coga/bootstrap/skills/retro/done-ticket/SKILL.md`
  — deletion boundary where uncopied blackboard findings disappear.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
