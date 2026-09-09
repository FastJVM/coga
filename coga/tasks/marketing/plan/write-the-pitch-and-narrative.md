---
slug: marketing/plan/write-the-pitch-and-narrative
title: Write the pitch and narrative
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
  - marketing/positioning
skills: []
workflow: draft-for-human
secrets: null
---

## Description

Write the reusable Coga pitch and a short narrative from the reviewed public
examples. Lead with the owner's direction: Coga makes the intent, instructions,
knowledge and working state behind an AI session explicit and editable.
Explain the experience through a real piece of work before introducing the
company-OS category or the parallel queue.

Produce one short pitch, a narrative outline with source links, and a mapping
from the supported message to the existing launch deliverables. The owner
reviews the wording before it becomes canonical marketing copy.

## Context

### Dependency and sources

The reviewed packet from
`marketing/plan/collect-public-examples-for-the-launch` is the prerequisite
for final narrative claims. Its durable output is
`coga/contexts/marketing/positioning/examples.md`. If that file is absent,
or a needed example is still unaccepted, record the specific dependency under
the session's conduct; do not manufacture an example. The source collector can
report an honest shortfall, in which case narrow the narrative accordingly.

`marketing/positioning` supplies the full audience, voice, ownership spine
and limits. `marketing/map` locates the strategic sources and the newer
owner decision in the documentation-reorganization ticket. Read only the
retained message briefs and phase constraints needed from `marketing/plan`;
channel/account mechanics belong to `marketing/distribution`.

### Deliverable and acceptance

Draft on this blackboard:

1. A one-sentence pitch and a short expansion that explain what the reader can
   do with Coga, for whom, and why managing the inputs changes the interaction.
2. A narrative outline from rough intent through execution and correction to
   later reuse, with each claimed event linked to an accepted public example.
3. A compact source-to-claim table: what is observed, what is interpretation,
   what is the founder's thesis, and what must be conceded or omitted.
4. A proposed mapping to the README and retained three essay tickets,
   identifying repetition or unsupported angles for the owner's keep/drop
   decision in `marketing/build-the-launch-plan`.

Draft for a technically capable reader without assuming the Pirsig/Lisp
reading list. Make ownership concrete in the opening: the maintained material
is in files the reader can inspect and edit. Preserve the personal internal-tool,
open-source posture; avoid claims of historical priority or universal benefit.
Use the relevant `clarity` review guidance for the short copy, without running
the post-publication workflow.

The owner chooses and edits the wording at step 2. At step 3, put the accepted
pitch and narrative in `marketing/positioning`, linking the source packet,
and hand the deliverable mapping to `marketing/build-the-launch-plan`.
Do not leave the reusable message only on a task blackboard.

### Boundaries

This ticket prepares the message. The existing post tickets write the full
essays under `marketing/write-post`; `marketing/readme-top` implements the
landing page. The existing launch-plan owner gate decides whether an essay or
channel is kept, changed or dropped. This ticket does not cancel them.

The token/time experiment was dropped on 2026-09-09. No receipt quota, paired
run, efficiency result, multiplier, or unsupported generality claim belongs
here. Private-repo evidence is excluded. Publication, account actions,
product cleanup and the proposed documentation migration remain with their
own tickets.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
