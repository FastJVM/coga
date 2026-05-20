---
title: Post Slack notification on mode-script failures
status: draft
mode: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
- relay/architecture
- relay/principles
- relay/codebase
- relay/current-direction
- relay/project-stage
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement-and-pr
  - name: review
step: 1 (implement)
---

## Description

When a `mode: script` task fails, `docs/spec.md` (around L942-943)
specifies that relay should post to the Slack feed so a human notices.
Current code in `src/relay/launch_script.py` (`run_script_mode`) logs the
failure to the task log but never calls `post_feed`. Scripted tasks fail
silently from Slack's perspective.

Fix: on non-zero exit from the script, call `slack.post_feed` with a
short message including the ticket slug, exit code, and a pointer to the
log file. Keep the existing log write — Slack is in addition, not
instead.

## Context

- Audit entry: `docs/spec-audit.md` §D.23.
- Implementation: `src/relay/launch_script.py` — function `run_script_mode`.
- Slack helper: `src/relay/slack.py` — `post_feed(cfg, message)`.
- Spec contract: `docs/spec.md` L942-943.
- Related ticket: `diagnose-slack-notifications-not-firing-in-practic`
  (this fix relies on Slack actually working — coordinate ordering).

## Acceptance criteria

- [ ] `run_script_mode` posts to Slack on non-zero exit.
- [ ] Message includes: ticket slug, exit code, path to log.
- [ ] Successful runs do *not* post (or post a quieter "done" — match
      whatever interactive/auto modes already do).
- [ ] Test added covering the failure-posts-to-slack path with a stubbed
      `post_feed`.
