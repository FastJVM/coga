---
slug: commit-post-session-coga-writes-usage-record-spool
title: Auto-commit dirty coga/ state (machine writes + manual edits) so the tree stays
  clean
status: in_progress
autonomy: interactive
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
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
step: 1 (implement)
---

## Description

Coga's always-on git sync commits only the task dir + `log.md` on state
transitions, so a class of side-effect writes under `coga/` is structurally
left uncommitted and the working tree on `main` stays permanently dirty. The
dominant source is the **per-session `## Usage` record**: `coga launch`'s
`finally` block appends it to the ticket blackboard *after the agent session
exits*, i.e. after the agent already ran its final `coga bump`/`mark` that did
the last sync. Nothing comes back to commit it, so every finished/parked task
accumulates a dangling usage line. Secondary sources: stray `coga/log.md`
launch lines that don't ride a later `sync_paths`, and the
`coga/recurring/digest/spool.md` append-only spool, which is part of no
task-dir sync.

The requirement is broader than machine writes: humans also hand-edit ticket
bodies, blackboards, and contexts directly in the working tree, and those edits
must be recorded too. So the target invariant is **all dirty tracked content
under the `coga/` subtree gets committed automatically** — machine
side-effects (usage record, spool, stray log) *and* human hand-edits alike.

Fix: at session end (and/or as a shared step in the coga commands that already
sync) commit everything dirty under `coga/`, scoped to the `coga/` subtree so
files outside it (`src/`, `tests/`, product code) are **never** swept in. This
does *not* violate the existing "never `git add -A`" rule — that rule exists to
protect a feature worktree's uncommitted **code** (`coga/sync` SKILL.md,
"Scope is narrow"), and `coga/` is exactly the OS-state boundary that rule
draws the line at. Widening from "one task's dir" to "the whole `coga/`
subtree" stays on the OS-state side of that line.

Done = after any coga session/command, `git status` shows no dirty tracked file
under `coga/` attributable to it, on both the control-branch and feature-branch
paths, with `src/`/`tests/` edits left untouched.

## Mechanism (decided)

Use a **primitive invoked per mutating command**, NOT a filesystem watcher.

A daemon / `inotify` watcher is rejected on principle: `coga/architecture`
states "There is no database, no daemon, no in-memory state." A watcher is
invisible background state that races with the very commands writing these
files, needs supervision/restart, and makes commit provenance un-traceable. Its
only win is *instant* commits, which we don't need.

Instead, factor one subtree-scoped primitive — conceptually
`git.sync_coga_state(cfg, message="coga: sync state")`, committing everything
dirty under the `coga/` subtree (reusing the existing branch-aware
commit/overlay machinery, never `git add -A`) — and call it from a single
shared boundary at the **end** of every mutating command (a `finally`/`atexit`
in the CLI dispatch) plus the launch teardown, *after* `capture_session`.

Semantics to document (and accept): a human hand-edit made in an editor commits
on the **next coga command**, not the instant they save. Lazy/on-access
convergence — the working tree is the source of truth, git catches up at the
next invocation. This is the deliberate alternative to a daemon's zero-latency
commit.

Hard constraints:
- The primitive must **never** run from read-only commands (`status`, `show`,
  `validate`) — `coga/principles` #6 forbids those from mutating as a
  side effect of rendering. Wire it to mutating commands + the launch boundary
  only, not a blanket all-commands hook.
- A single sweep may commit heterogeneous changes (a usage append + a human's
  ticket edit) under one message; that's acceptable for OS state, but the
  message should name it as a state sync rather than impersonate a specific
  transition.

Design question still open for implement (decide explicitly, write to the
blackboard): today's cross-branch sync lands only the *current* task's dir on
the control branch via the temp-index overlay. A `coga/`-subtree sweep would
also land hand-edits to *other* dirty tickets/contexts. Is that wanted (shared
OS state converging on `main`), or should the sweep stage the whole `coga/`
subtree but only on the control-branch path, leaving cross-branch landing still
task-scoped? This changes the semantics from "this command commits its own
task" to "this command commits all dirty OS state."

## Context

Key code:
- `src/coga/commands/launch.py:784-799` — the `finally` block that calls
  `usage_tracking.capture_session(...)` with no sync afterward. This is the
  structural root cause; the usage line is always written past the last commit.
- `src/coga/usage.py` — `capture_session` → `append_record` writes the
  `## Usage` JSON into the ticket blackboard.
- `src/coga/git.py` — `sync_paths` / `sync_task_state` / `sync_log`. Note the
  deliberate path-scoping (module docstring + `git.py:108-111`): Coga never
  `git add -A`, so the fix must pass explicit paths. `sync_log` already exists
  for the log-only case; `launch.py:752-758` shows the gated `commit_log` path.
- Digest spool writer: `src/coga/spool.py` and the digest drain job
  (`src/coga/commands/digest.py`).

Behavioral contract to keep in sync: the `coga/sync` context (attached) — and
its packaged twin under
`src/coga/resources/templates/coga/bootstrap/contexts/coga/sync/SKILL.md`.
Update both if behavior changes (per CLAUDE.md's "update the matching context
in the same PR").

Watch out for:
- The feature-branch path: `coga/` state written/edited while an agent is on
  its PR branch must land via the same cross-branch temp-index overlay
  (`_build_overlay_tree`), not get swept into the feature commit incorrectly.
  The `coga/`-subtree boundary keeps `src/`/`tests/` code out regardless.
- The `merge=union` files inside `coga/` (`log.md`, the digest spool) must keep
  riding the local-commit + union-merge path, never the cross-branch overlay
  (which replaces the file wholesale and drops concurrently-appended lines).
  See `git.py`'s `local_rels` vs `rels` split — a `coga/`-wide sweep must
  preserve that distinction.
- The `coga.toml` extension-fields / required-field edits are also `coga/`
  content; make sure the sweep doesn't trip validation on an in-flight draft.

Add a test: a launch teardown (and a hand-edit-then-bump) leaves no dirty
tracked file under `coga/`, while a dirty `src/` file is left untouched. The
current 5 dirty files in the working tree (3 usage appends, 1 `log.md` line, 1
spool block) plus my own in-flight edits to *this* draft are a live example of
the symptom.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
