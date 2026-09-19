---
title: narrative-candidates.md publishes log text the owner ruled confidential
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

**This needs an owner decision, and it is the one finding in this Dream run
with a live exposure.**

`FastJVM/coga` is a public repository — `marketing/phase-0-audit`'s own
step-1-findings confirms it, and the audit blackboard notes "this repo is
public, so anything recorded here is public too".

`coga/tasks/marketing/phase-0-audit/narrative-candidates.md` is tracked (added
in `18cae534`). It opens with the owner's ruling that "magicator, xpllm, and
admin are confidential; the literal text, slugs, and block reasons must not be
quoted" — and then reproduces exactly that: ten candidates of verbatim
`coga/log.md` lines from those private repos, with ticket slugs, dates, line
numbers and the reasoning behind them (JVMTI hidden-class interception and
HotSpot strategy from magicator; LLVM slice gates and DaCapo sourcing from
xpllm), plus two admin-repo entries that step-1-findings describes as sitting
beside a trademark serial, Xero reconciles, payroll and tax questions, and a
named accountant.

Publishing the ruling next to the material it forbids does not un-publish the
material.

The file also no longer has a consumer: `marketing/post-async-megalaunch` has
been rescoped and contains no reference to it, and `marketing/plan` now says the
only publishable narrative evidence is Coga operating on Coga. So the retention
rationale — "kept here as evidence of the practice" — is buying nothing against
a real exposure.

Two secondary defects in the same file argue for deleting rather than editing:
its `### Shortfall statement` and step-1-findings both still assert "eight
strong ones with no confidentiality concern", pre-ruling text that directly
contradicts the header — so an agent reading either could conclude eight
candidates are quotable.

## Context

The decision is the owner's. The two coherent options:

- **Delete the attachment**, and decide separately whether the exposure warrants
  purging it from git history (a history rewrite on a public repo is disruptive
  and is not something to do casually or without the owner's explicit
  instruction); or
- **reduce it** to the non-quoting per-repo summary table, and fix the two
  "eight strong ones with no confidentiality concern" statements so nothing in
  the tree contradicts the ruling.

Either way the contradictory pre-ruling sentences must go.

Do not act on this without the owner. Dream deliberately did not open a PR that
would touch the file, because deleting it and purging history are different
decisions with different costs, and because a PR diff would quote the material
again.

<!-- coga:blackboard -->

## Dev

branch: remove-narrative-candidates
worktree: /home/n/Code/coga-remove-narrative-candidates

## Owner decision (2026-09-19, attended session)

Owner chose **delete from the tree only; no history rewrite**. Rationale
surfaced and accepted: the material is already in public history at
`18cae534`, so a deletion diff adds no new exposure, while a
`filter-repo` + force-push on a public repo with hundreds of PR refs is
disruptive and GitHub caches may still serve the old blob. If the owner
later wants a history purge, that is a separate ticket, not this PR.

## What changed (commit `358f5b11`)

- `git rm coga/tasks/marketing/phase-0-audit/narrative-candidates.md`.
- `step-1-findings.md` §3: replaced the "eight strong ones with no
  confidentiality concern" paragraph and the "Owner to confirm ... publishable"
  / "probably safe" bullets with the ruling and a pointer to the deletion.
  Also dropped the parenthetical paraphrasing the private repos' research
  direction. The non-quoting per-repo table stays (it was always here, not
  in the attachment).
- `audit-history.md`: the two mentions of the attachment now say it was
  deleted and why; no date changed.
- `coga/contexts/marketing/map/SKILL.md`: the "Private-repo narrative
  attachment" row now says the file is gone and must not be recovered from
  history or re-collected. `marketing/*` has no packaged twin.
- Left alone on purpose: `phase-0-audit/ticket.md`, the
  `phase-0-audit-is-complete...` and `document-the-remedy...` tickets, and
  `marketing/plan` — they reference this ticket or describe the historical
  move without asserting quotability.

## Verification

- `uv run --python 3.12 --with-editable ".[test]" --no-project python -m pytest -q`
  in the feature worktree: 2657 passed.
- `coga validate --json`: same issue set as `main` (the only extra line is
  the fresh worktree's missing `coga.local.toml` user).
- `grep` for the quoted research topics and "eight strong" across `coga/`:
  the only remaining hits are this ticket's own description.
- Rebased on `origin/main` (already up to date). Nothing pushed, no PR.

## Note for retro/done-ticket

This ticket's own `## Description` paraphrases the private repos' research
direction (it was written by Dream to explain the exposure). It is deleted
with the ticket at retro; do not carry that paragraph into a context.
