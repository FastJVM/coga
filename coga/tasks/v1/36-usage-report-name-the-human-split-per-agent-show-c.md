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
step: 4 (review)
agent: claude
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

pr: https://github.com/FastJVM/coga/pull/1172
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

## Peer review

Completed direct, independent Codex review on 2026-11-04 of head
`b3903b4e83b9a9f1a516a7ef1b5dcb863d0f25f7` against base
`a6c2ccedb5e624a45459ca58678d9c798dd2d941`. Claude authored the
implementation, evidenced by the implement handoff and its commit's
`Co-Authored-By: Claude Opus 5.5` trailer; this fresh Codex session reviewed
it directly. No nested review CLI or additional reviewer ran.

No must-fix findings and no code changes. Reviewed all six changed paths,
the shared rollup implementation, and the usage/report contracts. Both
rollups use the same half-open UTC bounds, retain unknown buckets and sort
largest first. The headline counts input + cache write + output separately
from cache reads; both entry points name `cfg.current_user`, while the
period owner's Slack ping is unchanged. JSON contains the same new data.

Rebased the branch unconditionally onto fetched main before review and
testing. The final fetch found no further main commits. Force-with-lease
pushed `usage-report-name-human-agent-split` at the reviewed head, then
returned this checkout cleanly to main before writing this handoff. No PR
exists yet; the next step owns opening it.

Verification:

- `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest`:
  4454 passed, 10 skipped on Linux / Python 3.12.12, including all 22
  usage-report tests, after the rebase.
- `git diff --check origin/main...HEAD`: passed on the feature branch.
- Real PTYs at 80 columns / 24 rows and 120 columns / 40 rows ran
  `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python coga/recurring/usage-report/report.py --since 2026-10-26 --until 2026-11-02`.
  Both returned the complete plain-text report: named header, 461.2M total,
  15.7M excluding cache reads, 445.4M cache reads, 104 sessions with the
  three-session floor caveat, codex 284.3M above claude 176.9M, and the
  labeled model block including unknown and synthetic zero rows. The same
  command with `--json` returned matching exact totals and the new keys.
- An 80-by-24 PTY run with `--since 2000-01-03 --until 2000-01-10`
  retained the named header and printed the empty-window message.
- `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m coga.cli validate --task v1/36-usage-report-name-the-human-split-per-agent-show-c --json`:
  one task valid, no issues.
- `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m coga.cli validate --json`:
  exit 1 on both the reviewed feature head and clean main
  `a6c2ccedb5e624a45459ca58678d9c798dd2d941` (base equal to head for that
  main comparison): 92 valid, 3 errors, 12 warnings. The errors are
  `unsynthesized-draft-blackboard` in
  `v1/26-make-the-readme-install-section-the-only-install-p`,
  `v1/27-link-uninstall-from-the-readme`, and
  `v1/31-test-install-on-windows`. Their files and the validator are
  unchanged by this branch. Those tickets still need their draft notes
  synthesized into their bodies or intentionally classified as production
  notes before activation; this review leaves their authors' intent intact.

No live Slack message was sent or inspected; terminal output and the suite's
stubbed transport/no-channel echo cover the changed report content. Python
3.11 and native Windows were not run. The advisory depth is `deep` because
the repository-wide validation failures remain visible; there are no
unresolved findings against this implementation.

## PR

```yaml
title: Name the human, split per agent, and show cache reads in the usage report
author: claude
author_evidence: >-
  The implement handoff identifies Claude Code (claude-opus-5-5), and the
  implementation commit carries a Co-Authored-By trailer for Claude Opus
  5.5. This fresh Codex session performed the independent review.
head: b3903b4e83b9a9f1a516a7ef1b5dcb863d0f25f7
base: a6c2ccedb5e624a45459ca58678d9c798dd2d941
depth: deep
rationale: >-
  Bounded report presentation change with completed independent review, a
  passing full suite, terminal inspection, and clean task validation.
  Repository-wide validation fails on three unrelated draft tickets and
  reproduces on clean main, so the failed check remains visible under the
  publication rubric rather than presenting an all-green recommendation.
implementation: >-
  The weekly report names the configured user when present, keeps the total
  first while separating cache reads from input plus cache write plus
  output, and adds largest-first By agent rows before labeled By model rows.
  Unknown buckets and the unknown-session floor caveat remain. Both the CLI
  and period shim pass cfg.current_user, and JSON adds user,
  non_cache_read_tokens, and agents.
deviations: >-
  Also updated coga/skills/coga/usage-report/post/SKILL.md, which described
  the old message content. All six changed files are repo-local; there is no
  packaged twin for this recurring report.
limitations: >-
  No live Slack post or Slack-client rendering was exercised; real terminal
  output and the suite's stubbed transport/no-channel echo cover the content.
  Verification ran on Linux with Python 3.12.12, not Python 3.11 or native
  Windows. Repository-wide validation reports unsynthesized draft
  blackboards in v1/26-make-the-readme-install-section-the-only-install-p,
  v1/27-link-uninstall-from-the-readme, and v1/31-test-install-on-windows;
  the same errors occur on clean main and their paths are outside this diff.
files:
  coga/recurring/usage-report/report.py: Header user, cache-read headline split, per-agent rollup and labeled blocks, JSON keys.
  coga/recurring/usage-report/ticket.py: Pass cfg.current_user to the report so the posted header names the user.
  coga/recurring/usage-report/ticket.md: Describe the new message contents and reword the per-person attribution line.
  coga/workflows/usage-report/post.md: List the new message contents in the post step prose.
  coga/skills/coga/usage-report/post/SKILL.md: Keep the skill's content description and out-of-scope note in line with the new rendering.
  tests/test_usage_report.py: Cover user and no-user headers, cache-read amounts, ordered agent buckets including unknown, JSON keys, and period-shim behavior.
review:
  reviewer: codex
  kind: independent
  status: passed
  head: b3903b4e83b9a9f1a516a7ef1b5dcb863d0f25f7
  base: a6c2ccedb5e624a45459ca58678d9c798dd2d941
  detail: >-
    Direct independent Codex review completed on the final rebased diff
    across all six paths and relevant contracts. No must-fix findings or
    code changes. Inspected actual report output in 80x24 and 120x40 PTYs.
checks:
  - command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest
    status: passed
    head: b3903b4e83b9a9f1a516a7ef1b5dcb863d0f25f7
    base: a6c2ccedb5e624a45459ca58678d9c798dd2d941
    detail: >-
      4454 passed, 10 skipped in 565.71s on Linux with Python 3.12.12,
      including all 22 usage-report tests. Run after the final rebase.
  - command: git diff --check origin/main...HEAD
    status: passed
    head: b3903b4e83b9a9f1a516a7ef1b5dcb863d0f25f7
    base: a6c2ccedb5e624a45459ca58678d9c798dd2d941
    detail: No whitespace errors in the final feature diff.
  - command: |
      stty cols 80 rows 24 && PYTHONPATH=/home/n/Code/coga/src .venv/bin/python coga/recurring/usage-report/report.py --since 2026-10-26 --until 2026-11-02
      stty cols 120 rows 40 && PYTHONPATH=/home/n/Code/coga/src .venv/bin/python coga/recurring/usage-report/report.py --since 2026-10-26 --until 2026-11-02
    status: passed
    head: b3903b4e83b9a9f1a516a7ef1b5dcb863d0f25f7
    base: a6c2ccedb5e624a45459ca58678d9c798dd2d941
    detail: >-
      Both real PTYs emitted the full named report with 461.2M total,
      15.7M excluding cache reads, 445.4M cache reads, 104 sessions and
      the three-session floor caveat. Agent and model blocks retained all
      buckets and descending totals.
  - command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python coga/recurring/usage-report/report.py --since 2026-10-26 --until 2026-11-02 --json
    status: passed
    head: b3903b4e83b9a9f1a516a7ef1b5dcb863d0f25f7
    base: a6c2ccedb5e624a45459ca58678d9c798dd2d941
    detail: >-
      user is nicktoper; total_tokens 461186503 equals non_cache_read_tokens
      15748721 plus cache_read_input_tokens 445437782. Agent totals codex
      284315710 and claude 176870793 agree with the overall total.
  - command: stty cols 80 rows 24 && PYTHONPATH=/home/n/Code/coga/src .venv/bin/python coga/recurring/usage-report/report.py --since 2000-01-03 --until 2000-01-10
    status: passed
    head: b3903b4e83b9a9f1a516a7ef1b5dcb863d0f25f7
    base: a6c2ccedb5e624a45459ca58678d9c798dd2d941
    detail: The empty-window output kept nicktoper in the header and stated that no sessions were recorded.
  - command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m coga.cli validate --task v1/36-usage-report-name-the-human-split-per-agent-show-c --json
    status: passed
    head: b3903b4e83b9a9f1a516a7ef1b5dcb863d0f25f7
    base: a6c2ccedb5e624a45459ca58678d9c798dd2d941
    detail: One task valid, no issues.
  - command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m coga.cli validate --json
    status: failed
    head: b3903b4e83b9a9f1a516a7ef1b5dcb863d0f25f7
    base: a6c2ccedb5e624a45459ca58678d9c798dd2d941
    detail: >-
      Exit 1; 92 valid, 3 unsynthesized-draft-blackboard errors in the
      unrelated v1/26, v1/27, and v1/31 tickets listed under limitations,
      and 12 warnings. No errors concern this ticket or changed files.
      Repeating the same command on clean main
      a6c2ccedb5e624a45459ca58678d9c798dd2d941 reproduced the same errors;
      the full comparison receipt is under Peer review.
```
