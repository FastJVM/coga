---
title: Fix release_env fixture interpreter symlink in fresh venvs
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
    skills:
    - code/peer-review
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
step: 3 (open-pr)
agent: claude
---

## Description

Fix `tests.test_clean_install_harness.release_env` so the fixture's tool
interpreter retains the packages of the Python environment running pytest.
Its bare symlink to `sys.executable` loses the originating venv's package
lookup, causing `test_release_check_requires_completed_logged_clean_task`
to fail with `ModuleNotFoundError: No module named 'yaml'` in a fresh Python
3.11 venv; globally installed PyYAML masked the failure in the reported
development environment.
Done means the release success and failure checks pass in a fresh Python
3.11 venv whose base interpreter cannot import PyYAML, and a regression check
detects the old symlink behavior even on a developer machine with global
packages installed.
Keep the change focused on the fixture, its regression coverage, and the
reusable testing lesson.

## Context

### Fixture contract and scope

- `tests/test_clean_install_harness.py`, symbols `release_env`, `_executable`,
  `_release`, `test_release_check_requires_completed_logged_clean_task`, and
  `test_release_check_does_not_claim_success_after_failure`, are the starting
  points. `release_env` creates `tools/coga/bin/python` as a symlink to
  `sys.executable` and supplies synthetic distribution metadata plus this
  checkout's `src` through `PYTHONPATH`.
- The `release` branch of `scripts/clean-install/container.sh` executes
  `$(uv tool dir)/coga/bin/python -c ...`, imports `yaml`, reads distribution
  metadata, and runs the release checks with terminal descriptors attached.
  Preserve that tool path, the fixture metadata/source imports, arguments,
  exit status, and terminal forwarding when changing the fixture interpreter.
  A wrapper or correctly configured venv layout is acceptable; choose the
  smallest solution that preserves the running interpreter's environment.
  Account for spaces in interpreter paths and use portable shell syntax if
  choosing a wrapper.
- Keep working when pytest runs from either a venv or a base interpreter.
  Installing PyYAML into the base interpreter is not a fix. Runtime installer
  changes, release-policy changes, and CI trigger changes are out of scope.
  This module is intentionally skipped on native Windows because it exercises
  the Unix host-side bash harness; this task does not port that harness.
- Shared workflow-skill cleanup is out of scope. Prompt review identified
  `code/open-pr`'s historical recovery narrative and
  `code/address-pr-comments`'s embedded GraphQL examples as separate trim
  candidates; retain this ticket's review gates.
- Found during `windows-native/02-pr-ci-with-linux-and-windows-test-jobs`.
  The original report contrasted a fresh Python 3.11 venv with a local Python
  3.12 base that already had PyYAML and CI's base-interpreter install. That
  historical observation is not evidence that current CI verifies this case.

### Verification and durable guidance

Cite `coga-dev/testing` (`docs/contexts/coga-dev/testing/SKILL.md`) rather than
attach it; read "Commands", "Which code you are actually testing",
"Test-writing rules", and "CI posture and receipts". Add the fixture
interpreter lesson to its test-writing guidance in the same PR; this topic
is a local development topic and has no packaged twin.

Install the declared test extra into a fresh `python3.11 -m venv` environment
and run `tests/test_clean_install_harness.py` with that venv's interpreter and
an absolute `PYTHONPATH` pointing at this checkout's `src`. Verify that the
base interpreter lacks `yaml`, and record the exact interpreter, commands,
and pass/skip counts. The regression should demonstrate access to a package
available only in the intended environment so global PyYAML cannot hide a
fallback; keep routine tests self-contained and independent of network or
real agent credentials. A Python 3.12-only pass does not establish the 3.11
case. Preserve both the successful release receipt assertions and rejection
of failed or repeated release checks.

<!-- Ticket guide — keep this comment when filling in or updating the ticket.
It documents field shapes; these are examples, not values to copy into every
ticket. Omit optional fields and sections until needed. Editing rules come
from the base prompt; body regions from coga/tickets; blackboard conventions
(superseded designs, draft cleanup, oversized notes) from coga/blackboard.
Write requirements under ### subheadings of Description or Context; any other
level-two heading above the fence does not reach the launch prompt.

FRONTMATTER
The real values are in this ticket's YAML header. Required ordinary-ticket
keys are title, status, owner, and workflow. A minimal draft has workflow: null.

    title: Fix retry diagnostics           # What the work is called; identity comes from the file path.
    status: draft                          # CLI state: draft, active, in_progress, paused, blocked, done, canceled.
    owner: human-name                      # Accountable human; receives notifications and owner gates.
    agent: codex                           # Optional configured main agent; activation supplies the default if absent.
    contexts:                              # Optional facts to include in every launch; attach only what is needed.
      - service/retries
    skills:                                # Optional ticket-wide procedures, in addition to workflow step skills.
      - infra/testing-conventions
    workflow: code/with-review             # Draft reference or null; live tickets have the frozen mapping below.
    secrets:                               # Optional environment names mapped to references, never credentials.
      - API_TOKEN: env:LOCAL_API_TOKEN
      - SERVICE_KEY: op://automation-vault/service/api-key

The agent choice is not the current operator or the ticket interviewer.
Omit empty contexts, skills, and secrets lists. Each secrets entry has exactly
one unique name (no COGA_ prefix); env: reads the operator's environment and
op:// reads a 1Password item at launch, exposing the value under the left-hand
name. An unavailable reference prevents launch. Never put a literal secret here.

A workflow must be selected before activation. Creation with --workflow, or
activation of a draft reference, freezes its steps. CLI transitions manage step;
do not rewrite a live snapshot or advance it by editing YAML. Frozen example:

    workflow:
      name: code/with-review                # Selected workflow name.
      steps:
        - name: implement                  # Ordered step name.
          skills:                          # Optional procedures for this step; plural, never skill.
            - code/implement
          assignee: agent                  # Role: owner, agent, or other-agent (the configured peer).
          requires: branch                 # Optional completion gate: branch or pr.
    step: 1 (implement)                    # One-based position plus name; CLI removes this on completion.

An omitted step assignee inherits the previous role; the first defaults to
owner. The current step determines who holds the ticket. There is no top-level
assignment field. Removed keys slug, human, assignee, and watchers are invalid.
There is no execution-mode field: a sibling ticket.py supplies a script phase.

Repo extensions are string fields declared under [ticket.fields.<name>] in
coga.toml: description explains the field, values restricts its choices,
default seeds it, and required prevents activation while it is empty. Actual
values live below the extensions marker comment in the YAML header. Preserve
them; do not invent extension fields or change their definitions in config.

Machine-owned fields: delegate freezes a recurring parent's bootstrap/<name>
target; period_generation identifies its materialized run. Both belong only on
period tasks directly under tasks/recurring/. launch_generation is megalaunch's
session claim. Preserve these fields; do not add or clear them yourself.

BLACKBOARD (BELOW THE FENCE)
Keep current decisions and their reasons, verification, next actions, and
blockers here. Update current values in place instead of appending stale copies.

Optional ## Dev: branch: <name> when created; pr: <full /pull/ URL> when opened;
worktree: <path> only for a sandbox clone. One field per line, notes on separate
lines, omit unknown values. For multiple owned branches, the first branch is
the workflow branch.

Optional ## PR: one fenced YAML mapping of PR-preparation receipts (title,
author, head/base OIDs, review depth, files, review, checks). Record only actual
implementation and evidence, never placeholders; coga/pr-publication/
preparation owns the fields and the publishing workflow the review rules.

Optional ## Blockers and ## Blocker reminders are CLI-maintained. Preserve
blocker IDs, timestamps, actor names, resolved answers, and reminder fingerprints
with last_reminded timestamps; use lifecycle commands to block or resolve them.

Recurring parents (coga/recurring/<name>/ticket.md) take schedule and related
template settings owned by coga/recurring/templates; do not add them to an
ordinary ticket.
-->

Previous ref: `fix-release-env-fixture-interpreter-symlink-in-fre` (renamed 2026-10-27); earlier audit lines retain that ref.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: coga/v1-12-release-env-interpreter

## Implement handoff (claude, 2026-11-04)

- `tests/test_clean_install_harness.py`: new helper `_tool_python(path, interpreter)`
  writes `#!/bin/sh` + `exec <shlex-quoted interpreter> "$@"` instead of the bare
  symlink; `release_env` uses it with `sys.executable`. Tool path, metadata
  `PYTHONPATH`, argv, exit status and PTY forwarding are unchanged (exec).
- Regression `test_tool_python_keeps_the_running_environment`: makes a
  `--without-pip` venv under a path with a space, drops `coga_venv_marker.py`
  into its purelib, and runs the wrapper importing it with an argv containing
  a space. Venv-only module, so global PyYAML cannot mask a fallback.
- `docs/contexts/coga-dev/testing/SKILL.md` "Test-writing rules": new bullet on
  exec wrapper vs symlink for tool interpreters (local topic, no twin).
- Reproduced first: fresh 3.11 venv on old code → release success test failed
  with `ModuleNotFoundError: No module named 'yaml'`.
- Old-behavior detection verified by temporarily restoring the symlink in
  `_tool_python`: fresh 3.11 venv → regression + release success test fail;
  repo `.venv` (3.12, base has PyYAML) → release test passes (masked) but the
  regression test fails. Restored afterwards.
- Note: the failure-path parametrizations "pass" under the old symlink too
  (any nonzero exit counts), so only the success test and the new regression
  catch it.
- Bare base `python3.12` cannot run the suite (no `tomlkit`), so "pytest from a
  base interpreter" was not exercised directly; the regression builds its own
  venv, so it is independent of whether pytest runs from a venv.
- Implementation handed off to peer review; the completed outcome is below.

## Peer review

Codex direct review **completed** on 2026-11-04 against head `5e7de7278ad186e8324d09d4f123cf7caefccbe4` and
base `6ecd398e804ccd4cb184f5296c0cbccbd47ebfe8`, after rebasing onto current main.
No unresolved implementation findings.

- Fixed one review finding: the testing topic still described this resolved
  fixture bug as open and recommended a workaround. Removed that entry in
  `5e7de7278`; the new reusable lesson remains.
- Claude authored the implementation (handoff and original commit coauthor
  evidence). Codex independently reviewed that code and self-reviewed its own
  documentation correction. The final PR receipt conservatively uses
  `author: claude/codex`, `kind: self`, and advisory `skim`.
- Fresh environment: `python3.11 -m venv /home/n/.codex/coga-release-peer-hwnr4lgi/v311`,
  then `/home/n/.codex/coga-release-peer-hwnr4lgi/v311/bin/python -m pip install -e ".[test]"`.
  Python 3.11.15; base `/home/n/.local/bin/python3.11` cannot import `yaml`;
  the venv loads PyYAML 6.0.3 from its own site-packages.
- Fresh 3.11 focused harness: **38 passed, 0 skipped**. Full 3.11 suite:
  **4454 passed, 10 skipped**. Exact commands and revision receipts are in `## PR`.
- Base Python 3.12.12 focused harness: **38 passed, 0 skipped** with existing
  venv test dependencies on PYTHONPATH; no base installation changes.
- Negative controls replaced only the helper in memory via a scratch pytest
  plugin. Old symlink on fresh 3.11: expected **2 failed, 0 passed** (missing
  marker and yaml). On base 3.12 with global PyYAML: expected **1 failed,
  1 passed** (the marker regression fails while the old release check passes).
  Both drivers asserted those results and returned success; source files
  stayed unchanged.
- Terminal contract exercised with real PTYs: focused release tests cover
  successful receipts, all five failures, and repeat-run rejection. A separate
  probe verified stdin/stdout/stderr are terminals, exact spaced/empty/literal
  shell-metacharacter argv, and exit 37 for both base and venv interpreters;
  the venv path included a space and an apostrophe.
- Final fetch confirmed main had not moved. Branch committed and pushed with
  an explicit force-with-lease, then checkout returned cleanly to main.
  Next step is the mechanical PR-opening step.

## PR

```yaml
title: Keep the venv for the release_env tool interpreter
author: claude/codex
author_evidence: Claude Code (claude-opus-5-5) implemented the fixture, regression and testing lesson;
  the implement handoff and original commit 62e4eb7da1b4aad813ae7befb2b59d74bc764fb0 record that identity.
  Codex performed this peer-review session and removed the stale known-failure/workaround entry in 5e7de7278ad186e8324d09d4f123cf7caefccbe4.
head: 5e7de7278ad186e8324d09d4f123cf7caefccbe4
base: 6ecd398e804ccd4cb184f5296c0cbccbd47ebfe8
depth: skim
rationale: Small fixture-only fix with full Python 3.11 verification and negative controls that prove
  global PyYAML cannot hide the regression. Read the description for the interpreter wrapper choice and
  base-interpreter test setup. Codex independently reviewed Claude's implementation and self-reviewed
  its own documentation correction; the final receipt is conservatively marked self.
implementation: Uses a portable /bin/sh exec wrapper with a shlex-quoted interpreter path at tools/coga/bin/python,
  retaining the pytest interpreter's packages, argv, exit status, metadata/source PYTHONPATH and terminal
  descriptors. Adds a regression importing a venv-only module under a path with a space. Documents the
  testing lesson and removes the resolved known-failure entry.
deviations: None. The peer-review correction removes obsolete guidance in the same testing topic; runtime
  installer, release-policy, CI and shared workflow-skill behavior are unchanged.
limitations: Native Windows intentionally skips this Unix bash harness. The Python 3.12 base-interpreter
  run borrowed existing venv test dependencies through PYTHONPATH because the base lacks tomlkit; no packages
  were installed into a base interpreter. Verification uses the fixture's synthetic agents/artifacts,
  without a real-agent or cloud clean-install walkthrough.
files:
  tests/test_clean_install_harness.py: Replace the release_env symlink with the quoted exec-wrapper helper
    and add an isolated venv-only import/argv regression.
  docs/contexts/coga-dev/testing/SKILL.md: Own the reusable fixture-interpreter lesson and remove the
    resolved failure/workaround. This local development topic has no packaged twin.
review:
  reviewer: codex
  kind: self
  status: passed
  head: 5e7de7278ad186e8324d09d4f123cf7caefccbe4
  base: 6ecd398e804ccd4cb184f5296c0cbccbd47ebfe8
  detail: Direct Codex review completed on the final head/base after rebasing and correcting the documentation.
    Independent of Claude's fixture and regression authorship; Codex self-reviewed its own documentation-only
    correction, so the aggregate receipt uses self. Found and fixed the stale known-failure/workaround
    entry; no unresolved findings. Reviewed portable quoting, package isolation, unchanged metadata/source
    imports, failure and repeat-run rejection, and actual PTY forwarding. No nested review CLI or delegated
    review was used.
checks:
- command: '/home/n/.local/bin/python3.11 -c ''import importlib.util, sys; print(sys.executable); print(sys.version);
    assert sys.prefix == sys.base_prefix; assert importlib.util.find_spec("yaml") is None; print("base
    yaml: absent")'''
  status: passed
  detail: Python 3.11.15 base interpreter; sys.prefix equals sys.base_prefix and no yaml module is available.
    The fresh venv supplies PyYAML 6.0.3 from its own site-packages.
  head: 5e7de7278ad186e8324d09d4f123cf7caefccbe4
  base: 6ecd398e804ccd4cb184f5296c0cbccbd47ebfe8
- command: PYTHONPATH=/home/n/Code/coga/src /home/n/.codex/coga-release-peer-hwnr4lgi/v311/bin/python
    -m pytest -q -p no:cacheprovider --basetemp /home/n/.codex/coga-release-peer-hwnr4lgi/focused311 tests/test_clean_install_harness.py
  status: passed
  detail: 38 passed, 0 skipped on Python 3.11.15 in a fresh python3.11 -m venv with .[test] installed.
    Its base interpreter cannot import yaml. Includes successful release receipts, repeated-run rejection,
    and all five failure cases with real PTYs.
  head: 5e7de7278ad186e8324d09d4f123cf7caefccbe4
  base: 6ecd398e804ccd4cb184f5296c0cbccbd47ebfe8
- command: PYTHONPATH=/home/n/Code/coga/src /home/n/.codex/coga-release-peer-hwnr4lgi/v311/bin/python
    -m pytest -q -x -p no:cacheprovider --basetemp /home/n/.codex/coga-release-peer-hwnr4lgi/full311
  status: passed
  detail: 4454 passed, 10 skipped in 555.52s on Python 3.11.15, after the rebase and documentation correction.
  head: 5e7de7278ad186e8324d09d4f123cf7caefccbe4
  base: 6ecd398e804ccd4cb184f5296c0cbccbd47ebfe8
- command: PYTHONPATH=/home/n/Code/coga/src:/home/n/Code/coga/.venv/lib/python3.12/site-packages /home/n/.local/share/uv/python/cpython-3.12.12-linux-x86_64-gnu/bin/python3.12
    -m pytest -q -p no:cacheprovider --basetemp /home/n/.codex/coga-release-peer-hwnr4lgi/base312 tests/test_clean_install_harness.py
  status: passed
  detail: 38 passed, 0 skipped with pytest running under the Python 3.12.12 base interpreter; existing
    venv test dependencies supplied on PYTHONPATH. The base interpreter was not modified.
  head: 5e7de7278ad186e8324d09d4f123cf7caefccbe4
  base: 6ecd398e804ccd4cb184f5296c0cbccbd47ebfe8
- command: PYTHONPATH=/home/n/Code/coga/src /home/n/.codex/coga-release-peer-hwnr4lgi/v311/bin/python
    /home/n/.codex/coga-release-peer-hwnr4lgi/check_old_symlink.py 2 -q -p no:cacheprovider --basetemp
    /home/n/.codex/coga-release-peer-hwnr4lgi/old311 tests/test_clean_install_harness.py::test_tool_python_keeps_the_running_environment
    tests/test_clean_install_harness.py::test_release_check_requires_completed_logged_clean_task
  status: passed
  detail: 'Negative control: an in-memory pytest plugin restores the old symlink, without changing source
    files. Driver passed after asserting the expected 2 failed, 0 passed, 0 skipped: missing coga_venv_marker
    and missing yaml.'
  head: 5e7de7278ad186e8324d09d4f123cf7caefccbe4
  base: 6ecd398e804ccd4cb184f5296c0cbccbd47ebfe8
- command: PYTHONPATH=/home/n/Code/coga/src:/home/n/Code/coga/.venv/lib/python3.12/site-packages /home/n/.local/share/uv/python/cpython-3.12.12-linux-x86_64-gnu/bin/python3.12
    /home/n/.codex/coga-release-peer-hwnr4lgi/check_old_symlink.py 1 -q -p no:cacheprovider --basetemp
    /home/n/.codex/coga-release-peer-hwnr4lgi/old312 tests/test_clean_install_harness.py::test_tool_python_keeps_the_running_environment
    tests/test_clean_install_harness.py::test_release_check_requires_completed_logged_clean_task
  status: passed
  detail: 'Negative control: driver asserted 1 failed, 1 passed, 0 skipped. The regression fails for missing
    coga_venv_marker even though global PyYAML lets the old release-success test pass.'
  head: 5e7de7278ad186e8324d09d4f123cf7caefccbe4
  base: 6ecd398e804ccd4cb184f5296c0cbccbd47ebfe8
- command: PYTHONPATH=/home/n/Code/coga/src /home/n/.codex/coga-release-peer-hwnr4lgi/v311/bin/python
    /home/n/.codex/coga-release-peer-hwnr4lgi/check_terminal.py
  status: passed
  detail: 'Two direct real-PTY probes, using a base interpreter and a venv interpreter in a path containing
    a space and apostrophe: all three descriptors remain terminals, spaced/empty/literal shell-metacharacter
    arguments are unchanged, and exit status 37 is preserved.'
  head: 5e7de7278ad186e8324d09d4f123cf7caefccbe4
  base: 6ecd398e804ccd4cb184f5296c0cbccbd47ebfe8
- command: git diff --check origin/main...HEAD
  status: passed
  detail: No whitespace errors in the final branch diff.
  head: 5e7de7278ad186e8324d09d4f123cf7caefccbe4
  base: 6ecd398e804ccd4cb184f5296c0cbccbd47ebfe8
```
