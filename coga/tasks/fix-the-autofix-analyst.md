---
slug: fix-the-autofix-analyst
title: Fix the autofix analyst
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
- coga/recurring
skills: []
workflow:
  name: code/with-self-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: self-qa
    skills:
    - code/self-qa
    assignee: agent
  - name: pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
secrets: null
step: 3 (pr)
---

## Description



## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Investigation

- The ticket's Description and Context are empty, and there is no attached run
  log or recorded symptom.
- The focused baseline passes: `python -m pytest
  tests/test_recurring_autofix.py -q` -> 31 passed.
- The immediately preceding draft was titled "Make the autofix analyst legible
  and its agent selectable", but that ticket was also empty before it was
  deleted and replaced by this one.

## Ambiguity

Resolved with the owner: the recurring autofix analyst failed because its
Claude Code call used an unusable authentication source.

## Reproduced failure

- The machine-local run record at
  `/home/n/Code/claude/coga/coga/.coga/recurring-runs/20260825T105618.md`
  shows a healthy 10:56 sweep: three completed tasks and zero run problems.
- The corresponding Claude analyst session started at 10:58:05 and returned
  `billing_error: Credit balance is too low`.
- `claude auth status` says the user is logged in through claude.ai, but also
  reports `apiKeySource: ANTHROPIC_API_KEY`; that exported variable is present
  in `.bashrc` and takes precedence. No credential value was read or recorded.
- Running the same auth-status check with only `ANTHROPIC_API_KEY` removed
  confirms a usable claude.ai Max subscription login, so the analyst has a
  working automatic fallback on this machine.
- With no override, `recurring_autofix._analyze_agent` chooses the first agent
  declared in `coga.toml` (Claude here). The existing recurring `--agent`
  override also changes agent-backed task launches, so it cannot independently
  route only the analyst around this auth failure.

The owner confirmed the automatic fallback contract below.

## Proposed fix

Keep the configured Claude authentication source as the first attempt. When
that attempt exits with a recognized authentication or billing error and an
ambient `ANTHROPIC_API_KEY` is present, check whether Claude Code has a usable
claude.ai login without the variable and retry the analyst once with only that
variable removed. Announce the fallback, preserve API-key-only installations,
and leave unrelated failures single-attempt and loud. Cover the auth failure,
successful subscription retry, missing-subscription, and unrelated-failure
paths with deterministic subprocess fakes; update the recurring contract and
its packaged copy.

## Dev

branch: autofix-claude-auth-fallback
worktree: /tmp/coga-autofix-auth-fallback

## Implemented

- The analyst keeps the configured environment for its first call. A
  successful Claude API-key call is never probed or replaced.
- A non-zero Claude result containing a recognized authentication or billing
  marker now triggers a bounded `claude auth status` check with only
  `ANTHROPIC_API_KEY` removed. Coga retries once in that environment only when
  the JSON status confirms a signed-in claude.ai account and no other API-key
  source.
- The fallback is announced on stderr. API-key-only installations retain the
  original failure, and unrelated failures plus non-Claude agents never switch
  authentication.
- Updated the live `coga/recurring` contract, `docs/reference.md`, and the
  packaged CLI context that describes recurring autofix behavior.

## Verification

- `python -m pytest tests/test_recurring_autofix.py -q`: 35 passed.
- Full suite with the feature `src/` and the already-cached declared build
  dependencies on `PYTHONPATH`: 1990 passed in 119.28s. The first bare
  worktree run had 19 environment-only failures because child Python
  processes could not import the uninstalled src-layout package and
  `hatchling` was absent; representative child-process/wheel tests and then
  the full suite passed once the declared test environment was supplied.
- `git diff --check origin/main...HEAD`: clean.
- `env -u ANTHROPIC_API_KEY claude auth status` confirmed the real fallback
  account is logged in through claude.ai with a Max subscription. No real
  analyst/model call was made during verification.
- Commit: `8e3f6451` (`Retry autofix analyst with Claude subscription`).
- `git fetch origin main` followed by `git rebase FETCH_HEAD`: already current;
  the branch is clean and one commit ahead of `origin/main`.

## Self-QA

- `codex review --base main` found that the initial fallback check did not
  prove the retry would use an entitled first-party subscription: custom
  analysis argv or Anthropic routing could change the effective credential,
  a forced Console login policy was ignored, and a signed-in free account was
  accepted without a subscription entitlement.
- The `/simplify` UI command was unavailable in this launched session, so an
  equivalent `codex exec` simplify pass reviewed the diff and consolidated the
  duplicated analyzer subprocess calls into a bounded two-attempt loop.
- Applied the review findings by limiting fallback to Claude's built-in
  analysis argv and standard auth routing, honoring `forcedLoginMethod`, and
  requiring a first-party Pro, Max, Team, or Enterprise subscription with no
  other API-key source. Added deterministic coverage for every rejected path
  and updated the live, reference, and packaged contracts.
- `python -m pytest tests/test_recurring_autofix.py -q`: 41 passed.
- Full suite with the feature `src/` and declared test dependencies on
  `PYTHONPATH`: 1996 passed in 132.66s.
- `git diff --check`: clean; feature worktree clean after commit.
- QA commit: `947aad11` (`self-qa: harden Claude subscription fallback`).
