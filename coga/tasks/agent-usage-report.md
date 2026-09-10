---
slug: agent-usage-report
title: agent-usage-report
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
  - coga/usage
skills: []
workflow: code/design-then-implement
secrets: null
---

## Description

A recurring report that tells people where they stand with their AI usage, so
they can right-size their subscription. If someone on the $200 plan is only
using a quarter of it, the report should make that visible enough that
downgrading becomes an obvious call. Runs weekly or monthly — often enough to
act on, not so often it becomes noise.

## Context

Deliberately thin: this is the vision, not the design. The engineering path is
the `design` step's call — including the first question, which is that plan
utilization has **no defined denominator today**. Subscription plans are metered
by rate-limit windows, not a cumulative token allowance, so "a quarter of the
$200 plan" needs a proxy to be invented (API-equivalent cost via the price table
`coga/usage` defers, or something else). Deciding that is design work, not a
given.

Prior art and pointers:

- `coga usage` reads token records from `coga/log.md`; the attached `coga/usage`
  context describes that primitive and its deferred price table.
- `coga/recurring/digest/` is the closest model for a scheduled Slack report.
  Attach `coga/recurring` at design time if that shape is chosen — it's 54KB,
  too heavy to carry by default.
- `src/coga/recurring_autofix.py` (`_CLAUDE_SUBSCRIPTION_TYPES`, ~L105/L458) is
  the only place in the repo that knows which plan someone is on.

Two known gaps to caveat around, both **out of scope** here — fixing either is
its own ticket, so recommend a split rather than absorbing it:

- Usage records carry no `user` field. Attribution today is an approximate join
  through the record's `slug` to that ticket's `human:`/`owner:`; no schema
  change is needed or wanted for a first report.
- Only Coga-launched sessions are recorded, and only for this repo, so totals
  understate real usage — the direction of error that biases toward over-eager
  downgrade advice.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Evaluator review

Read cold, the ticket is close to launchable. Findings below.

**Verdict: launch after fixing 1–3.** Workflow fit is right; scope is one PR only if the split in (2) is taken.

**Must-fix**

1. **The `_CLAUDE_SUBSCRIPTION_TYPES` pointer is misleading.** It is not a plan registry. At `src/coga/recurring_autofix.py:105` it is an allowlist gate inside `_claude_subscription_fallback_env` (~L415-469), reachable only when a `claude` run has already failed with an auth/billing marker and an `ANTHROPIC_API_KEY` is set; it reads `claude auth status` and never persists the value. It knows only the coarse tier (`pro|max|team|enterprise`) — it cannot distinguish Max 5x from Max 20x, i.e. the ticket's own "$200 plan" example is not derivable from it. It also describes the local machine's login, not each teammate's plan. So the design must either invent a declared-plan config input or state the plan as an operator-supplied parameter. As written, an agent will follow this pointer and find nothing usable.

2. **The proxy reverses a documented decision, and a naive version is wrong.** `coga/usage` states outright: "No dollar cost is computed — the team runs on a subscription… a price table is a deferred follow-up." Adopting API-equivalent cost undoes that, so the same PR must update `coga/contexts/coga/usage/SKILL.md` and its packaged twin (CLAUDE.md rule). The direction is sound — "would the API bill exceed the plan price?" is the honest denominator absent a cumulative allowance — but it only works with **per-category weights**: cache-read is ~10% of input price, cache-create ~125%, and the same context says cache tokens dominate coga's prompts. A total-tokens denominator would be off by an order of magnitude. Also consider splitting "define the cost proxy + where the price table lives (core constants vs edge file, and its staleness policy)" from "the recurring report that renders it" — that is the ticket's own recommend-a-split posture applied to itself.

3. **Two unstated decisions block a cold start.** (a) Delivery surface: digest is cited as "the closest model for a scheduled Slack report", but the ticket never says whether Slack is required, one option, or the design's call. (b) Unit of report: per-person or per-repo? Given (1), per-person plan right-sizing is only attainable for the operator running the job. State both as design questions rather than leaving them implied.

**Assumptions to question**

- *No defined denominator today* — correct, and well stated.
- *Out-of-scope gap 1 (no `user` field)* — correctly scoped out, but the slug→`human:` join is lossier than implied: the log deliberately **outlives** deleted/retired tasks, and bootstrap records are tagged `bootstrap/ticket` with `step: null` and have no ticket to join to. The design should measure the join hit rate before committing to per-person rows.
- *Out-of-scope gap 2 (coverage)* — correctly scoped out and the direction-of-error reasoning is right, but understated: deterministic recipe iterations (Dream workers, autoclose, digest, skill-update) record **nothing**, and ambiguous concurrent sessions yield `usage_status: unknown` with zero tokens. Any utilization figure must print `unknown_sessions` beside it; `Rollup` already carries that field.

**Contexts**

`coga/usage` at 2319 tok / ~50% is over the 40% line and a real trim candidate. Roughly half of it — capture gating, the Claude/Codex parser seam, bounded activity extraction — is write-side detail a read-side consumer never touches. Keep it for `design` (that step must understand the primitive), but require the design step to **replace it with a distilled `## Context`** before bumping, so `implement` does not carry parser-seam detail. The facts worth copying: records are tagged JSONL lines in `coga/log.md`; the four token categories stay distinct; `coga usage --json --by task --since/--until` is the accessor; `src/coga/usage.py:load_records` is importable by an edge `ticket.py`. Missing and cheap: `coga/period-task` (4 KiB) if a recurring task is the deliverable. Deferring the 60 KiB `coga/recurring` is the right call. The microkernel rule needs no attachment — `src/coga/resources/prompt.md:94` already carries it in the base prompt.
