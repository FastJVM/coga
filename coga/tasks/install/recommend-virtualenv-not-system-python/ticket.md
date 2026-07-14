---
slug: install/recommend-virtualenv-not-system-python
title: Onboarding install should use a virtualenv, not system Python
status: in_progress
mode: agent
owner: zach
human: zach
agent: claude
assignee: zach
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
step: 4 (review)
---

## Description

Following the README, a new user installs Relay's dependencies into their system
Python; many external users won't want their system Python polluted. Make the
recommended install path a virtualenv (create + activate + install), with a
global/system install as an explicit opt-out. While in the same README install
block, also fix the `python` vs `python3` nit — macOS ships only `python3`, so
the copy-pasted command fails out of the box.

## Context

Reported by Greg; he got it working in a venv himself, but only by deviating
from the docs. Touchpoint: README Getting Started / quickstart, currently under
editorial revision in `marketing/readme-and-docs`. Distinct from
`document-cross-machine-sandbox-dev-loop-friction-i` (that captures the
*contributor* dev-loop python-version friction — .venv 3.9 vs the 3.11+ Relay
needs); this one is about first-time *user* onboarding.

<!-- coga:blackboard -->

## Dev
pr: https://github.com/FastJVM/coga/pull/542
branch: readme-venv-install
worktree: /home/n/Code/claude/coga/.coga/worktrees/coga-readme-venv-install

## Findings (implement step)

- "Relay" in the ticket is Coga's pre-rename name (see docs/migrating-to-coga.md);
  the touchpoint is this repo's top-level README.md.
- The README was rewritten since the ticket was filed (#520) and now leads with
  `uv tool install coga`, which is already venv-isolated — the spirit of the
  ticket's "recommended path" is satisfied by keeping that lead.
- Residual problems the ticket still covers: the plain-`pip` block installs into
  whatever Python is active (system Python for a new user) with no warning, and
  the from-source block uses `python -m pip install -e .` — both system-Python
  installs, and `python` doesn't exist on stock macOS (only `python3`).
- No tests pin README install copy; README is not mirrored under
  src/coga/resources/templates (test_init vendors the host repo's README at
  runtime, not a static copy). CLAUDE.md's contributor build command left
  untouched — ticket scopes to the README install block.
- marketing/readme-and-docs (broader editorial pass) is in_progress but
  currently sitting with the human at its design step; this scoped fix doesn't
  conflict.

## Decisions

- Kept `uv tool install coga` as the first recommendation (it creates its own
  venv, so it meets "don't pollute system Python"); made the non-uv path an
  explicit venv create + activate + install; folded `uv pip install` / plain
  `pip install` into a clearly-labeled opt-out for current/system environment;
  switched from-source block to `python3 -m venv` + `pip install -e .`.
- Also updated the pip hash-checking escape-hatch example (`python -m pip
  install -e .` → `pip install -e .`) to match the new venv-based from-source
  block — same `python`-on-macOS problem, same README install section.

## Implement step — done

- Commit 6db6ef0a on `readme-venv-install` ("README: recommend a virtualenv
  for pip installs, not system Python"); README.md only, worktree clean.
- Tests: full suite passes — 1170 passed, 1 skipped (Python 3.12 venv; this
  machine's default python is 3.9, which fails Coga's version guard before
  collection — pre-existing environment issue, unrelated to this docs change).
- No push, no PR — that's the later open-pr step.

## Peer review

- Native `codex review --base main` found one must-fix: the explicit opt-out
  showed `uv pip install coga`, but uv requires `--system` when no virtualenv is
  active. Corrected it to `uv pip install --system coga` in commit 1135a9c0.
- Full suite: `PYTHONPATH=src python -m pytest` — 1170 passed, 1 skipped. Without
  the source path, the known stateless-script test fails because this
  interpreter does not have Coga installed; the source-backed run exercises the
  current checkout and passes.
- Branch is clean, has two commits ahead of its fork point, and merges cleanly
  with current `main` (which advanced only with this task's control-plane state).

## PR

### Summary

- Keep `uv tool install coga` as the isolated default and explain that it does
  not touch system Python.
- Make the non-uv and source-install paths create and activate a virtualenv,
  while labeling current/system-environment installation as an explicit opt-out.
- Use macOS-compatible `python3` commands and a working `uv pip --system`
  opt-out.

### Test plan

`PYTHONPATH=src python -m pytest` — 1170 passed, 1 skipped.

## Usage

{"agent":"claude","cache_creation_input_tokens":123250,"cache_read_input_tokens":2185750,"cli":"claude","input_tokens":90,"model":"claude-fable-5","output_tokens":34190,"provider":"anthropic","schema":1,"session_id":"4a5cc6bf-320d-40c4-b0a0-c0a411e32313","slug":"install/recommend-virtualenv-not-system-python","step":"implement","title":"Onboarding install should use a virtualenv, not system Python","ts":"2026-07-14T01:07:40.433781Z","usage_status":"ok"}

{"agent":"codex","cache_creation_input_tokens":null,"cache_read_input_tokens":3733504,"cli":"codex","input_tokens":118702,"model":"gpt-5.6-sol","output_tokens":11429,"provider":"openai","schema":1,"session_id":"019f5e2a-5bf9-7f41-b66f-805a29579f96","slug":"install/recommend-virtualenv-not-system-python","step":"peer-review","title":"Onboarding install should use a virtualenv, not system Python","ts":"2026-07-14T01:17:32.718888Z","usage_status":"ok"}
