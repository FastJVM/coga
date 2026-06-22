The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev
branch: add-recurring-aliases
worktree: ../relay-add-recurring-aliases
pr: https://github.com/FastJVM/relay/pull/421
ci: no checks configured on this repo (`gh pr checks 421` → "no checks reported")

## Plan / notes
- Add two default aliases to `_DEFAULT_ALIASES` in `src/relay/cli.py`:
  - `skill-update` → `recurring launch skill-update` (mirror of `dream`)
  - `autoclose` → `recurring launch autoclose-merged` (renaming alias; legal,
    `_validate_aliases` only checks target verb is a built-in + no key collision;
    `recurring` is a built-in).
- Extend `tests/test_aliases.py` with dispatch round-trip coverage for both,
  mirroring `test_default_build_alias_dispatches_without_user_aliases_section`.

## Result
- Implemented both aliases + clarifying comment in `src/relay/cli.py`.
- Extended `tests/test_aliases.py`: `test_recurring_launch_aliases_are_defaults`
  + parametrized `test_default_recurring_alias_dispatches_without_user_aliases_section`.
- Full suite green: 842 passed, 1 skipped (hatchling packaging importorskip).
  Ran via `PYTHONPATH=<worktree>/src python3.12 -m pytest` (system python is 3.9,
  no tomllib; no .relay/.venv present).
- Committed on branch `add-recurring-aliases` (commit 8ac07f1). No push / no PR
  (left for code/open-pr).

## Discrepancy noted (not a blocker)
The ticket says "automerge is already a built-in" and asks for a comment
distinguishing `autoclose` (sweep merged PRs) from `automerge` (mark a merged
task done). In the actual code there is NO `automerge` command — it's not in
`_BUILTIN_COMMANDS` and nothing registers it. The merged-task close path is
`relay mark done` / the autoclose-merged recurring sweep (see
status.py:103 and the autoclose-merged ticket which says "no manual automerge
command"). I wrote the clarifying comment accurately rather than referencing a
command that doesn't exist.

## Peer review
- Ran `codex review --base main` from `../relay-add-recurring-aliases` after the
  sandboxed attempt failed with the known read-only app-server error. Review
  found no correctness issues and no must-fix findings.
- No code changes were made during peer review.
- Verification: `env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/n/Code/codex/relay-add-recurring-aliases/src python3.12 -m pytest -p no:cacheprovider`
  passed: 842 passed, 1 skipped.
