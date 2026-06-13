---
title: one-line-install
status: draft
mode: interactive
owner: zach
human: zach
agent: claude
assignee: nick
contexts: []
skills: []
workflow: null
---

## Description

Give new users a one-line install for the relay CLI. Today the only
documented path is clone-the-source-repo + `pip install -e .`, which
assumes repo access and a dev setup — too much friction for the launch
onboarding story ("install, then `relay setup`"). Either publish
`relay-os` to PyPI (`pipx install relay-os`) or, as the immediate cheap
step once the repo is public, document
`pipx install git+https://github.com/FastJVM/relay` in the README — and
decide what the update story becomes (README currently tells people to
`git pull && pip install -e .` periodically).

## Context

- README "Install" section opens with "Not yet on PyPI. Bootstrap from
  the source repo" — that's the gap.
- `pyproject.toml` already names the package `relay-os` (0.2.0,
  hatchling), and the packaged `relay/cli` context already says
  "`pip install relay-os` installs bundled batteries" as if it were
  published. No publish workflow exists under `.github/workflows/`.
- `relay init` also shallow-clones `https://github.com/FastJVM/relay`
  at runtime to vendor `.relay/` (`RELAY_REPO_URL` in
  `src/relay/commands/update.py`), so install alone isn't enough for a
  private repo — that auth friction is tracked separately in the
  `relay-forces-https` ticket, and making the repo public is part of
  the `relay-discord` rollout.
- Prerequisite-shaped for the launch: the target onboarding is
  invite/nothing → one-line install → `relay setup <dir>` (PR #348).
