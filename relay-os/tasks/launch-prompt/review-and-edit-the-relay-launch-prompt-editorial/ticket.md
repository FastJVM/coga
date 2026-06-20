---
title: review and edit the relay launch prompt (editorial pass)
status: active
mode: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts:
- relay/architecture
- relay/principles
skills: []
workflow:
  name: autonomy/assist-only
  steps:
  - name: agent-produces
    skills: []
    assignee: agent
  - name: human-owns-and-finishes
    skills: []
    assignee: human
  - name: report-to-relay
    skills: []
    assignee: agent
secrets: null
step: 1 (agent-produces)
---

## Description

A human-owned editorial pass over the Relay launch prompt. Where the sibling
ticket (`improve-prompt-for-relay-launch`) does the mechanical/structural trim,
this ticket is nick's broader review-and-edit of the prompt's wording, tone,
and clarity — the parts that are taste and judgment on the behavioral contract,
not a clean code change.

Claude drafts support material (a marked-up read of the launch prompt:
remaining redundancy, awkward phrasings, instructions that could be sharper or
clearer, anything ambiguous to a launched agent). Nick reviews, edits the
wording to the bar he wants, and owns the result.

Best done after the sibling trim ticket lands so this pass refines the already-
trimmed prompt rather than churning against it — though it can start earlier if
nick wants to set direction first.

## Context

- Scope is the launch prompt surface: `prompt.md` plus the mode overlays
  `prompt-interactive.md` / `prompt-auto.md`, all single-source under
  `src/relay/resources/` (no `templates/relay-os/` copy and no live `relay-os/`
  copy; don't touch the vendored `relay-os/.relay/` snapshot).
- This is `autonomy/assist-only` by design: the prompt is a taste/voice
  artifact, so the agent produces input and the human owns final wording. The
  agent draft is support material, not the delivered edit.
- Sibling ticket: `improve-prompt-for-relay-launch` (Claude, `code/with-review`)
  does dedupe, reference-relocation, core-loop-first, and overlay-trim. This
  ticket assumes that mechanical work and layers editorial judgment on top.
- The prompt is the behavioral contract for every launched agent — wording
  changes still must not silently drop a load-bearing rule, and must keep the
  `relay-os/contexts/relay/` contexts accurate.

