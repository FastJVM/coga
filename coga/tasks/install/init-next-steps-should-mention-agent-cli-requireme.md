---
slug: install/init-next-steps-should-mention-agent-cli-requireme
title: Init next steps should mention agent CLI requirement
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

Init's "Next steps" tells a fresh user to run `coga build` without mentioning
that an agent CLI (Claude Code or Codex) must be installed and authenticated
first. The eventual failure is clear ("Agent CLI 'claude' not found in PATH")
but arrives after the user has committed to the flow. Add a line to the
next-steps output (and the README Getting Started, once it exists) naming the
agent-CLI prerequisite and where to get one. Consider whether agent CLIs
belong in the `coga.dependencies` manifest as `required_at_init=False`
entries so the point-of-need error carries an install hint too.

## Context

Found in the 2026-07-08 fresh-container retest (launch with pseudo-TTY, no
claude installed). Touchpoints: `src/coga/commands/init.py` (next-steps
block), `src/coga/dependencies.py`, README. Related:
`install/document-where-to-run-init-and-adopt-existing-repo` (the wider
Getting Started gap).

<!-- coga:blackboard -->

## Dev
branch: init-agent-cli-hint
worktree: /home/n/Code/claude/coga-init-agent-cli-hint

## Implement step — done (commit d0f3287b, rebased onto a546501f)

All three ticket asks landed:

- `src/coga/dependencies.py`: `claude` (https://claude.com/claude-code) and
  `codex` (https://github.com/openai/codex) added as `required_at_init=False`
  manifest entries. New helpers: `install_hint(name)` and
  `agent_cli_missing_message(cli)` — the latter appends the install hint when
  the manifest knows the binary, and still fails loud (no URL) for a custom
  `cli` value. Docstring's stale README-section name fixed ("External CLI
  Tools" → "Getting Started").
- Point-of-need sites now share that message: `commands/launch.py`,
  `commands/ticket.py`, `commands/project.py`, `megalaunch.py` (megalaunch's
  preflight detail string included — its casing changed from "agent CLI" to
  "Agent CLI"; no test asserted the old casing).
- `commands/init.py`: next-steps line "Install an agent CLI, if you haven't…"
  inserted before the `coga build`/`coga ticket` coax, URLs pulled from the
  manifest via `install_hint()` so docs can't drift.
- `README.md` Getting Started: names the prerequisite and that init itself
  works without it.
- Tests: new `tests/test_dependencies.py` (helpers + not-required-at-init);
  `test_init.py` gains dep-check-ignores-missing-agent-CLIs and
  next-steps-name-the-prerequisite; `test_launch.py`'s not-in-PATH test now
  asserts the install hint.

Verification: full suite green after rebase — 1214 passed, 1 skipped — via a
scratch venv with the worktree installed editable (`pip install -e`), because
this machine has no py3.11+ editable install and pytest's `pythonpath=src`
doesn't reach script subprocesses.

Adjacent issues found (for follow-up tickets, not fixed here):

- `tests/test_usage_probe.py` codex-probe tests are flaky under full-suite
  load (different ones failed on two runs: `..._primes_once_across_reads`,
  `..._primes_then_reads_fresh_rollout`; both pass 5/5 in isolation —
  likely an mtime/freshness timing race).
- `tests/test_launch_script.py::test_bootstrap_script_launch_is_stateless`
  fails on any checkout without a real editable install: the bootstrap
  script's subprocess can't import `coga` since pytest's `pythonpath` config
  doesn't propagate to child processes. Environmental, but a dev-setup trap
  worth documenting.
