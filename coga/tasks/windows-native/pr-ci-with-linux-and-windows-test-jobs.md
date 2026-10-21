---
title: PR CI with Linux and Windows test jobs
status: draft
owner: nicktoper
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 1 (implement)
---

## Description

Add PR CI so Windows support can't silently regress after the port. Today
`.github/workflows/` holds only `release.yml`, and no tests run on PRs at
all. Add a workflow that runs `python -m pytest` on pull requests and pushes
to `main`, on both `ubuntu-latest` and `windows-latest`, with Python 3.11
(the floor).

Start after `windows-native/core-port-cli-and-test-suite-pass-on-native-window`
is merged; before that, the Windows job can't pass.

Done when the workflow is merged, both jobs pass on its own PR, and a
deliberately broken commit on a scratch branch shows the Windows job failing
(for example a top-level `import fcntl` in a module the CLI imports). Link
that run in the PR.

## Context

- Install as the repo documents: `python -m pip install -e ".[test]"`, then
  `python -m pytest`.
- Some tests may need git identity (`git config user.name/email`) set in CI.
- Tests that need a real agent CLI, network or AWS must already skip
  cleanly. If one doesn't, fix the skip; don't add it to CI.
- Interactive launch is checked on EC2 (the interactive-launch ticket), not
  in CI.
- `coga-dev/testing` (`docs/contexts/coga-dev/testing/SKILL.md`) owns test
  expectations. Add one line there saying PR CI exists and what it runs,
  in both the canonical and packaged copies (`coga-dev/packaging`).

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
