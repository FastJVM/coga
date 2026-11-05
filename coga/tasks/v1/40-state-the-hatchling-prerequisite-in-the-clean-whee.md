---
title: State the hatchling prerequisite in the clean-wheel proof
status: draft
owner: nicktoper
workflow: docs/with-review
---

## Description

The "Clean installed-wheel proof" section of the phone-home runbook builds the
wheel with
`python -m pip wheel --no-deps --no-build-isolation . -w /tmp/coga-telemetry-wheel`.
`--no-build-isolation` makes pip import the build backend from the running
interpreter, so from a plain system Python the command fails with
`BackendUnavailable: Cannot import 'hatchling.build'`. This happened on
2026-10-13 during `v1/41-verify-posthog-telemetry-with-the-live-clean-wheel`.
As of 2026-11-04 the runbook still shows the bare command with no prerequisite.

Keep the flag (offline build, known hatchling version — the owner chose this
over dropping it) and state the prerequisite right next to the command: run
the build with a Python that has Coga's `[test]` extra installed, e.g. the
checkout's `.venv/bin/python` after `python -m pip install -e ".[test]"`. Make
clear that this builder interpreter is not the install target: the wheel still
goes into the fresh external venv the runbook creates next. The section's two
existing rules govern the proof run, not the builder: "no editable
installation" applies to that external venv, and "from an ordinary shell with
no test/CI environment" means the test/CI gates must not be set when running
the installed `coga`. A `[test]`-equipped builder venv does not violate it.
Say so briefly, so a reader doesn't think the two rules contradict the
prerequisite.

Done means the package runbook
`src/coga/resources/templates/coga/recurring/phone-home/operations.md` states
the prerequisite beside the build command (prose note and/or the code block
itself invoking the `[test]`-equipped interpreter), the legacy repo copy and
its pinned digest are left untouched, the `LEGACY_DEFINITION_DIFFERENCES`
reason for that copy is extended to name the new packaged content, and
`python -m pytest tests/test_packaging.py` passes.

## Context

- **Edit only the package copy.** The package file
  `src/coga/resources/templates/coga/recurring/phone-home/operations.md` is the
  owner. `coga/recurring/phone-home/operations.md` is a transitional legacy
  copy (listed in `tests/legacy_removal_inventory.txt`) that already differs
  from the owner by one link and is pinned by SHA-256 in
  `tests/test_packaging.LEGACY_DEFINITION_DIFFERENCES`. `AGENTS.md`: never
  edit a live recurring definition; edit the package copy.
  `test_live_and_packaged_copies_stay_identical` skips paths in that dict, and
  the digest check only hashes the legacy file, so a package-only edit keeps
  the test green. Do not edit the legacy copy or its digest. Do update the
  entry's reason string: `AGENTS.md` says to record the reviewed difference
  there, and the current reason (`_LINKS_TO_PACKAGE_OWNERS`) covers only
  links. Follow the `coga/recurring/phone-home/ticket.md` entry, which appends
  `+ "; packaged instructions also …"` to the same constant. Only
  `test_legacy_definition_differences_pin_unchanged_live_bytes` checks the
  digest, and it hashes the live file only. No test hashes the packaged
  runbook's content. Avoid adding a relative link to the runbook.
- **Shipped surface: keep the note self-contained.** The runbook ships in the
  wheel, so per `coga/context-layout` ("Context audiences") it must not
  require reading a `coga-dev/` topic (those are local-only). State the fact
  inline. Facts to stay consistent with (cited, not attached):
  - `pyproject.toml`, comment above `[project.optional-dependencies] test`:
    hatchling is the build backend, dev/test-only, never imported at runtime,
    so it stays out of the runtime dependencies.
  - `docs/contexts/coga-dev/testing/SKILL.md`: "`hatchling` is a tracked test
    extra, not a runtime dependency, because
    `tests/test_packaging.py::test_wheel_includes_bootstrap_batteries` builds
    with `--no-build-isolation` and fails (not skips) without it". The test
    extra also pins `pip` because uv-created environments may omit it, so
    the builder needs `pip` too, and `[test]` provides it.
  Use the same terms ("`[test]` extra", "build backend") rather than new
  phrasing.
- Docs-only apart from that one reason-string edit in `tests/test_packaging.py`:
  no telemetry code, no `pyproject.toml` change, no test logic change.
- The workflow is `docs/with-review`. Its peer-review step checks prose,
  accuracy, and repo↔packaged sync. Tell the reviewer up front that the legacy
  copy diverging further is intended (stage A of `v1/package-definitions`).

Previous ref: `marketing/state-the-hatchling-prerequisite-in-the-clean-whee` (renamed 2026-10-27); earlier audit lines retain that ref.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
