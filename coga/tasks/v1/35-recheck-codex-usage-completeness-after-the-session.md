---
title: Recheck Codex usage completeness after the session matching fix
status: active
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
step: 1 (implement)
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
