---
slug: install/improve-reinit-already-exists-message
title: Improve reinit already-exists message
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: codex
contexts:
- dev/code
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 2 (peer-review)
---

## Description

Running `coga init` in an already-initialized repo prints only
"`/path/coga` already exists." with no next step. `--update` no longer
exists, so the user is left guessing what re-running init was supposed to do.
Extend the refusal with the actual remedies: upgrading the CLI is
`pip install --upgrade coga` (batteries resolve from the package, no re-init
needed); a broken/partial `coga/` is recovered by fixing the cause or
removing the dir; `coga uninstall` removes the footprint.

## Context

Found in the 2026-07-08 fresh-container retest. The old `--update` wedge
(`install/init-does-not-persist-user-then-blocks-on-reinit`) is fixed — init
is atomic with verified rollback — this is just the terse message left
behind. Touchpoint: `src/coga/commands/init.py` (`_do_init`, the
`coga_os.exists()` refusal).

<!-- coga:blackboard -->

## Dev
branch: reinit-message
worktree: /home/n/Code/claude/coga-reinit-message

## Notes

- Touchpoint confirmed: `src/coga/commands/init.py` `_do_init`, the
  `coga_os.exists()` refusal at the top (exit 2, message was just
  "`<path>` already exists.").
- `coga uninstall` exists (`src/coga/cli.py` registers it), so the message can
  reference it safely.

## Implemented (commit b9bffc79)

- Extended the refusal to four lines, keeping exit 2 and red/stderr styling
  consistent with the neighboring refusals: already initialized; upgrade CLI
  via `pip install --upgrade coga` (batteries resolve from the package, no
  re-init); broken/partial coga/ → fix the cause or remove the dir, re-run
  init; `coga uninstall` removes the footprint. All three ticket remedies
  covered.
- Extended `tests/test_init.py::test_init_refuses_existing_coga_os` to pin the
  remedies (pip upgrade, uninstall, remove-the-dir) with a docstring saying
  why.
- Verified: full suite green in a py3.12 venv (1207 passed, 1 skipped) and an
  end-to-end smoke of `coga init` against an existing coga/ prints the new
  message with exit 2.
- Environment note (not a code issue): the repo checkout has no editable
  install for a 3.11+ interpreter; `tests/test_launch_script.py::
  test_bootstrap_script_launch_is_stateless` fails without one (its subprocess
  imports `coga`), on unmodified main too. Green once coga is pip-installed
  editable (per CLAUDE.md dev setup).
