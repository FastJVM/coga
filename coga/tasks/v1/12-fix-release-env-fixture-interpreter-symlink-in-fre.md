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
step: 2 (peer-review)
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
- Review not run yet; peer-review is the next step.

## PR

```yaml
title: Keep the venv for the release_env tool interpreter
author: claude
author_evidence: Implement session ran as Claude Code (claude-opus-5-5); see implement handoff.
head: 62e4eb7da1b4aad813ae7befb2b59d74bc764fb0
base: 48c00f79cba7ae3df028ea4a5166bcb6f4b6ab11
depth: skim
rationale: Test-only fixture fix plus a doc bullet; read the description for the wrapper choice and verification matrix.
implementation: Replaces the release_env tool-interpreter symlink with a /bin/sh exec wrapper (shlex-quoted path) via a new _tool_python helper, adds a regression test importing a module present only in a throwaway venv, and documents the lesson in coga-dev/testing.
deviations: None.
limitations: Not exercised with pytest running from a bare base interpreter (base python3.12 lacks test deps); the regression creates its own venv so it does not depend on that. Native Windows still skips this module by design.
files:
  tests/test_clean_install_harness.py: Exec wrapper helper, release_env uses it, regression test for venv package visibility.
  docs/contexts/coga-dev/testing/SKILL.md: Test-writing rule on exec wrappers versus symlinks for tool interpreters.
review:
  reviewer: none
  kind: none
  status: not-run
  detail: Implement step; peer-review step follows.
checks:
  - command: PYTHONPATH=/home/n/Code/coga/src <scratch>/v311/bin/python -m pytest -q -p no:cacheprovider tests/test_clean_install_harness.py
    status: passed
    head: 62e4eb7da1b4aad813ae7befb2b59d74bc764fb0
    base: 48c00f79cba7ae3df028ea4a5166bcb6f4b6ab11
    detail: 38 passed. Fresh python3.11 -m venv (3.11.15) with .[test]; base /home/n/.local/bin/python3.11 cannot import yaml.
  - command: PYTHONPATH=/home/n/Code/coga/src <scratch>/v311/bin/python -m pytest -q -x -p no:cacheprovider --basetemp ~/.cache/coga-pytest/bt
    status: passed
    head: ca4a256953256095465e0affde38ef3f07d99838
    base: da0ec17244cc6870c1ec5c9386449cb126376564
    detail: 4454 passed, 10 skipped on the pre-rebase commit; rebase added only a coga/ ticket commit and non-coga trees are identical.
  - command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q tests/test_clean_install_harness.py
    status: passed
    head: ca4a256953256095465e0affde38ef3f07d99838
    base: da0ec17244cc6870c1ec5c9386449cb126376564
    detail: 38 passed on Python 3.12 venv (uncommitted tree identical to that commit).
```
