---
title: Publish coga 1.0 as the final V1 step
status: in_progress
owner: nicktoper
contexts:
- coga/releasing
- marketing/plan
workflow:
  name: draft-for-human
  steps:
  - name: agent-produces
    skills: []
    assignee: agent
  - name: human-owns-and-finishes
    skills: []
    assignee: owner
  - name: report-to-coga
    skills: []
    assignee: agent
step: 2 (human-owns-and-finishes)
agent: claude
---

## Description

Prepare and publish coga 1.0.0 to PyPI as the final V1 product-delivery step, after all remaining V1 changes and readiness checks are complete and before the public V1 launch. The 0.4.0 release published on 2026-10-02 is an interim release, not the final V1 release. Prepare a tested release candidate and release notes for owner approval, publish through the existing Trusted Publishing workflow when authorized, then verify the public package and record the release evidence.

## Context

### Ordering and scope

Owner request, 2026-10-02: this is the last V1 product-delivery ticket. Keep it
in draft until the owner confirms the remaining V1 work is complete. Follow
the release ordering in `marketing/plan`; coordinate readiness with
`marketing/build-the-launch-plan` without taking over its public launch work.

The earlier ticket `cleanup/publish-coga-1-0-to-pypi` shipped **0.4.0** despite
its historical title. The owner confirmed that release works. Its successful
install check is historical evidence, not approval to skip the final V1 gate.
Release: https://github.com/FastJVM/coga/releases/tag/v0.4.0 .

### Execution and acceptance

- Prepare the final candidate from `main` after the remaining V1 fixes land.
  Record the exact commit, readiness evidence, release notes, and proposed
  `1.0.0` version bump for the owner to review.
- Include the final README from `main` as the PyPI project description via
  `pyproject.toml` (`[project] readme = "README.md"`). Coordinate the rewrite
  with `marketing/readme-top`; keep one source rather than separate PyPI copy.
  Check the built metadata and the published PyPI description against the
  release commit's README, including Markdown rendering and documentation
  links. The 0.4.0 description was verified byte-identical to the current
  `main` README on 2026-10-02; recheck after the V1 README changes land.
- Read `coga/testing` (`docs/contexts/coga/testing/SKILL.md`) for the local
  suite and validation gate, and `coga/packaging`
  (`docs/contexts/coga/packaging/SKILL.md`) for pristine-checkout build checks.
  These are cited rather than attached. Record exact commands and results;
  do not carry forward the 0.4.0 validation exception without a new decision.
- Follow the attached release runbook. The owner approves the final candidate
  and publication; an explicitly authorized agent may assist with publishing.
  This draft does not authorize an immediate upload.
- After publishing, verify that a fresh public-index install obtains `1.0.0`,
  init and validation succeed on the documented Python floor, and the README
  first-task path works against the published artifact. Reuse the existing
  clean-install harnesses and coordinate outstanding platform and PostHog
  evidence with their owning tickets.
- Record the GitHub Release, PyPI page, workflow run, artifact hashes, and
  verification receipts. Hand the verified release links to the launch
  execution ticket before the public V1 announcement.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Step 1 (agent-produces) — provisional 1.0.0 candidate brief, 2026-10-06

**Status: NOT a final candidate.** The ticket says to hold until the owner
confirms remaining V1 work is done, and it is not done yet. Nothing was bumped,
tagged or uploaded. This step produced a dry run of the pre-tag gate on current
`main` plus draft release notes, so the real gate is a re-run, not discovery.

### Outstanding V1 work (as of 2026-10-06, `main` @ 6222b47ee)
- `marketing/readme-top` — draft. README has been edited heavily on `main`
  10-05/10-06 (owner commits); final README must land before the candidate.
- `marketing/verify-posthog-telemetry-with-the-live-clean-wheel` — draft; the
  plan names it the one open PostHog launch gate.
- `marketing/fix-installer/*`: CLT prerequisite (PR #971), agent-CLI offer at
  init (PR #970), pin Python 3.11 in macOS harness (PR #968) — all in review;
  `complete-the-authenticated-clean-install-audit` — **blocked**;
  `affordable-macos-testing...` — draft (owner decides whether V1-gating).
- Other open product PRs not on the marketing path: #962–#967, #969. Owner to
  decide which must land in 1.0.
- `marketing/build-the-launch-plan` — step 2 (human). Coordinate only.

### Provisional gate on `main` @ 6222b47ee (pristine `git clone` in scratch)
| Check | Command | Result |
| --- | --- | --- |
| Suite | `PYTHONPATH=<clone>/src .venv/bin/python -m pytest -q -p no:cacheprovider` | **1 failed, 3273 passed** (283s) |
| Build | `uv build` (hatchling 1.32.4, Metadata-Version 2.5) | ok |
| Metadata | `uvx --python 3.11 twine check dist/*` (twine 7.0.0) | both PASSED |
| Install | fresh `python3.11 -m venv` (3.11.15), `pip install --no-cache-dir <wheel>` | `coga 0.4.0` |
| Init | `coga init --user tester` in scratch git repo | rc 0 |
| Validate | `coga validate --json` (with `SLACK_WEBHOOK_URL` unset) | rc 0, no issues |
| README | wheel `METADATA` body vs `README.md` | byte-identical, `text/markdown` |

Hashes (0.4.0-versioned dry build, for reference only): wheel
`3f40289f…eec27`, sdist `378a416f…b3d224f`.

### Findings to resolve before the real gate
1. **Suite failure — locale-dependent test/runbook (fix needed).**
   `tests/test_edge_distribution.py::test_documented_legacy_adoption_preserves_state_and_reconciles_callers`
   runs the documented `<!-- migration:inventory -->` command
   (`rg … | sort` in `docs/contexts/coga/packaging/edge-code-upgrades.md` +
   packaged twin) and compares to Python `sorted()`. Under `en_US.UTF-8`,
   `sort` puts `autoclose-merged/` before `_custom-phone-home/`; passes with
   `LC_ALL=C`. Suggested fix: `LC_ALL=C sort` in both runbook copies (keeps
   operator output deterministic), or set `LC_ALL=C` in the test env. Needs
   its own small code ticket; the 1.0 gate must not carry a failing test.
2. **First-run friction: `SLACK_WEBHOOK_URL` in the user's env makes
   `coga validate` exit 2** ("Bare `SLACK_WEBHOOK_URL` is no longer supported"),
   while `coga init` says notifications are optional. Anyone migrating with
   that var exported hits a red validate on step one. Owner decision: accept
   (documented) or downgrade to a warning before 1.0.
3. **README relative links won't resolve on PyPI.** ~11 links like
   `docs/contexts/coga/install/SKILL.md`, `CONTRIBUTING.md` render as
   pypi.org-relative 404s. Fix in `readme-top` with absolute
   `https://github.com/FastJVM/coga/blob/main/...` links (one source, still
   works on GitHub). This was true for 0.4.0 too.
4. **Runbook note (no product bug):** bare `uvx twine check` on this host
   picked Python 3.9 → twine 6.2.0, which rejects Metadata 2.5 (false failure).
   CI used a newer twine and passed for 0.4.0. Suggest `coga/releasing` say
   `uvx --python 3.11 twine check dist/*`.
5. Minor: `license = { text = "Apache-2.0" }` is the legacy table form; PEP
   639 SPDX string `license = "Apache-2.0"` is preferred. Optional.

### Proposed version bump (do not land until owner approves candidate)
`pyproject.toml`: `version = "0.4.0"` → `version = "1.0.0"`. Consider adding
`"Development Status :: 5 - Production/Stable"` classifier. Check for other
version strings (`coga --version` reads package metadata).

### Draft release notes — coga 1.0.0 (edit freely)
> **coga 1.0.0** — first stable release. A CLI on top of your coding agents:
> per-task context and workflows, stored as Markdown in Git.
>
> **Licensing:** coga is now **Apache-2.0** (0.4.0 and earlier: AGPL-3.0-or-later).
>
> **Since 0.4.0**
> - Concurrent agent sessions are matched to their launch by a prompt marker;
>   malformed pinned transcripts stay "unknown" rather than mis-attributed.
> - Persisted usage reasons redact local paths.
> - Published blobs hash through the checkout's clean filters (CRLF/line-ending
>   repos no longer see spurious drift); local `main` realigns over state-only
>   commits already on control.
> - Recurring jobs record why a child bailed; weekly telemetry snapshot reserved.
> - [installer/onboarding items from PRs #968/#970/#971 if they land]
> - Docs: platform support recorded; release gate and macOS harness guidance.
>
> **Install:** `uv tool install coga` (or `python -m pip install coga`), Python ≥ 3.11.
> Then `coga init` and `coga build`. See the README.

Assumptions/weak spots: notes cover `src/`+packaging commits only from
`v0.4.0..origin/main`; items from still-open PRs are placeholders; install line
assumes README's recommended method — match the final README.

### Real-gate checklist (after owner confirms V1 complete)
1. Land remaining V1 PRs + fixes 1/3 (and 2 if chosen); land version bump.
2. Re-run the table above on the exact tag commit; record count + hashes.
3. Owner approves candidate + notes → owner (or explicitly authorized agent)
   drafts Release `v1.0.0` on `main`; workflow publishes.
4. Verify: fresh 3.11 venv, `pip install --no-cache-dir --index-url https://pypi.org/simple coga==1.0.0`;
   init + validate; PyPI page description renders and links resolve;
   `scripts/verify-clean-install.sh 1.0.0` with a real agent (first-task path).
5. Record Release URL, PyPI URL, run ID, sha256s → hand to `build-the-launch-plan`.
