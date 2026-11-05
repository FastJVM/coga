---
title: State the hatchling prerequisite in the clean-wheel proof
status: in_progress
owner: nicktoper
workflow:
  name: docs/with-review
  steps:
  - name: implement
    skills: []
    assignee: agent
    requires: branch
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills: []
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 3 (open-pr)
agent: claude
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

## Dev

branch: coga/v1-40-hatchling-prerequisite

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Implement handoff (2026-11-04)

Branch `coga/v1-40-hatchling-prerequisite`, commit `8e0c3c8a6` (rebased on
origin/main, pushed). Diff:

- `src/coga/resources/templates/coga/recurring/phone-home/operations.md`:
  prose before the build block explains `--no-build-isolation` imports the
  build backend from the running interpreter (the `BackendUnavailable` error),
  says to build with a `[test]`-extra Python (e.g. `.venv/bin/python` after
  `python -m pip install -e ".[test]"`), that the builder is not the install
  target, and that "no editable installation" / "no test/CI environment"
  govern the proof run, not the builder. Code block now invokes
  `.venv/bin/python -m pip wheel ...` with a one-line comment. No links added.
- `tests/test_packaging.py`: phone-home `operations.md` reason extended
  (`_LINKS_TO_PACKAGE_OWNERS + "; packaged instructions also state the
  [test]-extra builder prerequisite ..."`). Digest unchanged.

**For the reviewer:** the legacy copy `coga/recurring/phone-home/operations.md`
was deliberately left untouched and now diverges further from the package
owner — intended under stage A of `v1/package-definitions`; its SHA-256 still
matches the pinned digest.

Verification: `.venv/bin/python -m pytest tests/test_packaging.py -q` → 37 passed;
`sha256sum` of the legacy copy = pinned `80fee364…820a`.

## Peer review

2026-11-04 — Codex independent content review: passed, no must-fix findings
and no review edits needed. Authorship is evidenced by the implement launch
receipt in `coga/log.md` (Claude session
`139937db-a439-4f7f-842e-5ba238887da2`) and the Claude co-author trailer in
implementation commit `8e0c3c8a60408ec0608b06868575cbd01ce723e4`.

Reviewed the markdown and reason-string diff after rebasing onto current
`origin/main`. Final reviewed head:
`0ac717cb6c1b9da85d1d837fff57a33a6517d46f`; base:
`9c0de2d8efc9733e4aa343dc6bff678dfd2cd89d`.

- The prerequisite matches `pyproject.toml`, `coga-dev/testing`, and the
  installed pip implementation: disabling build isolation requires the
  builder's installed build backend; Coga's `[test]` extra provides hatchling
  and pip. The example keeps `--no-build-isolation` and uses the checkout venv.
- The builder is clearly distinct from the fresh external installation.
  The explanation of proof-time gates agrees with
  `src/coga_edge/phone_home.py::_admitted` and the packaged phone-home ticket.
- Scope is limited to the package runbook and the documented divergence
  reason. No links were added; the sibling `ticket.md` reference resolves.
  The note is self-contained and requires no local-only development topic.
- The additional legacy/package divergence is intended under stage A.
  The live runbook and its pinned digest are unchanged; its SHA-256 remains
  `80fee3648b7ca9cc4051e142d73c33642cdad23e089a1879cd4ee9dff559820a`.
- `.venv/bin/python -m pytest tests/test_packaging.py -q`: **37 passed**
  in 3.75s, Python 3.12.12. `git diff --check main...HEAD`: passed.
  The full runtime suite and owner-run live ingestion proof were not needed
  for this prose/reason-string change.

Final fetch confirmed no further main drift. Pushed the rebased branch with
an explicit lease and returned this checkout to clean, current `main` before
writing this handoff. The next step can publish from the preparation below.

## PR

```yaml
title: State the hatchling prerequisite in the clean-wheel proof
author: claude
author_evidence: >-
  coga/log.md records implement session 139937db-a439-4f7f-842e-5ba238887da2
  running Claude; implementation commit 8e0c3c8a60408ec0608b06868575cbd01ce723e4
  also carries the Claude co-author trailer. Codex performed this review.
head: 0ac717cb6c1b9da85d1d837fff57a33a6517d46f
base: 9c0de2d8efc9733e4aa343dc6bff678dfd2cd89d
depth: merge
rationale: >-
  Small runbook clarification with independent source-backed review,
  all 37 packaging tests passing, and no unresolved findings or behavior changes.
implementation: >-
  Explain beside the wheel command that --no-build-isolation needs a builder
  with Coga's [test] extra, which supplies hatchling and pip. Use .venv/bin/python
  for the build and distinguish that builder from the fresh external venv
  where the no-editable and no-test/CI proof rules apply. Extend the packaged
  runbook's divergence reason while preserving the legacy bytes and digest.
deviations: >-
  None. Further package-only divergence is required by the ticket and stage A
  of package-definitions.
limitations: >-
  Verification used Python 3.12.12. The owner-run live PostHog ingestion proof
  was not executed; this change only documents its builder prerequisite.
files:
  src/coga/resources/templates/coga/recurring/phone-home/operations.md: >-
    State the builder prerequisite beside the command and explain its scope.
  tests/test_packaging.py: >-
    Extend only the legacy-definition divergence reason; retain its digest
    and all test logic.
review:
  reviewer: codex
  kind: independent
  status: passed
  head: 0ac717cb6c1b9da85d1d837fff57a33a6517d46f
  base: 9c0de2d8efc9733e4aa343dc6bff678dfd2cd89d
  detail: >-
    No must-fix findings. Checked accuracy against pyproject.toml, installed
    pip, testing guidance, and telemetry admission; confirmed scope, references,
    self-contained shipped prose, and intentional legacy-copy divergence.
checks:
  - command: .venv/bin/python -m pytest tests/test_packaging.py -q
    status: passed
    head: 0ac717cb6c1b9da85d1d837fff57a33a6517d46f
    base: 9c0de2d8efc9733e4aa343dc6bff678dfd2cd89d
    detail: 37 passed in 3.75s on Python 3.12.12.
  - command: git diff --check main...HEAD
    status: passed
    head: 0ac717cb6c1b9da85d1d837fff57a33a6517d46f
    base: 9c0de2d8efc9733e4aa343dc6bff678dfd2cd89d
    detail: No whitespace errors in the reviewed feature diff.
  - command: sha256sum coga/recurring/phone-home/operations.md
    status: passed
    head: 0ac717cb6c1b9da85d1d837fff57a33a6517d46f
    base: 9c0de2d8efc9733e4aa343dc6bff678dfd2cd89d
    detail: >-
      Matches the unchanged pinned digest
      80fee3648b7ca9cc4051e142d73c33642cdad23e089a1879cd4ee9dff559820a.
  - command: .venv/bin/python -m pytest
    status: not-run
    detail: >-
      Only prose and a packaging reason string changed; the ticket's required
      packaging suite passed. No runtime logic or fixtures changed.
```
