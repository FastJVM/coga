---
title: Title-only tickets have no convention and no validator
status: in_progress
owner: nicktoper
agent: claude
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
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
step: 4 (review)
---

## Description

Twenty-one tickets under `coga/tasks/` have a literally empty `## Description`
and `## Context`. Eleven were found in a single Dream shard: `manage-security-and-pii`,
`autoroute-agent-based-on-remaining-usage`, `pick-model-on-workflow-to-save-on-cost`,
`why-ai-asks-me-to-bump-instead-of-doing-it`, `remote-stale-command-line-toosl`,
`in-general-relay-files-should-be-easier-to-access`,
`generic-lib-to-use-e-g-patent-models`,
`project-manager-split-spec-in-tickets-block`,
`update-all-doesn-t-copy-workflow-correctly-to-atta`, and two
`create-vault*-and-service-account-for-*-trust-sec` tickets.

All that survives is a title, sometimes a typo'd one, so the intent is
unrecoverable by anyone but the author — `remote stale command line toosl` and
`generic lib to use e.g. patent models` cannot be launched or even
premise-checked. `src/coga/validate.py` checks blackboard size and workflow
shape but never that the body says anything, so these are invisible to every
sweep.

This is a different shape from the tracked workflow-less concept-capture draft:
a workflow-less draft is a decision deferred, a body-less draft is a thought
that was never written down.

Three such stubs also sit at the `coga/tasks/` root rather than in `v2/` —
`add-an-agent-picker-for-recurring`, `remov-digest-in-recurring`, and
`make-sure-repo-clietn-don-t-edit-coga` — where they read as current work in
`coga status` rather than as dated parked artifacts. The only document that
governs the stub habit is `coga/tasks/v2/README.md`, whose premise-check
contract is scoped entirely to the parking area, and the three open triage
tickets built on it all count and act only within `coga/tasks/v2/`.

## Context

Two directions, and the design step should pick one (or both):

- add a validator warning for an empty `## Description` so the capture path
  stays honest — note `validate.py`'s `unsynthesized-draft-blackboard` rule
  fires only when a draft blackboard carries pre-launch authoring notes, so an
  untouched placeholder is silent everywhere today; or
- document title-only capture as a supported shape with an explicit expiry,
  and either generalize the v2 README's "read every draft as a dated artifact"
  contract to any title-only draft wherever it sits, or rule root-level capture
  out so the habit lands in the one directory that has a triage contract.

Guard, carried verbatim by three existing tickets and by no context: a green
`coga validate` is never a reason to cancel a draft — it is a consequence of
correct verdicts, never an input to them.

<!-- coga:blackboard -->

## Dev

pr: https://github.com/FastJVM/coga/pull/815
branch: title-only-validator
worktree: /home/n/Code/claude/coga-title-only-validator

## Plan (implement step, no design step in this workflow)

Both directions from `## Context`, kept small:

1. Validator: new `empty-description` warning in `validate._check_one_task`
   for any non-terminal ticket whose `## Description` is empty or absent.
   Uses `compose._extract_section` (already shared with `open_pr`). `warn`,
   not `error`: `assert_task_valid` runs on every mutating command and
   `coga create` without `--description` legitimately produces this shape.
   Terminal tickets are history, not capture debt (one `done` and one
   `canceled` ticket in this repo have empty bodies).
2. Drift classifier: `empty-description` → `human-needed`; only the author
   can supply the intent, and the guard (a green validate is never a cancel
   reason) goes into the remediation text.
3. Convention: root-level title-only capture is ruled out. A bare thought
   goes to `v2/` (`coga create "v2/<title>"`), the one directory with a
   triage contract; anywhere else the description is written at create time.
   Owner surfaces: `coga/roadmap` "Deferred work" (the rule) and
   `coga/tasks/v2/README.md` (a "Title-only drafts" section: what a stub
   is, its expiry = the first sweep that reports it, describe-or-cancel).
   Neither file has a packaged twin.

## Implement — done (commit `7f5005e9` on `title-only-validator`)

What changed:

- `src/coga/validate.py`: new `empty-description` warning in
  `_check_one_task`, right after the `unsynthesized-draft-blackboard` rule.
  Fires for any non-terminal ticket whose `## Description` is empty or has
  no heading; reads the body via `taskfile.split_body` +
  `compose._extract_section` (the parser `compose` and `open_pr` already
  share). Docstring check-list updated.
- `src/coga/dream_validate_drift.py`: `empty-description` → `human-needed`;
  remediation says "do not infer from the slug, never cancel just to clear
  the warning".
- `src/coga/commands/create.py`: `--description` help now says omitting it
  is for a `v2/` capture and names the validator kind.
- `coga/contexts/coga/roadmap/SKILL.md` ("Deferred work"): the rule —
  bare capture only via `coga create "v2/<title>"`; everywhere else the
  description exists from creation.
- `coga/tasks/v2/README.md`: new "Title-only drafts: a capture, not a
  ticket" section (definition, why the premise check can't run on it, the
  expiry = first sweep reporting `empty-description`, describe-or-cancel,
  the green-validate guard, pointer to the interview ticket as precedent).
- Tests: four new cases in `tests/test_validate.py` (warns on empty; warns
  on missing heading; silent on `canceled`; silent when described), the
  kind added to the `human-needed` parametrize in
  `tests/test_dream_validate_drift.py`, and `description=` added to the six
  existing fixtures that asserted an issue-free report (plus
  `_make_task` in `tests/test_commands.py`).

Decisions:

- **Warn, not error.** `assert_task_valid` runs after every mutating
  command; an error would make `coga create` without `--description` fail
  its own post-write check. The ticket asked for a warning anyway.
- **Both directions, root capture ruled out** rather than generalizing the
  "dated artifact" contract to the root. The ticket's own complaint is that
  root stubs read as current work in `coga status`; generalizing the v2
  contract would keep them there. The warning still fires in `v2/` — a stub
  is tolerated there, not invisible.
- **Expiry is event-based** (the first sweep that reports the stub), not
  a date: no creation timestamp lives in frontmatter, and a date rule would
  need `log.md` archaeology in the validator for no extra signal.
- **Not touched:** the 24 live stubs themselves. 17 are the cohort of
  `interview-the-owner-on-the-17-title-only-v2-stubs` (at `review-design`,
  planning 1 describe / 16 cancels); the 4 root ones
  (`dream-should-be-able-to-use-codex-instead-of-claud`,
  `recurring-task-to-manage-all-open-pr-and-address-c`,
  `some-recurring-tasks-are-not-launched-correctly-to`,
  `where-have-code-review-disappeared`) and 3 under `automerge/`,
  `marketing/` (`automerge/fix-let-a-lot-of-open-craps`,
  `marketing/add-telemetry`, `marketing/fix-installer`) now surface in every
  sweep and need the owner's verdict per the new v2 README section. The
  ticket's inventory was already stale: `add-an-agent-picker-for-recurring`
  and `make-sure-repo-clietn-don-t-edit-coga` have descriptions now, and
  `remov-digest-in-recurring` too.

Verification:

- `python -m pytest` in the worktree: 2500 passed.
- `coga validate --json` on this repo with the branch's source: 24
  `empty-description` warnings, the 4 pre-existing
  `unsynthesized-draft-blackboard` errors unchanged, no new errors.
- `coga validate --json` in `example/`: 0 issues, 4 ok (needs
  `SLACK_WEBHOOK_URL` unset in this shell — pre-existing, unrelated).
- Rebased on `origin/main`: already up to date. Not pushed, no PR.

## Peer review

`codex review --base main` **returned** from the recorded feature worktree:
no actionable regressions, no must-fix findings. The reviewer ran all 2500
tests successfully and compared the validator against the base: existing
findings stayed identical apart from the intended `empty-description`
warnings (4 existing errors on both versions). No code changes required.

Independent full-suite verification passed **2500 tests before rebase and
2500 tests after rebase** using
`PYTHONPATH=/home/n/Code/claude/coga-title-only-validator/src /home/n/Code/claude/coga/.venv/bin/python -m pytest`.
Use that virtualenv: the ambient `python` lacks `tomlkit` and cannot collect
the suite. From `example/`,
`env -u SLACK_WEBHOOK_URL PYTHONPATH=/home/n/Code/claude/coga-title-only-validator/src coga validate --json`
also passed before and after rebase (4 ok, no issues). A branch-source sweep
of the primary repo reported 24 `empty-description` warnings and the same
4 pre-existing `unsynthesized-draft-blackboard` errors.

Terminal check: drove `coga create --help` in real PTYs at 80x24 and 120x40
(explicit `COLUMNS=120 LINES=40` for the wider rendering), and
`coga validate --task marketing/add-telemetry` at 80x24. The new help wraps
within both widths, the warning text is complete, and the warning-only
command exits 0. No interactive terminal-loop or Slack-rendering changes.

Ran `git fetch origin main && git rebase FETCH_HEAD` successfully. The branch
is now at `d1a27208`, one commit ahead of fetched `main` (`20bbbe9b`); the
incoming changes were task/log state only. `git diff --check origin/main...HEAD`
passes and the feature worktree is clean. No review-fix commit was needed;
the implementation commit remains the one feature commit ahead of main.
Review, freshness, testing, and PR-body gates are complete; ready to bump.

## PR

Warn when a non-terminal ticket has an empty or missing `## Description`, and
classify the warning as human-needed in Dream. The owner must supply the
intent or confirm cancellation with a reason; clearing validation warnings
alone is never a reason to cancel. Document `v2/` as this repo's place for
title-only capture, with a verdict due at the first sweep, and add the
guidance to `coga create --description` help.

Test plan: `PYTHONPATH=/home/n/Code/claude/coga-title-only-validator/src /home/n/Code/claude/coga/.venv/bin/python -m pytest` (2500 passed after rebase); from `example/`, `env -u SLACK_WEBHOOK_URL PYTHONPATH=/home/n/Code/claude/coga-title-only-validator/src coga validate --json` (4 ok, no issues); real PTY help at 80x24/120x40 and warning output at 80x24.

## PR review follow-up (2026-09-16)

Addressed the requested comments on [PR #815](https://github.com/FastJVM/coga/pull/815) in `/tmp/coga-review-pr815-20260916`.

Updated the package-only CLI command contract with the v2-only bare-capture convention and the warn-only empty-description validator behavior. CLI argument syntax is unchanged.

Verification: `PYTHONPATH=/tmp/coga-review-pr815-20260916/src /home/n/Code/claude/coga/.venv/bin/python -m pytest -q tests/test_packaging.py` — 11 passed.
