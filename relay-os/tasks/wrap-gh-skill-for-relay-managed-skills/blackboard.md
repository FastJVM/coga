## Creation Notes

Created from the bootstrap/orient session after checking current `gh skill`
docs. The user wants Relay-managed skills installed in `relay-os/skills`, a way
to install/remove from URLs, an update-all path, and a Dream PR so skill changes
are reviewed before merge.

Key decision: use `gh skill` as the substrate for GitHub-backed installs and
updates, but keep Relay wrappers for non-GitHub URLs, exact removal, local
adaptation conflict reporting, and PR/blackboard workflow.

External requirement: GitHub CLI `2.90.0+` with `gh skill` available. Do not
put this in Python `requirements.txt`; it is not a pip dependency.

## Dev

branch: codex/wrap-gh-skill-relay
worktree: /tmp/relay-gh-skill-worktree
pr: https://github.com/FastJVM/relay/pull/143

## Implementation Notes

- Added `relay skill` as a new CLI group with `install`, `install-url`,
  `install-local`, `update`, `remove`, and `status`.
- GitHub-backed installs/updates delegate to `gh skill` and fail loud with a
  GitHub CLI 2.90.0+ upgrade hint when `gh skill` is unavailable.
- URL-backed installs download/materialize a skill directory, install through
  `gh skill --from-local`, and write Relay-owned `.relay-source.json` metadata
  with original URL, selector, timestamp, content digest, source-tree digest,
  and installed-tree digest.
- URL-backed updates compare installed-tree digest first and skip local
  adaptations instead of overwriting; clean changed sources replace the skill
  tree and refresh metadata.
- `relay skill update --all --pr` renders a Dream-friendly summary, runs
  verification commands, and opens or updates one draft PR.

## Verification

- `env PYTHONPATH=src /home/n/Code/relay/.venv/bin/python -m pytest tests/test_skill_manager.py`
  -> 13 passed.
- `env PYTHONPATH=src /home/n/Code/relay/.venv/bin/python -m pytest -k 'not test_status_narrow_terminal_keeps_each_task_on_one_line'`
  -> 323 passed, 1 deselected.
- `env PYTHONPATH=src /home/n/Code/relay/.venv/bin/python -m pytest`
  -> 323 passed, 1 failed on existing
  `tests/test_commands.py::test_status_narrow_terminal_keeps_each_task_on_one_line`
  because `relay status` prints the totals summary as a fourth nonblank line.
- `env PYTHONPATH=/tmp/relay-gh-skill-worktree/src /home/n/Code/relay/.venv/bin/python -m relay.cli skill --help`
  -> passed.
- `env PYTHONPATH=src /home/n/Code/relay/.venv/bin/python -m compileall -q src/relay tests/test_skill_manager.py`
  -> passed.

## Follow-up: local gh upgrade

- Active `gh` before upgrade was `/home/n/.local/bin/gh` at 2.86.0; Ubuntu apt
  package candidate was older at 2.45.0.
- Downloaded official `cli/cli` v2.92.0 linux amd64 tarball and checksums to
  `/tmp/gh-upgrade`.
- Verified SHA256 for `gh_2.92.0_linux_amd64.tar.gz` matched
  `gh_2.92.0_checksums.txt`.
- Backed up old binary to `/tmp/gh-upgrade/gh.2.86.0.backup` and replaced
  `/home/n/.local/bin/gh` with the verified v2.92.0 binary.
- `gh --version`, `gh auth status`, and `gh skill --help` now pass.
