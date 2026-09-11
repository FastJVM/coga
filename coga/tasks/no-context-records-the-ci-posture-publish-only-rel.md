---
title: 'No context records the CI posture: publish-only release workflow, no test
  gate'
status: in_progress
owner: nicktoper
agent: claude
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
step: 4 (review)
---

## Description

Record this repo's actual CI posture in `coga/contexts/coga/codebase/SKILL.md`, the
context that owns "how to run tests and validation".

Three independent tickets each had to re-derive the CI state from scratch, and all
three are now wrong in the same direction — they assert there is no CI at all, when
in fact a publish-only release workflow exists and no test gate does.

Deliverable: a short CI subsection in `coga/codebase` (and its enforced packaged twin)
stating (a) that the only GitHub Actions workflow is publish-only `release.yml`,
triggered by a published Release or manual dispatch, pointing at `docs/releasing.md`;
(b) that there is no PR/push test job, so the local suite plus `coga validate` are the
release gate, and a verifier must state the exact commands and counts they ran; and
(c) that the clean-checkout-only wheel collision documented above that section is
therefore never caught automatically.

The point is not to add CI. It is to stop the open `minimal-ci` design ticket — and
every future verification plan — from starting on a false premise.

## Context

Citations name symbols and files, not line numbers.

**The three stale re-derivations:**

- `coga/tasks/v2/minimal-ci-run-pytest-on-prs-and-tags.md` asserts "There is no CI
  today (`.github/workflows/` does not exist)".
- `coga/tasks/v2/add-dev-testing-setup-skill.md`'s discovery notes record "**no CI
  exists** — local commands are the only gate".
- `coga/tasks/v2/fix-windows-cli-import-crash.md` builds its whole hand-verification
  protocol on "there is no platform-matrix CI today, so no-regression must be proven
  by hand."

**Current reality:** `.github/workflows/release.yml` exists but is publish-only — it
triggers on `release: published` and `workflow_dispatch` and does `uv build` plus
PyPI/TestPyPI Trusted Publishing (OIDC), with one-time setup documented in
`docs/releasing.md`. Nothing runs `pytest` on a push or a PR.

So the *conclusion* those tickets draw (a local run is the only correctness gate) is
still right, but their *premise* is wrong, and the consequence they miss is sharper: a
release tag ships whatever the publisher's local run happened to cover.

`coga/codebase`'s "Daily commands" section lists only local commands and never states
that there is no PR test gate, nor that a release workflow exists at all.

Note for whoever picks this up: `v2/minimal-ci-run-pytest-on-prs-and-tags` is the
ticket that would *change* the posture. This ticket only records it. If that one is
being taken up at the same time, fold this into it rather than landing both.

`coga/contexts/coga/codebase/SKILL.md` is an enforced byte-identical twin with
`src/coga/resources/templates/coga/bootstrap/contexts/coga/codebase/SKILL.md`
(`IDENTICAL_LIVE_PACKAGED_PAIRS` in `tests/test_packaging.py`) — edit both.

**Review notes (evaluator, verified against the repo):**

- Leave the three stale v2 tickets as they are. `coga/tasks/v2/README.md` defines
  them as dated records, not specs; `release.yml` landed 2026-06-25 and they were
  drafted at or after that, so they are stale, not to be corrected here.
- `release.yml` also runs `twine check` on the built artifacts before publishing —
  the one automated check that exists. Mention it in the subsection.
- "A verifier must state the exact commands and counts they ran" is a new norm this
  subsection introduces, not an existing fact. The owner accepted carrying it in
  `coga/codebase`.
- `IDENTICAL_LIVE_PACKAGED_PAIRS` is derived from `_discover_live_packaged_twins()`
  filtered by `INTENTIONALLY_DIVERGENT_TWINS`; it is not a registry to append to.
  Just edit both files identically and run `pytest tests/test_packaging.py`.
- No contexts attached on purpose: the ticket edits `coga/codebase`, which the
  agent opens first thing regardless.

Filed by Dream 2026-W36, Phase 2 knowledge scan (shard `ks-07`), classified `gap`.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

pr: https://github.com/FastJVM/coga/pull/787
branch: ci-posture
worktree: /home/n/Code/claude/coga-ci-posture

## Implement — 2026-09-11

**What changed.** Added `### CI posture: publish-only release workflow, no test
gate` at the end of `## Daily commands` in `coga/contexts/coga/codebase/SKILL.md`
and its packaged twin
`src/coga/resources/templates/coga/bootstrap/contexts/coga/codebase/SKILL.md`
(byte-identical, confirmed with `cmp`). Placement: directly after the
PYTHONPATH guidance and before `## Installed-versus-source skew warning`, so it
sits below the wheel-collision section it references.

**Content covers the three deliverables plus the review notes:** (a) `release.yml`
is the only workflow, publish-only, triggered by published Release or
`workflow_dispatch`, runs `uv build` + `twine check` + Trusted Publishing, points
at `docs/releasing.md`; (b) no PR/push test job — local `pytest` + `coga validate
--json` are the release gate, and a verifier must state exact commands and counts
(the new norm the owner accepted); (c) the clean-checkout-only wheel collision is
never caught automatically (release.yml builds pristine, but only at publish
time). Closes with a pointer to `v2/minimal-ci-run-pytest-on-prs-and-tags` as the
parked design that would change the posture.

**Decisions.**
- Left the three stale v2 tickets untouched, per the evaluator note.
- Did not touch `tests/test_packaging.py`: twins are discovered, not registered.
- Verified `release.yml` by reading it (`d0645a19`, 2026-06-26): both jobs run
  `uvx twine check dist/*` before publishing, matching the review note.

**Verification.** See `## Verification` below.

## Verification

Commit `79d23488` on `ci-posture`, rebased on `origin/main` (already up to date).

- `cmp` of live vs packaged twin → identical.
- `PYTHONPATH=$PWD/src /home/n/Code/claude/coga/.venv/bin/python -m pytest`
  from the feature worktree → **2434 passed, 1 failed** (172s).
- The one failure is `tests/test_packaging.py::test_wheel_includes_bootstrap_batteries`,
  error `No module named pip` — the project `.venv` has no pip, so the test's
  `python -m pip wheel` subprocess cannot run. **Pre-existing and unrelated:**
  fails identically on `main` in the primary checkout. Not masked, not fixed here.
- Substitute check for that test: `uv build` from the feature worktree (what
  `release.yml` itself runs) succeeds, and the wheel contains
  `coga/resources/templates/coga/bootstrap/contexts/coga/codebase/SKILL.md`
  with the new subsection.
- `coga validate --json` from the worktree → 204 ok; only issue is
  `missing-user` (no `coga.local.toml` in the worktree), unrelated.

## Implement-time environment finding (resolved during peer review)

`test_wheel_includes_bootstrap_batteries` failed during implementation because
the project `.venv` lacked `pip`; peer review also found the declared
`hatchling` dependency missing. Both were installed locally during peer review,
and the complete suite now passes. No source or test change was needed.

## Peer review

2026-09-11, Codex in `/home/n/Code/claude/coga-ci-posture` on `ci-posture`.

- Ran `git fetch origin main` and `git rebase FETCH_HEAD` unconditionally;
  rebase succeeded without conflicts onto `9074b67f`, producing `644fff69`.
- Ran `codex review --base main` outside the sandbox. **The review returned**
  (exit 0) with no findings. Its packaging check used the ambient Python and
  reported 10 passed / 1 failed because that interpreter lacks `hatchling`.
- Independent review corrected one factual overstatement in both context
  copies: the wheel collision has no automatic PR/push gate, but the release
  build can catch it before uploading. The wording now distinguishes that late
  build from earlier verification and covers manual dispatch as well as a
  published Release. This preserves the ticket's warning without claiming a
  failing build can upload artifacts.
- Repaired only the local test environment: ran
  `/home/n/Code/claude/coga/.venv/bin/python -m ensurepip`, then
  `/home/n/Code/claude/coga/.venv/bin/python -m pip install --disable-pip-version-check 'hatchling>=1.18'`.
  No dependency manifest or test code changed. Before the wording correction,
  `PYTHONPATH=$PWD/src /home/n/Code/claude/coga/.venv/bin/python -m pytest tests/test_packaging.py`
  returned **11 passed** (two sandbox cache-write warnings).
- `cmp coga/contexts/coga/codebase/SKILL.md src/coga/resources/templates/coga/bootstrap/contexts/coga/codebase/SKILL.md`
  and `git diff --check` from the feature worktree both returned exit 0.
- Source-pinned repo validation from the feature worktree:
  `PYTHONPATH=$PWD/src /home/n/Code/claude/coga/.venv/bin/python -m coga.cli validate --json`
  returned **204 ok, 23 warnings, 5 errors** (exit 1). The same command on
  primary `main` returned **204 ok, 22 warnings, the same 5 errors**; the extra
  feature-worktree warning is `missing-user`. Existing errors are the removed
  `coga/digest/flush` skill referenced by `recurring/digest` and unsynthesized
  blackboards in four v2 drafts (`autotrigger-ticket-type`,
  `measure-relay-prompt-scope-and-agent-precision`,
  `split-context-to-doc-user-accessible-and-editable`,
  `use-worktree-when-starting-a-dev-task`). These are unrelated to this diff.
- Task-specific validation from the primary checkout:
  `PYTHONPATH=$PWD/src /home/n/Code/claude/coga/.venv/bin/python -m coga.cli validate --json --task no-context-records-the-ci-posture-publish-only-rel`
  returned **1 ok, 0 issues** (exit 0).
- Final full suite after the rebase and wording correction, from the feature
  worktree outside the sandbox:
  `PYTHONPATH=$PWD/src /home/n/Code/claude/coga/.venv/bin/python -m pytest`
  returned **2435 passed in 168.84s** (exit 0), including all 11 packaging tests.
- Committed the correction as `1c1e5255` (`peer-review: clarify release build
  timing`). `git status --short --branch` confirms a clean `ci-posture` worktree;
  `git rev-list --left-right --count main...HEAD` returns `0 2`. The branch
  changes only the two context copies. Peer review is complete and ready for
  the mechanical `open-pr` step.

## PR

Record the repository's actual CI posture in `coga/codebase` and its packaged
twin: `release.yml` builds, checks metadata, and publishes on a published
GitHub Release or manual dispatch, with no PR/push test job. Point to
`docs/releasing.md`, require exact local verification commands and counts,
and explain that a clean-checkout wheel collision has no PR/push gate even
though the release build can catch it before upload.

Test plan: feature worktree `PYTHONPATH=$PWD/src /home/n/Code/claude/coga/.venv/bin/python -m pytest` — **2435 passed**; `cmp coga/contexts/coga/codebase/SKILL.md src/coga/resources/templates/coga/bootstrap/contexts/coga/codebase/SKILL.md` — identical; primary checkout `PYTHONPATH=$PWD/src /home/n/Code/claude/coga/.venv/bin/python -m coga.cli validate --json --task no-context-records-the-ci-posture-publish-only-rel` — **1 ok, 0 issues**.

Repo-wide `PYTHONPATH=$PWD/src /home/n/Code/claude/coga/.venv/bin/python -m coga.cli validate --json` reports **204 ok, 5 existing errors** on both the feature branch and `main` (23 and 22 warnings respectively; the extra worktree warning is its missing local user). Codex review returned with no findings; independent review clarified the release-build timing.

## Open-PR — 2026-09-11

Confirmed the peer-review note records the Codex review as returned (no
findings) before publishing. Ran `coga open-pr` from the primary control
checkout on `main`; it reported `origin/main` advanced only through
non-overlapping task/log state, pushed `ci-posture` at `1c1e5255`, and opened
https://github.com/FastJVM/coga/pull/787. `pr:` recorded under `## Dev`;
primary checkout clean afterwards. Next step is the owner's merge decision.
