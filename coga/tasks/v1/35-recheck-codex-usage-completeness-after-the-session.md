---
title: Recheck Codex usage completeness after the session matching fix
status: done
owner: nicktoper
workflow:
  name: code/with-self-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: self-qa
    skills:
    - code/self-qa
    assignee: agent
  - name: pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
agent: claude
---

## Description

Find out why two completed Codex `bootstrap/orient` sessions were recorded with
`usage_status: unknown` and reason `codex rollout not found for cwd`, even
though Codex ran for 36s and 119s. Fix the matching if the rollout existed and
Coga missed it.

The broader recheck this ticket originally carried is done (see Context): the
PR #961 session-matching fix worked, so this ticket is now only about these
residual misses.

Done means one of the following:

- **A defect is found:** the matcher in `usage._parse_codex_session` excluded
  a rollout that belonged to the launch. A narrow fix plus a regression test
  ships through this workflow. Old log records are not restamped.
- **No defect:** Codex wrote no matching rollout, or the evidence is gone.
  Record that under `## Already satisfied` on the blackboard, with the
  evidence, and close the ticket through the workflow's already-satisfied
  path.

Either way, state whether the 0–5s failed launches are legitimate unknowns.

## Context

### Recheck result — 2026-11-04 (tallied from `coga/log.md` during authoring)

- PR #961 merged 2026-10-06 11:38 PDT (18:38 UTC), merge commit `d59d42d80`.
  The original intake said 2026-10-07 11:23; that was wrong.
- Sessions that started up to 2026-10-08 00:03 UTC still had gaps (9 of
  them), all with `usage_reason: null`. They probably ran an older installed
  revision; this was not verified per launch.
- From 2026-10-08 through 2026-11-04 there were about 140 Codex sessions. 5
  were missing both `session_id` and `human_turns`, about 4%, compared with
  10 of 21 in the pre-fix baseline. All 5 had `usage_status: unknown` and
  reason `codex rollout not found for cwd: <path>`:
  - `bootstrap/orient`: started 2026-10-16T19:13:25Z, completed, 36s.
  - `bootstrap/orient`: started 2026-10-28T19:00:55Z, completed, 119s.
  - `marketing/fix-installer/ask-which-agents-to-enable-during-coga-init`:
    2026-10-28T02:56Z and 02:57Z, both failed, 0s.
  - `v1/10-preflight-dirty-tracked-files-before-skill-update`:
    2026-11-04T17:58Z, failed, 5s.
- For the 0–5s failures: a usage record is written only when `spawn_started`
  is true, so Codex was spawned. The question is whether Codex exited before
  writing a rollout. If it did, `unknown` is correct. Confirm this; it is
  not the main question.
- Keep three things separate: missing metadata, duplicate records, and
  incorrectly classified failures.

### Where to look

- `usage._parse_codex_session` returns this reason when no rollout survives
  its filters. A rollout is dropped if any of these hold:
  - it was in the pre-spawn snapshot (`pre_existing`);
  - it is a subagent thread (`thread_source == "subagent"` or a
    `parent_thread_id`);
  - its `session_meta.cwd` is not exactly `str(cwd.resolve())`;
  - its meta timestamp is outside `[window_start, window_end]`.
- `window_end` is taken in `launch.py` right after the agent exits.
  `capture_session` is then called with it.
- The rollouts still existed on 2026-11-04. Only the directory listing was
  checked during authoring, not file contents; `CODEX_HOME` was unset. Rollout
  file names are in local time (PDT, UTC−7):
  - Oct 16 session: 12:13:25–~12:14:01 PDT. The nearest rollouts in
    `~/.codex/sessions/2026/10/16/` are `rollout-2026-10-16T12-14-22-…` and
    `…T12-14-52-…`, both named *after* the session ended. Lead: Codex may
    create the rollout lazily, or stamp it late, so it is not visible at
    capture time or its meta timestamp falls after `window_end`.
  - Oct 28 session: 12:00:55–~12:02:54 PDT. `~/.codex/sessions/2026/10/28/`
    has `rollout-2026-10-28T12-02-31-…`, which is inside the window. Lead: a
    rollout was there but a filter rejected it, most likely cwd or
    `session_meta` parsing.
- Hypotheses to test against those files:
  - The cwd differs from `str(cwd.resolve())`: a symlink, a trailing
    component, or orient running outside the checkout root.
  - The meta timestamp falls outside the window. Note that the window check
    uses the `session_meta` start timestamp, not when the file was written.
    `_parse_ts` treats naive timestamps as UTC.
  - The file did not exist yet, or was not readable, when
    `_codex_rollout_paths()` ran during capture.
  - `_read_codex_session_meta` silently returns `None` when the first line
    is not `session_meta`, or is partial or invalid JSON. The rollout is then
    skipped with the same "not found" reason. A Codex format change would
    cause this.
  - Only a subagent rollout existed, or a resumed session was already in
    `pre_existing`.
  - The rollout root is hardcoded to `~/.codex/sessions` and ignores
    `CODEX_HOME`. It was unset here, so this is unlikely to be the cause, but
    note it.
- Compare against successful orient sessions near the same times, with the
  same cwd and Codex version. That cheaply separates a matcher defect from an
  environmental one.
- If you conclude there is no defect or the evidence is unavailable, name
  every directory and file you checked and what each showed. Do not guess.
  If a fix is warranted, reproduce it with a synthetic rollout in a test.
- Do not paste private transcript content onto the blackboard or into the PR.
  Metadata fields such as cwd, timestamps and thread source are fine.
- Cited, not attached: coga/usage (`docs/contexts/coga/usage/SKILL.md`) and
  coga-dev/internals/activity-capture
  (`docs/contexts/coga-dev/internals/activity-capture/SKILL.md`). Read the
  sections on unknown reasons and Codex matching. If behavior changes, update
  them in the same PR.

Previous ref: `recheck-codex-usage-completeness-after-the-session` (renamed
2026-10-27); earlier audit lines retain that ref.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Already satisfied

Verdict: **no matcher defect.** `usage._parse_codex_session` missed no rollout.
None of the five sessions wrote a rollout, so `unknown` with reason "codex
rollout not found for cwd" is correct for all of them. No code change and no
PR. Investigated 2026-11-04 by claude (claude-opus-5-5), metadata only. I read
the first-line `session_meta` fields, file mtimes, log row counts, and
history `ts`/`session_id`. No transcript content was read.

### Evidence checked
- `CODEX_HOME` is unset, so `~/.codex/sessions` is the real root.
- **Global scan.** Parsed the first line of all 3,177 `*.jsonl` files under
  `~/.codex/sessions/**`. `archived_sessions` does not exist. 0 files were
  unparseable, so the "`_read_codex_session_meta` returns None" hypothesis is
  ruled out. I matched each file's meta timestamp and mtime against every
  failure window ±120s. Every hit belongs to *another* launch, by `session_id`
  in `coga/log.md`:
  - **Oct 16 orient** (19:13:25–19:14:01Z):
    - `…T12-14-22-01a14623-03e9…` has meta ts 19:14:22Z and cwd
      `/home/n/Code/codex/coga`. It is the *next* orient launch, which started
      19:14:18Z and matched it (`usage_status: ok`).
    - `…T12-14-52-01a14623-7b71…` is the peer-review launch for
      `run-clone-local-recurring-work-in-every-clone`, started 19:14:48Z.
    - Both start after `window_end`, and both are already owned. Nothing
      started inside the window.
  - **Oct 28 orient** (19:00:55–19:02:55Z):
    - `…T12-02-31-01a183e4-7b80…` (the lead from authoring) is the
      `bootstrap/ticket` launch that started 19:02:27Z in a parallel terminal.
      Its log record carries that session id.
    - `…T11-56-05-…95d7` is an earlier `bootstrap/ticket` launch, and
      `…T11-58-23-…b0cd` is a subagent of `95d7`.
    - `…T12-03-28-…5a45` is the next orient launch, started 19:03:24Z.
    - No unowned rollout was found, so no filter rejected anything.
- **`~/.codex/history.jsonl`** records every submitted prompt (keys `ts`,
  `session_id`, `text`). Oct 16 19:13:20–19:14:30Z had no entries. Oct
  28 19:00:50–19:03:40Z had only `01a183e4-7b80` (the bootstrap/ticket
  session). Neither failed orient ever submitted a turn, so Codex never
  created a thread or rollout.
- **Likely cause, inferred and not proven:** both failed orients sit exactly
  on a Codex CLI upgrade.
  - The last cli rollout before Oct 16 is 0.162.1. The relaunch is 0.163.0.
  - Oct 28 rollouts up to 19:02:31Z are 0.164.0. The relaunch at 19:03:24Z
    is 0.165.0.
  - This fits the human accepting Codex's startup update prompt (exit 0, no
    thread) and immediately relaunching orient.
- `~/.codex/logs_2.sqlite` keeps only 2026-11-03 onward, so it cannot show
  the October sessions. `~/.codex/log/` is empty.

### 0–5s failed launches: legitimate unknowns
- `marketing/fix-installer/ask-which-agents-to-enable-during-coga-init`
  failed twice on 2026-10-28, at 02:56:24Z (0.37s) and 02:57:23Z (0.15s).
  - Both exited with `exit_code: 2` in under 0.4s. That is the
    argument-parse exit code; the stderr text is not retained.
  - No rollout or history entry exists in either window.
  - Correct as `unknown`.
- `v1/10-preflight-dirty-tracked-files-before-skill-update` peer-review failed
  on 2026-11-04 at 17:58:31Z (5.0s, `exit_code: null`).
  - `logs_2.sqlite` has **0 rows** from any process in 17:57:30–17:59:40Z.
  - For comparison, the successful 22:20:45Z start of the same ticket wrote
    79 rows from 3 processes within 10s.
  - Codex never initialised, so there is no rollout and no history entry.
    Correct as `unknown`.
- The three categories stay separate. All 5 are missing metadata where no
  data exists. None is a duplicate record. Whether `outcome_status: failed`
  is right for the 0–5s launches is a launch question, not a usage question.
  Nothing here suggests it is wrong.

### Follow-up filed
- `v1/honor-codex-home-when-locating-codex-rollouts` (draft).
  `_codex_rollout_paths` hardcodes `~/.codex/sessions` and ignores
  `CODEX_HOME`. It did not affect these misses. Nothing else is left open.

## Retro

status: processed
skill: retro/done-ticket
result: knowledge-pr
title: New context: legitimate Codex no-rollout unknowns and the unsupported CLAUDE_CONFIG_DIR
