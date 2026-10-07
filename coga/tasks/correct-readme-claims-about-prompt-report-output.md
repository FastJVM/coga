---
title: Correct README claims about prompt report output
status: draft
owner: nicktoper
workflow: null
---

## Description

Correct the README claim that coga launch --prompt-report shows the exact prompt. The reported behavior is a layer and token-count report, not full prompt text.

Verify installed help and current source, then make the README accurately describe the existing inspection surface with a runnable target-specific example. If full prompt output is desired, explicitly scope that option and its behavior before implementing it; the default scope here is the factual documentation correction. Done when documented output matches a representative invocation and does not claim unavailable functionality.

## Context

### Report relayed by the owner — 2026-10-07

Another AI reports that --prompt-report lists layers and token estimates, and found no full-text output option. Intake confirms README.md claims it “shows the exact prompt before anything runs.” Verify the current command surface before deciding whether any existing way to inspect full text can be documented.

Read coga/prompt-composition (`docs/contexts/coga/prompt-composition/SKILL.md`) and coga/launch (`docs/contexts/coga/launch/SKILL.md`), cited rather than attached; inspect the report contract. Start with README.md, `src/coga/commands/launch.py`, `src/coga/compose.py`, and CLI help. Use an isolated fixture if invoking report mode can mutate generated views or sweep state. This ticket does not fix body-section omission, which belongs to autofix-write-ups-lose-their-body-to-h2-headings.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
