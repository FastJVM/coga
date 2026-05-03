The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: codex/clear-step-field-done

## Notes

- Confirmed with Nick: implement code + tests + spec update, no one-shot backfill of existing done tickets.
- Current checkout had unrelated dirty files, so work is isolated in `.codex-worktrees/clear-step-field-done` from `origin/main`.
- Implemented `mark_done()` cleanup so every done transition removes stale `step` frontmatter, including manual bump and automerge callers.
- Verification:
  - `.venv/bin/python -m pytest tests/test_commands.py -k bump` -> 13 passed.
  - `.venv/bin/python -m pytest` -> 214 passed.
  - `../.venv/bin/relay validate --json` from `example/` -> no issues.
  - `.venv/bin/relay validate --json` from repo root is blocked by local config: `user` is missing from `relay-os/relay.local.toml`.
