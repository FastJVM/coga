---
name: browser/build-automation
description: Turn a described browser task into a concrete automation ticket by checking for an API first, selecting an autonomy workflow, attaching browser execution capability only when needed, and launching the resulting work.
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

This is a routing decision, not a deep probe. The concrete ticket's
prerequisites step verifies the target, credentials, scopes, and feasibility.

## 3. Choose the autonomy workflow

Classify the requested end action by failure radius:

- read-only, reversible, or idempotent work → `autonomy/fully-automated`;
- irreversible or high-radius work such as send, submit, pay, post, or delete →
  `autonomy/human-verify`;
- work that cannot be performed by the machine → `autonomy/human-only`.

Classify from the requested intent. The chosen workflow confirms feasibility in
its own prerequisites step and can downgrade if the dry run is unreliable.

## 4. Create and launch the concrete ticket

Create one ticket named for the actual requested automation and bind it to the
chosen `autonomy/<tier>` workflow. Write the goal, target, success check, and
API-first decision into its `## Description` and `## Context` sections.

Attach browser capability only when the agent will drive a browser:

- For `autonomy/fully-automated` or `autonomy/human-verify` with a browser
  component, attach context `browser/dom-backed` and ticket-level skill
  `browser/playwright`.
- For an API/script solution or `autonomy/human-only`, attach neither; the
  former does not need a browser, and in the latter the human performs the
  action while the agent stays read-only.

Keep the autonomy workflows domain-generic. Browser-specific context and the
runner belong on the concrete ticket, selected here per task rather than baked
into those workflows.

Launch the concrete ticket after its body and frontmatter are complete. From
that point, its autonomy workflow owns prerequisite verification, dry runs,
execution or brink preparation, human gates, and outcome reporting.
