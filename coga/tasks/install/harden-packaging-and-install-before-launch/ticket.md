---
slug: install/harden-packaging-and-install-before-launch
title: Harden packaging and first-install before launch
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
secrets: null
step: 1 (implement)
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

## Prerequisite audit (2026-07-12 relaunch)

- Checked before running the verification gate, per the scope decision above.
- PyPI: latest published release is `coga 0.2.0`, uploaded 2026-06-27 — before
  the 2026-07-08 clean-container retest that produced the sibling fixes. The
  repo's `pyproject.toml` also says 0.2.0, so the realigned release has not
  been cut; `install/cut-release-to-realign-pypi-with-main` is still `active`.
- Sibling fixes named in Prerequisites are not merged/done:
  `vendor-cli-from-installed-package-not-git-clone` (active),
  `warn-loud-when-init-commit-is-skipped` (active),
  `init-next-steps-should-mention-agent-cli-requireme` (active),
  `add-migration-errors-for-removed-config-keys` (active),
  `external-users-cannot-install-managed-skills` (in_progress, step 4 review),
  `decide-whether-gh-stays-required-at-init` (active).
- Conclusion: running the gate now would verify a release that predates every
  fix and fail for known reasons. Blocked instead; relaunch once the named
  siblings are done and the realignment ticket has published a new version to
  PyPI.

## Prerequisite audit (2026-07-16 megalaunch)

- This launch came from the 2026-07-16 10:10 `coga megalaunch` sweep that
  started every install/ ticket at once; the gate got picked up alongside the
  sibling fixes it depends on, which are mid-`implement` in parallel sessions
  today (warn-loud-when-init-commit-is-skipped just reached peer-review; none
  have reached open-pr, so nothing is merged).
- PyPI latest is still `coga 0.2.0` (uploaded 2026-06-27) and `pyproject.toml`
  on current `main` (c36b92bd, fetched from origin, 0 commits behind) still
  says 0.2.0 — the realigned release has not been published.
- `main` still lacks the fixes the gate must verify: `src/coga/commands/init.py`
  still vendors via `clone_upstream` (line 436), so
  `vendor-cli-from-installed-package-not-git-clone` has not landed in code.
- The ticket's own Prerequisites section (siblings merged + realigned version
  on PyPI) is therefore objectively unmet; running the five verification steps
  now would re-verify 0.2.0 and fail for already-known reasons, producing no
  new evidence. The 2026-07-15 owner reset changed ownership and workflow
  (code/with-review so the gate's evidence gets peer-reviewed) but did not
  assert the prerequisites were met.
- Decision: block with a relaunch condition rather than manufacture a branch —
  the ticket's acceptance criteria still say the gate produces no feature
  branch or PR, and it forbids absorbing sibling implementation. If the owner
  instead wants a standalone implement deliverable now (e.g. an automated
  clean-container harness that scripts the five verification steps), that
  needs an explicit say-so since it contradicts the written acceptance
  criteria.

---

## Blockers

- [x] [2026-07-11 10:52] [agent:claude] id=20260711T105203 This umbrella ticket has no standalone implementation acceptance: its concrete fixes are owned by still-active install/ siblings. Please approve converting it into the final clean-machine end-to-end verification gate after those fixes land, or name the specific standalone deliverable for this step.
  resolved: [2026-07-12 18:04] [human:nicktoper] Approved: convert this ticket to the final clean-machine end-to-end verification gate, using a one-step direct/body workflow and no implementation PR.

- [x] [2026-07-12 20:37] [agent:claude] id=20260712T203710 Verification gate prerequisites unmet: PyPI latest is coga 0.2.0 (uploaded 2026-06-27, predating the 2026-07-08 retest fixes) and the named install/ siblings (vendor-cli-from-installed-package, warn-loud-when-init-commit-is-skipped, agent-CLI guidance, migration errors, external-users-cannot-install-managed-skills) plus cut-release-to-realign-pypi-with-main are still active/in_progress. Relaunch this gate after those tickets are done and the realigned version is published to PyPI.
  resolved: [2026-07-15 21:00] [human:nicktoper] Owner reset 2026-07-15: nicktoper is taking over all install/ tickets; this gate is reset to active on code/with-review at step 1 alongside its siblings, overriding the 2026-07-12 direct/body scope decision.

- [x] [2026-07-16 10:14] [agent:claude] id=20260716T101438 Gate prerequisites still unmet at today's megalaunch: PyPI latest is coga 0.2.0 (pre-retest) and no sibling install/ fix has merged — they are mid-implement in parallel sessions launched this morning (init.py on main still clones upstream). Relaunch this gate after the sibling PRs merge and cut-release-to-realign-pypi-with-main publishes the realigned version; or, if you want a standalone deliverable now (e.g. an automated clean-container harness scripting the five verification steps), say so explicitly since the ticket's acceptance criteria currently forbid a branch/PR. Consider excluding this gate from megalaunch sweeps until then.
  resolved: [2026-07-19 20:05] [human:nicktoper] Proceed now with a standalone automated clean-container verification harness that scripts the five verification steps; this explicitly overrides the prior no-branch/no-PR acceptance constraint for this ticket.
## Blocker reminders

- 5f5852d1e838 last_reminded: 2026-07-15 12:33

- 3427f9e5e914 last_reminded: 2026-07-16 10:15
