---
slug: a-slack-repo-without-important-webhook-can-abort-t
title: A Slack repo without important_webhook can abort the recurring scan phase
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
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
secrets: null
step: 1 (implement)
---

## Description

A repo that selects a Slack channel but does not configure `important_webhook` can abort the
recurring **scan phase** outright.

`SlackChannel.webhook_for` (`src/coga/notification/slack.py`) is fail-loud with no fallback when an
important webhook is requested and none is configured. `_broadcast_scan` in
`src/coga/recurring_runner.py` calls `notify(..., important=True)` **unwrapped**, so that fail-loud
raise propagates and takes the scan down before any period task runs.

Both surviving *launch* sites wrap `SystemExit`, so the blast radius is the scan phase specifically,
not recipe execution.

Decide whether an unresolved important webhook should be fatal at all. Options: fall back to the
ordinary channel, warn-and-continue, or fail fast at config-validation time instead of mid-scan —
but a misconfigured notification sink silently killing the whole sweep is the worst of the three.

## Context

Found by Dream 2026-08-24, Phase 6, while verifying an unrelated finding for PR #721.

**The original finding was wrong and this is its corrected form.** Dream Phase 2 (shard-04) reported
that the seeded `example/coga/coga.toml` enables a Slack opt-in that halts recurring runs. That
premise is false — the fixture has `channels = []`, no `[notification.slack]` table, and no
`important_webhook`, and `example/coga/coga.local.toml` is Slack-free. The PR agent rejected the fix
and left the fixture alone.

The abort path itself is partially real, but differently shaped than reported: the finding blamed
`_run_recipe_task`, which no longer exists (removed in the recurring -> `ticket.py` migration). The
live path is `_broadcast_scan`. Filed as its own ticket so the corrected version does not die with
the rejected one.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
