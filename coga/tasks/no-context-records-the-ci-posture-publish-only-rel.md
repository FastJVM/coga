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
step: 2 (peer-review)
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

## Adjacent finding (not fixed here)

`test_wheel_includes_bootstrap_batteries` fails on this machine because the
`.venv` was created without `pip` (likely `uv venv`). The context already
documents the hatchling-missing variant of this trap; the pip-missing variant
reads the same way (environment noise that looks like a packaging regression).
Fix is environment-side (`uv pip install pip` or `python -m ensurepip`), or the
test could shell out via `uv build`. No follow-up ticket exists that I know of.
