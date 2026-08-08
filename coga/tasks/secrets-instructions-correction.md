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

 62  A credential is declared per ticket, in `secrets:` frontmatter, as an `op://`
pointer that `coga launch` resolves and injects:
pointer that `coga launch` resolves and injects. **It is a list of single-key
entries, not a mapping** — `coga validate` rejects a dict with
bad-shape — ticket 'secrets:' must be null or a list of 'NAME: <ref>' entries`,
and a launch fails validation after already marking the task active:

```yaml
    secrets:
       NASA_FIRMS_MAP_KEY: op://weather-events/nasa-firm/credential (wrong)
       - NASA_FIRMS_MAP_KEY: op://weather-events/nasa-firm/credential (correct)

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
