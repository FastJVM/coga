---
slug: remove-mode-from-ticket-frontmatter-and-deduce-scr
title: Remove mode from ticket frontmatter and deduce script-vs-agent from context
status: in_progress
mode: agent
owner: nicktoper
human: nicktoper
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
secrets: null
script: null
step: 1 (implement)
---

## Description

Remove the `mode:` ticket frontmatter field entirely. Whether a launch runs a
script or spawns an agent is deduced from context, per launch:

1. **Step-skill script** — the current workflow step has exactly one skill and
   that skill's SKILL.md declares `script:` → run that script (this is the
   existing `current_step_is_script`, already mode-blind).
2. **Ticket-owned script** — otherwise the ticket's own `script:` is set
   (`inline` or a sibling file) → run that.
3. **Neither → agent** — spawn the assignee's REPL (TTY required).

I.e. `script ⟺ current_step_is_script(ticket) or ticket.script`. The same rule
applied to a recurring template's workflow step 1 (resolving the named workflow
file — it is not frozen yet) replaces the template TTY gate in
`recurring._effective_mode`. That pre-freeze deduction is the only genuinely
new logic; everything else is mechanical removal.

Work items:

- **Dispatch** — `is_script_launch` becomes the deduced rule; delete the
  unknown-mode bail (`launch.py:284`); key the TTY gate, prompt handling,
  session naming, and the assignee-must-be-an-agent guard (`launch.py:305,
  861, 965, 1006, 1202`), `compose.py:120/150/166`,
  `recurring_runner.py:1027`, and `megalaunch.py:245` off the deduction.
- **Recurring** — replace `_effective_mode` (`recurring.py:478`) with
  template-level deduction; update its TTY-skip error message ("give the
  template a script", not "make it `mode: script`").
- **Schema/writers** — drop `mode` from the canonical frontmatter set
  (`ticket.py:30`), `Ticket.mode` (`ticket.py:130`), `VALID_MODES` /
  `invalid-mode` (`validate.py`), the reserved-extension-name list
  (`config.py:586`), `create.py:177`, `--mode` on `commands/create.py`, and
  the authoring stamp in `commands/ticket.py:182`.
- **Cosmetic** — drop `mode=` from launch log/echo strings
  (`launch.py:174, 1093, 1098`) and the `mode` column from
  `coga recurring list` (`commands/recurring.py:196, 208`).
- **Migration** — strip `mode:` lines from all tickets and recurring templates
  in this repo, the packaged templates under
  `src/coga/resources/templates/coga/`, and the `example/` fixture. Leftover
  `mode:` on old tickets surfaces as validate's warn-only orphan key.
- **Docs sync** — rewrite the "Mode and execution" section of the
  `coga/architecture` context, update `coga/cli`, and the calendar-reminder
  skill's examples; keep live `coga/` and packaged copies in sync.
- **Tests** — update tests pinning `--mode` / `_effective_mode` /
  `ticket.mode`; add coverage for the deduced dispatch and the template
  pre-freeze deduction.

Out of scope: `[agents.<name>].mode = "local"` in config is an unrelated
homonym (agent-type transport) — untouched.

## Context

Decided in a bootstrap/orient session (2026-07-13, PR #541 removed the status
`mode` column first). Rationale: `mode` was a cached copy of what
`_resolve_script` already derives. Verified across all 109 tickets (repo +
packaged templates + example fixture): no ticket's deduced substance disagrees
with its declared mode — every `mode: agent` ticket has `script: null`, and all
six `mode: script` recurring templates deduce via their workflow step-1 skill
(none has a ticket-level `script:`; the bootstrap script targets carry
`script: run.py` directly). The `_rem` template's placeholder workflow can't
resolve but is `_`-prefixed and skipped by discovery.

Accepted behavior change: a script ticket whose script vanishes (skill
`script:` renamed away, workflow edit) now deduces to an agent launch instead
of bailing loud; TTY-less contexts still fail on the TTY gate.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
