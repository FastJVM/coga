---
slug: validate-drift-classifier-misses-17-emitted-kinds
title: Validate-drift classifier misses 16 emitted kinds
status: done
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
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
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
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

## Dev
pr: https://github.com/FastJVM/coga/pull/702
branch: codex/validate-drift-kinds
worktree: /home/n/Code/codex/coga-validate-drift-kinds

## Implement notes

- Re-derived 35 literal validator kinds from `src/coga/validate.py` and five
  dynamic GitHub preflight names from `src/coga/github_preflight.py`; the 16
  kinds in the ticket are exactly the kinds reaching the unknown fallback.
- Agreed classification: `github-*`, `missing-user`, and `unset-secret-env`
  stay `human-needed`; the other eight file-backed structural/template kinds,
  including `unsynthesized-draft-blackboard`, become `pr-proposal`.
- Coverage will derive literal and f-string kind samples from validator source
  so a new emitter cannot silently rely on the unknown-kind backstop.
- Added the regression first: all 16 per-kind cases and the aggregate coverage
  check failed against the old classifier. After the explicit branches were
  added, `tests/test_dream_validate_drift.py` passes (30 tests).
- The unknown fallback remains unchanged. The packaged skill now describes it
  as a runtime backstop and points to the source-derived coverage guard.

## Verification

- Focused: `tests/test_dream_validate_drift.py` — 30 passed.
- Full suite: 1810 passed, 1 skipped, 3 failed. All three failures reproduce
  unchanged on `main` when run directly there:
  - `test_recipe_preflights_live_summary_before_closing` expects an inherited
    `SLACK_WEBHOOK_URL` that is absent.
  - `test_named_launch_keeps_control_only_malformed_ledger_blocked_on_retry`
    and `test_sweep_retry_revalidates_control_only_malformed_ledger` now hit
    the control-branch gate before their older ledger assertions.
- These failures do not exercise validate-drift or any changed file; no
  unrelated fixes have been attempted.

## Expanded verification cleanup

The owner asked to fix the three baseline failures and remove the skip on this
branch.

- Autoclose failure combined two stale test assumptions: the autouse Slack
  fixture deliberately removes `SLACK_WEBHOOK_URL` and then resolves that
  exact fixture reference to a stub URL. The test now points its config at a
  distinct explicitly-unset variable, so it reaches the intended live-summary
  preflight failure without depending on the caller's environment.
- Both recurring failures exercise a feature-branch entrypoint even though the
  shipped control-branch gate now refuses every recurring entrypoint before it
  reads period state. The retained feature-branch landing path is explicitly a
  low-level migration surface, so the ledger regressions should target that
  surface rather than bypass the public gate accidentally.
- The sole skip is the wheel test's old `pytest.importorskip("hatchling")`.
  `hatchling` is already a required test extra in `pyproject.toml`; the skip
  still hides a missing test-environment dependency instead of failing loud.
- The repaired failure cases plus validate-drift pass together (33 tests), and
  the wheel module passes all 5 tests in a disposable environment installed
  with `.[test]`; it no longer skips when the declared dependencies are present.
- Full declared-dependency suite: 1814 passed, 0 skipped.
- Scoped validation: 1 task valid, no issues. Example fixture validation: 2
  tasks valid, no issues (run with the caller's unrelated bare
  `SLACK_WEBHOOK_URL` export removed from the command environment).

## Final implementation state

- Commits after final rebase:
  - `cbf46643 Classify all emitted validate drift kinds`
  - `6d9158ca Repair stale full-suite checks`
- Rebasing onto `origin/main` at `7ad12388` replayed cleanly; the 17 incoming
  commits touched none of this branch's six changed files.
- Post-rebase verification: 1814 passed, 0 skipped; `git diff --check` clean;
  scoped task and example fixture validation both report no issues.
- Feature checkout is clean and contains `origin/main`. No push or PR was
  created in this step.

## Peer review

- `codex review --base main` found one P2: removing the wheel test's Hatchling
  skip made the documented `pip install -e .` plus standalone `pytest` setup
  incomplete. The test correctly fails loud because its wheel subprocess uses
  `--no-build-isolation`, but contributor setup did not install the declared
  Hatchling test dependency.
- Review decision: keep the owner-requested no-skip behavior and align the
  development contract on `pip install -e ".[test]"` in `AGENTS.md`,
  `docs/development.md`, and `coga/codebase`. Restoring the skip would recreate
  the masked packaging failure the test-extra dependency was added to prevent.
- The review tool's broader run excluding the packaging module passed 1809
  tests. After installing the branch's declared `.[test]` extra in a disposable
  Python 3.12 environment, the complete pre-rebase suite passed: 1814 passed,
  0 skipped.
- Final rebase onto current `origin/main` at `d3746ed0` replayed all three
  commits cleanly. Post-rebase verification passed 1814 tests with 0 skips;
  `git diff --check` is clean; task-scoped validation reports one valid task
  plus only the feature checkout's expected gitignored `missing-user` warning;
  the example fixture reports 2 valid tasks with no issues.
- Final feature commits are `4e8729fb` (classifier and coverage), `9d52c056`
  (stale full-suite checks), and `9e06440f` (peer-review test-setup contract).
  The feature worktree is clean, contains `origin/main`, and is three commits
  ahead.

## PR

Classify every validator kind currently emitted by `coga validate`: route
file-backed structural and template drift to reviewable PR proposals while
keeping GitHub, identity, and secret-environment failures human-owned. Add a
source-derived regression guard for literal and dynamically generated kinds,
correct the packaged validate-drift contract, repair the three stale baseline
tests and hidden packaging skip exposed by full verification, and document the
declared `.[test]` development setup required by the fail-loud wheel check.

Test plan: `python -m pytest` (1814 passed, 0 skipped); task-scoped validation reports 1 valid task; example validation reports 2 valid tasks with no issues; `git diff --check` passes.
