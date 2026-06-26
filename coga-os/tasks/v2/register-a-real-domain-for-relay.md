---
slug: v2/register-a-real-domain-for-relay
title: Register a real domain for Relay
status: draft
autonomy: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
step: 1 (design)
---

## Description

Relay needs a real domain before launch — for the install one-liner, the README
links, and the eventual landing/docs page. Right now there's nothing to point
people at.

Scope:

- Pick + register a domain (shortlist names, check availability, buy).
- Decide the minimal surface it needs to serve at launch: a one-page landing
  with the install command + a link to the GitHub repo and docs is enough.
  Full docs site can come later.
- Wire DNS; HTTPS.
- Make sure the README and the `one-line-install` story reference the final
  domain (not a placeholder), so all the Wave 1 launch copy is consistent.

This is mostly a human action (purchasing), but the agent can shortlist names,
check availability, and draft the landing page.

## Context

Wave 1 launch-gate item. Pairs tightly with `one-line-install`,
`improve-readme-and-doc`, and the `marketing/launch-relay-product-launch-comms`
copy — they all need a final URL to point at.

<!-- relay:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
