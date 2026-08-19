---
slug: validate-drift-classifier-misses-17-emitted-kinds
title: Validate-drift classifier misses 16 emitted kinds
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
workflow: code/with-review
secrets: null
---

## Description

`classify_issue` in `src/coga/dream_validate_drift.py` has no branch for
sixteen validator kinds `coga validate` emits today: eleven literal tags and
five GitHub preflight tags built dynamically. Each falls through to the generic
"Unknown validator issue kind" remediation and is routed to `human-needed` —
including several that are mechanical `pr-proposal` material. The validate-drift
skill's contract claims the mapping is complete, so extend the mapping, correct
that sentence, and pin coverage with a test so the claim cannot rot again.

## Context

### The false contract

`src/coga/resources/templates/coga/bootstrap/skills/bootstrap/dream/tasks/validate-drift/SKILL.md:94-97`:

> The classifier covers every validator kind currently emitted by
> `coga validate`. Anything new is routed to `human-needed`…

That frames the fallback as forward-compatibility for kinds that do not exist
yet. Sixteen kinds hit it today.

### The sixteen

Reproduced against the tree as of 2026-08-19 (35 `kind=` literals plus five
preflight tags constructed by `kind=f"github-{result.name}"` in
`src/coga/validate.py`, fed through `classify_issue`). This list has already
rotted once — the original enumeration had seventeen, but
`notification-deprecated-config` was deleted in `0947be77` (2026-08-17) —
so **re-derive it against the current tree before implementing** rather than
trusting the enumeration below:

```python
from coga.dream_validate_drift import classify_issue, ValidationIssue
# each of these returns the generic "Unknown validator issue kind" remediation
```

- `bad-recurring-template`
- `broken-recurring-template-skill`
- `broken-workflow`
- `duplicate-slug`
- `duplicate-task-number`
- `github-gh-auth`
- `github-gh-installed`
- `github-git-auth`
- `github-git-branch-current`
- `github-git-branch-state-only-drift`
- `github-git-remote`
- `invalid-recurring-schedule`
- `missing-step-instructions`
- `missing-user`
- `unset-secret-env`
- `unsynthesized-draft-blackboard`

The generic fallback is at `src/coga/dream_validate_drift.py:307`. Note the
family asymmetry: `kind.startswith("slack-")` covers every Slack issue, but
nothing covers the six GitHub issues (the five dynamic failures plus the
literal state-only drift warning).

### Not theoretical

The 2026-08-15 Dream run's Phase 1 hit exactly that output for
`unsynthesized-draft-blackboard`. Nothing is mis-remediated — `human-needed` is
the safe default — but a human is asked to look at drift that Dream could have
proposed a PR for.

### Suggested shape

Extend `classify_issue` with branches for the sixteen, bucketing by who can
safely correct them: config/environment kinds (`unset-secret-env`,
`missing-user`) and the `github-` family stay `human-needed` for the same
reason the `slack-` branch does; structural task-tree kinds (`duplicate-slug`,
`duplicate-task-number`, `unsynthesized-draft-blackboard`) are the
`pr-proposal` candidates. These are candidates, not verdicts —
`unsynthesized-draft-blackboard` in particular has content-authoring flavor
(synthesizing a draft's blackboard is not purely mechanical), so the
pr-proposal/human-needed call for it deserves scrutiny at peer review. Then
replace the coverage sentence in the skill with one that describes the
fallback as a real backstop rather than a claim of completeness, **and** pin
coverage with a test that accounts for both validator literals and dynamically
generated families so the claim cannot rot again — this test is required, not
optional; the per-kind test pattern to extend lives in
`tests/test_dream_validate_drift.py`. Note the skill file exists only as the
packaged copy under `src/coga/resources/templates/` — there is no live-repo
copy under `coga/` to keep in sync.

### Origin

Verified against the package source during the 2026-08-15 Dream run in the
`admin` repo (Phase 3 contract audit), filed from
`admin/carry-three-verified-coga-bugs-upstream`.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
