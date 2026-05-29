---
title: 'Enforce mode: auto for recurring templates'
status: draft
mode: interactive
owner: nick
human: nick
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

Recurring templates today can declare `mode: interactive` (Dream does:
`relay-os/recurring/dream/ticket.md:9`). Interactive mode tells the agent to
ask when uncertain and sit and wait, so a long interactive Dream stalls on
free-form questions when no human is at the keyboard. `relay recurring`'s
sweep then trips `_stop_if_unfinished_after_launch`
(`src/relay/commands/recurring.py:163`) on the in-flight task and bails
before reaching the next due template — the user's reported "Dream never
exits, sweep never advances".

Recurring is a machine-driven surface: `relay recurring` scaffolds, sequences,
and launches without prompting. So `mode: interactive` does not belong on a
recurring template. Enforce that constraint at template load and flip Dream
to `mode: auto` to match. Keep the on-demand debug story out of this ticket —
that lives in `debug-surface-for-recurring-tasks-streamed-output`.

Changes:

- `src/relay/recurring.py` — reject `mode: interactive` in `Template.load`
  (or earliest validation point). Fail loud with a message naming the
  template and pointing at the future debug surface.
- `relay-os/recurring/dream/ticket.md` — flip `mode: interactive` to
  `mode: auto`. Adjust the "Console Progress" section's phrasing if the
  console-output story depends on the other ticket landing first.
- `src/relay/resources/templates/relay-os/recurring/dream/ticket.md` —
  packaged copy; keep in sync per CLAUDE.md's "live + packaged" rule.
- `relay-os/contexts/relay/architecture/SKILL.md` — add one sentence under
  the recurring primitive: "recurring templates must be `mode: auto` (or
  `mode: script`); interactive recurring is rejected at load."
- `tests/` — add a test that loading an `interactive` recurring template
  raises `RecurringError`, and that loading the shipped Dream template
  succeeds (regression for the flip).

Verification:

- `python -m pytest`
- `relay validate --json`
- `relay recurring` in a scratch repo with the shipped Dream template
  (should scan and launch without stalling).

## Context

Related: `debug-surface-for-recurring-tasks-streamed-output` covers the
follow-on debug surface. This ticket only enforces the constraint; debug
ergonomics are deferred.
