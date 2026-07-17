---
slug: install/init-next-steps-should-mention-agent-cli-requireme
title: Init next steps should mention agent CLI requirement
status: done
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
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
pr: https://github.com/FastJVM/coga/pull/589
branch: init-agent-cli-hint
worktree: /home/n/Code/claude/coga-init-agent-cli-hint

## Implement step — done (commit a873d1de, rebased onto 41ae58ef)

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

Verification: full suite green after the latest rebase onto 41ae58ef — 1227
passed, 1 skipped — via a scratch venv (python3.12) with the worktree
installed editable (`pip install -e`), because this machine's default python3
is 3.9 and pytest's `pythonpath=src` doesn't reach script subprocesses. The
previously-flaky `test_usage_probe.py` codex-probe tests passed on this run.

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

## Peer review — done (commit e7bdf307, rebased onto ad2ed0ae)

Native `codex review --base main` found one must-fix: the supervisor's
mid-workflow agent-rotation check still omitted the manifest install hint when
the next agent CLI was missing. The check now uses
`agent_cli_missing_message()` too, with a regression asserting Codex's install
URL. The fresh rebase preserved upstream's concurrent change making `gh`
optional at init while retaining this ticket's independent agent-CLI guidance.

Verification after the rebase: 107 focused tests passed; full Python 3.12 suite
passed with 1244 passed, 1 skipped via an editable scratch-venv install. Branch
is clean, two commits ahead of `origin/main`, and zero commits behind.

## Open-PR step — done

PR opened: https://github.com/FastJVM/coga/pull/589 (recorded under `## Dev`).
First `coga open-pr` attempt failed loud on a stale branch (origin/main had
moved with overlapping paths); rebased the worktree onto FETCH_HEAD (clean, no
conflicts) and re-ran the full Python 3.12 suite: 1276 passed, 1 skipped.
Retry pushed the rebased branch and opened the PR. Note: the globally installed
`coga` (uv tool, v0.2.0) predates `open-pr`; ran it from repo source via
`PYTHONPATH=src` with the uv tool's Python instead.

## Usage

{"agent":"claude","cache_creation_input_tokens":83957,"cache_read_input_tokens":976483,"cli":"claude","input_tokens":51,"model":"claude-fable-5","output_tokens":9190,"provider":"anthropic","schema":1,"session_id":"8751d17e-a64d-461d-98be-813ffe9be2f6","slug":"install/init-next-steps-should-mention-agent-cli-requireme","step":"implement","title":"Init next steps should mention agent CLI requirement","ts":"2026-07-16T04:26:49.093072Z","usage_status":"ok"}

## PR

Summary:

- Tell fresh users during `coga init` and in Getting Started that agent-driven commands require an installed, authenticated Claude Code or Codex CLI.
- Keep supported agent CLIs optional at init, but centralize manifest-backed install hints across launch, ticket, project, megalaunch, and chained-agent failures.

Test plan: `python -m pytest -p no:cacheprovider` under Python 3.12 with an editable install — 1244 passed, 1 skipped.
