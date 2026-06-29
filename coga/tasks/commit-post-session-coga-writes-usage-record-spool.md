---
slug: commit-post-session-coga-writes-usage-record-spool
title: Auto-commit dirty coga/ state (machine writes + manual edits) so the tree stays
  clean
status: in_progress
autonomy: interactive
owner: nicktoper
human: nicktoper
agent: claude
assignee: codex
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
step: 2 (peer-review)
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

## Findings (implement step, session 1)

Code map confirmed:
- `cfg.repo_root` **is** the `coga/` subtree (holds `coga.toml`); git toplevel is
  its parent. So "everything dirty under `coga/`" == everything dirty under
  `cfg.repo_root`. Sweep pathspec = repo-relative `coga` (or whatever
  `repo_root` resolves to relative to the git root).
- `git.py` already has the exact machinery to generalize:
  `sync_paths(cfg, anchor, paths, message)` does the branch-aware commit+land
  with the **`local_rels` (commit, incl. union files) vs `rels` (overlay set,
  excl. union files)** split. The new primitive is essentially `sync_paths`
  with the path set computed as "all dirty tracked files under `coga/`" and the
  union split generalized from "just log.md" to "any `merge=union` file".
- Union detection: `git check-attr merge -- <files>` cleanly reports
  `merge: union` for `log.md` and `recurring/digest/spool.md` (there is a
  `coga/.gitattributes`). Use that instead of hardcoding paths — future-proof.
- Digest commit-subject filter: `digest.py::_is_coga_state_sync_commit` filters
  `Sync task state:` and `Ticket: <slug> — <status>`. The sweep's commit
  subject must be added here so swept commits don't show up under "Also merged".
- Wiring: meaningful per-command syncs (`Ticket: <slug> — bump` etc.) stay
  UNCHANGED — they carry the human-readable git history + digest semantics. The
  sweep is an **additional catch-all** that no-ops when the command already
  committed everything (common case). It runs at: (a) launch teardown finally,
  after `capture_session` (the dominant root cause), and (b) a CLI-dispatch
  boundary for mutating commands only (read-only `status`/`show`/`validate`
  excluded by an explicit name set, per principles #6).

Test harness: `tests/test_git.py` + `git_repo` fixture (real git, bare origin).
Mirror `test_sync_lands_on_main_from_feature_branch` /
`test_sync_scopes_commit_to_the_task_dir` style for the new tests.

## Open decisions — RESOLVED by human (session 1)

1. **Cross-branch scope:** land *all* dirty `coga/` OS state on `origin/main`
   from any branch (generalize `sync_paths` exactly; union files stay
   local-only + union-merge). Semantics: "this command commits all dirty OS
   state."
2. **Untracked files:** the sweep DOES `git add` new untracked files under
   `coga/` too (not just tracked modifications). So enumeration = full
   `git status --porcelain` under the subtree (modified + deleted + untracked +
   renamed).

## Dev

branch: commit-coga-state-sweep
worktree: /home/n/Code/claude/coga-state-sweep

## Implementation plan

- `git.py`: add `sync_coga_state(cfg, *, message="Sync coga state")`.
  - git root via `_toplevel(cfg.repo_root)`; subtree pathspec = repo_root rel.
  - enumerate changed paths: `git status --porcelain -z -- <subtree>` (incl.
    untracked + deletions + renames). Empty → clean no-op.
  - union split via `git check-attr merge -z -- <paths>`: union files →
    local-commit set only; non-union → overlay (cross-branch land) set.
  - reuse a shared branch-dispatch (extracted from `sync_paths`):
    control-branch → commit local_rels + push (union rides push-rebase);
    feature/detached → local commit of local_rels, land overlay_rels on main.
  - non-fatal on GitError (stderr + `append_log`), mirroring `sync_paths`.
- `launch.py` `_run_agent_session` finally: after `capture_session`, call
  `git.sync_coga_state(cfg, ...)` so each step's usage record commits promptly
  (supervised chains don't reach the CLI-dispatch finally between steps).
- `cli.py` `main()`: wrap `app()` in a finally that sweeps for mutating
  commands (explicit non-sweep set: status/show/validate/usage/init/uninstall;
  skip when cfg is None or argv[0] is an option). This is the
  "hand-edit commits on next command" boundary.
- `digest.py`: add the sweep subject to `_is_coga_state_sync_commit` so swept
  commits never render under "Also merged (no ticket)".
- Sync BOTH `coga/sync` SKILL.md copies (live + packaged bootstrap twin).
- Tests in `tests/test_git.py` mirroring `git_repo` style: usage-record sweep
  leaves coga/ clean while a dirty `src/` file is untouched; feature-branch
  sweep lands non-union files on main + keeps union files local; hand-edit
  sweep on next command.

## Implement step — DONE (session 1)

Committed on `commit-coga-state-sweep` (worktree clean). Full suite green:
`912 passed, 1 skipped`.

What landed:
- `git.py`: `sync_coga_state(cfg, *, message="Sync coga state")` + extracted
  `_dispatch_branch_sync` (now shared with `sync_paths`, so the detached-HEAD
  stderr message is generic "changes landed on …" — existing test only asserts
  the "detached HEAD" substring, still passes). Helpers `_changed_paths_under`
  (`git status --porcelain -z` under the subtree, incl. untracked/deletes/
  renames) and `_union_merge_paths` (`git check-attr merge -z` — future-proof,
  no hardcoded paths).
- `launch.py`: sweep call in the teardown `finally`, inside the
  `should_capture_usage and spawn_started` block, right after
  `capture_session` (per-step usage record commits promptly).
- `cli.py`: `_sweep_coga_state` + `_NON_SWEEPING_COMMANDS` frozenset; `app()`
  wrapped in `try/finally`. Excludes status/show/validate/usage/init/uninstall,
  `--help`/`-h`, option-only argv, and `cfg is None`.
- `digest.py`: `_is_coga_state_sync_commit` now also filters `Sync coga state`.
- Both `coga/sync` SKILL.md copies updated (kept byte-identical via `cp`).
- `conftest.py`: fixture now seeds `coga/.gitattributes` (union marking) AND
  stubs `sync_coga_state` in `_stub_git` (so non-git tests don't shell out).

Decisions realized: cross-branch lands ALL non-union dirty coga/ on main (Q1=A);
sweep includes untracked files (Q2). Both per the human's answers this session.

Note for reviewer: the per-session sweep is gated on `should_capture_usage`
(only fires when usage was captured) — chosen because the usage record is the
only per-step machine write past the last sync; non-usage sessions are covered
by the CLI-dispatch sweep at launch exit. Flag if you'd prefer it unconditional
on `spawn_started`.

NEXT: peer-review step (step 2). No push / PR yet — that's `code/open-pr`
(step 3).
