---
slug: awaken-recurring-auto-blocked-tasks
title: Awaken recurring auto blocked tasks
status: done
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts:
- coga/architecture
- coga/cli
- coga/sync
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
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
---

## Description

Follow up to the first-class `coga block` / `coga unblock` workflow.

Blocked work is already visible through `status: blocked` and
`coga status --blocked`, but an unresolved ask still needs to be re-surfaced
after the initial live Slack post. This task adds that wakeup loop without
creating a second blocker model.

Build a markdown-first blocked-task reminder, not a hosted service:

- Scan ordinary tasks, including recurring-created period tasks, whose
  frontmatter says `status: blocked`.
- Reuse the existing blackboard blocker parser (`## Blockers`) that backs
  `coga block`, `coga unblock`, `coga status --blocked`, and megalaunch.
- Re-notify owners for unresolved blockers from an unattended script path using
  the existing notification/sync surfaces.
- Point the human at the command-owned answer handshake:
  `coga unblock <slug> --answer "..."`. Do not introduce direct
  `answered:` / `resolved:` edits as a parallel public contract.
- Deduplicate reminder posts so the same unresolved blocker is not posted on
  every scan. Store the reminder watermark in markdown state on the blocked
  task's own blackboard so it travels with the ask and remains inspectable.
- Do not launch, unblock, or otherwise advance blocked tasks from the reminder
  job. It only makes unresolved asks visible again.
- Cover the behavior with tests that prove blocked tasks are reminded once,
  duplicate reminders are suppressed, resolved blockers are ignored, and
  non-`blocked` tasks with historical blocker text are not re-awakened.

Product decision for this ticket:

This ticket does not change task selection, `autonomy:`, `coga status`, or the
broader drain model. It only reminds owners about tasks already stopped by
`coga block`. Future work may decide whether a drain path should attempt all
active agent-owned work, but that migration must be explicit and should not
happen as a side effect of blocker reminders.

## Context

Relevant existing pieces:

- `block-unblock-and-megalaunch` defines the first-class blocker lifecycle.
- `v2/issue-inbox-slack` covers richer immediate Slack posts for blockers.
- `nightly-auto-drain-run-for-ready-tickets` is the future drain loop that may
  consume this wakeup behavior.

Implementation shape:

- Put reminder scan/watermark logic in reusable code instead of duplicating it
  in the script skill.
- Let `coga.blackboard` remain the source of truth for blocker entry parsing
  and resolution.
- The canonical next command is `coga unblock <slug> --answer "..."`.
- If reminder watermarking needs a section name, prefer a small plain-markdown
  section in the blocked task blackboard such as `## Blocker reminders`; keep it
  compact and machine-readable enough to deduplicate by blocker fingerprint.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Design decision

- [2026-06-30] Superseded implementation direction: earlier scope treated
  blocker visibility as generic task behavior and proposed appending an
  `Open blockers` table to plain `coga status`.
- [2026-06-30] Still-current part of that direction: reminder posts/watermark
  writes stay out of `status` and belong in an explicit script-backed recurring
  task.
- [2026-07-01] Owner review on PR #485 pointed out that current main already has
  `coga block` / `coga unblock` as the blocker model. Revised this PR to remove
  the separate generic blocker queue: reminders now scan `status: blocked`
  tasks, use `coga.blackboard` parsing, and point humans at `coga unblock`.

## Dev

branch: codex/awaken-blocker-reminders
worktree: /tmp/coga-awaken-blocker-reminders
pr: https://github.com/FastJVM/coga/pull/485

Implementation notes:

- Added `coga.blocker_reminders` as the recurring reminder scanner/watermark
  writer for first-class blocked tasks. It reads `status: blocked` tickets,
  reuses `coga.blackboard` blocker parsing, and records reminder watermarks
  under `## Blocker reminders`.
- Kept blocker visibility on the existing `coga status --blocked` queue instead
  of adding a second plain-status table.
- Added the script-backed `recurring/blocker-reminders` battery with matching
  workflow and `coga/blockers/remind` skill in both live and packaged template
  trees.
- Updated sync/CLI contexts for the existing blocked-task queue and new live
  reminder notification path.

Verification:

- `PYTHONPATH=src python -m pytest tests/test_blocker_reminders.py tests/test_commands.py::test_status_blocked_expands_open_blockers tests/test_packaging.py::test_package_includes_coga_resources -q`
  (6 passed).
- `PYTHONPATH=src python -m pytest -q` (952 passed, 1 skipped).
- `git diff --check origin/main...HEAD` (clean).
- `PYTHONPATH=src python -m coga.cli validate --task awaken-recurring-auto-blocked-tasks --json`
  (ok_count 1, no issues).

Peer review:

- [2026-06-30] Ran `codex review --base main` from
  `/tmp/coga-awaken-blocker-reminders` (sandboxed run hit Codex app-server
  read-only FS; escalated rerun completed). Review found one P2 bug:
  indented Markdown sub-bullets under a blocker were parsed as separate open
  blockers. Fixed on the feature branch in commit `9571c187`
  (`peer-review: fix nested blocker bullets`) by restricting blocker starts to
  top-level bullets and adding a regression test.
- [2026-07-01] That peer-review fix is historical for the superseded parser
  design. PR-comment fix rebased the branch onto current main and removed the
  duplicate parser/status-table path instead of carrying that shape forward.
