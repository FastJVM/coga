The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev
branch: rm-postmerge-hook
worktree: ../relay-rm-postmerge-hook
pr: https://github.com/FastJVM/relay/pull/320
commit: c6a0516 (includes peer-review fix; implement commit was 6c89aef)

## Status (peer-review step done)
- Ran required native review from the feature worktree:
  `codex review --base main`. The sandboxed attempt failed with the known
  read-only filesystem initialization error, then the approved out-of-sandbox
  run completed.
- Must-fix finding: repos upgraded from pre-bootstrap Relay could still have
  `.git/hooks/post-merge` pointing at `relay-os/hooks/post-merge`, so cleanup
  needed to remove that legacy Relay-owned symlink/target too.
- Applied fix and committed `c6a0516`:
  `_remove_post_merge_hook` now recognizes both `relay-os/bootstrap/hooks/post-merge`
  and legacy `relay-os/hooks/post-merge`; `init --update` keeps pruning the
  legacy `hooks` dir; the tracked legacy hook file is deleted; workflow/review
  docs and stale status comments now point to explicit `relay automerge` or
  launch freshness checks.
- Verification:
  `PYTHONPATH=/home/n/Code/codex/relay-rm-postmerge-hook/src /home/n/.local/bin/python3.12 -m pytest tests/test_init.py -q`
  → 67 passed.
  `PYTHONPATH=/home/n/Code/codex/relay-rm-postmerge-hook/src /home/n/.local/bin/python3.12 -m pytest -p no:cacheprovider`
  → 579 passed, 1 skipped, 1 pre-existing unrelated failure:
  `test_dream_worker_templates.py::test_cleanup_orphan_markers_declares_contract`.

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
`.git/hooks/post-merge` symlink. Peer-review also caught the older
pre-bootstrap target (`relay-os/hooks/post-merge`). So `_install_post_merge_hook`
is replaced by `_remove_post_merge_hook`, which deletes the symlink iff it
points at a Relay-owned hook target (never clobbers a user's own post-merge
hook).

### Files touched
- Delete `src/relay/resources/templates/relay-os/bootstrap/hooks/post-merge`
  (tracked) + live gitignored `relay-os/bootstrap/hooks/post-merge` + legacy
  tracked `relay-os/hooks/post-merge`.
- `commands/init.py` — replace install logic with `_remove_post_merge_hook`,
  rework `_UpdateResult` hook fields → `hook_removed: bool`, update prints,
  keep `_find_git_dir` (still needed to locate `.git/hooks`).
- `commands/update.py` — keep `"hooks"` as a legacy pre-bootstrap prune entry,
  drop `bootstrap/hooks` docstring mentions, drop the hooks chmod loop in
  `_chmod_packaged_executables`.
- `automerge.py` + `commands/automerge.py` docstrings — drop hook-caller mention.
- `commands/status.py` + `git.py` comments — drop post-merge hook mention.
- Contexts: `bootstrap/contexts/relay/cli` (packaged src) + tracked
  `relay-os/contexts/relay/sync` + packaged `bootstrap/contexts/relay/sync`.
- `README.md` automerge section.
- `tests/test_init.py` — remove hook install tests, fixture hook entries,
  EXPECTED_FILES entry, `_UpdateResult` construction hook fields.
