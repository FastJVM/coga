The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: remote-default-origin
worktree: ../relay-remote-default-origin

## Findings

- The configurable infrastructure already existed before this ticket:
  `Config.git_remote` is parsed from `[git].remote` (default `origin`) in
  `config.py:_parse_git`, and `git.py`, `digest.py`, `recurring.py`,
  `validate.py`/`github_preflight.py` already use `cfg.git_remote`.
- The only true hardcoded push the ticket names was `skill_manager.py`
  `open_or_update_pr` (`git push --force-with-lease -u origin <branch>`).
- Skill prompts (`code/open-pr`, `dev/code` context, etc.) say "push the
  branch" generically — none hardcode `origin`, so there was nothing to
  sweep in the prompts. Remaining `origin` mentions in `git.py` are
  comments/docstrings, not commands.

## Change

- `skill_manager.open_or_update_pr` gains a `remote: str = "origin"` kwarg
  and uses it in the push.
- The one caller, `run_skill_update_pr_flow`, passes `cfg.git_remote`.
- Regression test `test_dream_pr_summary_pushes_to_configured_non_origin_remote`
  in `tests/test_skill_manager.py`: with `[git] remote = "upstream"`, the
  push uses `upstream` and no git command mentions `origin`.

## Test status

- `python3.12 -m pytest tests/test_skill_manager.py` → 33 passed.
- Full suite: 807 passed, 1 skipped, **2 failed** in
  `tests/test_autoclose_sweep.py`
  (`..._live_and_packaged_copies_stay_in_sync`,
  `..._recurring_template_creates_idempotently`). These are PRE-EXISTING and
  fail identically on `main` — they assert a hardcoded
  `last_serviced_period` date that drifts with the current date
  (expected `2026-06-11`, got `2026-06-17`). Unrelated to this change; not
  masked, just noted.
- Note: repo needs Python 3.11+ (`tomllib`); use `python3.12` here.
