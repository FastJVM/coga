---
title: Define the API-equivalent cost proxy and price table
status: draft
owner: nicktoper
agent: claude
contexts:
  - coga/usage
workflow: code/design-then-implement
---

## Description

Subscription plans have no cumulative token allowance — they are metered by
rate-limit windows — so "you are using a quarter of your $200 plan" has no
denominator today. Define one: convert recorded token usage into an
API-equivalent dollar figure, so a plan's price becomes the denominator and
"would the API bill have exceeded what I pay?" becomes answerable. Ship the
price table this needs, decide where it lives, and decide how it is kept from
silently going stale. `agent-usage-report` consumes what this ticket defines.

## Context

This reverses a decision `coga/usage` states outright: "No dollar cost is
computed — the team runs on a subscription, so tokens-per-task is the question,
not dollars (a price table is a deferred follow-up)." That deferral is the thing
being un-deferred, so the same PR updates `coga/contexts/coga/usage/SKILL.md`.
That context has no packaged twin under
`src/coga/resources/templates/coga/bootstrap/contexts/` today, so there is
nothing to mirror — but re-check before editing, because the twin rule in
`CLAUDE.md` is enforced by `tests/test_packaging.py` and a one-sided edit of a
paired file fails the suite.

Constraints and pointers:

- **Per-category weights are mandatory.** The four token categories are kept
  distinct precisely because coga composes large cached context layers and cache
  tokens dominate. Cache-read bills at roughly 10% of the input rate and
  cache-create at roughly 125%, so a flat total-tokens price would be off by an
  order of magnitude. Confirm current published rates at design time rather than
  trusting these ratios.
- Codex records leave cache-create null and fold reasoning into output; Claude
  records carry all four. The proxy must be honest about a provider whose
  categories do not decompose, not silently price it as if they did.
- Records with `usage_status: unknown` carry zero tokens. They must not be
  priced as zero dollars silently — `Rollup.unknown_sessions`
  (`src/coga/usage.py:148`) already counts them.
- **Where it lives is the real design question.** A price table is data that
  goes stale on Anthropic's and OpenAI's schedule, not coga's. Weigh: constants
  in `src/coga/usage.py`, a committed data file at the edge, or config in
  `coga.toml`. The microkernel rule in `CLAUDE.md` argues against new core
  surface that has one consumer; the counter-argument is that `coga usage` is
  already the single read accessor and consumers are told not to re-parse
  records themselves. Whatever the answer, state the staleness policy: how a
  reader knows the table's vintage, and what happens when a model id is absent
  from it.
- Model ids in records are whatever the CLI reported. Unknown-model handling is
  part of the contract, not an afterthought.

Out of scope: the report itself, its cadence, and its delivery surface — that is
`agent-usage-report`. Adding a `user` field to usage records is also out of
scope and is its own ticket.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
