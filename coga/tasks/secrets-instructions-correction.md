---
slug: secrets-instructions-correction
title: secrets-instructions-correction
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
workflow: null
secrets: null
---

## Description

A credential is declared per ticket, in `secrets:` frontmatter, as an `op://`
pointer that `coga launch` resolves and injects. **It is a list of single-key
entries, not a mapping** — `coga validate` rejects a dict with `bad-shape —
ticket 'secrets:' must be null or a list of 'NAME: <ref>' entries`, and a launch
fails validation *after* already marking the task active:

```yaml
secrets:
  NASA_FIRMS_MAP_KEY: op://weather-events/nasa-firm/credential    # wrong (mapping)
  - NASA_FIRMS_MAP_KEY: op://weather-events/nasa-firm/credential  # correct (list)
```

## Context

Original report was a raw paste; the text above is the same content with the
line-number prefix, duplicated half-sentence, and unclosed fence cleaned up. No
scope decision has been made — see the blocker below.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Ticket authoring notes (2026-08-13)

Interview was cut short — parked for Zach before the workflow/contexts were
picked. Frontmatter is still `workflow: null`, `contexts: []`.

**The ticket's premise does not reproduce in this repo.** Every instruction here
already documents the correct list form:

- `coga/tasks/_template/ticket.md:12` — "one `- NAME: <ref>` list entry per secret"
- `docs/operations.md:183` — "Each entry is a single-key map", list example
- `coga/contexts/coga/architecture/SKILL.md:156` — "a list of single-key maps `- NAME: <ref>`"
- `coga/contexts/coga/secrets/SKILL.md:28` — list example
- `src/coga/config.py:1094` — the validator error quoted in the Description

A repo-wide grep for a mapping-form `secrets:` example returned nothing outside
this ticket's own body. So the instruction that produced the mistake is not in
this repo, and there is no target here to correct.

Three candidate scopes, unresolved:

1. **Wrong instruction lives elsewhere** — e.g. the `weather-events` repo's own
   docs, or something an agent wrote there. Fix is over there, or hoist the rule
   somewhere agents actually read.
2. **Docs are fine; the real defect is the failure mode** — the reported "launch
   fails validation after already marking the task active" is a `coga launch`
   ordering bug: the active transition happens before `secrets:` is validated, so
   a typo strands the ticket in a state that needs hand-repair. That is a code
   ticket in `src/coga/`.
3. **Both**, as one ticket or split into two.

Scope 2 is worth a look regardless of how 1 resolves — it is the part that costs
manual cleanup every time.

