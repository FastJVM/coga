---
slug: recurring-bugs/skill-update-aborts-on-uncommitted-log-file
title: skill-update aborts on uncommitted log file
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
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
    skills: []
    assignee: owner
secrets: null
script: null
step: 1 (implement)
---

## Description

A `coga recurring` sweep that fires `recurring/skill-update` (script step
running `coga skill update --all --pr`) aborts with:

```
error: Your local changes to the following files would be overwritten by checkout:
    coga/log.md
Please commit your changes or stash them before you switch branches.
Aborting
Script exited with 2.
```

The script exits non-zero, so the period task is left stuck `in_progress` and
its next scheduled firing is deferred until a human clears it. Any script step
that switches git branches mid-run is exposed to this, not just skill-update.

Fix the launcher so a script step starts against a clean-enough tree (its own
pending `coga/log.md` append committed), so branch-switching script steps don't
abort.

## Context

### Root cause

The script-launch path leaves its own launch log append uncommitted while the
script runs, then the script switches branches on the dirty tree:

1. `run_script_mode` appends a `launched as a script` line to `coga/log.md`
   (`src/coga/commands/launch_script.py:216`) and does **not** commit it. The
   agent-spawn path commits its equivalent append immediately when
   `commit_log=True` (`src/coga/commands/launch.py:984-991`), but the script
   path has no such commit.
2. The skill-update PR flow then runs `git checkout -B coga/skill-update <control-branch>`
   to carry updates onto a dedicated branch (`_commit_skill_updates` →
   `_checkout`, `src/coga/skill_manager.py:488`).
3. git refuses the checkout because the tracked `coga/log.md` is dirty, and the
   raw error surfaces.

The existing preflight `_assert_no_unmerged_paths`
(`src/coga/skill_manager.py:417`) only detects **unmerged** paths
(`--diff-filter=U`), so it walks right past an ordinary dirty tracked file and
does not produce a friendly error either.

Note: this is a race with the launcher's own logging, not stale user state —
retrying by hand after the tree settles (log committed) succeeds, which is how
this period was cleared. So the current-period task has already been marked
`done`; this ticket is only the durable fix.

### Proposed fix

Primary (general, fixes all branch-switching script steps): in
`run_script_mode`, commit the pre-run `coga/log.md` append before invoking the
script — mirror the `commit_log` pattern in `spawn_agent_session`
(`launch.py:984-991`, non-fatal on git failure). Then the tree the script
inherits has no uncommitted Coga-state file to block a checkout.

Secondary (defense-in-depth, better error): widen the skill-update preflight
(`_assert_no_unmerged_paths`) — or add a sibling check — to also detect a
plain dirty tree that would block `git checkout -B`, and fail with a named,
actionable message instead of the raw git abort. Consider committing/stashing
unrelated pending state rather than only erroring.

### Seams
- `src/coga/commands/launch_script.py:216` — uncommitted log append
- `src/coga/commands/launch.py:984-991` — `commit_log` pattern to mirror
- `src/coga/skill_manager.py:417,488` — preflight + the checkout that aborts

### Verification
- Add a test that a script step whose script switches branches succeeds when
  the launcher left a pending `coga/log.md` append (regression for this abort).
- `python -m pytest`; `coga validate --json`.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
