---
title: Define the API-equivalent cost proxy and price table
status: in_progress
owner: nicktoper
agent: claude
contexts:
- coga/usage
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
step: 2 (evaluate-design)
launch_generation: pending:eb4458f5-206b-4247-a4db-2f16accf1522
---

## Description

Subscription plans have no cumulative token allowance — they are metered by
rate-limit windows — so "you are using a quarter of your $200 plan" has no
denominator today. Define one: convert recorded token usage into an
API-equivalent dollar figure, so a plan's price becomes the denominator and
"would the API bill have exceeded what I pay?" becomes answerable. Ship the
price table this needs, decide where it lives, and decide how it is kept from
silently going stale. `agent-usage-report` consumes what this ticket defines.

Sanity check against this repo's own log (578 records, 2026-07-16 → 2026-09-13,
priced with the rates confirmed below): **≈ $3,655 API-equivalent**, of which
`claude-opus-5` ≈ $1,792, `gpt-5.6-sol` ≈ $754, `claude-fable-5` ≈ $583,
`claude-opus-4-8` ≈ $300, `gpt-6-astra` ≈ $203. 63 sessions are
`usage_status: unknown` (zero tokens) and 13 are attributed to `<synthetic>`
(38.8M tokens, unpriceable). The figure is a floor, and the design below makes
that floor-ness explicit in every output instead of leaving it to the reader.

### Acceptance criteria

- [ ] `src/coga/resources/prices.toml` exists, is packaged (readable through
      `paths.read_packaged_resource`), and carries a top-level
      `vintage = "YYYY-MM-DD"` (the date the rates were confirmed), a
      `[sources]` table with one URL per provider, and one `[models."<id>"]`
      entry per model with `provider`, `input`, `cache_read`, `output`, and —
      for Anthropic models only — `cache_write` (all USD per million tokens).
      Keys are the exact model ids the CLIs report (`claude-opus-5`,
      `gpt-5.6-sol`); no fuzzy or prefix matching.
- [ ] `coga.usage.load_price_table() -> PriceTable` parses that file with
      `tomllib`, validates every entry (Decimal-parsable non-negative rates;
      `cache_write` required for `provider = "anthropic"`, forbidden for
      `provider = "openai"`), and raises `ValueError` on a malformed file.
- [ ] `coga.usage.price_record(record, table) -> Priced | None` is the
      single pricing primitive. It returns `None` (never `$0`) when
      `usage_status != "ok"`, when `record.model` is absent from the table,
      or when a category the table prices for that model is `None` on the
      record. Otherwise `Priced(usd: Decimal, model: str)` where
      `usd = Σ tokens_c × rate_c / 1_000_000` over the four categories, with a
      `None` category whose rate is absent (Codex `cache_creation_input_tokens`)
      contributing 0.
- [ ] `RollupRow` gains `usd: Decimal`, `unpriced_sessions: int`, and
      `unpriced_tokens: int`. `rollup()` accepts `price_table: PriceTable |
      None = None` (default: load the packaged table) and prices every record
      through `price_record` inside `_build_row`, so every grouping (`task`,
      `model`, `agent`, `step`, and `overall`) carries dollars plus the
      explicit unpriced remainder. `unknown_sessions` keeps its meaning and
      is *not* folded into `unpriced_sessions`.
- [ ] `Rollup` gains `price_vintage: str`, `price_stale: bool` (vintage older
      than `PRICE_TABLE_STALE_AFTER_DAYS = 90` relative to today, UTC), and
      `unpriced_models: dict[str, int]` (model id → sessions, with `None`
      rendered as `"(unknown)"`). `to_dict()` emits all three; `usd` is
      serialized as a string quantized to 4 decimal places, never a float.
- [ ] `coga usage` text output adds a `usd` column and prints the vintage on
      the `Overall:` line together with `unknown`, `unpriced`, and the
      unpriced-model list. When `price_stale` is true it prints one warning
      line to stderr and still exits 0. `--json` carries the same fields.
- [ ] `_parse_claude_session` no longer lets a trailing `<synthetic>`
      assistant line overwrite the session's real model: model attribution
      skips `<synthetic>`. Existing `<synthetic>` records are left as-is and
      land in `unpriced_models`.
- [ ] Every pricing input is documented for the operator: the table file
      header states the 1h cache-write choice, the gpt-5.5 base-tier choice,
      and that fast mode / `inference_geo` premiums are not represented.
- [ ] `coga/contexts/coga/usage/SKILL.md` is updated in the same PR: the
      "No dollar cost is computed" paragraph is replaced by a section that
      states the proxy's definition, its floor semantics, where the table
      lives, the staleness policy, and the update procedure. Re-check
      `tests/test_packaging.py` twins before editing (none exists today).
- [ ] Tests in `tests/test_usage.py`: packaged table loads and validates;
      malformed table raises; `price_record` on an ok Claude record, an ok
      Codex record (null cache-create priced as 0), an unknown-status record
      (`None`), an unpriced model (`None`), and a priced-category-`None`
      record (`None`); `rollup()` sums `usd` per group and populates
      `unpriced_*` and `unpriced_models`; stale detection flips at the
      boundary; `coga usage --json` emits `usd` as a string and the vintage;
      the `<synthetic>` attribution fix.
- [ ] `python -m pytest` passes; `coga usage` and `coga usage --json` run
      against this repo without error.

### Proposed shape

**1. The table — `src/coga/resources/prices.toml` (new).** Packaged data,
read via `read_packaged_resource("prices.toml")`; not under `templates/`, so
the twin test does not apply. Shape:

```toml
# API-equivalent list prices, USD per million tokens. Exact model ids as the
# CLIs report them. `vintage` is the date these rates were confirmed against
# the source URLs; bump it whenever a rate or row changes.
vintage = "2026-09-13"
stale_after_days = 90

[sources]
anthropic = "https://platform.claude.com/docs/en/about-claude/pricing"
openai = "https://developers.openai.com/api/docs/pricing"

# Anthropic `cache_write` is the 1-hour TTL rate (2x input), not the 5-minute
# rate (1.25x): Claude Code writes cache with the 1h TTL (measured locally:
# 70,171 assistant lines with ephemeral_1h_input_tokens > 0 vs 120 with 5m).
# Records do not carry the split, so one rate is chosen for all writes.
[models."claude-opus-5"]
provider = "anthropic"
input = "5"
cache_write = "10"
cache_read = "0.50"
output = "25"

# OpenAI has no cache-write charge, so `cache_write` is absent and a null
# cache_creation_input_tokens on a Codex record is the correct shape.
[models."gpt-5.6-sol"]
provider = "openai"
input = "4"
cache_read = "0.40"
output = "20"
```

Rates are TOML strings so they parse to `Decimal` without float drift. Seed
the full current non-retired list from both sources (Anthropic: fable-5-1,
fable-5, opus-5, opus-4-8, opus-4-7, opus-4-6, opus-4-5, sonnet-5,
sonnet-4-6, sonnet-4-5, haiku-4-5; OpenAI: gpt-6-astra, gpt-5.6-sol,
gpt-5.6-terra, gpt-5.5, gpt-5.3-codex) — the confirmed numbers are in
`## Context`.

**2. Loading and validation — `src/coga/usage.py`.**

```python
PRICE_TABLE_RESOURCE = "prices.toml"
PRICE_TABLE_STALE_AFTER_DAYS = 90
TOKENS_PER_MTOK = Decimal(1_000_000)

@dataclass(frozen=True)
class ModelPrice:
    model: str
    provider: str
    input: Decimal
    cache_write: Decimal | None   # None: provider has no cache-write charge
    cache_read: Decimal
    output: Decimal

@dataclass(frozen=True)
class PriceTable:
    vintage: str                  # "YYYY-MM-DD"
    stale_after_days: int
    sources: dict[str, str]
    models: dict[str, ModelPrice]
    def lookup(self, model: str | None) -> ModelPrice | None: ...
    def is_stale(self, today: date | None = None) -> bool: ...

def load_price_table(text: str | None = None) -> PriceTable:
    """Parse the packaged prices.toml (or `text`, for tests)."""
```

Validation is strict and raises `ValueError` with the offending key: every
rate must be a string that `Decimal` accepts and is `>= 0`; `provider` must be
`anthropic` or `openai`; `cache_write` presence must match the provider rule
above; `vintage` must parse as an ISO date. A broken table must fail
`coga usage` loudly (exit 2 through the existing `ValueError` handling in
`commands/usage.py`), never price silently.

**3. Pricing primitive.**

```python
@dataclass(frozen=True)
class Priced:
    usd: Decimal
    model: str

def price_record(record: UsageRecord, table: PriceTable) -> Priced | None:
```

Rules, in order: `usage_status != "ok"` → `None`; `table.lookup(record.model)`
is `None` → `None`; for each of the four categories, if the rate is present and
the record's token count is `None` → `None` (a priced category that did not
decompose is not partially priced); otherwise sum `tokens × rate /
TOKENS_PER_MTOK`, treating a `None` count under an absent rate as 0. This is
the seam `agent-usage-report` was told to design against; its `cost.py`
should import `price_record` (record-level) or read `RollupRow.usd` rather
than the provisional `price_rollup_row(model, row)` it sketched — see the
blackboard note for the owner.

**4. Rollup integration.** Extend `RollupRow` with `usd`, `unpriced_sessions`,
`unpriced_tokens`; extend `_build_row(key, records, table)` to call
`price_record` per record, summing `usd` for priced records and
`total_tokens` of the record into `unpriced_tokens` for `ok` records that
returned `None`. `rollup(..., price_table=None)` loads the packaged table
when not given. `Rollup` gains `price_vintage`, `price_stale`,
`unpriced_models` (computed once over the filtered records). Keep
`total_tokens` as-is: dollars are additive to the token view, not a
replacement.

**5. `coga usage` surface — `src/coga/commands/usage.py`.** Add the `usd`
column (`$1234.56`, 2dp in text; 4dp string in JSON), extend
`_format_overall` to
`Overall: sessions=… unknown=… unpriced=… usd=$… (floor; prices vintage 2026-09-13)`,
append `unpriced models: <synthetic>×13` when non-empty, and print
`warning: price table vintage 2026-09-13 is older than 90 days — refresh
src/coga/resources/prices.toml` to stderr when stale. No new flags.

**6. `<synthetic>` attribution fix.** In `_parse_claude_session`, replace
`model = _first_str(...) or model` with a form that ignores `"<synthetic>"`
so a trailing synthetic line does not claim the session. One helper,
one test.

**7. Context and docs.** Rewrite the "read surface" paragraph of
`coga/contexts/coga/usage/SKILL.md` and add a "Cost proxy" section covering:
definition (list-price API equivalent, per-category rates, 1h cache-write
choice), floor semantics (unknown-status and unpriced sessions are excluded
and counted, never $0), table location and update procedure (edit
`prices.toml`, bump `vintage`, cite the source URL in the commit), staleness
policy (vintage on every output, stale flag after 90 days, unknown ids
surface as `unpriced_models`), and known understatements (fast mode,
`inference_geo`, gpt-5.5 long-context tier). Update the `coga usage` entry in
`docs/reference.md` and the packaged `coga/cli` context's `coga usage`
section for the new columns.

Order of work: 1 → 2 → 3 (with tests) → 4 → 5 → 6 → 7.

### Out of scope

- The report, its cadence, roster, and Slack delivery — `agent-usage-report`.
- A `user` field on usage records — its own ticket.
- Capturing the 5m/1h cache-write split (`usage.cache_creation.ephemeral_*`
  in Claude transcripts) as new record fields. That is a schema-3 change; this
  ticket picks one documented rate instead.
- Operator-side price overrides (negotiated rates, a `[usage.prices]` section
  in `coga.toml`). Prices are third-party facts, not operator policy; if a
  need appears it gets its own ticket. See Open Questions.
- Automatic fetching of vendor pricing pages or any network access from
  `coga usage`. The table is edited by hand and committed.
- Batch, fast-mode, `inference_geo`, and long-context tier premiums —
  records cannot tell which applied; documented as understatements.
- Re-attributing existing `<synthetic>` records in `coga/log.md`. The log is
  append-only; they stay unpriced.
- Migrating `RollupRow.usd` consumers to a dollar-first default view. Tokens
  by task remains the default framing.

## Context

Codebase facts an implementer needs.

**Where things are.**

- `src/coga/usage.py` — `UsageRecord` (L65), `RollupRow` (L145),
  `Rollup` (L170), `load_records` (L329), `rollup` (L355),
  `_parse_claude_session` (L382; model attribution at L465),
  `_parse_codex_session` / `_parse_codex_rollout` (L527/L569; category
  mapping at L663–672: `input_tokens = max(0, input - cached)`,
  `cache_creation_input_tokens = None`, `cache_read_input_tokens = cached`),
  `_build_row` (L920), `_group_key` (L938).
- `src/coga/commands/usage.py` — Typer command, `_format_rollup`,
  `_format_overall`; `ValueError` from `rollup` already exits 2.
- `src/coga/paths.py::read_packaged_resource(name)` — reads a top-level
  `coga/resources/` file via `importlib.resources`, raising
  `PackagedResourceMissing` on `OSError`. Use it for `prices.toml`.
- `tests/test_packaging.py` — twins are derived only from
  `src/coga/resources/templates/coga/`; a top-level resource has no twin.
  `coga/contexts/coga/usage/SKILL.md` has no packaged counterpart today.
- `tests/test_usage.py` — 14 tests; `test_rollup_filters_and_groups_records`
  (L458) is the model for rollup tests; `test_usage_command_outputs_json`
  (L517) for the CLI.
- Consumer: `coga/tasks/agent-usage-report.md` (at `review-design`). Its
  `cost.py` seam sketch imports `coga.usage.price_rollup_row`; its evaluator
  (P2 #5) flagged that as unagreed and asked this ticket to settle it.

**Confirmed list prices (USD / MTok), 2026-09-13.**

Anthropic — https://platform.claude.com/docs/en/about-claude/pricing
(columns: input / 5m cache write / 1h cache write / cache read / output):

| model id | input | 5m write | 1h write | cache read | output |
|---|---|---|---|---|---|
| claude-fable-5-1 | 10 | 12.50 | 20 | 0.25 | 50 |
| claude-fable-5 | 10 | 12.50 | 20 | 1 | 50 |
| claude-opus-5 / -4-8 / -4-7 / -4-6 / -4-5 | 5 | 6.25 | 10 | 0.50 | 25 |
| claude-sonnet-5 | 2 | 2.50 | 4 | 0.20 | 10 |
| claude-sonnet-4-6 / -4-5 | 3 | 3.75 | 6 | 0.30 | 15 |
| claude-haiku-4-5 | 1 | 1.25 | 2 | 0.10 | 5 |

Cache read is 0.1× input on all models except Fable 5.1 (0.025×), so the
ticket's "≈10% / ≈125%" ratios are not uniform — the table stores absolute
per-category rates, not multipliers. Fast mode (Opus 5 / 4.8) is $10 / $50
and `inference_geo: "us"` is 1.1×; neither is visible in records.

OpenAI — https://developers.openai.com/api/docs/pricing (input / cached
input / output; no cache-write charge; reasoning tokens bill as output, which
matches the Codex parser folding `reasoning_output_tokens` into
`output_tokens`):

| model id | input | cached input | output |
|---|---|---|---|
| gpt-6-astra | 10 | 1 | 50 |
| gpt-5.6-sol | 4 | 0.40 | 20 |
| gpt-5.6-terra | 2 | 0.20 | 12 |
| gpt-5.5 (≤272K context tier) | 5 | 0.50 | 30 |
| gpt-5.3-codex | 1.75 | 0.175 | 14 |

`gpt-5.6-sol` is promotional pricing "at least through November 21, 2026" —
a concrete reason the vintage must be visible. `gpt-5.5` has a higher
>272K-context tier that records cannot distinguish; price at the base tier.

**Record survey (this repo's `coga/log.md`, 578 usage records).** Models:
`claude-opus-5` 209, `gpt-5.6-sol` 153, `claude-fable-5` 53,
`claude-opus-4-8` 48, `gpt-6-astra` 34, `<synthetic>` 13, `claude-fable-5-1`
3, `gpt-5.5` 2; `usage_status: unknown` 63 (model null, all tokens null).
`<synthetic>` is Claude Code's placeholder model on synthetic assistant
messages; 8 of the 13 carry zero tokens, 5 carry real sessions (e.g. 7.9M
cache-read tokens) because `_parse_claude_session` keeps the *last* model
seen. Model ids in records are exact API ids on both providers.

**Cache-write TTL.** Claude transcripts carry
`usage.cache_creation.{ephemeral_5m_input_tokens, ephemeral_1h_input_tokens}`;
the parser sums only the combined `cache_creation_input_tokens`. Measured
over this machine's `~/.claude/projects/*/*.jsonl`: 70,171 assistant lines
with a positive 1h count vs 120 with a positive 5m count. Pricing all writes
at the 1h rate moves this repo's total from ≈ $3,357 (5m) to ≈ $3,655 (1h),
about 9%.

**Microkernel placement.** The table and loader go in core because pricing
has two real consumers — `coga usage` (the single read accessor; consumers
are told not to re-parse records) and the `agent-usage-report` recurring
job — and because the table's contract (exact ids, four-rate shape, vintage)
is co-versioned with `RollupRow`. Rejected: an edge file under
`coga/recurring/usage-report/` (then `coga usage` cannot price and the
report re-implements the math); `coga.toml` (prices are vendor facts, not
operator policy; every repo would carry an independently stale copy, and
the packaged `coga.toml` twin is already intentionally divergent).

<!-- coga:blackboard -->

## Design findings (2026-09-13)

- Rates confirmed live on both vendor pricing pages; see `## Context`. The
  ticket's ratio hints (10% / 125%) are wrong in two ways: Fable 5.1 cache
  reads are 2.5%, and Claude Code's cache writes are 1h (200%), not 5m
  (125%). The table therefore stores absolute per-category dollar rates.
- Codex records are already disjoint across categories (`input` excludes
  `cached`), and OpenAI has no cache-write charge — so `cache_creation =
  None` on Codex is the *correct* pricing shape, not missing data. The
  honesty rule is at the table: `cache_write` is required for anthropic
  entries and forbidden for openai entries, and a `None` count under a
  priced rate makes the record unpriced rather than partially priced.
- Real-data floor for this repo: ≈ $3,655 over 2026-07-16 → 2026-09-13
  (script in the design session; reproducible from `coga/log.md` with the
  Context table). 63 unknown-status sessions and 13 `<synthetic>` sessions
  (38.8M tokens) are excluded and counted.
- `<synthetic>` mis-attribution is a parser bug (last-model-wins); fixing it
  is a one-line change in `_parse_claude_session` and is in scope because
  unknown-model handling is part of this contract.

## Decisions

- **Home: packaged `src/coga/resources/prices.toml` + loader/pricer in
  `src/coga/usage.py`.** Two real consumers (`coga usage`, the report); the
  microkernel argument is in `## Context`.
- **Pricing happens at the record level inside `rollup()`**, so every
  grouping carries `usd` and the unpriced remainder. The consumer's sketched
  `price_rollup_row(model, row)` is superseded: `agent-usage-report` should
  read `RollupRow.usd` / `Rollup.unpriced_models` (or call `price_record`
  on records). Its `cost.py` null-pricer fallback remains valid until this
  lands. Owner: please carry this into the `agent-usage-report` review-design
  step.
- **Staleness policy:** vintage stamped in the file and echoed on every
  `coga usage` output; `price_stale` after 90 days (stderr warning, exit 0,
  JSON flag); unknown model ids surface as `unpriced_models` with session
  counts and are never $0. Updating the table is a hand edit + vintage bump
  + source URL in the commit. No network access.
- **Anthropic cache writes priced at the 1h rate** (measured 70,171 vs 120
  lines). Documented in the file header and the context.
- `usd` is `Decimal`, serialized as a 4dp string in JSON.

## Open Questions

1. **1h vs 5m cache-write rate.** The design prices all Anthropic cache
   writes at the 1h rate (2× input) because Claude Code measurably uses the
   1h TTL. Alternative: the 5m rate as a deliberate lower bound consistent
   with the report's floor framing (≈ 9% lower). Confirm 1h, or say 5m.
2. **Operator override.** Should a repo be able to override or extend the
   packaged table (e.g. negotiated rates, a model coga has not shipped a
   row for yet) via a committed edge file? The design says no — a new model
   shows up as `unpriced_models` until the packaged table is bumped — but
   this team installs coga editable from this repo, so the friction is
   small. If yes, it is a separate ticket.
3. **Should `coga usage` default to hiding `usd` behind a flag** (e.g.
   `--cost`) to keep the default view token-first? The design adds the
   column unconditionally because the vintage/stale signal is only useful
   if it is seen.
