---
title: 'Usage report: name the human, split per agent, show cache reads separately'
status: in_progress
owner: nicktoper
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills:
    - code/peer-review
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
agent: claude
launch_generation: 942a1a51-a23e-4c20-88e0-2e311e5554bd
---

## Description

The weekly usage report currently opens with "Agent usage — week of …" and a
bare total: 780.9M tokens for the week of 2026-09-21. It doesn't say whose
usage this is or how the total splits between agents. The headline also hides
that 97% of the total is cache reads, which cost roughly a tenth of fresh
input. As a result the number reads as alarmingly large. Make the report say
who it is for, split the total per agent, and break the headline down.

Done means `python coga/recurring/usage-report/report.py` (and so the Monday
post) renders three changes:

1. **Header names the human.** The header line includes the configured `user`
   (`cfg.current_user`), for example
   `Agent usage — nicktoper — week of 2026-09-21 (Mon–Sun)`. Records carry no
   per-human field. The owner decided a header is enough, so do not add a
   record field. When `user` is empty (an ad hoc run on a fresh clone uses
   `require_user=False`, which yields `""`), leave the name out and do not
   print a placeholder.
2. **Headline keeps the total and shows the split.** The total stays first,
   followed by the non-cache-read and cache-read amounts, for example
   `780.9M tokens (25.4M excluding cache reads + 755.5M cache reads) across 142 sessions`.
   Non-cache-read means input + cache write + output. The existing four-category
   line and the unknown-session floor caveat stay.
3. **Per-agent split.** Add a labeled `By agent:` block with one row per
   `agent` (e.g. `claude`, `codex`) and its total tokens. Place it before the
   existing per-model rows, which stay and get a matching `By model:` label.
   An empty agent falls into `(unknown)` like the model buckets do, and it is
   never dropped. Sort agent rows largest first, as the model rows are.

When some sessions have unknown counts, the floor caveat follows the session
count as it does today, for example
`780.9M tokens (25.4M excluding cache reads + 755.5M cache reads) across 142 sessions (2 sessions have unknown counts, so this is a floor)`.
The empty-window output keeps its header, user name included.

`--json` carries the same new data, using the keys `user`,
`non_cache_read_tokens`, and `agents: [{agent, total_tokens}]` (the same
shape as the existing `models`). Tests in `tests/test_usage_report.py` cover all three changes,
including the case with no user.

## Context

- **Prerequisite already landed.** The sibling ticket
  `dedupe-claude-transcript-usage-by-message-id` merged as PR #947 on
  2026-10-02. It fixed a ~1.9× Claude token overcount in
  `usage._parse_claude_session`, which was the real reason the total looked
  too big. Nothing to wait for. This ticket only changes how the report
  presents the number. Old `coga/log.md` records stay inflated, and the
  owner does not care about them, so don't add a recount or caveat.
- All the code is repo-local edge code beside the recurring template: the
  `Report` dataclass, `build_report`, `render`, and `main` in
  `coga/recurring/usage-report/report.py`, and its shim
  `coga/recurring/usage-report/ticket.py`, which calls `load_config()` with
  a required user, so a name is always available on the posted path. Do not
  move logic into `src/coga/` (microkernel rule: single consumer).
- `usage.rollup(records, by="agent", since=…, until=…)` already works:
  `usage._group_key` falls back to `getattr(record, by)` with a `(unknown)`
  bucket. Use the same half-open window construction as the existing model
  rollup in `build_report`.
- `render` needs the user. Pass it in explicitly, either as a `Report` field
  set by `main`/the shim from `cfg.current_user` or as an argument. Keep
  `render` pure so tests stay config-free. The header names
  `cfg.current_user`, the person running the job, not the ticket owner. The
  shim's Slack ping (`ticket.owner or cfg.current_user`) is unchanged.
- Slack routing (`post(cfg, text, important=True, fatal=False)` in the shim)
  is out of scope. Keep it as it is.
- Update `coga/workflows/usage-report/post.md` (its `## post` prose lists
  what the message carries) and `coga/recurring/usage-report/ticket.md`
  (step 2 lists the message contents). The latter ends by saying the report
  has "no per-person attribution". Reword that line: the header names the
  configured user, but records are still not attributed per person. Both are
  repo-local files with no packaged twin.
- Many existing tests in `tests/test_usage_report.py` pin the old header or
  headline. Expect to update all of them, not just one. As of this writing
  they include `test_render_keeps_every_model_bucket_and_states_the_floor`,
  `test_render_omits_the_floor_caveat_when_every_session_is_counted`,
  `test_render_names_a_window_that_is_not_a_calendar_week`,
  `test_empty_window_still_renders_and_says_so`,
  `test_main_prints_the_window_and_writes_nothing`,
  `test_main_json_carries_the_report_fields`, and
  `test_main_renders_without_a_local_user` (which asserts
  `"10 tokens across 1 session"`).
- Two period-task tests need extra care:
  `test_period_task_posts_with_project_and_owner_before_bumping` and
  `test_period_task_renders_last_week_from_the_template_and_closes_its_step`.
  Each builds `expected` with `report.render(report.build_report(...))` and
  no user, but the shim now renders with `cfg.current_user` (e.g. `"marc"`).
  Pass that user when building `expected`, or the
  `stderr.count(expected)` check fails.

Previous ref: `usage-report-name-the-human-split-per-agent-show-c` (renamed 2026-10-27); earlier audit lines retain that ref.

<!-- coga:blackboard -->

## Dev

branch: usage-report-name-human-agent-split

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Handoff (implement, 2026-11-04)

Implemented on `usage-report-name-human-agent-split` (pushed, one commit
`e72c44948`, rebased on current `origin/main`). No PR yet.

- `report.py`: `Report` gains `agents` and `user` (defaulted fields) and a
  `non_cache_read_tokens` property (total − cache reads). `build_report(...,
  *, user="")` takes the user as a keyword so `render` stays config-free and
  runs a second `rollup(by="agent")` over the same half-open window; both
  splits share `_largest_first`. `render` prints `Agent usage — <user> — …`
  (name omitted when empty, also in the empty-window header), the headline
  `X tokens (Y excluding cache reads + Z cache reads) across N sessions`
  (floor caveat after), then `By agent:` and `By model:` blocks via `_rows`.
  `main` passes `cfg.current_user` (`""` under `require_user=False`).
  `--json` adds `user`, `non_cache_read_tokens`, `agents`.
- `ticket.py` shim passes `user=cfg.current_user`; Slack routing and owner
  ping unchanged (the shim AST test still pins imports/post/bump).
- Prose: `coga/workflows/usage-report/post.md`, `coga/recurring/usage-report/ticket.md`
  (step 2 + reworded "no per-person attribution" line), and also
  `coga/skills/coga/usage-report/post/SKILL.md` step 2 + out-of-scope line,
  which described the old content. All repo-local, no packaged twin.
- Tests: updated every pinned header/headline; `_record` takes `agent=`;
  new `test_render_leaves_the_name_out_when_no_user_is_configured`; the
  bucket test covers codex + empty agent → `(unknown)`; JSON test asserts
  the three new keys; period-task tests build `expected` with the shim's user.
- Real-data smoke (week of 2026-10-26): `Agent usage — nicktoper — week of
  2026-10-26 (Mon–Sun)` / `461.2M tokens (15.7M excluding cache reads +
  445.4M cache reads) across 104 sessions (3 … floor)` / `By agent:` codex
  284.3M, claude 176.9M / `By model:` ….

## PR

```yaml
title: Name the human, split per agent, and show cache reads in the usage report
author: claude
author_evidence: Implement session ran as Claude Code (claude-opus-5-5) under megalaunch; see implement handoff.
head: e72c44948dae87302adf3bcb19d8281824b0d670
base: f2ce44d478a4c383d7267ba30e6c7e0cb9ba2a1b
depth: skim
rationale: Repo-local edge renderer and its prose; presentation-only change with no core code touched. Glance at the rendered sample in the tests.
implementation: Report gains agents, user, and non_cache_read_tokens; build_report takes user as a keyword and adds an agent rollup over the same window; render names the user, splits the headline into non-cache-read and cache-read amounts, and prints labeled By agent and By model blocks; main and the shim pass cfg.current_user; JSON carries the new keys.
deviations: Also updated coga/skills/coga/usage-report/post/SKILL.md, which the ticket did not list but which described the old message content.
limitations: No live Slack post was exercised; the period-task tests cover the stubbed transport and the no-channel stderr echo.
files:
  coga/recurring/usage-report/report.py: Header user, cache-read headline split, per-agent rollup and labeled blocks, JSON keys.
  coga/recurring/usage-report/ticket.py: Pass cfg.current_user to the report so the posted header names the user.
  coga/recurring/usage-report/ticket.md: Describe the new message contents and reword the per-person attribution line.
  coga/workflows/usage-report/post.md: List the new message contents in the post step prose.
  coga/skills/coga/usage-report/post/SKILL.md: Keep the skill's content description and out-of-scope note in line with the new rendering.
  tests/test_usage_report.py: Update pinned header/headline expectations and cover user, no-user, per-agent split with unknown agent, and new JSON keys.
review:
  reviewer: none
  kind: none
  status: not-run
  detail: Implement step; the workflow's peer-review step (other-agent) has not run yet.
checks:
  - command: python -m pytest tests/test_usage_report.py
    status: passed
    head: e72c44948dae87302adf3bcb19d8281824b0d670
    base: f2ce44d478a4c383d7267ba30e6c7e0cb9ba2a1b
    detail: 22 passed.
  - command: python -m pytest
    status: passed
    head: 00821ee9a77640b77080714b965f662fd0c314c3
    base: e6e5c11da56bb56c131f588c5adaeea9355f1c61
    detail: 4454 passed, 10 skipped on the pre-rebase tree (uncommitted, then committed identically as 00821ee9); the rebase brought only this ticket file, so code paths are identical to e72c4494, but the full suite was not re-run on the rebased head.
```
