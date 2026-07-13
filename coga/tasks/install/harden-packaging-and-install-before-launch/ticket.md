---
slug: install/harden-packaging-and-install-before-launch
title: Harden packaging and first-install before launch
status: in_progress
mode: agent
owner: zach
human: zach
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: direct/body
  steps:
  - name: execute
    skills:
    - direct/body
    assignee: agent
secrets: null
step: 1 (execute)
---

## Description

Final release gate for Coga's public first-install path. Once the concrete
`install/` sibling fixes have landed and the target version is published, prove
that a clean machine can install Coga from PyPI, initialize an existing Git
repository, and run its first task through a workflow without relying on a Coga
source checkout, private repository access, or undocumented recovery steps.

## Context

Greg's onboarding feedback and the 2026-07-08 clean-container retest produced
the concrete fixes tracked by sibling tickets under `install/`. Those tickets
own implementation; this ticket owns only the final integrated verification.

The supported public path is the published `coga` wheel installed as an
isolated CLI with `uv tool install coga`. `uv pip install coga` and plain
`pip install coga` remain alternatives, not separate release gates. Do not add
a curl-to-shell installer or dependency lockfile unless a failed verification
produces evidence that the wheel-based path cannot meet the gate.

## Prerequisites

- First-install sibling fixes from the clean-container retest are merged,
  including package-based CLI vendoring, init failure/remediation, dependency
  guidance, migration errors, and managed-skill degradation.
- The release-realignment ticket has published the intended version to PyPI.
- The test environment has the documented external prerequisites: Python
  3.11+, Git, GitHub CLI if still required by the resolved dependency policy,
  and one supported authenticated agent CLI.

## Verification

Run the public path in a disposable clean Linux environment, without
`PYTHONPATH`, a source checkout, or private FastJVM repository credentials:

1. Install the released package with `uv tool install coga` and confirm
   `coga --version` reports the intended release.
2. Create an ordinary existing Git repository with an initial commit and run
   the documented `coga init --user <name>` command from its root.
3. Confirm init completes without cloning Coga main, the repo-local CLI matches
   the installed release, bundled workflows/skills are available, and every
   warning includes an actionable remedy.
4. Create and launch a minimal task through a bundled workflow using the
   installed authenticated agent CLI; complete its first state transition and
   confirm the task, blackboard, log, and Git state remain legible and valid.
5. Record the environment, exact commands, released version, and outputs on the
   blackboard. Any failure becomes a focused sibling ticket; do not absorb its
   implementation into this gate.

## Acceptance criteria

- The five verification steps pass from the public release in a clean
  environment.
- No install or init step reads Coga source from a local checkout, clones main,
  or requires access to a private repository.
- `coga validate --json` passes in the initialized repository after the first
  workflow transition.
- The blackboard contains reproducible evidence and links any follow-up ticket.
- This ticket is then marked done directly; it produces no feature branch or PR.

<!-- coga:blackboard -->

## Scope audit

- The supported install decision has already landed outside this ticket: the
  README leads with the isolated PyPI install `uv tool install coga`, with
  environment-local `uv pip install coga` / `pip install coga` alternatives;
  `pyproject.toml` defines the `coga` wheel; `tests/test_packaging.py` builds
  that wheel and checks its bundled batteries; and `.github/workflows/release.yml`
  publishes through PyPI Trusted Publishing.
- This ticket explicitly calls itself an umbrella/scoping ticket and says its
  concrete fixes are sibling `install/` tickets. It has no acceptance criteria
  naming a standalone code or documentation change for the current
  `code/implement` step.
- It is not safe to close as already satisfied: the 2026-07-08 clean-container
  retest produced still-active sibling defects, including vendoring the running
  installed package instead of cloning main, warning when init cannot create
  its first commit, dependency/agent-CLI guidance, migration errors, and release
  realignment.

## Scope decision

- Approved by the human on 2026-07-12: this is the final clean-machine
  verification gate, not an implementation umbrella.
- The code/PR workflow was replaced with the repository's one-step
  `direct/body` workflow. Relaunch only when the prerequisites in the ticket
  body are satisfied; a successful run records evidence and marks the ticket
  done directly.

---

## Blockers

- [x] [2026-07-11 10:52] [agent:claude] id=20260711T105203 This umbrella ticket has no standalone implementation acceptance: its concrete fixes are owned by still-active install/ siblings. Please approve converting it into the final clean-machine end-to-end verification gate after those fixes land, or name the specific standalone deliverable for this step.
  resolved: [2026-07-12 18:04] [human:nicktoper] Approved: convert this ticket to the final clean-machine end-to-end verification gate, using a one-step direct/body workflow and no implementation PR.
