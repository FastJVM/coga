---
slug: agent-usage-report
title: agent-usage-report
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: codex
contexts: []
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
step: 2 (evaluate-design)
---

## Description

Nobody on this team can answer "am I paying for more AI subscription than I
use?" without guessing. Coga already records every launched agent session's
token usage into `coga/log.md` and reads it back with `coga usage`, but that
surface answers "which task burned tokens", not "should I downgrade". This
ticket ships the missing half: a recurring report that puts recorded usage
next to what the team actually pays, on a cadence short enough to act on
inside a billing cycle.

The honest version of this report is shaped by one measurement, taken from
this repo's own 509 records (2026-07-16 → 2026-09-10, 3.39B tokens): **only
38.1% of recorded tokens can be attributed to a named human**, and recorded
tokens themselves are a floor, not a total. That asymmetry decides the
design. Understated usage biases utilization *downward*, which makes a
downgrade look better justified than it is — so this report is built to make
the "keep your plan" conclusion trustworthy and the "downgrade" conclusion
explicitly provisional, rather than emitting a confident recommendation it
cannot support.

### Acceptance criteria

- [ ] A recurring task at `coga/recurring/usage-report/` fires weekly and
      posts exactly one Slack message summarising the period.
- [ ] The same renderer runs ad hoc and prints to stdout without posting or
      mutating state, so a human can preview any window:
      `python coga/recurring/usage-report/report.py --since 2026-08-01 --until 2026-09-01`.
- [ ] The report is computed from a **calendar window** (`--since`/`--until`),
      not a stored high-water mark, so re-running it for the same period
      produces the same output and a missed week is recoverable by re-running
      with explicit dates. The recurring task therefore declares no
      `state_keys:` and writes no cursor to its parent blackboard.
- [ ] Plan cost is read from an operator-declared, git-tracked
      `coga/recurring/usage-report/plans.toml`. Nothing tries to detect the
      plan tier from the machine.
- [ ] `plans.toml` supports `aliases` per person, and the report folds them
      into one row. (Required, not cosmetic: this repo's records already carry
      `nicktoper` and `nick` as two identities for the same human, splitting
      1.02B and 264M tokens.)
- [ ] The headline is **repo-total**, not per-person. A per-person section
      appears below it, labelled with the share of period tokens it actually
      covers, and never carries the plan verdict.
- [ ] Every utilization figure is rendered as a floor ("at least N%") and is
      accompanied on the same message by: the count of `usage_status:
      unknown` sessions in the window (from `Rollup.unknown_sessions`), and
      the share of period tokens that did not join to a declared person.
- [ ] The verdict logic respects the direction of error:
      - recorded API-equivalent value **≥** total declared plan cost → a
        confident "plan is paying for itself" (understatement cannot break
        this conclusion);
      - recorded value **well below** plan cost → "worth reviewing", naming
        the coverage gaps that could explain it. The report must not print an
        unqualified instruction to downgrade.
- [ ] Pricing is consumed through a single narrow seam (see Proposed shape),
      not reimplemented here. When the cost proxy has not landed, the report
      still runs and still posts: it prints the token totals and per-person
      split, and replaces every dollar and utilization figure with one line
      saying the cost proxy is unavailable. Shipping is not gated on the
      dependency.
- [ ] Models absent from the price table (this repo's records already contain
      `<synthetic>` and a `(unknown)` model bucket) are counted and reported
      as unpriced tokens rather than silently priced at zero.
- [ ] Tests under `tests/` cover: alias folding, the unpriced-model path, the
      cost-proxy-absent fallback, the floor framing of utilization, and an
      empty window.
- [ ] `python -m pytest` and `coga validate --json` pass.

### Proposed shape

**Everything lands at the edge.** No new `src/coga/` module, no new Typer
command, and no new `runner.RECIPES` entry: the microkernel rule in
`CLAUDE.md` puts single-consumer deterministic work beside its ticket, and
this report's only consumer is its own recurring task. It imports only
shared core infra (`coga.config`, `coga.usage`, `coga.notification`). Note
this is the first recurring task whose `ticket.py` does *not* delegate to a
core recipe — the existing four all predate the rule.

New files:

1. **`coga/recurring/usage-report/report.py`** — the whole implementation,
   and the only file with real logic. Structure:
   - `load_plans(path) -> Roster` — parses `plans.toml` via `tomllib`.
     `Roster` maps every alias to a canonical `Person(name, plan_label,
     monthly_usd)`. Unknown/absent file → empty roster, which degrades the
     per-person section rather than raising.
   - `attribute(records, roster) -> tuple[dict[Person, list[UsageRecord]], list[UsageRecord]]`
     — joins each record's `slug` to its ticket's `human:`/`owner:` and folds
     through the alias map; returns the attributed buckets plus the
     unattributed remainder. Resolve the slug by trying
     `coga/tasks/<slug>.md`, then `coga/tasks/<slug>/ticket.md`; a slug with
     no live ticket (deleted, retired, or a `bootstrap/*` ref) is
     unattributed by construction, not an error.
   - `build_report(records, roster, since, until) -> Report` — pure, no IO.
     Calls `coga.usage.rollup(subset, by="model", since=..., until=...)` for
     the repo total and once per person, because per-model category splits
     are exactly what pricing needs. Prices each model row through the seam
     below.
   - `render(report) -> str` — the Slack/stdout text.
   - `__main__` with `--since`/`--until`/`--plans`/`--json`, defaulting to the
     last completed ISO week. Printing only; it must not post or write.

2. **`coga/recurring/usage-report/cost.py`** — the dependency seam, and the
   reason this ticket is not blocked on
   `define-the-api-equivalent-cost-proxy-and-price-tab` (still `status:
   draft`). One function:

   ```python
   def price(model: str | None, row: RollupRow) -> Priced | None
   ```

   returning `Priced(usd: Decimal, model: str)` for a known model and `None`
   for an unknown or absent one. The module tries the real implementation
   first and falls back to a null pricer that returns `None` for everything:

   ```python
   try:
       from coga.usage import price_rollup_row as _price   # provided by the proxy ticket
   except ImportError:
       _price = None
   ```

   `build_report` reads `report.priced is False` when `_price is None` and
   suppresses every dollar figure. When the proxy lands, deleting the
   fallback branch is the entire integration. **Do not invent a price table
   here** — an unpriced report is the correct interim output, and a
   second table would be exactly the staleness problem that ticket exists to
   solve.

3. **`coga/recurring/usage-report/plans.toml`** — operator-declared, one
   entry per person. Prices are declared per person rather than through a
   plan-tier registry on purpose: a tier table is a second thing that goes
   stale, and the tier name carries no information the price doesn't.

   ```toml
   [[person]]
   name = "nicktoper"
   aliases = ["nick"]
   plan = "max-20x"        # label only, never used for arithmetic
   monthly_usd = 200
   ```

4. **`coga/recurring/usage-report/ticket.md`** — `schedule: "0 8 * * 1"`
   (Monday 08:00, after the 07:00 Monday branch sweep), `workflow:
   usage-report/post`, no `state_keys:`. Weekly, not monthly: this repo's
   own history runs 350–750M tokens/week, so a week is already a strong
   signal, and a monthly cadence can only tell you about a billing cycle
   that has already been paid.

5. **`coga/recurring/usage-report/ticket.py`** — thin, matching the existing
   pattern: build the report, `coga.notification.post(cfg, text,
   fatal=False)`, then complete the step by subprocessing `python -m
   coga.cli bump $COGA_TASK_SLUG`. `fatal=False` because the report is an
   announcement, not a state mutation.

6. **`coga/workflows/usage-report/post.md`** and
   **`coga/skills/coga/usage-report/post/SKILL.md`** — the one-step
   script-mode lifecycle, mirroring `coga/workflows/branch-sweep/sweep.md`.

Order of work: `plans.toml` schema and `load_plans` → `attribute` (test it
against the real `coga/log.md`, whose join rate is the design's load-bearing
number) → `cost.py` seam → `build_report`/`render` → the recurring task,
workflow, and skill → tests.

Message shape:

```
Agent usage — week of 2026-09-01 (Mon–Sun)

Recorded: 496.0M tokens across 61 sessions
API-equivalent value: at least $X            [omitted until the cost proxy lands]
Declared plans: $200/mo (1 person)
→ Recorded usage covers at least N% of what the team pays.

Attributed (38% of period tokens):
  nicktoper (max-20x, $200/mo)   1.02B tokens
Unattributed: 62% — deleted/retired tickets, bootstrap sessions

Coverage: 7 of 61 sessions have unknown token counts. Only Coga-launched
sessions in this repo are recorded, so these totals are a floor.
```

### Out of scope

- **Adding a `user` field to usage records.** The approximate slug→`human:`
  join is what this report uses. Fixing attribution at the schema level is
  its own ticket, and the measured 38% join rate is the evidence for filing
  it — but not for absorbing it here.
- **Closing the coverage gaps** (unrecorded non-Coga sessions, deterministic
  recipe iterations that record nothing, ambiguous concurrent sessions
  yielding `usage_status: unknown`). This report caveats them; it does not
  fix them. Also its own ticket.
- **The price table and the cost proxy itself** —
  `define-the-api-equivalent-cost-proxy-and-price-tab`. This ticket consumes
  the seam and must not re-litigate or duplicate it.
- **Packaging the recurring task as a shipped template** under
  `src/coga/resources/templates/coga/recurring/`. Live-only for a first cut;
  a packaged twin becomes byte-sync-enforced by `tests/test_packaging.py`,
  and the plan roster is operator-specific. Revisit once the shape has run
  for a few weeks.
- **Per-model or per-agent cost breakdowns, trend charts, and history
  beyond the reported window.** `coga usage --by model` already answers the
  first for anyone who asks.
- **Any change to `coga usage`, `src/coga/usage.py`, or the record schema.**

## Context

Codebase facts the implementer needs.

**The read surface.** `coga.usage.load_records(cfg) -> list[UsageRecord]`
parses `coga/log.md`, skipping every line that is not a usage record.
`coga.usage.rollup(records, *, by, since, until, task) -> Rollup` filters and
groups; `by` accepts `task | model | agent | step | None`. `Rollup` carries
`.overall` and `.groups`, each a `RollupRow` with `sessions`,
`unknown_sessions`, the four token fields, and a `.total_tokens` property.
Both take a plain `records` list, so pre-partitioning records by person and
calling `rollup(subset, by="model")` needs no new core API. `since`/`until`
accept an ISO timestamp or a `YYYY-MM-DD` date. `coga usage --json` is the
CLI equivalent (`src/coga/commands/usage.py`).

**Record fields this report reads:** `ts` (session end, what the date filters
use), `slug`, `model`, `agent`, `provider`, the four token categories
(`input_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens`,
`output_tokens`), and `usage_status` (`ok | unknown`). Keep the four
categories distinct — coga composes large cached layers, cache tokens
dominate, and per-category rates differ by more than an order of magnitude.
Schema-1 records still parse; their activity fields are absent and their
token values roll up unchanged. `_group_key` buckets a null `model` as the
string `"(unknown)"`.

**Measured on this repo's `coga/log.md` (509 records, 2026-07-16 →
2026-09-10, 3.39B tokens) — the numbers the design rests on:**

- Records joining to a `human:`/`owner:`: 142/509 = **27.9%**; by tokens,
  1.29B/3.39B = **38.1%**.
- Unjoinable tokens split: `bootstrap/*` refs with no ticket 25.5%,
  deleted/retired tickets 36.4%.
- `usage_status: unknown`: 60/509 = **11.8%**, carrying 0 tokens.
- Identities present: `nicktoper` (1.02B), `nick` (264M) — **the same human**
  — and `zach` (11M). Alias folding is required for a correct per-person row.
- Providers: anthropic 319, openai 190. Models: `claude-opus-5` 162,
  `gpt-5.6-sol` 153, null 60, `claude-fable-5` 53, `claude-opus-4-8` 48,
  `gpt-6-astra` 15, **`<synthetic>` 13**, `claude-fable-5-1` 3. The
  `<synthetic>` and null buckets are why unpriced-model handling is an
  acceptance criterion.
- Weekly totals range 350–750M tokens — the basis for the weekly cadence.

**Plan tier is not detectable.** `_CLAUDE_SUBSCRIPTION_TYPES`
(`src/coga/recurring_autofix.py:105`) is a coarse `pro|max|team|enterprise`
allowlist inside `_claude_subscription_fallback_env` (~L415–469), reached
only after a `claude` run has already failed with an auth/billing marker,
read from `claude auth status` and never persisted. It cannot distinguish
Max 5x from Max 20x and describes the local machine's login, not each
teammate's plan. Treat the plan as an operator-declared input.

**Recurring-task anatomy** (model on `coga/recurring/branch-sweep/`, the
smallest example): a directory under `coga/recurring/<name>/` holding
`ticket.md` (with `schedule:` cron, `schedule_comment:`, `title:`,
`workflow:`), the reserved sibling `ticket.py` that `coga launch`
subprocesses directly with no agent and no composed prompt, plus a workflow
at `coga/workflows/<name>/<step>.md` and a skill at
`coga/skills/coga/<name>/<step>/SKILL.md`. Existing `ticket.py` files end by
subprocessing `python -m coga.cli bump $COGA_TASK_SLUG` — calling the Typer
function in-process would pass `OptionInfo` sentinels instead of real
defaults. Cross-run state, when a task needs it, goes in the *parent*
template's blackboard and is declared in `state_keys:`; this report is
window-based and needs none.

**Notifications.** `coga.notification.post(cfg, message, *, important=False,
fatal=True, ...)`. Use `fatal=False`: a delivery miss must not fail the run,
and this posts an announcement rather than announcing a disk mutation.
`important=True` is reserved for posts needing human action — a usage report
is not one. `coga/recurring/digest/` is the closest prior art for a
scheduled Slack post, but note the digest is spool-and-watermark driven,
which this report deliberately is not.

**Microkernel constraint** (`CLAUDE.md`): `src/coga/` holds only shared infra
with ≥2 real consumers, or a reviewed command contract. A single-consumer
helper lives beside its ticket and imports only shared core infra. Backing a
CLI spelling is not by itself a pass into core. This ticket adds nothing to
`src/coga/`.

**Dependency status.** `define-the-api-equivalent-cost-proxy-and-price-tab`
is `status: draft` — not landed. Its ticket states the constraints the seam
must respect: per-category weights are mandatory (cache-read ≈10% of input,
cache-create ≈125%), Codex records leave cache-create null and fold
reasoning into output, `usage_status: unknown` records must not be priced as
$0 silently, and unknown-model handling is part of its contract. Design to
the seam; do not build a price table here.

<!-- coga:blackboard -->

## Design step — what was decided and why

Spec written into `## Description` / `## Context`. The two questions the
ticket left open are answered there; the reasoning is here.

**Delivery surface → both, one implementation.** `report.py` holds the whole
renderer with a `__main__` for ad hoc preview; `ticket.py` is the scheduled
half that posts and bumps. A CLI-only report can't nag, and a Slack-only one
can't be checked against a custom window when someone disputes it. Two
entrypoints over one pure `build_report`/`render` pair costs almost nothing.
No new core command — the microkernel rule puts a single-consumer helper
beside its ticket. This is the first recurring `ticket.py` that doesn't
delegate to a `runner.RECIPES` function; the existing four predate the rule,
so that's compliance, not divergence.

**Unit of report → repo-total headline, per-person as a labelled subset.**
This was decided by measurement, not preference. I ran the join the ticket
asked me to measure against the live `coga/log.md` (509 records, 3.39B
tokens): **27.9% of records and 38.1% of tokens** reach a `human:`/`owner:`.
The 62% that doesn't is structural, not a bug to fix — 25.5% is
`bootstrap/*` refs that have no ticket by design, and 36.4% is tickets that
were deleted or retired while the log deliberately outlived them. A
per-person headline built on 38% coverage would be a number that looks
precise and is wrong, and the error points toward advising a downgrade.

**Alias folding is required, not nice-to-have.** The same measurement turned
up `nicktoper` (1.02B tokens) and `nick` (264M) as two identities for one
human. Without folding, the largest user's row understates by 20%.

**The direction-of-error asymmetry is the report's most useful idea.**
Recorded tokens are a floor (non-Coga sessions, other repos, and
deterministic recipe iterations record nothing; 11.8% of sessions are
`usage_status: unknown` with zero tokens). A floor that already exceeds the
plan price proves the plan pays for itself. A floor below the plan price
proves nothing. So the report is allowed to say "keep" confidently and is
forbidden from saying "downgrade" — only "worth reviewing", with the
coverage gaps named. This inverts the ticket's framing ("downgrading becomes
an obvious call") and the inversion is deliberate: the data cannot support
an obvious downgrade call, and pretending otherwise is how you cancel a plan
you needed.

**Not blocked on the cost proxy.** `define-the-api-equivalent-cost-proxy-and-price-tab`
is still `status: draft`, so per the ticket's instruction the spec designs
against its interface: a one-function `cost.py` seam that falls back to a
null pricer, letting the report ship and post token totals with dollar
figures suppressed. When the proxy lands, deleting the fallback branch is
the whole integration. Explicitly forbade building an interim price table —
that would duplicate the exact staleness problem the other ticket exists to
solve.

**Window-based, not watermark-based.** Unlike `digest`, this report is a pure
function of a calendar window, so it declares no `state_keys:`, writes no
cursor, and is idempotent — a missed week is recovered by re-running with
explicit dates. Worth noting because the digest is the prior art an
implementer would otherwise copy wholesale, and copying its spool machinery
here would add state for nothing.

**Not split.** The honest shape is ~4 new small files plus a workflow, a
skill, and tests — one PR. Both known gaps (no `user` field; unrecorded
sessions) are pushed out as separate tickets rather than absorbed, per the
ticket's own instruction.

**Attachment dropped.** `contexts:` is now `[]`. The read-side facts from
`coga/usage` are distilled into `## Context`; the write-side half (capture
gating, Claude/Codex parser seam, bounded activity extraction) is not
something the report touches, so later steps no longer pay ~2.3k tokens per
launch for it.

## Open Questions

1. **Should the per-person section appear at all at 38% coverage?** The spec
   keeps it, labelled with its coverage share and excluded from the verdict,
   because it is the only view that speaks to the per-person right-sizing
   question the ticket actually asks. The alternative is repo-total only
   until a `user` field exists. Owner's call — this is a product judgement
   about whether a labelled-partial number is more useful than no number.
2. **Who is on the roster, and at what price?** `plans.toml` needs real
   entries to be worth posting. Records show `nicktoper`/`nick` and `zach`;
   whether `zach` (11M tokens, 0.3%) is a current teammate with a paid plan
   or an artifact of past work is not derivable from the repo.
3. **Where does it post?** The spec sends it to the default channel via
   `notification.post(..., fatal=False)`, not `important=True`. If the
   report is meant to be seen by the person who pays rather than the whole
   team, that's a different destination and worth saying now.
4. **Is Monday 08:00 right?** Chosen to land after the 07:00 Monday branch
   sweep and before the 09:00 daily digest, so a Monday doesn't open with
   three separate Coga posts competing for attention. Easy to move.
