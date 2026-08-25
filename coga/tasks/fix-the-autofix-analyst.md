---
slug: fix-the-autofix-analyst
title: Fix the autofix analyst
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
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
step: 1 (implement)
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
- With no override, `recurring_autofix._analyze_agent` chooses the first agent
  declared in `coga.toml` (Claude here). The existing recurring `--agent`
  override also changes agent-backed task launches, so it cannot independently
  route only the analyst around this auth failure.

No feature branch or worktree has been created yet; implementation awaits
owner confirmation of the proposed selection contract.
