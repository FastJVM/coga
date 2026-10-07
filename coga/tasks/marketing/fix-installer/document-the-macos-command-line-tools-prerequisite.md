---
title: Document the macOS Command Line Tools prerequisite
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
step: 2 (peer-review)
agent: claude
launch_generation: pending:bf161e7e-7278-42d8-8ee7-9e6df997c59e
---

## Description

Reproduced 2026-10-01 on fresh macOS 27.0 (26A428), arm64 EC2 mac2.metal, AMI ami-0531fecfb292182a3. Exact harness command: AWS_PROFILE=multiply-telemetry ./scripts/clean-install/aws-mac.sh walk installer-mac-20261001 pypi cltprobe nicktoper. First failing command: git --version (exit 1), output: xcode-select: error: No developer tools were found and no install could be requested (possibly because there is no active GUI session). Python and Coga artifact resolution were not reached; intended matrix is Python 3.11 with current PyPI release and main wheel. This machine prerequisite affects both artifact paths before installation; neither artifact was installed in this probe. The harness deliberately removes the AMI CLT to reproduce a fresh Mac. Expected: the documented prerequisites explain the first Git invocation, graphical CLT install prompt, and an actionable SSH/headless path before telling users to git init or coga init. Suggested fix owner: docs/contexts/coga/install/SKILL.md and its packaged twin, linking the existing coga/testing/clean-install/macos-aws runbook as appropriate. Coordinate README wording with marketing/readme-top; do not duplicate that ticket or add an automatic Coga installer. Evidence: .coga/clean-install/installer-mac-20261001/walks/cltprobe/mac/evidence/steps.txt and transcript.txt. The SSH error is observed; the GUI dialog was not exercised. A headless softwareupdate CLT install is the test-machine workaround. Prior independent reproduction is recorded in marketing/fix-installer/macos-clean-install-harness-on-aws. Parent findings: marketing/fix-installer/run-clean-installs-and-file-issues.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: docs/macos-clt-prerequisite

Plan: add a macOS Command Line Tools prerequisite to `coga/install` (canonical + packaged twin, byte-identical), linking the `coga/testing/clean-install/macos-aws` runbook. Docs only; README wording stays with `marketing/readme-top`. Note why `coga init`'s git offer does not help on a fresh Mac: `/usr/bin/git` is a CLT shim, so `shutil.which("git")` in `init._require_init_tools` succeeds.

## Implement handoff (2026-10-06)

Commit `a64f4683b` on `docs/macos-clt-prerequisite` (pushed, rebased on current `origin/main`). Changed `docs/contexts/coga/install/SKILL.md` and its byte-identical packaged twin `src/coga/resources/templates/coga/bootstrap/contexts/coga/install/SKILL.md`:
- The Git prerequisite bullet now points macOS users to the CLT section.
- New `### macOS: install the Command Line Tools first` under Prerequisites, placed before Install the CLI, so it comes before any `git init`/`coga init`. It covers: `/usr/bin/git` is a stub, so the first git call triggers the CLT install; why `coga init` can't help (the stub passes `shutil.which` in `init._require_init_tools`, then the next git command init runs fails); the GUI path (`xcode-select --install`, then Install); the SSH/headless path with the exact observed error and the `softwareupdate` recipe; the CLT is machine-wide; CLT Python 3.9 is below the 3.11 floor; evidence caveat (SSH error observed 2026-10-01, dialog not exercised); a link to `coga/testing/clean-install/macos-aws`.

Decisions: docs only, no installer and no code change. README not touched: `marketing/readme-top` owns it and should link to or summarize `coga/install` instead of restating it. `coga/init`'s install-offer text was left alone; the new section explains the gap.

Tests: `python -m pytest`: 3273 passed, 1 failed (`tests/test_edge_distribution.py::test_documented_legacy_adoption_preserves_state_and_reconciles_callers`). It fails the same way on clean `main` (ordering of recurring `ticket.py` inventory). That is unrelated and already recorded in `marketing/fix-installer/offer-agent-cli-install-and-setup-at-init`. `test_packaging` twins pass. `git diff --check` is clean.

Possible follow-up (not done here): `coga init` could detect the macOS CLT stub (for example, `xcode-select -p` failing) and print the CLT hint, instead of failing later at its first git call.
