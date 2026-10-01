---
title: "Usage report: name the human, split per agent, show cache reads separately"
status: draft
owner: nicktoper
workflow: code/with-review
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
   never dropped.

`--json` carries the same new data (user, non-cache-read total, per-agent
rows). Tests in `tests/test_usage_report.py` cover all three changes,
including the case with no user.

## Context

- **Land this after** the sibling ticket
  `dedupe-claude-transcript-usage-by-message-id`. It fixes a ~1.9× Claude
  token overcount in `usage._parse_claude_session`, which is the real reason
  the total looked too big. This ticket only changes how the report presents
  the number. It does not fix the count. Old `coga/log.md` records stay
  inflated, and the owner does not care about them, so don't add a recount
  or caveat.
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
  `render` pure so tests stay config-free.
- Slack routing (`post(cfg, text, important=True, fatal=False)` in the shim)
  is out of scope. Keep it as it is.
- Update `coga/workflows/usage-report/post.md` (its `## post` prose lists
  what the message carries) and `coga/recurring/usage-report/ticket.md`
  (step 2 lists the message contents). The latter ends by saying the report
  has "no per-person attribution". Reword that line: the header names the
  configured user, but records are still not attributed per person. Both are
  repo-local files with no packaged twin.
- Existing tests pin the old headline (e.g.
  `test_main_renders_without_a_local_user` asserts
  `"10 tokens across 1 session"`). Expect to update them.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
