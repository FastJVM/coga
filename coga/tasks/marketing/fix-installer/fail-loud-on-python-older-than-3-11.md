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
launch_generation: fb42269c-04cf-43d5-85c5-7eba22739d76
---

## Description

On Python 3.10 (Ubuntu 22.04 and other older distros), `pip install coga` silently installs the unyanked `coga 0.0.1` placeholder (`requires_python >=3.9`) and leaves no `coga` command, with no error: a Fail-loud violation. A venv does not help because it reuses the same interpreter. Plan agreed 2026-10-12: (1) owner yanks `coga 0.0.1` on PyPI so pip refuses with a clear Requires-Python error (human-only step; the agent confirms it via the PyPI JSON `yanked` flag and stops to ask if it is still unyanked); (2) update `coga/install` (canonical `docs/contexts/coga/install/SKILL.md` and its packaged twin) and the README install section to lead with `uv tool install coga`, which fetches a managed Python 3.11+ when none is present, give the old-Python remedy (`uv tool install coga` or `pipx install --python python3.11 coga`), and replace the note that calls the 0.0.1 install expected behaviour; (3) optionally add a Python 3.10 case to the Linux clean-install harness asserting that pip fails loudly and uv succeeds. Rejected: lowering the floor to 3.10 via `tomli`, because 3.10 reaches end of life in October 2026. Done means docs and twin are merged, the yank is confirmed, and any harness change has run with recorded evidence.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
