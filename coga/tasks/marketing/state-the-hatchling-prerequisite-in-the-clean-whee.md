---
title: State the hatchling prerequisite in the clean-wheel proof
status: draft
owner: nicktoper
workflow: code/with-review
---

## Description

The "Clean installed-wheel proof" section of `coga/recurring/phone-home/operations.md`
builds the wheel with
`python -m pip wheel --no-deps --no-build-isolation . -w …`. Because
`--no-build-isolation` makes pip use the running interpreter's packages, this
fails with `BackendUnavailable: Cannot import 'hatchling.build'` from a plain
system Python. It happened on 2026-10-13 during
`marketing/verify-posthog-telemetry-with-the-live-clean-wheel`.

Keep the flag (offline, known hatchling version) and state the prerequisite
next to the command: run the build with a Python that has the `[test]` extra
installed, e.g. the repo's `.venv/bin/python` after
`python -m pip install -e ".[test]"`. That builder is not the install target;
the wheel still goes into a fresh external venv. Owner chose this over dropping
the flag.

Done means the canonical topic and its packaged twin both carry the
prerequisite, byte-identical, and `python -m pytest tests/test_packaging.py`
passes.

## Context

- Read and edit both runbook copies:
  `coga/recurring/phone-home/operations.md` and
  `src/coga/resources/templates/coga/recurring/phone-home/operations.md`.
  `tests/test_packaging.py` requires byte-identity.
- Why hatchling is not a runtime dependency: `pyproject.toml`
  `[project.optional-dependencies] test` comment, and `coga/testing`
  (`docs/contexts/coga/testing/SKILL.md`), which already notes the
  `--no-build-isolation` / `[test]` relationship for the packaging test. Link
  or mirror that phrasing rather than restating it differently.
- Docs-only. No telemetry code, no change to `pyproject.toml`.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
