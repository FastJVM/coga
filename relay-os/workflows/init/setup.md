---
name: init/setup
description: Turn the init-interview answers plus a repo scan into durable relay-os artifacts, reviewed by the owner before they count as final.
steps:
  - name: scan-and-generate
    assignee: agent
  - name: review-and-sign-off
    assignee: human
  - name: apply-review
    assignee: agent
---

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

## review-and-sign-off

Read the generated files and the open-questions list. Edit files directly,
answer open questions on the blackboard, delete what's wrong. Bump when the
set reflects how you actually work.

## apply-review

Fold the review back in: apply the blackboard answers, regenerate anything
the human flagged, and confirm `relay validate` passes. Summarize what
landed, then finish with `relay mark done`.
