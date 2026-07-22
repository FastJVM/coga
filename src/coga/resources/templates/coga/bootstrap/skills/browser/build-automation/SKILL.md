---
name: browser/build-automation
description: Turn a described browser task into a concrete automation ticket by checking for an API first, matching workflow handoffs to the requested action, attaching browser execution capability only when needed, and launching the resulting work.
---

# Build a browser automation

Use this skill as the orchestration layer between a human's description of a
browser task and the concrete Coga ticket that will implement and run it. The
skill does not drive the browser itself; `browser/playwright` is the separate
lower-level execution skill.

The bootstrap launcher carrying this skill is stateless. Do all four phases in
this session, and create durable state only for the concrete automation the
human actually requested. Do not create or preserve a generic router ticket.

## 1. Understand the task

Ask the human to describe the browser task if they have not done so yet. Restate
it as:

- a concrete goal;
- a target site, URL, or system; and
- an explicit success check: what will be observably true when the task is done.

Ask one clarifying question only when the task is genuinely ambiguous.
Otherwise, proceed.

## 2. Choose the approach

Apply the attached `browser/api-first` context. Decide whether an API, SDK, or
ordinary script can perform the task without browser automation.

- If an API or script covers the task, create the concrete ticket for that
  approach and do not attach browser-specific context or skills.
- If coverage is partial, keep the API-backed portion and use a browser only
  for the UI-only remainder.
- If no practical API path exists, choose DOM-backed browser execution and
  attach `browser/dom-backed` to the concrete ticket.

This is a routing decision, not a deep probe. The concrete ticket verifies the
target, credentials, scopes, and feasibility before it acts.

## 3. Choose the workflow

Inspect the available workflows and pick the one whose assignee handoffs match
the requested end action:

- read-only, reversible, or idempotent work → the lightest all-agent workflow
  that fits;
- an irreversible or outward-facing action such as send, submit, pay, post, or
  delete → a workflow with a human or owner gate before that action;
- an action the machine cannot safely perform → a workflow where the human
  performs it and the agent provides read-only support.

Bind to a real workflow ref, not a category label. If none has the right
handoff shape, say so and let the human decide whether the repo needs a new
workflow.

## 4. Create and launch the concrete ticket

Create one ticket named for the actual requested automation and bind it to the
chosen workflow's real ref. Write the goal, target, success check, API-first
decision, and why the workflow's gates fit the requested action into its
`## Description` and `## Context` sections.

Attach browser capability only when the agent will drive a browser:

- When an agent will drive the browser, attach context `browser/dom-backed` and
  ticket-level skill `browser/playwright`.
- For an API/script solution, or a workflow where the human performs the browser
  action, attach neither; the former does not need a browser, and in the latter
  the human drives it while the agent stays read-only.

Browser-specific context and the runner belong on the concrete ticket, selected
here per task rather than baked into a domain-generic workflow.

Launch the concrete ticket after its body and frontmatter are complete. From
that point, its workflow owns the operator handoffs. Put prerequisite checks,
dry runs, and outcome verification in the ticket body when the selected
workflow does not already specify them.
