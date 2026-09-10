---
title: narrative-candidates.md publishes log text the owner ruled confidential
status: draft
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
step: 1 (implement)
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

The blackboard is a notepad to be written to often as the human and agent works through a task.
