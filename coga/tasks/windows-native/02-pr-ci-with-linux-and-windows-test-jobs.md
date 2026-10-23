---
title: PR CI with Linux and Windows test jobs
status: active
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
agent: claude
---

## Description

Add PR CI so Windows support can't silently regress after the port. Today
`.github/workflows/` holds only `release.yml`, and no tests run on PRs at
all. Add a workflow that runs `python -m pytest` on pull requests and pushes
to `main`, on both `ubuntu-latest` and `windows-latest`, with Python 3.11
(the floor).

Start after `windows-native/01-core-port-cli-and-test-suite-pass-on-native-window`
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
  expectations. Add one line there saying PR CI exists and what it runs.
  This development topic is local-only (`coga-dev/packaging`).

<!-- coga:blackboard -->

## Implementation preflight — 2026-10-22

- Codex checked a clean `main`, fetched and fast-forwarded it to
  `e2958c82d4fa7e3b9a930e7df7e0e311afba0fea`, and fetched again before
  handing off; the remote tip was unchanged.
- The required predecessor,
  `windows-native/01-core-port-cli-and-test-suite-pass-on-native-window`, is
  still `in_progress` at step 3 (`review-design`, owner-held), with no
  recorded implementation branch or PR. GitHub PR searches for `core-port`
  and Windows titles found no merged core-port PR; merged PR #1026 is the
  Windows EC2 harness, not the port.
- Current main still imports `fcntl` unconditionally at module scope in
  `src/coga/git.py`, `src/coga/launch.py`, and
  `src/coga/repl_supervisor.py`; `src/coga/commands/megalaunch.py` still
  imports `termios` and `tty`. The prerequisite's promised Windows import
  fixes have not landed, so a Windows test job cannot yet pass.
- Follow the ticket's explicit start-after-merge constraint: block on
  `windows-native/01-core-port-cli-and-test-suite-pass-on-native-window` being
  merged. No implementation branch, workflow changes, PR, or test run was
  made in this attempt.
- Resume after that merge: add the Python 3.11 Linux/Windows workflow,
  replace the obsolete no-CI posture in `coga-dev/testing`, run the suite,
  and prepare the implementation handoff. Later PR steps still owe both
  green jobs and the linked scratch-branch Windows failure run.

---

## Blockers

- [ ] [2026-10-22 11:50] [agent:claude] id=20261022T115057 Merge windows-native/01-core-port-cli-and-test-suite-pass-on-native-window before starting this CI ticket. It is still at owner-held review-design, and main retains unconditional POSIX-only imports that prevent the Windows test job from passing.

---

## Blocker reminders

- 9f1f52929c3a last_reminded: 2026-10-23 10:25
