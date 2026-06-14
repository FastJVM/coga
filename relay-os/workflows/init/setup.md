---
name: init/setup
description: Interview the owner at first launch, then turn the answers plus a repo scan into durable relay-os artifacts, reviewed by the owner before they count as final.
steps:
  - name: interview
    assignee: agent
  - name: scan-and-generate
    assignee: agent
  - name: resolve-open-questions
    assignee: agent
  - name: review-and-sign-off
    assignee: human
  - name: apply-review
    assignee: agent
---

## interview

`relay init` only scaffolds this ticket — it arrives with an empty
Context and placeholder `owner`/`human` fields. Start by setting both
fields to the `user` value in `relay.local.toml`. Then interview the
owner, one question at a time, and record each answer verbatim under the
ticket's `## Context` heading before asking the next:

1. What is this repo for? What project or operation does it coordinate,
   and what does success look like?
2. What knowledge does this work depend on that an outsider couldn't get
   from reading the repo? The stuff in your head: accounts and tools you
   use, vendor quirks, who's who, deadlines, thresholds, things that have
   bitten you before. If you mention a document, say where it lives so
   the setup agent can read it.
3. What rules should every agent always follow here? The non-negotiables
   — e.g. "never touch real financial data without asking", "never email
   anyone external", "X is read-only".
4. What work comes up repeatedly — and is any of it on a schedule? List
   each one rather than summarizing ("a few year-end processes" hides
   them). Include the cadence, and an anchor date for cadences a calendar
   can't infer (bi-weekly: which week?).

Record what the owner says — don't interrogate. Gaps and vague spots
become open questions for the resolve-open-questions step, after the
scan has given the agent something concrete to ask with. Bump when all
four answers are recorded.

## scan-and-generate

Read the interview answers in the ticket Context, then scan the host repo —
README, docs, scripts, config, anything a new teammate would read. Generate
draft artifacts under `relay-os/`: contexts for what the repo is for and the
knowledge an outsider couldn't infer, `rules.md` additions for the
non-negotiables, workflows for processes that repeat, and `recurring/` tasks
for work on a schedule. Add a skill only when a procedure is concrete enough
to execute verbatim.

Ground rules:

- Repo documents win on facts; interview answers win on intent. When they
  conflict, follow the document and note the conflict on the blackboard.
- Never fabricate. When a fact is missing — an anchor date, a document's
  location, the items behind a summary like "a few year-end processes" —
  stub the artifact and record the gap as an open question instead of
  guessing.
- The open-questions list on the blackboard is a first-class deliverable:
  everything the artifacts need that neither the answers nor the repo
  provides. In a repo with little to scan it is the main deliverable.
- A sparse repo is normal. Generate from the answers alone and present the
  result as a starter relay-os, not a finished one.

Finish by listing every generated file with a one-line purpose on the
blackboard, alongside the open questions, then bump.

## resolve-open-questions

Walk the owner through every open question on the blackboard, one at a
time. Present each as a concrete choice — a few plausible options drawn
from the scan and the interview answers, plus a free-form escape — rather
than an open-ended prompt; options surface assumptions the owner can
correct cheaply. Follow up when an answer is incomplete: if it names a
document or resource without a location ("it's in Drive somewhere"), use
the tools available to find candidates and put the exact link in front of
the owner to confirm — never leave a pointer the next agent can't follow.

Record each answer verbatim under an "Answers" heading on the blackboard.
Where an answer changes a generated artifact — a cadence, a schedule, a
missing fact — fold it into the draft immediately so the review step sees
the real shape, not a known gap. Questions the owner explicitly defers
stay on the open list, marked deferred with a reason. Bump when every
question is answered or deferred.

## review-and-sign-off

Read the generated files, the answers, and anything still open. Edit files
directly, settle remaining questions on the blackboard, delete what's
wrong. Bump when the set reflects how you actually work.

## apply-review

Fold the review back in: apply the blackboard answers, regenerate anything
the human flagged, and confirm `relay validate` passes. Summarize what
landed, then finish with `relay mark done`.

As your closing message, point the human at their first real move now that
the repo knows the project: run `relay setup` again to plan a piece of work
as an ordered set of tickets (a short interview → draft tickets), or
`relay draft "<title>"` for a single one-off ticket. Keep it to a line or
two — they just finished a long setup.
