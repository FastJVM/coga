---
title: Sweep orphan tmp trees that contain read-only directories
status: in_progress
owner: nicktoper
workflow:
  name: code/with-review
  steps:
  - name: open-branch
    skills: []
    assignee: agent
    requires: branch
    run: git/open-branch
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills:
    - code/peer-review
    assignee: other-agent
  - name: push-and-open-pr
    skills: []
    assignee: agent
    requires: pr
    run: git/push-and-open-pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 4 (push-and-open-pr)
agent: claude
---

## Description

Launch sweeps orphaned launch tmp areas under `coga/.coga/tmp/<token>/` with plain `shutil.rmtree` (`_remove_tree` in `src/coga/run_state.py`). When a dead launch left a read-only directory behind, the sweep fails with `[Errno 13] Permission denied` on every entry inside it, then `[Errno 39] Directory not empty` up the tree. It retries on every later launch, printing about 14 warnings each time until a human runs `chmod -R u+w` and deletes the area.

Observed 2026-11-23: a launch ran pytest with `$TMPDIR` inside its tmp area. `test_installed_wheel_init_and_*` left `company/coga/bootstrap/recurring-promote/` as `dr-xr-xr-x`, which blocked the sweep on `coga launch` and `coga chat` until the area was removed by hand.

### Requirements

- `_remove_tree` handles permission failures. When a delete fails because the parent directory is not writable, make that directory (and the entry, if it is a directory) owner-writable and retry. Only report what still fails after the retry. Never follow symlinks out of the tmp area while changing permissions.
- A remaining failure produces one concise warning per orphan area, not one line per file and ancestor.
- Add a regression test: an orphan tmp area that contains a read-only subdirectory holding files is fully removed by `sweep_orphans`, and so is the same layout found by validate's `orphan-tmp` fix.
- Find why `test_installed_wheel_init_and_*` leaves read-only copies of packaged resources (wheel install permissions, or a chmod in the test), and make the test clean up or avoid creating them.
- Update the owning topic for launch tmp/run state if its contract mentions sweep failure behavior.

## Context

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
        - name: open-branch
          run: git/open-branch               # Local-first skill directory containing run.py.
          assignee: agent
        - name: implement                  # Ordered step name.
          skills:                          # Optional procedures for this step; plural, never skill.
            - code/implement
          assignee: agent                  # Role: owner, agent, or other-agent (the configured peer).
          requires: branch                 # Optional completion gate: branch or pr.
    step: 1 (open-branch)                    # One-based position plus name; CLI removes this on completion.

An omitted step assignee inherits the previous role; the first defaults to
owner. The current step determines who holds the ticket. There is no top-level
assignment field. Removed keys slug, human, assignee, and watchers are invalid.
A workflow run: selects a script for its step. A sibling ticket.py supplies the default script phase.

Repo extensions are string fields declared under [ticket.fields.<name>] in
coga.toml: description explains the field, values restricts its choices,
default seeds it, and required prevents activation while it is empty. Actual
values live below the extensions marker comment in the YAML header. Preserve
them; do not invent extension fields or change their definitions in config.

The recurring runner writes delegate on materialized period tickets. It
names the parent template's frozen bootstrap/<name> target.

BLACKBOARD (BELOW THE FENCE)
Keep current decisions and their reasons, verification, next actions, and
blockers here. Update current values in place instead of appending stale copies.

Optional ## Dev records branch:, base:, remote:, reviewed: (the commit OID),
and pr: (the full /pull/ URL). Write one field per line and omit unknown
values. coga/git owns the fields and the workflow that writes them.

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

<!-- coga:blackboard -->
## Dev

branch: coga/sweep-orphan-tmp-trees-that-contain-read-only-di-c1cc7a
base: coga/report-an-unknown-or-directory-workflow-name-wit-41c8d8
remote: origin
reviewed: 0aaa67fbbc54037ebf50d7c341df7fabf228a067

## Implement notes

Most of the ticket had already landed on main before this branch opened:

- Permission retry: c771516f2 + d5e09df4c. `run_state._remove_tree` retries
  once after `_make_owner_writable` grants owner rwx on directories (files
  only on Windows), skipping symlinks, so a hard-linked or linked-to file
  outside the area keeps its mode. Covered by
  `test_sweep_removes_read_only_orphans_without_touching_link_targets` and
  `test_purge_keeps_modes_of_hard_linked_files_outside_the_area`.
- Packaging root cause (c771516f2): `test_installed_wheel_init_and_phone_home_are_isolated`
  strips write bits from the installed `coga/resources/` to prove the package
  stays read-only. Its script then `copytree`s `bootstrap/recurring-promote`
  into the project as a fork, and copytree carries directory modes
  (copy_function only covers file contents), so the fork in `tmp_path` was
  `dr-xr-xr-x`. The test now chmods the fork's directories to 0755. After a
  full suite run in this launch, `find "$TMPDIR" -type d ! -perm -u+w` → 0.

This branch adds what was still missing:

- `run_state._summarize`: one line per area (first failure + "(and N more)")
  for the launch purge warning and each `sweep_orphans` failure. Sweep
  failures feed launch warnings and validate's `orphan-tmp` issues, so both
  now give one line per area.
- Tests: `test_validate_fix_removes_read_only_orphans` (validate's
  `orphan-tmp` fix) and `test_unremovable_orphan_reports_one_failure_per_area`
  (fails on the old per-problem output; checked by stashing the src change).
- `coga/launch` topic: sweep failure paragraph now states the per-area line.

## Peer review notes

- The first diff left two warnings in `validate --fix` when a failed area
  was still old enough to be rediscovered after the sweep retired its lock.
  The correction uses the sweep's warning in fix mode and escapes line
  breaks in cleanup diagnostics.
- The permission retry now skips Windows junctions alongside symlinks. A
  native test covers the junction target's file mode.
- Fetched `origin` and reviewed against the recorded stacked base,
  `7b1aa74f11c6c182fca335b2d405c095f50f6a26`. The base ticket
  `report-an-unknown-or-directory-workflow-name-witho` is at its PR step and
  its branch is still local. Publication also requires reconciling the
  pending state edits for that ticket and
  `move-the-assembler-trial-evidence-out-of-the-shipp`.

## PR

```yaml
title: Report each failed launch tmp cleanup once
author: claude
author_evidence: >-
  Claude Code (Claude Opus 5.5) authored the original change in launch
  1a4a5a62-88cd-4e1b-b407-971254e8f3ed. Codex authored the review
  corrections in 0aaa67fbbc54037ebf50d7c341df7fabf228a067.
head: 0aaa67fbbc54037ebf50d7c341df7fabf228a067
base: 7b1aa74f11c6c182fca335b2d405c095f50f6a26
depth: skim
rationale: >-
  The change affects cleanup diagnostics and junction handling. The Linux
  full suite and verification of the Python 3.11 retry path passed.
implementation: >-
  Report the first remaining failure and a count of additional failures
  for each tmp area. Escape line breaks in diagnostics, use the sweep
  result for orphan-tmp warnings in validate fix mode, and skip junctions
  when granting write access. Cover read-only orphans and failed repairs
  with regression tests.
deviations: >-
  The review uses the recorded stacked base branch. The core permission
  retry and installed-wheel fixture repair landed on main in c771516f2 and
  d5e09df4c.
limitations: >-
  Native Windows and macOS verification is deferred to release, including
  the Windows junction regression. Publication depends on the stacked
  base and reconciliation of the unrelated task state in the checkout.
files:
  src/coga/run_state.py: "Summarize each failed purge or sweep on one line and skip Windows junctions during permission repair."
  src/coga/validate.py: "Use the sweep result as the source of orphan warnings in fix mode."
  tests/test_run_state.py: "Exercise read-only cleanup, one-line failures in sweep and validation, and a Windows junction target."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/launch/SKILL.md: "Document cleanup diagnostics and junction handling."
review:
  reviewer: codex
  kind: independent
  status: passed
  head: 0aaa67fbbc54037ebf50d7c341df7fabf228a067
  base: 7b1aa74f11c6c182fca335b2d405c095f50f6a26
  detail: >-
    Codex independently inspected Claude's stacked diff in launch
    b52fa35d-ba2c-40e8-bc16-b538bb1c5536 and traced launch purge, orphan
    sweep, and both validation modes. Codex made and self-reviewed the
    corrections above, reviewed the resulting full diff, and found no
    remaining must-fix issues.
checks:
  - command: 'TMPDIR=/tmp/coga-orphan-review.yfpiYYCE/py312 PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q'
    status: passed
    head: 0aaa67fbbc54037ebf50d7c341df7fabf228a067
    base: 7b1aa74f11c6c182fca335b2d405c095f50f6a26
    detail: "Pop!_OS 24.04 LTS, Python 3.12.12. 3257 passed, 30 skipped in 193.50s."
  - command: >-
      TMPDIR=/tmp/coga-orphan-review.yfpiYYCE/py311 PYTHONPATH=$PWD/src
      /tmp/coga-orphan-review.yfpiYYCE/venv311/bin/python -m pytest -q
      tests/test_run_state.py
      tests/test_packaging.py::test_installed_wheel_init_and_phone_home_are_isolated
    status: passed
    head: 0aaa67fbbc54037ebf50d7c341df7fabf228a067
    base: 7b1aa74f11c6c182fca335b2d405c095f50f6a26
    detail: "Pop!_OS 24.04 LTS, Python 3.11.15. 35 passed, 1 Windows-only test skipped in 5.75s."
  - command: 'PYTHONPATH=$PWD/src .venv/bin/python -m coga.cli validate --json > /tmp/coga-orphan-review.yfpiYYCE/validate.json'
    status: passed
    head: 0aaa67fbbc54037ebf50d7c341df7fabf228a067
    base: 7b1aa74f11c6c182fca335b2d405c095f50f6a26
    detail: "Pop!_OS 24.04 LTS, Python 3.12.12. Exit 0 with 0 errors and 82 warnings."
  - command: 'env -u SLACK_WEBHOOK_URL PYTHONPATH=/home/n/Code/coga/src /home/n/Code/coga/.venv/bin/python -m coga.cli validate --fix --json'
    status: passed
    head: 0aaa67fbbc54037ebf50d7c341df7fabf228a067
    base: 7b1aa74f11c6c182fca335b2d405c095f50f6a26
    detail: >-
      Pop!_OS 24.04 LTS, Python 3.12.12. In a disposable fixture with launch
      variables cleared, exit 0 removed one read-only tmp area and reported
      one warning for the orphan symlink. Its target file remained intact.
```
