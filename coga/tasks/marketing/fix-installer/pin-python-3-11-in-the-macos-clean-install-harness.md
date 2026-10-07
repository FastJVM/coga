---
title: Pin Python 3.11 in the macOS clean-install harness
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
launch_generation: bd84e51e-1f13-4ebd-a456-0b74c3c7f9df
---

## Description

The macOS harness does not enforce the required Python 3.11 matrix, unlike Linux. Repro OS: macOS 27.0 (26A428), arm64 EC2 mac2.metal AMI ami-0531fecfb292182a3. After CLT installation, /usr/bin/python3 --version prints Python 3.9.6. scripts/clean-install/macos-walk.sh walk installs uv then invokes container.sh without UV_PYTHON or a Python provision/check. Prior unmodified macOS PyPI walk resolved coga 0.0.1 with no executable (2026-09-30, recorded in macos-clean-install-harness-on-aws). Current 2026-10-01 test-only workaround adds uv python install 3.11, UV_PYTHON=3.11, UV_PYTHON_DOWNLOADS=never and the managed interpreter bin directory to PATH: AWS_PROFILE=multiply-telemetry ./scripts/clean-install/aws-mac.sh walk installer-mac-20261001 pypi pypi311 nicktoper then reports Python 3.11.16, uv 0.12.21, Coga 0.2.0 and reaches init. Expected: the shared Linux/macOS matrix explicitly selects and records Python 3.11, refusing or provisioning the prerequisite rather than silently testing another interpreter. Applies to both main and PyPI artifact selection; this is a current harness gap, not a Coga 0.0.1 release regression. Suggested fix: scripts/clean-install/macos-walk.sh, macOS runbook docs/contexts/coga/testing/clean-install/macos-aws/SKILL.md and packaged twin, with appropriate harness tests. Existing macos-clean-install-harness-on-aws owns the merged original harness; this draft isolates the newly confirmed interpreter-contract gap. Evidence: .coga/clean-install/installer-mac-20261001/walks/pypi311/, and parent marketing/fix-installer/run-clean-installs-and-file-issues. Do not change package Python floor or publish a release.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: pin-mac-python-311

Plan: container.sh (shared Linux/macOS walk) refuses to run unless
UV_PYTHON + UV_PYTHON_DOWNLOADS=never select a 3.11 interpreter, records it,
and installs coga with that interpreter explicitly; macos-walk.sh provisions
3.11 with `uv python install` and exports the pins. Runbook + twin updated.

## Handoff (implement)

Commit 384b769e1 on `pin-mac-python-311` (pushed):

- `scripts/clean-install/container.sh` (shared Linux/macOS walk): before
  creating evidence, refuses (exit 2) unless `UV_PYTHON` is set and
  `UV_PYTHON_DOWNLOADS=never`. Replaces the bare `python3 --version` with
  `uv python find "$UV_PYTHON"` + `check_python`, which records
  `Python X.Y.Z at <path>` in the transcript and fails the step (exit 2, before
  any install) unless it is 3.11.*. `uv tool install` now passes
  `--python "$UV_PYTHON"` for both pypi and wheel modes. Note:
  `uv python find` ignores the `UV_PYTHON` env var (verified locally with
  uv 0.11), hence the explicit argument.
- `scripts/clean-install/macos-walk.sh walk`: after the uv installer, runs
  `uv python install 3.11` and exports `UV_PYTHON=3.11
  UV_PYTHON_DOWNLOADS=never`. Dropped the ticket's workaround of putting
  the managed interpreter's bin dir on PATH, because the walk no longer
  reads `python3` from PATH. The Linux Dockerfile already sets both vars
  (path form), so it needed no change.
- Tests (`tests/test_clean_install_harness.py`): the fixture now has a stub
  3.11 interpreter and pinned env. New tests cover the unpinned refusal (both
  vars), the 3.9.6 refusal before install, and the macOS walk provisioning
  and pinning (stubbed sudo/sysadminctl/uv).
- Docs: macOS runbook "walk pins Python 3.11" paragraph and step list; Linux
  parent topic notes the refusal. Packaged twins copied byte-identical.
- Not verified on a real Mac (needs an approved EC2 host). Package Python
  floor unchanged; no release.

Verification: `.venv/bin/python -m pytest` gave 3277 passed, 1 failed.
The failure was already there and is unrelated:
`tests/test_edge_distribution.py::test_documented_legacy_adoption_preserves_state_and_reconciles_callers`
(ordering mismatch: `coga/recurring/autoclose-merged/ticket.py` vs
`coga/recurring/_custom-phone-home/ticket.py` at index 0). It fails
identically with this change stashed on main 9d9a87de3. No follow-up ticket
filed.
