---
title: Fail loud on Python older than 3.11
status: in_progress
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

On Python 3.10 (Ubuntu 22.04 and other older distros), `pip install coga` silently installs the unyanked `coga 0.0.1` placeholder (`requires_python >=3.9`) and leaves no `coga` command, with no error: a Fail-loud violation. A venv does not help because it reuses the same interpreter. Plan agreed 2026-10-12: (1) owner yanks `coga 0.0.1` on PyPI so pip refuses with a clear Requires-Python error (human-only step; the agent confirms it via the PyPI JSON `yanked` flag and stops to ask if it is still unyanked); (2) update `coga/install` (canonical `docs/contexts/coga/install/SKILL.md` and its packaged twin) and the README install section to lead with `uv tool install coga`, which fetches a managed Python 3.11+ when none is present, give the old-Python remedy (`uv tool install coga` or `pipx install --python python3.11 coga`), and replace the note that calls the 0.0.1 install expected behaviour; (3) optionally add a Python 3.10 case to the Linux clean-install harness asserting that pip fails loudly and uv succeeds. Rejected: lowering the floor to 3.10 via `tomli`, because 3.10 reaches end of life in October 2026. Done means docs and twin are merged, the yank is confirmed, and any harness change has run with recorded evidence.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Yank check (2026-10-14, implement step)

- `curl -s https://pypi.org/pypi/coga/json`: `coga 0.0.1` wheel and sdist both report `yanked: false` (`requires_python >=3.9`); 0.2.0 and 0.4.0 are `>=3.11`, latest 0.4.0.
- Per the agreed plan, the agent stops and asks while 0.0.1 is unyanked: the doc change claims pip fails loudly on Python < 3.11, which is only true after the yank. No branch created yet; start check passed (clean `main` at `origin/main` 7ddde4be3).
- To resume: owner yanks 0.0.1 at https://pypi.org/manage/project/coga/release/0.0.1/ (Options → Yank), then `coga unblock`; the next session re-checks the JSON flag and proceeds with docs + twin + README (and optional 3.10 harness case).

---

## Blockers

- [x] [2026-10-14 11:46] [agent:claude] id=20261014T114630 coga 0.0.1 is still unyanked on PyPI (JSON yanked=false for wheel and sdist, checked 2026-10-14). Please yank it at https://pypi.org/manage/project/coga/release/0.0.1/ so pip on Python <3.11 fails with a Requires-Python error, then unblock; the docs change depends on that behaviour.
  resolved: [2026-10-16 10:51] [human:nicktoper] Owner confirmed the PyPI yank; verified both coga 0.0.1 wheel and sdist report yanked=true in the PyPI release JSON. Proceed with install documentation updates.

---

## Blocker reminders

- cdbf327e37e9 last_reminded: 2026-10-16 09:31


## Dev

branch: fix-old-python-install

## Implementation plan (2026-10-16)

- Owner yanked 0.0.1; both release files verified `yanked: true` through https://pypi.org/pypi/coga/0.0.1/json. `coga unblock` recorded the resolution.
- Follow the agreed documentation plan: README summary plus canonical install topic and its packaged twin; explain uv-managed Python and explicit pipx interpreter selection, and why a venv alone does not upgrade Python.
- Keep the optional Linux harness extension out of this documentation change. Verify live installer behavior in isolated temporary directories and run the required suite; retain commands and results in the handoff.
