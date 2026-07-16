---
slug: move-per-session-usage-records-from-ticket-blackbo
title: Move per-session usage records from ticket blackboards to log.md
status: in_progress
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
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 4 (review)
---

## Description

Move the per-session usage records `coga launch` captures out of each
ticket's `## Usage` blackboard section and into the repo-global
`coga/log.md`, as ordinary tagged JSON lines.

Why: the blackboard is composed into every launch prompt, so usage records —
pure accounting history no agent needs for the next step — bloat every future
prompt on that ticket. `log.md` is the durable-history home: append-only,
never composed, tagged per task, and it outlives the task (`coga delete` /
retire removes the task directory and today takes its usage history with it).
It also removes the extra `sync_coga_state` commit in
`src/coga/commands/launch.py` that exists only because the record lands in
the ticket *after* the agent's final bump/mark sync — `log.md` already has
its own conflict-free merge=union sync path (`sync_log`).

Decided (2026-07-16, owner): write the existing `UsageRecord` JSON line
directly into `log.md` as the entry's payload — JSON is human-readable
enough; no sibling `usage.jsonl` file. Keep the standard log-line tagging
(task ref + timestamp) so `coga usage --task` filtering still works.

Scope:

- `capture_session` / `append_record` in `src/coga/usage.py`: append the
  record to `log.md` (via the shared `append_log` path so formatting and
  tagging stay uniform) instead of the ticket's `## Usage` section.
- `coga usage` rollup (`load_records` / `_usage_blackboards`): parse records
  from `log.md` instead of globbing every ticket `.md`.
- Drop the post-capture `sync_coga_state` call in `commands/launch.py`;
  reuse the log sync instead.
- Migration (decided 2026-07-16, owner): drop existing `## Usage` records —
  no back-compat parsing, the rollup reads `log.md` only. History is
  reconstructible later from the agent CLIs' own session files if ever
  needed. Remove the stale `## Usage` sections from live tickets in the
  same PR so no orphaned records linger.
- Update the `coga/cli` context (`coga usage` description) and the
  architecture context if it names the `## Usage` blackboard section;
  packaged copies under `src/coga/resources/templates/` and any live
  `coga/contexts/` override in the same PR.
- Tests: `tests/test_usage*.py` and any launch tests asserting the
  blackboard write.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Plan (implement step)

- `src/coga/usage.py`: drop `USAGE_HEADING` / `_USAGE_SECTION_RE` /
  `_SECTION_RE` / `_usage_blackboards`. `append_record(cfg, record)` writes
  `record.to_json()` via `logfile.append_log(cfg, record.slug, "system", ...)`
  so the line gets standard timestamp+ref+actor tagging. `capture_session`
  takes `cfg: Config` instead of `blackboard: Path`. `load_records(cfg)`
  reads `log.md` (via `paths.log_path`), strips the
  `YYYY-MM-DD HH:MM [ref] [actor] ` prefix with a regex, and feeds the
  payload to `UsageRecord.from_json`; non-JSON log lines are skipped.
- `src/coga/commands/launch.py`: `should_capture_usage` no longer checks the
  ticket file; capture passes `cfg`; post-capture `git.sync_coga_state(cfg)`
  becomes `git.sync_log(cfg, message=f"Log: {ref.id_slug}")` (union-safe,
  also carries the launch line for task launches).
- `src/coga/commands/usage.py`: `load_records(cfg)`; wording updated.
- Contexts: rewrite store/capture/read/tradeoff sections of
  `coga/contexts/coga/usage/SKILL.md` (live only — no packaged copy exists);
  update `coga/contexts/coga/sync/SKILL.md` + packaged copy (usage record is
  now a `log.md` append committed by `sync_log` at launch teardown;
  `sync_coga_state` stays wired only at the CLI dispatch boundary).
  Note: ticket asks to update the `coga/cli` context's `coga usage`
  description, but no live `coga/cli` context exists and the packaged one
  never mentions usage — nothing to change there.
- Migration: strip `## Usage` sections (heading + records) from all live
  tickets under `coga/tasks/` (~60 files). No back-compat parsing.
- Tests: rework `tests/test_usage.py` append/load tests around `log.md`;
  rework `tests/test_launch.py::test_spawn_sweeps_usage_record_at_teardown`
  (now asserts the log commit+push, ticket untouched) and the
  captures-usage-with-session-id test (`cfg` kwarg instead of `blackboard`).

## Dev

pr: https://github.com/FastJVM/coga/pull/562
branch: usage-records-to-log
worktree: /home/n/Code/claude/coga-usage-to-log

## Implemented (implement step, 2026-07-15)

Two commits on the branch, rebased onto origin/main (981047ad):

- `Move per-session usage records from ticket blackboards to log.md` —
  `usage.py`: `append_record(cfg, record)` writes the record JSON through
  `logfile.append_log` (line shape `YYYY-MM-DD HH:MM [<slug>] [system]
  <json>`); `capture_session` takes `cfg` instead of `blackboard`;
  `load_records(cfg)` parses `log.md` lines, skipping any whose message
  isn't a valid record. Launch teardown now runs `git.sync_log` (not
  `sync_coga_state`); the `## Usage`/section machinery and
  `_usage_blackboards` glob are gone. Contexts: `coga/usage` rewritten,
  `coga/sync` rewired (live + packaged copy kept identical).
- `Drop migrated ## Usage sections from live tickets` — stripped 61 ticket
  files; zero `^## Usage` matches remain anywhere under `coga/`.

Decisions / notes:

- Log-line actor for usage records is `system` (capture is launcher
  machinery, not an agent act); the task ref tag is the record's slug, so
  `coga show` history picks usage lines up too.
- Behavior change pinned in tests: launch teardown commits *only* `log.md`;
  human hand-edits under `coga/` now commit at the next CLI dispatch
  boundary instead of being swept at teardown
  (`test_spawn_commits_usage_log_at_teardown`).
- Ticket's `coga/cli` context touchpoint was a no-op: no live `coga/cli`
  context exists and the packaged one never mentions usage.
- Verified end-to-end: append→`coga usage` rollup round-trip through
  `log.md` in the worktree, plus `coga usage --json` on the migrated repo
  (empty rollup, as expected post-migration).
- Tests: `python -m pytest` → 1219 passed, 1 skipped, 1 failed —
  `test_bootstrap_script_launch_is_stateless`, which also fails on clean
  main in this environment (subprocess `run.py` cannot `import coga`;
  same known env-only failure recorded on make-megalaunch-user-specific's
  blackboard). Not caused by this change.
- Rebase onto 981047ad conflicted on 3 migrated tickets (new usage records
  had landed on main); resolved by taking main's version and re-running the
  strip, so records appended after the branch point are also removed.

## Peer review (2026-07-15)

- Native `codex review --base main` found no functional regressions.
- Applied one must-fix source-contract correction: `sync_coga_state` no longer
  claims per-session usage is a blackboard side effect it sweeps; launch now
  appends and commits the usage line through `sync_log`.
- Rebasing onto current `origin/main` reintroduced this task's newly captured
  `## Usage` section after the original migration commit. Removed it in the
  peer-review commit and confirmed zero `^## Usage` headings remain under
  `coga/` on the feature branch.
- Branch is clean, three commits ahead of `origin/main`, and rebased onto
  `b78be8cd`.
- Verification: `python -m pytest` -> 1219 passed, 1 skipped, 1 failed. The
  sole failure is the environment-only
  `test_bootstrap_script_launch_is_stateless` subprocess import failure; it
  reproduces on `main`. Focused usage/launch verification: 8 passed.

## PR

Move per-session agent usage records out of ticket blackboards and into tagged
JSON payloads in the repo-global `coga/log.md`. `coga usage` now reads the log,
launch teardown commits only the union-safe log path, stale live `## Usage`
sections are removed without back-compat parsing, and the usage/sync contracts
and tests describe the new durable-history boundary.

Test plan: `python -m pytest` (1219 passed, 1 skipped; one environment-only bootstrap subprocess import failure reproduced on `main`).
