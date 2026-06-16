# Blackboard — filter-relay-status-by-directory-group

## Dev
branch: status-group-filter
worktree: ../relay-status-group-filter
commit: 0e43ee0

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
