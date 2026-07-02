---
slug: v2/validate-tickets-on-hand-edit-gap-outside-relay-co
title: Validate tickets on hand-edit (gap outside relay commands)
status: draft
mode: llm
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
  - coga/architecture
  - coga/principles
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

`relay validate` is enforced at the edge of every **relay-owned** mutation —
`draft`, ticket-authoring exit, `mark`, `bump`, launch-time transitions, and
recurring/retire creating all run a task-scoped validate after the write and
before reporting success. But a **direct hand-edit to `ticket.md`** (a human or
agent editing the file with an editor / file-edit tool) is **not** validated
automatically. Today the only safeguard is remembering to run
`relay validate --task <slug>` by hand, so malformed frontmatter from a hand-edit
can sit undetected until the next relay command happens to touch the ticket.

Confirmed current state (2026-06-15): no git hooks are installed, and
`relay init` actively *prunes* legacy hooks (the post-merge automerge hook was
removed). So there is no hook backstop, and adding one cuts against the
direction the project has taken.

**Design fork to settle (this is why it's design-first):** where should the gate
live?

- **Command-time gate (preferred starting point).** Validate the ticket at the
  next relay command that reads it — most importantly `relay launch` / compose —
  and fail loud before composing a prompt from malformed frontmatter. Keeps
  enforcement on explicit relay surfaces (principle 6, fail-loud) with no hidden
  trigger. Open question: does `relay launch` already validate frontmatter, or
  only run the freshness check? If not, that's the cheapest fix.
- **Opt-in pre-commit hook.** A `relay validate` pre-commit hook catches bad
  edits before they're even committed — but it's an implicit git trigger, which
  the project has been removing. If offered at all, it should be opt-in and
  documented, not installed by default.
- **Both / neither** — decide in design.

Scope: pick the mechanism, implement it, fail loud with the same actionable
message `relay validate --task` gives, and document the enforcement boundary so
it's clear when a hand-edit is and isn't checked.

## Context

The validate enforcement contract and the "explicit-only surface / no implicit
triggers" stance are in `relay/architecture` and `relay/principles` (principle
6, fail-loud — `status`/`show`/`validate` are forbidden mutators, and implicit
git hooks were deliberately removed). Respect that direction when choosing the
mechanism. Validation logic lives in `src/relay/commands/validate.py`; the
relay-command call sites that already validate are the model to follow.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
