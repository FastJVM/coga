The blackboard is a notepad to be written to often as the human and agent works through a task.

## Findings (2026-06-11, implement step)

The bug this ticket describes is already fixed on main. The ticket's premise
and all four of its pointers are stale:

- `src/relay/launch_script.py` does not exist — the code is
  `src/relay/commands/launch_script.py` (`run_script_mode`).
- On non-zero exit, `launch_script.py:152-162` already calls `slack.post`
  with the slug, title, exit code, and failing step name. Present since the
  Slack-simplification commits (9b4b7c2 / 54ab04a), later reworded by
  4759b9a ("💥 script failed on …").
- `slack.post_feed` doesn't exist in the current tree — the helper is
  `slack.post(cfg, message, *, task_path, owner, watchers)`.
- `docs/spec.md` and `docs/spec-audit.md` are no longer on disk.

## Residual gaps (small, optional)

1. The Slack message omits the "pointer to the log file" the ticket asked
   for — it names slug + exit code + step, but not `log.md`'s path.
2. No test asserts the Slack post fires on failure —
   `tests/test_launch_script.py::test_script_mode_nonzero_exit_logged` only
   checks the log line.

## Decision (2026-06-11)

Human reviewed the findings and chose to close the ticket as already-done.
No code change made; the residual gaps (log-path in message, missing test
for the Slack post) were judged not worth pursuing. Closed via
`relay mark done`.
