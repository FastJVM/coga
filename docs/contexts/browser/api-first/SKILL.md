---
name: browser/api-first
description: Require an explicit "why not the API?" answer before any browser automation ticket lands. Browser automation is the fallback for workflows that cannot be done via an API or script.
---

# API-First For Browser Automation

Browser automation is brittle and expensive to maintain compared to API
or scripted integrations. Before creating a ticket that automates a
real workflow in a real SaaS UI, the ticket author must check whether
an API can do the same job and document the answer.

## Rule

Tickets that propose browser automation against a real site must, in
the ticket body or an attached note, answer all of these:

- Does the target SaaS expose an API (REST, GraphQL, SDK) that covers
  this workflow? Yes / No / Partial.
- If yes or partial: which endpoints, and what specifically is missing
  that forces a browser-based approach?
- If no: link or note the docs page checked, so the next person doesn't
  redo the search.

If the API can do the workflow, write the ticket as a script-or-SDK
ticket, not a browser-automation ticket.

If the API covers part of the workflow, prefer a hybrid where the
script does the API part and a browser pass handles only the
UI-only steps.

## When this context applies

Attach `browser/api-first` to any ticket whose workflow would mutate
or extract data from a real third-party SaaS UI. Read-only DOM
reconnaissance tickets (purely investigative, no mutation, no
data export) may skip it but the API question should still appear
in the blackboard.

## How to apply

- Author: do the API check before the ticket leaves `draft`.
- Reviewer: if the API question is not answered, push back before
  activation rather than after work begins.
- Agent picking up the ticket: if the API answer is missing, surface
  it as a question to the human before starting browser work.
