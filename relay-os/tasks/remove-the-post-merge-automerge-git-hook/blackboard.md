The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev
branch: rm-postmerge-hook
worktree: ../relay-rm-postmerge-hook
pr: (pending — opened in code/open-pr step)
commit: 6c89aef

## Status (implement step done)
- Implemented per scope + Nick's uninstall-on-update decision. Committed.
- Tests: `PYTHONPATH=$PWD/src /home/n/.local/bin/python3.12 -m pytest` →
  578 passed, 1 skipped, **1 pre-existing failure unrelated to this work**:
  `test_dream_worker_templates.py::test_cleanup_orphan_markers_declares_contract`
  (asserts a substring that the SKILL.md wraps across a line break; fails on
  `main` too — left alone, not in scope).
- New unit coverage: `_remove_post_merge_hook` (dangling symlink, live
  symlink, user hook untouched, foreign symlink untouched, no-git no-op,
  idempotent).
- Note for `.relay/.venv`: it's py3.12 but has no pytest; the conda pytest is
  py3.9 (no tomllib). Used `/home/n/.local/bin/python3.12` (pytest 9.0.3).

## Plan / decisions

Removing the post-merge automerge git hook entirely. Following the ticket
scope. **Decision with Nick (2026-06-08):** also add *uninstall-on-update* —
since `relay init --update` wholesale-mirrors `bootstrap/` and wipes the hook
target, existing repos would otherwise keep a now-dangling
`.git/hooks/post-merge` symlink. So `_install_post_merge_hook` is replaced by
`_remove_post_merge_hook`, which deletes the symlink iff it points at our
(now-gone) bootstrap hook (never clobbers a user's own post-merge hook).

### Files touched
- Delete `src/relay/resources/templates/relay-os/bootstrap/hooks/post-merge`
  (tracked) + live gitignored `relay-os/bootstrap/hooks/post-merge`.
- `commands/init.py` — replace install logic with `_remove_post_merge_hook`,
  rework `_UpdateResult` hook fields → `hook_removed: bool`, update prints,
  keep `_find_git_dir` (still needed to locate `.git/hooks`).
- `commands/update.py` — drop `"hooks"` prune entry, drop `bootstrap/hooks`
  docstring mentions, drop the hooks chmod loop in
  `_chmod_packaged_executables`.
- `automerge.py` + `commands/automerge.py` docstrings — drop hook-caller mention.
- `commands/status.py` + `git.py` comments — drop post-merge hook mention.
- Contexts: `bootstrap/contexts/relay/cli` (packaged src) + tracked
  `relay-os/contexts/relay/sync` + packaged `bootstrap/contexts/relay/sync`.
- `README.md` automerge section.
- `tests/test_init.py` — remove hook install tests, fixture hook entries,
  EXPECTED_FILES entry, `_UpdateResult` construction hook fields.
