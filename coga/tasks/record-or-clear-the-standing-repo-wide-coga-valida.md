---
title: Record or clear the standing repo-wide coga validate baseline
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
launch_generation: f24299db-f824-4252-8f3a-d2a452482ea8
---

## Description

`coga validate --json` exits 1 repo-wide as a matter of course, because four
`v2/` drafts carry unsynthesized blackboards: `v2/autotrigger-ticket-type`,
`v2/measure-relay-prompt-scope-and-agent-precision`,
`v2/split-context-to-doc-user-accessible-and-editable`, and
`v2/use-worktree-when-starting-a-dev-task`.

Independent tickets keep re-establishing this from scratch as part of their own
verification. `service-account-scoping-single-vault-rule-conflict` recorded "45
issues, 4 errors, all four pre-existing `unsynthesized-draft-blackboard` errors
on unrelated `v2/` drafts"; `redo-documentation-dir-and-merge-it-with-context-b`
recorded "exit 1, 175 OK, 40 warnings, four existing
`unsynthesized-draft-blackboard` errors" and named all four slugs. This Dream
run's own validate-drift pass found the same four.

`triage-the-v2-parking-area-empty-descriptions-prem`, whose title is literally
about the permanently red validate, is `canceled` — so nothing is scheduled to
clear it.

`coga/contexts/coga/codebase/SKILL.md` already tells agents to prefer
`coga validate --task <slug>`, but does not say that the repo-wide run is
expected to be red, which four errors are the standing baseline, or that they
must not be auto-fixed under an unrelated ticket.

## Context

Either outcome closes this, and they are not equivalent:

- **Record the baseline** beside the existing `--task` bullet in
  `coga/contexts/coga/codebase/SKILL.md` (and its enforced packaged twin) with
  its date and the four slugs, plus the rule that they must not be swept up by
  an unrelated ticket; or
- **clear it** by synthesizing or adjudicating those four drafts, so the
  repo-wide gate can go green and stay meaningful.

The second is better if the drafts are being adjudicated anyway — see the
sibling ticket `adjudicate-parked-and-active-tickets-whose-premise`, which
covers several of the same files. Sequence this behind it if both are worked.

Guard: a green validate is never a reason to cancel a draft.

<!-- coga:blackboard -->

## Dev

branch: validate-baseline
worktree: /home/n/Code/claude/coga-validate-baseline

## Decision: record the baseline (not clear it)

- Verified 2026-09-16 on `main` (`6184b971`): `coga validate --json` exits 1
  with 208 OK and exactly four errors, all `unsynthesized-draft-blackboard`,
  on the four `v2/` slugs the ticket names. Everything else is a warning.
- Every ticket that owns clearing them is still `draft`, so nothing to
  sequence behind: `adjudicate-the-eight-premise-dead-v2-drafts` (owns
  `autotrigger-ticket-type` + `split-context-to-doc…`, cancel only after an
  owner `review-design` gate), `correct-the-v2-known-stale-surfaces-table-and-rout`
  (owns synthesizing `measure-relay…` + `use-worktree…`), and
  `adjudicate-parked-and-active-tickets-whose-premise` (also lists
  `split-context-to-doc…`). Clearing here would either duplicate their
  synthesis or pre-empt an owner-gated cancel — exactly the "swept up under an
  unrelated ticket" move the ticket forbids.
- So: add a baseline bullet beside the existing `--task` bullet in
  `coga/contexts/coga/codebase/SKILL.md` and its packaged twin
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/codebase/SKILL.md`
  (byte-identical; `tests/test_packaging.py` enforces it). The bullet names
  the date, the four slugs, the "do not clear under an unrelated ticket" rule,
  the "green validate is never a reason to cancel" guard, and instructs
  whoever clears the last error to delete the bullet in the same PR.

## Implement handoff (2026-09-16)

- Commit `8135e9cd` on `validate-baseline` (worktree above), rebased on
  `origin/main` `6184b971`, tree clean. Two files changed, byte-identical:
  the live context and its packaged twin. No source or fixture change.
- Verified: `python -m pytest` in the worktree with the repo `.venv`
  (Python 3.12) — 2561 passed. `coga validate` behavior is unchanged, so the
  example fixture was not touched. Note for reviewers: the system `python` is
  3.9, so run tests with `.venv/bin/python`.
- Not done, by design: the four drafts are untouched. Their errors clear only
  through the adjudication tickets named above; the new bullet says the same
  and asks whoever clears the last one to delete it.
- Not pushed, no PR — `open-pr` step owns that.
