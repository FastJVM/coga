---
slug: filter-relay-status-by-directory-group
title: Filter relay status by directory/group
status: done
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts:
- coga/cli
- coga/architecture
- coga/codebase
skills: []
workflow:
  name: code/with-self-review
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
---

## Description

Add directory/group filtering to `relay status`. Today `relay status`
lists every task in the repo with no way to slice by where the task lives.
Tasks live under `relay-os/tasks/` either as direct children
(`tasks/<slug>/`) or one level deeper inside an organizational group
(`tasks/<group>/<slug>/`). Users want to see only the tasks in one group
(e.g. `marketing`) or only the top-level/root tasks.

Add a filter so the operator can narrow `relay status` to a single
directory/group:

- `relay status <group>` (or a `--group <name>` flag — pick the more
  idiomatic shape for the existing CLI and note the choice in the
  blackboard) shows only tasks under `tasks/<group>/`.
- A way to show only root (un-grouped) tasks — e.g. `relay status root`
  or `relay status --root`. Decide the sentinel and document it.
- Unknown group → fail loud with a clear message listing available
  groups, not a silent empty list.

Keep `relay status` read-only (principle 6 — no network, no state
mutation as a side effect of rendering). Add tests under
`tests/test_status.py` covering: a group filter, the root filter, and the
unknown-group error. Update the `relay/cli` context's `relay status`
section to document the new filtering.

## Context

The `relay status` command lives in `src/relay/commands/`. The
group-qualified slug convention (`<group>/<leaf>`) and the
`tasks/<group>/<slug>/` vs `tasks/<slug>/` layout are described in the
`relay/architecture` context already in this prompt. Keep the change
markdown-first and legible; no new dependencies.

<!-- coga:blackboard -->

# Blackboard — filter-relay-status-by-directory-group

## Dev
branch: status-group-filter
worktree: ../relay-status-group-filter
commit: 8fbfafb
pr: https://github.com/FastJVM/relay/pull/368

## PR step — rebase done, PR opened (2026-06-16)
Per human decision (interactive), rebased `status-group-filter` onto current
`main` (ab220e4) BEFORE opening the PR, to reconcile with #366 "scaffold→create"
(ba88284) which had diverged over the same context/test files.
- 6 conflicts resolved (create.py — git tracked the scaffold.py→create.py rename;
  commands/recurring.py; architecture + current-direction contexts; test_recurring.py;
  test_smoke.py). All were the two vocabulary sweeps overlapping: kept main's
  scaffold→create wording + this branch's group→directory purge in each.
- Second commit (self-qa) applied clean. Branch now sits on main; vs-main diff is
  back to the branch's own 25 files (no more rename noise).
- Verified: full suite 749 passed, 1 skipped, same 2 pre-existing test_recurring
  failures (`..._syncs_period_task_and_high_water`,
  `..._sweep_skips_task_removed_by_create_sync` — note #366 renamed the 2nd from
  `..._scaffold_sync`). Confirmed both still fail on clean main ab220e4.
- CLI smoke on rebased code: `status marketing` filters; unknown dir → exit 2
  "Unknown directory ... Use 'root' ...".
- No CI checks configured on the repo (`gh pr checks 368`: none) — nothing to wait on.
- Pre-rebase backup ref: `status-group-filter-prerebase-backup` @ 0e43ee0.

## Review closeout (2026-06-16)
Reviewed the merged PR state from Codex on the owner review step.
- #368 merged as `f3d0c81` with the main status-directory implementation.
- Review found a few stale task-directory "group" phrases/test names after the
  merge; fixed those in follow-up #370, merged as `970f81e`.
- Concurrent PR #369 landed after #370 and reintroduced one stale
  `grouped-slug` phrase in `relay/current-direction`; fixed in #371, merged as
  `b29c153`.
- Verification on the review cleanup branches:
  - targeted status/tasks/create tests passed (24 passed for #370; 23 passed
    for #371's final context sweep after #369 landed).
  - full suite on #370: 749 passed, 1 skipped, same 2 pre-existing
    `tests/test_recurring.py` failures (`...period_task_and_high_water`,
    `...skips_task_removed_by_create_sync`).
  - CLI smoke from primary checkout with PR code: `relay status marketing`,
    `relay status root`, and unknown-dir exit 2 path all behaved as expected.
- Final terminology scan on current `main` only returns unrelated digest
  grouping usage, not task-directory vocabulary.

## Coga stale-state closeout (2026-06-26 PT)
This migrated Coga task was still `in_progress` at `step: 1 (implement)`, but
the blackboard above records the Relay implementation, PR, review, follow-up
cleanups, and merge closeout as already complete.

Verified the live Coga repo also already has the directory-native status
behavior:
- `coga status marketing` filters to `tasks/marketing/`.
- `coga status --no-recurse` shows only tasks directly under `tasks/`.
- `coga status definitely-not-a-dir` fails loud with exit 2 and lists known
  directories.
- `coga validate --task filter-relay-status-by-directory-group --json` is clean
  (`ok_count: 1`, no issues).

Decision: treat this as stale task state after the Relay→Coga migration and
close with `coga mark done`, not another implementation pass or bump through
already-completed workflow steps.

## SCOPE CHANGE (human, mid-task) — directory-native, no "group" vocab

Human pushed back on two things after the first pass:
1. **Real nested paths.** A task is a `ticket.md` directory at *any* depth
   under `tasks/`; filter by directory path (`relay status marketing/social`).
   `list_tasks` is no longer one-level — it recurses until it finds a
   `ticket.md`, never recursing into a task dir.
2. **No parallel vocabulary.** "group" was just "directory" under a confusing
   second name. Full sweep: purge the "group" *concept* across code + tests +
   contexts. (Generic English uses of the word — regex `match.group`, process
   group, digest "grouped by owner", sort-partition comments — left alone.)

Renames:
- `TaskRef.group` → `TaskRef.directory` (relative parent path under tasks/, or
  None at top level). `id_slug` = the task's path under tasks/.
- `list_groups` → `list_task_dirs` (recursive, returns relative dir paths).
- `filter_tasks_by_group` → `filter_tasks_under` (subtree filter: keeps a dir
  and everything nested below it).
- `UnknownGroupError` → `UnknownDirectoryError`; `ROOT_GROUP` → `ROOT_DIR`.
- Field consumers updated: scaffold.py, recurring.py, commands/recurring.py,
  commands/status.py. "group-qualified slug" → "qualified slug / path under
  tasks/" in docstrings + architecture/codebase/principles/cli contexts.
- `root` sentinel kept = "tasks directly under tasks/, no sub-dirs".
- status.py recurring-table split now matches dir == "recurring" OR under it.

## Design decisions (settled with human, interactive)

- **Filter shape: positional path arg.** `relay status marketing` shows tasks
  under `tasks/marketing/`. Chosen over `--group`/`--root` flags and over
  cwd-sensing. Rationale: the arg is "just a directory under tasks/", so it
  reads like `ls <dir>`.
- **Root sentinel: `root`.** `relay status root` shows only top-level
  (un-grouped) tasks. `root` is reserved; a real group literally named `root`
  would be shadowed — documented.
- **Group = directory, full stop.** A group is a child dir of `tasks/` with no
  `ticket.md` of its own (matches existing `list_tasks` discovery). No registry,
  no metadata, no `relay group` command. An *empty* group dir still counts as a
  known group (it exists because `mkdir` made it) -> filtering to it yields
  "(no tasks)", NOT an unknown-group error.
- **Unknown group -> fail loud** listing the real subdirectories of `tasks/`
  (principle 6). Known groups come from the filesystem, not from groups that
  currently happen to hold tasks.
- **Read-only preserved** (principle 6): filtering is a pure in-memory select
  over `list_tasks()` output; no new IO beyond reading `tasks/` dir entries.

## Why the human raised this / context note

The "group" concept is purely a directory — Relay never reimplemented it. You
manage groups with `mkdir` / `mv` / `rm`, not a Relay command. Human asked to
capture the broader principle: **reuse the substrate (filesystem, git, shell)
instead of reinventing a worse version** — that's a core reason Relay is
powerful for shell-fluent users. Capturing it in:
- `relay/principles` #3 (Obvious) — new sentence + receipt (group = directory).
- `relay/architecture` — the group-layout paragraph notes mkdir/mv/rm management.

## Verification
- `tests/test_status.py` (new, 10 tests) + `tests/test_tasks.py` pass.
- 2026-06-16 follow-up verification after terminology sweep:
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/n/Code/relay-status-group-filter/src /home/n/Code/relay/.venv/bin/python -m pytest -p no:cacheprovider tests/test_status.py tests/test_tasks.py tests/test_compose.py::test_compose_header_uses_resolved_nested_task_directory tests/test_validate.py::test_same_leaf_name_in_different_directories_validates_clean tests/test_recurring.py::test_scan_due_resumes_stuck_prior_run_instead_of_new_period`
  -> 26 passed.
- 2026-06-16 follow-up scan:
  `rg -n "\bgroup\b|group-qualified|grouped task|TaskRef\.group|list_groups|filter_tasks_by_group|UnknownGroupError|ROOT_GROUP" src/relay tests relay-os/contexts src/relay/resources/templates/relay-os/bootstrap/contexts src/relay/resources/prompt.md`
  now only returns regex/process grouping uses, not task-directory vocabulary.
- 2026-06-16 task validation from primary checkout:
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/n/Code/relay/src /home/n/Code/relay/.venv/bin/python -m relay.cli validate --task filter-relay-status-by-directory-group --json`
  -> ok_count 1, issues [].
- Full suite: 746 passed, 1 skipped, **2 pre-existing failures** in
  `test_recurring.py` (`test_recurring_launch_syncs_period_task_and_high_water`,
  `test_recurring_sweep_skips_task_removed_by_scaffold_sync`) — confirmed
  failing on clean `main` too, unrelated to this change. Left untouched per the
  implement skill (don't fix unrelated failures). Worth a follow-up ticket.
- Manual smoke vs real repo: `relay status marketing` (group only),
  `relay status root` (97 top-level), `relay status sales` →
  "Unknown group 'sales'. Available groups: auto, marketing, v2. Use 'root'…"
  exit 2.
- `relay validate` on example fixture: clean (no fixture change needed — this
  is a read-only filter, not a layout/composition change).
- Note for running tests here: system python is 3.9 (no tomllib); use
  `PYTHONPATH=$PWD/src /home/n/Code/relay/.venv/bin/python -m pytest`.

## Self-QA (2026-06-16)
Ran `/code-review` + `/simplify` against the branch's own commit diff
(reviewed vs merge-base d0c886a, since `main` has since diverged — see the
rebase note below — so a vs-`main` diff is 131 files of pure rename noise).

Findings applied (both consensus across the cleanup agents):
1. **Double `list_task_dirs(cfg)` walk** in `filter_tasks_under` — the
   unknown-directory error path walked `tasks/` a second time just to build the
   error message. Bound the result once (`available = list_task_dirs(cfg)`).
2. **Subtree-prefix predicate duplicated** between `filter_tasks_under` and
   status.py's local `_under_recurring` helper. Extracted a shared
   `tasks.is_under(directory, target)` (exported); both call sites use it now,
   and the `_under_recurring` closure is gone. Edge case verified: a sibling
   dir sharing a name prefix (`recurring-other`) is correctly NOT under
   `recurring` (the `target + "/"` boundary holds).

Skipped (noted, not a defect): the two near-identical `walk` closures in
`list_tasks` / `list_task_dirs` differ in recursion semantics (one stops at a
task, the other descends past a matched dir), so unifying them needs a
callback-returns-recurse abstraction heavier than the duplication it removes.

Re-verified: full suite 749 passed, 1 skipped, same **2 pre-existing**
`test_recurring.py` failures (`..._syncs_period_task_and_high_water`,
`..._sweep_skips_task_removed_by_scaffold_sync`) — confirmed still failing with
the self-qa refactor stashed, so unrelated. `is_under` smoke + test_status.py
(10) + test_tasks.py all green.

## ⚠️ Rebase note for the PR step
This branch was cut from a `main` that predates **#366 "Rename scaffold
vocabulary to create"** (ba88284), which renamed `src/relay/create.py` ⇆
`scaffold.py` and touched ~100 files. This branch still edits
`src/relay/scaffold.py`. Result: a vs-`main` diff is 131 files and the PR will
**conflict on the scaffold↔create rename**. The branch's *own* logical change
is only 25 files. Recommend rebasing onto current `main` (re-applying the
`TaskRef.group→directory` edits onto the renamed `create.py`) before/at the PR
step. Flagging for the human — not resolved in self-qa (out of this step's
scope, and a rebase is a design call).

## Files touched
- src/relay/tasks.py — recursive task discovery, `list_task_dirs`,
  `filter_tasks_under`, `UnknownDirectoryError`, `is_under` (self-qa)
- src/relay/commands/status.py — positional directory arg + filter
- tests/test_status.py — new
- src/relay/resources/prompt.md — base task-directory wording
- bootstrap/contexts/relay/cli (template) — status doc
- contexts/relay/principles (override + template) — principle note
- contexts/relay/architecture (override + template) — task-directory paragraph note
- recurring/period/current-direction contexts + tests — remove remaining
  task-directory "group" wording

## Usage

{"agent":"codex","cache_creation_input_tokens":null,"cache_read_input_tokens":222592,"cli":"codex","input_tokens":68571,"model":"gpt-5.5","output_tokens":4071,"provider":"openai","schema":1,"session_id":"019f0732-5830-72a2-b661-29559f983110","slug":"filter-relay-status-by-directory-group","step":"implement","title":"Filter relay status by directory/group","ts":"2026-06-27T03:50:57.770545Z","usage_status":"ok"}
