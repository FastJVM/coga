# Blackboard — filter-relay-status-by-directory-group

## Dev
branch: status-group-filter
worktree: ../relay-status-group-filter

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

## Files touched
- src/relay/tasks.py — list_groups, filter_tasks_by_group, UnknownGroupError
- src/relay/commands/status.py — positional group arg + filter
- tests/test_status.py — new
- bootstrap/contexts/relay/cli (template + live) — status doc
- contexts/relay/principles (override + template) — principle note
- contexts/relay/architecture (override + template) — group paragraph note
