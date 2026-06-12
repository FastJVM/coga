---
title: init-questions
status: draft
mode: interactive
owner: zach
human: zach
agent: claude
assignee: nick
contexts: []
skills: []
workflow: null
---

## Description

Give a new user a guided start: `relay init` stays fully non-interactive
and scaffolds one launch-ready ticket, `relay-setup`, carrying the four
interview questions unanswered. The user's single onboarding step is
`relay launch relay-setup` (optionally shimmed as `relay setup`); the
launched agent conducts the interview conversationally — probing
follow-ups, recording answers verbatim into the ticket — then scans the
repo and generates the durable artifacts (contexts, rules, workflows,
recurring, possibly skills) **and a first batch of draft tickets** derived
from the answers. Everything lands for the owner's review: edit or accept
the artifacts, activate or delete the drafted tickets.

## Context

The four interview questions (artifact each answer feeds):

1. What is this repo for — what project or operation does it coordinate,
   and what does success look like? (contexts)
2. What knowledge does this work depend on that an outsider couldn't get
   from reading the repo? (contexts)
3. What rules should every agent always follow here? (rules.md)
4. What work comes up repeatedly — and is any of it on a schedule?
   (workflows, recurring)

Design revision 2026-06-12 — interview moved out of `relay init`:

- Nico's constraint: init is an automated command and must never prompt.
  The original phase-1 design ran the questions inside init (TTY-gated);
  that gate keeps scripts safe but was rejected as direction.
- Moving the interview into the launched setup ticket also fixes the
  static-question weakness seen live: printed text can't probe ("we will
  be regularly curating LinkedIn posts" went unchallenged — no cadence),
  a session agent can ask the follow-up. The questions become workflow
  text — a durable, editable artifact — instead of CLI string constants.
- Starter draft tickets are a third deliverable alongside the artifacts
  and the open-questions list: recurring answers map to `recurring/`,
  one-off work hiding in the answers ("decide the HN cadence") maps to
  drafts the user activates or deletes. Mirrors the "vision to task list"
  item in the Relay Additions wishlist doc.

Reference implementation: relay-cli branch `feat/init-interview` has a
working interview-at-init. The typer-prompt half is superseded by this
revision, but reusable as-is: `scaffold_setup_ticket` in
`src/relay/init_interview.py` (answers → active `relay-setup` ticket),
the `init/setup` workflow (packaged + live copies, carries the
generation ground rules), the question text with dry-run probes baked
in, and the init tests.

Design points validated by the pre-implementation dry run (2026-06-11;
full eval, scorecard, and Zach's recorded interview answers are on the
blackboard; fixtures kept at `~/Desktop/admin-init-test` and
`~/Desktop/admin-fresh`). Live empty-repo test runs (2026-06-12,
marketing and newsletter dirs) are scored on the blackboard as well:

- The interview captures intent; the scan captures the operation. Answers
  alone preserved about a third of ground-truth facts at partial
  fidelity; the scan recovered all of them, including scheduled work the
  human forgot to mention. Treat the scan step as load-bearing.
- The setup ticket should emit an **open-questions list** as a
  first-class output alongside the artifacts. On the empty-repo path it
  is the main deliverable — that path produces a starter relay-os, not a
  complete one.
- Conflict precedence: repo docs win on facts, interview answers win on
  intent. This resolved all four answer/doc conflicts in the dry run
  correctly.
- Generation must stub-and-ask rather than fabricate. Both dry-run
  agents did this unprompted (zero invented facts); make it an explicit
  requirement, not luck.
- Interview refinements worth adopting: probe enumerables ("a few
  year-end processes" → "list them"); ask *where* referenced documents
  live so the scan can ingest them; ask for anchor dates on cadences
  cron can't express (bi-weekly payroll broke both legs' schedules).
- The scan must degrade gracefully to answers-only: real ops repos can
  be nearly empty outside relay-os.
