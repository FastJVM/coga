---
slug: agent-usage-report
title: agent-usage-report
status: active
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
- coga/usage
skills: []
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
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
step: 1 (design)
---

## Description

A recurring report that tells people where they stand with their AI usage, so
they can right-size their subscription. If someone on the $200 plan is only
using a quarter of it, the report should make that visible enough that
downgrading becomes an obvious call. Runs weekly or monthly — often enough to
act on, not so often it becomes noise.

## Context

Deliberately thin: this is the vision, not the design. The engineering path is
the `design` step's call.

**Depends on `define-the-api-equivalent-cost-proxy-and-price-tab`.** Plan
utilization has no defined denominator today — subscription plans are metered by
rate-limit windows, not a cumulative token allowance — so the proxy that makes
"a quarter of the $200 plan" mean anything is being defined in its own ticket,
along with where the price table lives and how it is kept from going stale. This
ticket consumes that proxy and renders it; do not re-litigate it here. If that
ticket has not landed when design starts, design against its interface and say
so in the spec.

**The plan tier is not detectable from this repo.**
`src/coga/recurring_autofix.py:105` (`_CLAUDE_SUBSCRIPTION_TYPES`) is not a plan
registry: it is a coarse `pro|max|team|enterprise` allowlist inside
`_claude_subscription_fallback_env` (~L415–469), reached only after a `claude`
run has already failed with an auth/billing marker, read from `claude auth
status` and never persisted. It cannot distinguish Max 5x from Max 20x — the
"$200 plan" in the description is not derivable from it — and it describes the
local machine's login, not each teammate's plan. Treat the plan as an
operator-declared input.

Open design questions — answer these in the spec rather than assuming:

- **Delivery surface.** A scheduled Slack post modeled on
  `coga/recurring/digest/`, a CLI report command, or both?
- **Unit of report.** Per-person or per-repo? Per-person right-sizing is only
  reliably attainable for the operator running the job — see the attribution
  caveat below.

Prior art and pointers:

- `coga usage` reads token records from `coga/log.md`; `coga usage --json --by
  task --since/--until` is the accessor and `src/coga/usage.py:load_records` is
  importable from an edge `ticket.py`. The attached `coga/usage` context
  describes the primitive.
- `coga/recurring/digest/` is the closest model for a scheduled Slack report.
  Attach `coga/recurring` at design time if that shape is chosen — it's ~59 KiB,
  too heavy to carry by default. `coga/period-task` (~4 KiB) is the cheap one to
  attach if the deliverable is a recurring task.
- `coga/usage` is attached for `design`, which needs to understand the
  primitive, but roughly half of it is write-side detail (capture gating, the
  Claude/Codex parser seam, bounded activity extraction) that the read side
  never touches. Before bumping to `implement`, distil the facts that still
  matter into this section and drop the attachment, so later steps don't pay
  ~2.3k tokens per launch for parser-seam detail.

Two known gaps to caveat around, both **out of scope** here — fixing either is
its own ticket, so recommend a split rather than absorbing it:

- Usage records carry no `user` field. Attribution today is an approximate join
  through the record's `slug` to that ticket's `human:`/`owner:`; no schema
  change is needed or wanted for a first report. The join is lossier than it
  looks: `coga/log.md` deliberately outlives deleted and retired tasks, and
  bootstrap records are tagged `bootstrap/ticket` with `step: null` and have no
  ticket to join to. Measure the join hit rate before committing to per-person
  rows.
- Only Coga-launched sessions are recorded, and only for this repo, so totals
  understate real usage — the direction of error that biases toward over-eager
  downgrade advice. Deterministic recipe iterations (Dream workers, autoclose,
  digest, skill-update) record nothing at all, and ambiguous concurrent sessions
  yield `usage_status: unknown` with zero tokens. Print `unknown_sessions`
  (already carried on `Rollup`, `src/coga/usage.py:148`) beside any utilization
  figure rather than implying the number is complete.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
