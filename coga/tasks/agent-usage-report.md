---
title: agent-usage-report
status: done
owner: nicktoper
agent: claude
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
---

## Description

Post one Slack message every Monday saying how many tokens this repo's
Coga-launched agent sessions consumed last week. Coga already records every
launched session's usage into `coga/log.md` and reads it back with
`coga usage`, but nobody looks at it unless they ask. A weekly push of the
number is the whole feature: it makes the consumption visible on a cadence
short enough to notice a change, and gives a fixed reference point when the
cost proxy lands and a dollar line can be added.

This report does **not** compare usage to plan cost, attribute tokens to
people, or recommend anything. The owner reviewed and cut that design on
2026-09-20 (see `## Superseded designs` on the blackboard): the team is one
person on one subscription, so the comparison machinery had no reader, and
it was where every evaluator finding lived.

### Acceptance criteria

- [ ] A recurring task at `coga/recurring/usage-report/` fires weekly
      (`schedule: "0 8 * * 1"`, Monday 08:00, between the 07:00 branch sweep
      and the 09:00 digest) and posts exactly one Slack message for the
      previous completed ISO week, to the **important** route
      (`notification.post(cfg, text, important=True, fatal=False)`). "One
      message" means the report payload; the closing bump's ordinary done
      outcome is separate and untouched.
- [ ] The same renderer runs ad hoc and prints the identical text to stdout
      without posting or writing anything:
      `python coga/recurring/usage-report/report.py --since 2026-08-31 --until 2026-09-07`.
- [ ] The window is a **half-open calendar window `[since, until)` in UTC**,
      taken from `--since`/`--until` (`YYYY-MM-DD`), defaulting to the last
      completed ISO week (previous Monday 00:00 → this Monday 00:00 UTC).
      Given the same `coga/log.md`, re-running for the same window produces
      the same text, so a missed week is recovered by re-running with
      explicit dates. The recurring task declares no `state_keys:` and writes
      no cursor.
- [ ] The message carries: total tokens and session count, the four token
      categories, a per-model split (the `(unknown)` bucket and `<synthetic>`
      appear as their own rows, never dropped), and the count of
      `usage_status: unknown` sessions, stated as a floor.
- [ ] The materialized period task works: `coga launch` copies only
      `ticket.py` into `coga/tasks/recurring/usage-report/`, so `ticket.py`
      must find `report.py` through `$COGA_COGA_OS_ROOT`, not a sibling
      import. A test materializes the period task and runs the shim end to
      end with posting stubbed.
- [ ] Tests under `tests/` also cover: both window boundaries (a record at
      `until` 00:00 is excluded, one at `since` 00:00 included), the
      last-completed-week default, an empty window (still posts, says so),
      and the `(unknown)` model row.
- [ ] `python -m pytest` and `coga validate --json` pass. Baseline: validate
      currently exits 1 on four pre-existing `unsynthesized-draft-blackboard`
      errors under `v2/*` that are outside this ticket; do not expand scope to
      fix them, just do not add to them.

### Proposed shape

Everything lands at the edge: no new `src/coga/` module, no Typer command,
no `runner.RECIPES` entry. The microkernel rule puts single-consumer
deterministic work beside its ticket, and this report's only consumer is
its own recurring task. It imports only shared core infra (`coga.config`,
`coga.usage`, `coga.notification`). This is the first recurring `ticket.py`
that does not delegate to a core recipe; the existing recipe-backed shims
predate the rule.

1. **`coga/recurring/usage-report/report.py`** — the implementation.
   - `default_window(today: date) -> tuple[date, date]` — last completed ISO
     week. Pure; tested.
   - `build_report(records, since: date, until: date) -> Report` — pure, no
     IO. Calls `coga.usage.rollup(records, by="model", since=..., until=...)`
     once. Because `rollup`'s `until` is *inclusive* (`_record_matches` keeps
     `ts == until`, and a date-only `until` expands to end of that day), pass
     tz-aware `datetime`s: `since` at 00:00 UTC and `until` at 00:00 UTC minus
     one microsecond, which yields the half-open window without touching
     core.
   - `render(report) -> str` — the Slack/stdout text.
   - `__main__` with `--since`/`--until`/`--json`: `load_config()`,
     `load_records(cfg)`, build, print. Never posts or writes.
2. **`coga/recurring/usage-report/ticket.py`** — thin. Resolves
   `Path(os.environ["COGA_COGA_OS_ROOT"]) / "recurring/usage-report"`,
   inserts it on `sys.path`, imports `report`, builds for the default window,
   `notification.post(cfg, text, important=True, fatal=False)`, then completes
   the step by subprocessing `python -m coga.cli bump $COGA_TASK_SLUG`
   (calling the Typer function in-process would pass `OptionInfo` sentinels).
   `fatal=False` is deliberate: this is one post attempt per run, and a
   delivery miss must not leave the period task `in_progress`. Manual repost
   needs no new code:
   `coga slack --task <slug> --message "$(python coga/recurring/usage-report/report.py --since … --until …)"`.
3. **`coga/recurring/usage-report/ticket.md`** — `schedule: "0 8 * * 1"`,
   `schedule_comment:`, `title:`, `workflow: usage-report/post`, no
   `state_keys:`.
4. **`coga/workflows/usage-report/post.md`** and
   **`coga/skills/coga/usage-report/post/SKILL.md`** — the one-step
   script-mode lifecycle, mirroring `coga/workflows/branch-sweep/sweep.md`
   and `coga/skills/coga/branch-sweep/sweep/SKILL.md`.

Message shape (one consistent week; 2026-08-31 is a Monday):

```
Agent usage — week of 2026-08-31 (Mon–Sun)
496.0M tokens across 61 sessions (7 sessions have unknown counts, so this is a floor)
  input 12.3M · cache write 88.1M · cache read 380.2M · output 15.4M
  claude-opus-5   312.1M
  gpt-5.6-sol     140.2M
  claude-fable-5   43.7M
  (unknown)           0
```

Order of work: `default_window` + `build_report`/`render` with tests →
`ticket.py` + template `ticket.md` + workflow + skill → the materialized-shim
test.

### Out of scope

- **Dollar figures, utilization, and any plan comparison.** When
  `define-the-api-equivalent-cost-proxy-and-price-tab` lands, add one
  API-equivalent-value line to `render`; that is a follow-up, not this ticket.
  Do not build an interim price table here.
- **Per-person attribution and alias folding.** Records carry no `user`
  field and the slug→`owner:` join reaches only ~38% of tokens; with a
  one-person team there is no reader for it.
- **Closing the coverage gaps** (unrecorded non-Coga sessions, deterministic
  recipe iterations that record nothing, `usage_status: unknown` sessions).
  The report caveats them; fixing them is its own ticket.
- **Packaging the recurring task as a shipped template** under
  `src/coga/resources/templates/coga/recurring/`. Live-only for a first cut;
  a packaged twin becomes byte-sync-enforced by `tests/test_packaging.py`.
- **Any change to `coga usage`, `src/coga/usage.py`, or the record schema.**

## Context

**The read surface.** `coga.usage.load_records(cfg) -> list[UsageRecord]`
parses `coga/log.md`, skipping every line that is not a usage record.
`coga.usage.rollup(records, *, by, since, until, task) -> Rollup` filters and
groups; `by` accepts `task | model | agent | step | None`. `Rollup` carries
`.overall` and `.groups`, each a `RollupRow` with `key`, `sessions`,
`unknown_sessions`, the four token fields, and a `.total_tokens` property.
The unknown-session count for the whole window is
`Rollup.overall.unknown_sessions`. `since`/`until` accept an ISO timestamp,
a `YYYY-MM-DD` date, or a `datetime`; `_parse_filter_ts` treats a date-only
`until` as end of that day and `_record_matches` keeps a record whose `ts`
equals `until` — the reason the half-open window is built from datetimes
rather than dates. `_group_key` buckets a null `model` as the string
`"(unknown)"`. `coga usage --json --by model --since … --until …` is the CLI
equivalent (`src/coga/commands/usage.py`) and a quick way to cross-check
the renderer by hand.

**Record fields this report reads:** `ts` (session end, what the window
filters on), `model`, and the four token categories (`input_tokens`,
`cache_creation_input_tokens`, `cache_read_input_tokens`, `output_tokens`),
plus `usage_status` (`ok | unknown`). Keep the four categories distinct in
the message: coga composes large cached layers, cache tokens dominate, and
the future dollar line prices them at rates that differ by more than an
order of magnitude. Schema-1 records still parse and roll up unchanged.

**Measured on this repo's `coga/log.md`** (510 records, 2026-07-16 →
2026-09-10, 3.40B tokens): weekly totals run 350–750M tokens; 60 sessions
(11.8%) are `usage_status: unknown` carrying 0 tokens; models include
`claude-opus-5`, `gpt-5.6-sol`, `claude-fable-5`, `claude-opus-4-8`,
`gpt-6-astra`, `claude-fable-5-1`, plus 13 `<synthetic>` records and 60
null-model records — which is why the model split must show every bucket.

**Recurring-task anatomy** (model on `coga/recurring/branch-sweep/`): a
directory under `coga/recurring/<name>/` holding `ticket.md` (`schedule:`,
`schedule_comment:`, `title:`, `workflow:`), the reserved sibling
`ticket.py` that `coga launch` subprocesses directly with no agent and no
composed prompt, plus a workflow at `coga/workflows/<name>/<step>.md` and a
skill at `coga/skills/coga/<name>/<step>/SKILL.md`. **Materialization copies
only `ticket.py`** into the period task
(`recurring._create_at_slug`, `shutil.copyfile(entry, out_ref.task_dir /
SCRIPT_ENTRY_POINT)`; asserted by
`tests/test_recurring_shims.py::test_period_task_runs_its_shim_headlessly_and_closes_its_own_step`),
so every other file stays at the template and the shim reaches them through
`COGA_COGA_OS_ROOT`, which `task_env.build_task_env` exports as
`cfg.repo_root` — the active checkout's `coga/` directory itself, not the
host repository (`task_env.host_repo_root` is what strips the trailing
`coga`; `dream_cleanup_orphan_markers.coga_os_root` reads the variable the
same way). So the template path is `$COGA_COGA_OS_ROOT/recurring/usage-report`.
`tests/test_recurring_shims.py` is the model for the materialized-shim test.

**Notifications.** `coga.notification.post(cfg, message, *, important=False,
fatal=True, ...)`. `important=True` routes to the channel's alert
destination (the coga-important webhook) — the owner chose that destination
for this report. `fatal=False` returns normally on a delivery or
configuration miss (already reported on stderr and in `log.md`) so the shim
still bumps.

**Microkernel constraint** (`CLAUDE.md`): `src/coga/` holds only shared
infra with ≥2 real consumers or a reviewed command contract. This ticket
adds nothing to `src/coga/`.

<!-- coga:blackboard -->

## Design notes for implement

- Scope was cut at the owner gate on 2026-09-20 to a token-count-only weekly
  post; every open question and evaluator finding from the first design was
  either resolved by the cut or folded into the body above (half-open UTC
  window, `COGA_COGA_OS_ROOT` lookup from the copied shim, one post attempt
  per run with a documented `coga slack` repost, `important=True` route).
- Nothing on this ticket is blocked on
  `define-the-api-equivalent-cost-proxy-and-price-tab`.

## Dev

pr: https://github.com/FastJVM/coga/pull/854
branch: usage-report
worktree: /home/n/Code/codex/coga-usage-report
Layout: separate feature checkout (the primary checkout sits on
`quiet-first-run`, so `## Dev` and `coga bump` live here). The worktree
carries a gitignored `.venv/` (`uv venv --python 3.12` + `pip install -e
".[test]"`; the default `python3` here is 3.9.12, below the 3.11 floor) and a
0600 copy of `coga/coga.local.toml` seeded for `coga validate`; remove both
when the checkout is retired.

## Implement — 2026-09-21

Commit `7d1a7241b` on `usage-report`, rebased on `origin/main` (`ec23c317b`,
nothing new came in). Files, all at the edge, nothing in `src/coga/`:

- `coga/recurring/usage-report/report.py` — `default_window`, `build_report`
  (one `rollup(by="model")` over tz-aware `[since 00:00, until 00:00 − 1µs]`),
  `render`, `format_tokens`, and `main(argv)` with `--since/--until/--json`.
  `main` is a function so the CLI path is tested in-process.
- `coga/recurring/usage-report/ticket.py` — `sys.path` insert of
  `$COGA_COGA_OS_ROOT/recurring/usage-report`, `import report`, one
  `post(cfg, text, important=True, fatal=False)`, `coga bump` by subprocess.
- `coga/recurring/usage-report/ticket.md` (`schedule: "0 8 * * 1"`, no
  `state_keys:`), `coga/workflows/usage-report/post.md`,
  `coga/skills/coga/usage-report/post/SKILL.md` — mirror `branch-sweep`.
- `tests/test_usage_report.py` — 14 tests: default window (Mon/Wed/Sun), both
  half-open boundaries, inverted window, golden render with `(unknown)` and
  `<synthetic>` rows and the floor caveat, no-caveat case, non-week label,
  empty window, `main` (stdout only, `log.md` bytes unchanged, `--json`, exit
  2 on inverted window), an AST contract for `ticket.py` (imports, the single
  `post` call's kwargs, bump argv), and the end-to-end materialized period
  task launched from a seeded `example/` copy with `capfd` reading the
  subprocess's stderr.

Decisions:

- **Stubbed posting = no channel selected.** The shim runs in a subprocess, so
  an in-process `requests.post` monkeypatch cannot reach it. The seeded example
  has `channels = []`, so `notification.post` echoes
  `no channels configured: <text>` to stderr; the test asserts the exact
  rendered text appears once there and the ticket closes `done`. The
  `important=True`/`fatal=False` route is pinned structurally by the AST test
  instead. Rejected: a loopback HTTP server in the test (no precedent in the
  suite).
- **Render details** not fixed by the ticket: the floor parenthetical is
  omitted when zero sessions are unknown; a non-Mon→Mon window is labelled
  `<since> to <until> (UTC, end exclusive)`; model rows sort by total desc then
  key; token counts format as `B`/`M`/`k`/plain with the ticket's `496.0M`
  style; an empty window renders the header plus
  `No Coga-launched sessions recorded in this window.`
- `--since`/`--until` each default independently to their end of the last
  completed week; `until <= since` exits 2 via `parser.error`.
- The live-template test reads `coga/recurring/usage-report/` directly, unlike
  `test_recurring_shims.py` which reads the packaged tree — the template is
  live-only by the ticket's out-of-scope list, so the live copy is the only one.
- Period creation resolves the step's skill (`create_named` failed with
  "no skill file exists" before the skill was copied into the seeded repo), so
  the end-to-end test copies the skill alongside the workflow.

Verification: `.venv/bin/python -m pytest` → 2671 passed (one run hit
`test_wheel_includes_bootstrap_batteries` only because the fresh uv venv had no
`pip`; installing pip fixed it — environmental, not a code failure).
`.venv/bin/coga validate --json` → the same four pre-existing
`unsynthesized-draft-blackboard` errors, nothing on `usage-report`. Manual
cross-check against the live log for 2026-08-31 → 2026-09-07: 389.5M tokens,
65 sessions, 7 unknown, matching `coga usage --json --by model` for the same
window.

## Superseded designs

### 2026-09-20 — plan-utilization report

Superseded by: the token-count-only weekly post in `## Description`.
Reason: the owner is a one-person team on one subscription; the plan
comparison, per-person attribution, and verdict logic had no reader, and
they were where all six evaluator findings lived.

#### What it was

Operator-declared `plans.toml` (per-person `monthly_usd`, `aliases`, plan
label), an `attribute()` join from record slug → ticket `owner:` folded
through aliases (measured: 38.1% of tokens joined; `nicktoper`/`nick` were
one human), a `cost.py` seam falling back to a null pricer until the cost
proxy lands, and a verdict rendered as a floor: recorded value ≥ declared
cost → confident "plan pays for itself"; well below → "worth reviewing",
never "downgrade", because unrecorded usage biases utilization downward.

#### Evaluator findings that would apply if it is revived

Comparison population must match the plan's provider (declare `provider`
per plan and compare per provider); prorate monthly cost to the window and
define the "well below" threshold and the empty-roster case (never `0 ≥ 0`);
the upstream `coga.usage.price_rollup_row` name was never an agreed
contract, so the seam is a provisional adapter; distinguish proxy absent /
present-but-nothing-priced / mixed; pass attribution into the pure builder
instead of hiding ticket IO inside it.
