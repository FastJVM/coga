---
slug: fix-stale-relay-sync-context-git-failures-swallowe
title: 'Fix stale coga/sync context: git failures swallowed (exit 0), not typer.Exit(1)'
status: in_progress
mode: agent
owner: nick
human: nick
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: dev/with-self-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: self-qa
    skills:
    - code/self-qa
    assignee: agent
  - name: pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 2 (self-qa)
---

## Description

The `coga/sync` context is stale: it still describes git task-state sync
failures as fatal (`typer.Exit(1)`), but the actual contract is that
mid-workflow sync misses (`coga bump` / `mark`) are non-fatal — reported to
stderr and `log.md`, exit 0, work continues — while only the launch-entry push
preflight is fatal (see `coga/architecture`, "launch" section). Verify the
current behavior against source first (`src/coga/` git-sync path), then update
the `coga/sync` context to describe the real fatal/non-fatal split. Check both
the live copy under `coga/contexts/` and the packaged copy under
`src/coga/resources/templates/coga/` and keep them in sync. Docs-only change —
if the source turns out to actually raise `typer.Exit(1)` somewhere the
architecture context says it shouldn't, stop and block rather than guessing
which side is right.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Findings (source verification, implement step)

Verified the ticket premise against `src/coga/git.py` and `src/coga/commands/launch.py`:

- `git.py` contains **zero** actual `typer.Exit` raises (the one grep hit is a
  docstring mentioning the *old* behavior). All git operation failures raise
  `GitError` internally and are swallowed at the `sync_paths` boundary
  (`git.py` ~line 251): stderr + a tagged `coga/log.md` line, then the command
  continues — exit 0. Module docstring (~line 43) states the non-fatal
  contract explicitly and explains the history (re-raising `typer.Exit(1)`
  broke the supervised launch chain: bump's sync aborted before
  `emit_done_marker`).
- `sync_log` and `sync_coga_state` docstrings state the same non-fatal model.
- The context's claim "the same-branch push stays crash-loud on
  non-fast-forward; only the cross-branch land retries" is ALSO stale:
  `_push_control_branch` (~line 473) now fetch+rebases and retries on
  non-fast-forward, bounded by `_MAX_SYNC_ATTEMPTS`, same as the cross-branch
  land (`_land_on_control_branch`). Exhaustion raises `GitError` → swallowed
  at the boundary like everything else.
- The only fatal git gate is launch entry: `commands/launch.py::
  _preflight_push_auth` → `_bail` → `sys.exit(2)` (note: exit code 2, not
  `typer.Exit(1)`). Fires only for a configured, reachable-but-unauthenticated
  remote; self-skips for bootstrap tickets, `[git].enabled = false`, and
  unresolvable remotes. Runs pre-flip, so a refused launch never posts
  "started".
- Slack/notification fail-loud is unchanged and the context's Slack sections
  are accurate: `notification/slack.py` raises `typer.Exit(1)` at lines 78/92.
  Staleness is confined to the git section.
- Block condition from the ticket does NOT trigger: source raises no
  `typer.Exit(1)` in the sync path, matching the architecture contract.

Stale spots in `coga/sync` SKILL.md (both copies are byte-identical;
packaged copy lives at
`src/coga/resources/templates/coga/bootstrap/contexts/coga/sync/SKILL.md`):

1. Frontmatter `description`: "why failures crash" — true for Slack only.
2. Failure-model bullet in "Git — durable task-state sync": claims crash-loud
   `typer.Exit(1)` and no same-branch retry; both wrong.

Decisions:

- Docs-only change, no new tests (no runtime surface); `tests/test_packaging.py`
  only checks the packaged file exists, no content-parity test.
- Describing the launch preflight refusal as "non-zero exit (exit code 2)"
  rather than `typer.Exit(1)` since that's what `_bail` does.

## Dev

branch: sync-context-nonfatal-git
worktree: /home/n/Code/claude/coga-sync-context-nonfatal-git

## Implement step outcome

Committed `fb05a348` on the branch (docs-only, 2 files, live + packaged
copies byte-identical, verified with diff):

1. Frontmatter `description`: "why failures crash" → "why notification
   failures crash but git sync misses don't".
2. Replaced the stale crash-loud failure-model bullet with two bullets:
   git operation failures are non-fatal sync misses (stderr + `coga/log.md`,
   exit 0, `GitError` swallowed at the `sync_paths` boundary, both push paths
   retry non-fast-forward), and the one fatal gate is the launch-entry
   push-auth preflight (non-interactive `git push --dry-run` probe, refuses
   pre-flip, self-skips for bootstrap / git-disabled / unresolvable remote).

Tests: `python3.12 -m pytest -q` in the worktree — 1032 passed, 1 skipped.
(System `python3` is 3.9; use `python3.12` in this environment.)
No fixture changes needed — no task layout / composition / workflow
semantics touched. No push, no PR (later steps).
