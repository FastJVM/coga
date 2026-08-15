---
slug: validate-drift-classifier-misses-12-emitted-kinds
title: Validate-drift classifier misses 12 emitted kinds
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

`classify_issue` in `src/coga/dream_validate_drift.py` has no branch for twelve
validator kinds `coga validate` emits today, so each one falls through to the
generic "Unknown validator issue kind" remediation and is routed to
`human-needed` — including several that are mechanical `pr-proposal` material.
The validate-drift skill's contract claims the mapping is complete, so extend
the mapping and correct that sentence.

## Context

### The false contract

`src/coga/resources/templates/coga/bootstrap/skills/bootstrap/dream/tasks/validate-drift/SKILL.md:94-97`:

> The classifier covers every validator kind currently emitted by
> `coga validate`. Anything new is routed to `human-needed`…

That frames the fallback as forward-compatibility for kinds that do not exist
yet. Twelve kinds hit it today.

### The twelve

Reproduced against the current tree (35 `kind=` literals in
`src/coga/validate.py`, fed through `classify_issue`):

```python
from coga.dream_validate_drift import classify_issue, ValidationIssue
# each of these returns the generic "Unknown validator issue kind" remediation
```

- `bad-recurring-template`
- `broken-recurring-template-skill`
- `broken-workflow`
- `duplicate-slug`
- `duplicate-task-number`
- `github-git-branch-state-only-drift`
- `invalid-recurring-schedule`
- `missing-step-instructions`
- `missing-user`
- `notification-deprecated-config`
- `unset-secret-env`
- `unsynthesized-draft-blackboard`

The generic fallback is at `src/coga/dream_validate_drift.py:307`. Note the
asymmetry that produces the last one on the list: `kind.startswith("slack-")`
covers the whole Slack family, but nothing covers the `github-` family.

### Not theoretical

The 2026-08-15 Dream run's Phase 1 hit exactly that output for
`unsynthesized-draft-blackboard`. Nothing is mis-remediated — `human-needed` is
the safe default — but a human is asked to look at drift that Dream could have
proposed a PR for.

### Suggested shape

Extend `classify_issue` with branches for the twelve, bucketing by who can
safely correct them: config/environment kinds (`unset-secret-env`,
`missing-user`, `notification-deprecated-config`) stay `human-needed` for the
same reason the `slack-` branch does; structural task-tree kinds
(`duplicate-slug`, `duplicate-task-number`, `unsynthesized-draft-blackboard`)
are the `pr-proposal` candidates. Then replace the coverage sentence in the
skill with one that describes the fallback as a real backstop rather than a
claim of completeness — or, better, pin coverage with a test that walks the
validator's kind literals so the claim cannot rot again.

### Origin

Verified against the package source during the 2026-08-15 Dream run in the
`admin` repo (Phase 3 contract audit), filed from
`admin/carry-three-verified-coga-bugs-upstream`.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
