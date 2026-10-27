---
title: Move the non-executable-script validate contract into a shipped user topic
status: blocked
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

Filed by Dream 2026-W44 (Phase 6; knowledge-scan ks-05). Target: docs/contexts/coga-dev/testing/SKILL.md lines ~30-44 → a shipped coga/ topic (e.g. coga/cli's validate section, with its packaged twin under src/coga/resources/templates/coga/bootstrap/contexts/).

coga validate's repo-wide error non-executable-script (src/coga/validate.py:261, :1474-1536; Dream classification src/coga/dream_validate_drift.py:275-298) fires in every adopting repo, but its only explanation (scope: installed skills root plus packaged bootstrap skills; POSIX working-tree modes vs git-index modes on Windows / core.fileMode=false; skipped roots and untracked files; pruned dirs; packaged-tree hits are human-needed) now lives in the never-packaged coga-dev audience (moved there by 3e6956814). coga/context-layout (docs/contexts/coga/context-layout/SKILL.md:35-40) says knowledge needed to understand a shipped command's refusal is user knowledge that must ship. Move it to a user topic and leave coga-dev/testing a one-line link.

Why a draft, not a Dream PR: open PR #1097 (windows-native/02-pr-ci-with-linux-and-windows-test-jobs) rewrites docs/contexts/coga-dev/testing/SKILL.md; handle after it merges.

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

Previous ref: `move-the-non-executable-script-validate-contract-i` (renamed 2026-10-27); earlier audit lines retain that ref. Parked by the owner for v2; this work does not gate v1.

<!-- coga:blackboard -->

## Dev

branch: coga/non-executable-script-user-topic

## Implementation handoff

- Implemented and pushed `f07099be6fb0ec7d59267276450c5cadf756b81a` on the
  recorded branch. No PR opened and no workflow bump performed.
- Moved the complete contract to `coga/skill-management`, "Executable skill
  scripts", with its identical packaged twin. The CLI index now links that
  section, and `coga-dev/testing` has a one-line link. Skill management owns
  the installed/bundled skill behavior; `coga/cli` remains an index.
- Preserved scope, mode-source selection, exclusions, remediation, and Dream's
  packaged-finding classification. Runtime behavior and fixtures are unchanged.
- PR #1097 merged as `fe0b7fa198f6b11a3f7015073ea382ccc436aed5` before this
  work and is an ancestor of the tested branch.
- Actual implementing agent: Codex (GPT-6), regardless of the configured
  `agent: claude`; no agent delegation or model override was used.
- Fetched and reconciled with `origin/main`; rebase made no changes. The
  successful test run's staged tree `089dd38f542e593cda9a54436c2a14b1db54ee92`
  equals the committed tree. Returned to clean, current `main` before writing
  this handoff.
- The implementation is ready for peer review after machine-local recovery.
  Restore the missing local config, unblock, verify the checkout/config, and
  finish this implement step with `coga bump`; do not repeat the implementation.

## Verification and recovery

- Final valid run: Linux, Python 3.12.12, pytest 9.1.1; **4121 passed,
  10 skipped** in 381.29 seconds. The temp root was outside every Git checkout.
  The exact command and revision receipt are in `## PR` below.
- The first run exhausted `/tmp` inodes: 1413 passed, 10 skipped, 2708 setup
  errors. Removed only that completed run's `/tmp/pytest-of-n/pytest-92`
  fixtures after preserving its log. Other pre-existing temp files were left
  alone; `/tmp` remained near its inode limit. Use an external workspace-disk
  temp root for subsequent verification, never a directory inside this repo.
- **Agent-caused recovery incident:** I retried with pytest's temp root under
  this checkout's `.coga/`. Repo-discovery tests reached the real parent
  repository, and uninstall tests removed its Coga roots and instructions.
  That invalid run reported 388 failed, 3721 passed, 10 skipped, 12 errors.
  I restored every tracked change caused by the run from the unchanged index,
  preserving the five intended staged documentation edits. The tracked tree
  then matched the original staged tree exactly and the independent rerun
  above passed.
- The ignored `/home/n/Code/coga/coga/coga.local.toml` was also deleted and
  cannot be restored from Git. No verified backup was found. I did not invent
  its settings or write a replacement. Generated agent-discovery views may
  also need the ordinary setup to rebuild them after config recovery.
- To record the blocker, use the documented `COGA_LOCAL_CONFIG` override with
  `/home/n/Code/codex/coga/coga/coga.local.toml`. This existing config loads
  successfully with user `nicktoper`; it is not a verified backup of the
  deleted file and was not copied over it.
- Recovery evidence is retained at
  `/home/n/Code/coga-test-recovery-ijlh24q3/`: `staged.patch`,
  `unstaged.patch`, `head.txt`, `AGENTS.md.coga-bak`, `pytest-inodes.log`,
  `pytest-invalid-location.log`, and `pytest-independent.log`.
- Adjacent harness safety finding: `tests/conftest.py`'s `_isolate_tmpdir`
  does not reject a temp root inside the source checkout. Tests expecting no
  containing repo then discover the source repo; the invalid run's
  `tests/test_aliases.py::test_main_missing_repo_points_to_init` printed real
  task state, and `src/coga/commands/uninstall.py::_execute_plan` removed the
  real roots. No harness change is included in this documentation ticket.
  No follow-up ticket was created during this recovery.

## PR

```yaml
title: Ship executable-script validation guidance
author: codex
author_evidence: >-
  This implement session used Codex (GPT-6), with no model override or
  delegation; the configured ticket agent claude was not the implementing agent.
head: f07099be6fb0ec7d59267276450c5cadf756b81a
base: 06d0f9f6d9fa572a21a342d76f69303e0b984a4c
depth: deep
rationale: >-
  Bounded documentation relocation with a passing final full-suite run.
  Independent review has not run, and recovery of the local configuration
  deleted by an invalid intermediate test setup remains blocked on the owner.
implementation: >-
  Makes coga/skill-management the shipped owner of the complete
  non-executable-script contract, preserves packaged twins, links the contract
  from the CLI index, and replaces the developer-only explanation with one link.
deviations: >-
  Used the existing skill-management topic rather than the ticket's example
  CLI location because coga/cli is an index. No runtime behavior changed.
limitations: >-
  Verified on Linux with Python 3.12.12; no native Windows or Python 3.11 run.
  The ignored primary-checkout local config needs restoration after the invalid
  intermediate test setup; tracked files were fully restored before the valid run.
files:
  docs/contexts/coga-dev/testing/SKILL.md: Replace the developer-only contract with a link to its shipped owner.
  docs/contexts/coga/cli/SKILL.md: Make the script-permission contract discoverable from the validate command row.
  docs/contexts/coga/skill-management/SKILL.md: Own the full user-facing contract and include validation in the topic description.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md: Ship the identical CLI index link.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/skill-management/SKILL.md: Ship the identical contract in the bootstrap fallback.
review:
  reviewer: none
  kind: none
  status: not-run
  detail: Independent review belongs to the next workflow step; implementation is blocked pending local-config recovery.
checks:
  - command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest
    status: failed
    head: f07099be6fb0ec7d59267276450c5cadf756b81a
    base: 06d0f9f6d9fa572a21a342d76f69303e0b984a4c
    detail: >-
      1413 passed, 10 skipped, 2708 errors in 182.47s. /tmp exhausted its
      inodes and fixture setup failed. Initial staged tree matched the eventual
      commit; this failed environmental attempt is superseded by the final run.
  - command: >-
      TMPDIR=/home/n/Code/coga/.coga/non-executable-script-tests-ctl_r1f0/tmp
      PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest
      --basetemp=/home/n/Code/coga/.coga/non-executable-script-tests-ctl_r1f0/pytest
    status: failed
    head: f07099be6fb0ec7d59267276450c5cadf756b81a
    base: 06d0f9f6d9fa572a21a342d76f69303e0b984a4c
    detail: >-
      INVALID TEST SETUP: 388 failed, 3721 passed, 10 skipped, 12 errors in
      434.18s. Starting staged tree matched this commit, but locating fixtures
      inside the source checkout let discovery/uninstall tests mutate that
      checkout during the run. This is not verification of the final tree.
      Tracked files were restored before the valid independent-temp-root run;
      the ignored local config remains missing.
  - command: >-
      TMPDIR=/home/n/Code/ct-x8b33adk/tmp PYTHONPATH=/home/n/Code/coga/src
      .venv/bin/python -m pytest --basetemp=/home/n/Code/ct-x8b33adk/pytest
    status: passed
    head: f07099be6fb0ec7d59267276450c5cadf756b81a
    base: 06d0f9f6d9fa572a21a342d76f69303e0b984a4c
    detail: >-
      4121 passed, 10 skipped in 381.29s; Linux, Python 3.12.12, pytest 9.1.1.
      Verified the temp root has no Git ancestor before execution. The tested
      staged tree equals the committed tree, and the subsequent rebase changed
      neither head nor tree. Includes packaging twins/links and validator tests.
  - command: git diff --check origin/main...HEAD
    status: passed
    head: f07099be6fb0ec7d59267276450c5cadf756b81a
    base: 06d0f9f6d9fa572a21a342d76f69303e0b984a4c
    detail: No whitespace errors after the final fetch and no-op rebase.
  - command: env -u SLACK_WEBHOOK_URL coga validate --json
    status: not-run
    detail: Seeded-fixture validation is not required for this documentation-only move; validation behavior and fixtures are unchanged.
```

---

## Blockers

- [ ] [2026-10-26 21:11] [agent:claude] id=20261026T211110 Restore /home/n/Code/coga/coga/coga.local.toml from a verified backup or confirm its intended settings. My invalid pytest temp root inside the checkout let uninstall tests delete it. All tracked files are restored; the documentation branch is pushed and the valid full suite passed 4121 tests with 10 skipped. Unblock after config recovery, then finish implement with bump.

---

## Blocker reminders

- 5adf299f7d3d last_reminded: 2026-10-27 10:51
