The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: codex/fail-loud-interactive-tty
pr: https://github.com/FastJVM/relay/pull/87

Plan:
- Base from current `origin/main` in a clean worktree because the primary checkout has unrelated modified task/spec/source files.
- Add a pre-lock TTY guard for interactive launches in `src/relay/commands/launch.py`.
- Add launch regression coverage for non-TTY interactive refusal, plus TTY-positive monkeypatches for existing interactive launch tests.
- Keep the `--no-launch` scaffold-only follow-up out of this PR; it is explicitly out of scope for this ticket.

Verification:
- `PYTHONPATH=/home/n/Code/relay/.codex-worktrees/fail-loud-interactive-tty/src /home/n/Code/relay/.codex-worktrees/chat-agent-selector/.venv/bin/python -m pytest tests/test_launch.py` -> 24 passed.
- `PYTHONPATH=/home/n/Code/relay/.codex-worktrees/fail-loud-interactive-tty/src /home/n/Code/relay/.codex-worktrees/chat-agent-selector/.venv/bin/python -m pytest` -> 214 passed.
- `PYTHONPATH=/home/n/Code/relay/.codex-worktrees/fail-loud-interactive-tty/src /home/n/Code/relay/.codex-worktrees/chat-agent-selector/.venv/bin/python -m relay.cli validate --json` from `example/relay-os` -> no issues.
- Repo-root validation in the clean worktree was blocked because `relay.local.toml` was absent and local config is intentionally gitignored; did not create or edit local config.
- PR #87 merged on 2026-05-03 with merge commit `5f1a7b581053c864d555178df872809157124159`.
