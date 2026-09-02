---
slug: no-context-records-the-ci-posture-publish-only-rel
title: 'No context records the CI posture: publish-only release workflow, no test
  gate'
status: draft
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
secrets: null
step: 1 (implement)
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

Filed by Dream 2026-W36, Phase 2 knowledge scan (shard `ks-07`), classified `gap`.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
