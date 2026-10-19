---
title: Weekly usage report should mention its owner and identify the repo
status: active
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
step: 1 (implement)
agent: claude
---

## Description

Make the weekly usage report in `coga-important` ping the report's owner and
clearly identify the repository whose usage it reports. The current post starts
`[coga] Agent usage — week of 2026-10-12 (Mon–Sun)`: it names the repo but
does not @mention the human, so the report can go unnoticed. Done means the
posted message includes the configured repository/project name and a real Slack
mention for the mapped owner, for example `[coga] [<@MEMBER_ID>] Agent usage —
week of …`, with regression coverage of the report's delivery path and the
rendered prefix.

## Context

- The owner confirmed that "nudge" means an @mention and that the report must
  identify the repo in question. The existing `[coga]` prefix satisfies the repo
  part when it comes from the reporting repo's configuration; do not hardcode
  this repository's name or a Slack member ID. Keep `owner: nicktoper` for this
  work; leave the main agent to the configured default at activation.
- The producer is repo-local edge code:
  `coga/recurring/usage-report/ticket.py` renders with
  `report.build_report` / `report.render` from
  `coga/recurring/usage-report/report.py`, then calls
  `notification.post(cfg, text, important=True, fatal=False)` without `owner`.
  Supply the generated period ticket's owner, falling back to `cfg.current_user`
  when absent, following the existing `commands.slack.slack` owner-selection
  convention. Reuse the notification API; keep this single-consumer change at
  the edge.
- `coga/notifications` at `docs/contexts/coga/notifications/SKILL.md` is cited
  rather than attached; read "Pinging the owner" and "Message format".
  `notification.slack.SlackChannel.render_text` already prefixes
  `cfg.project_name` and the supplied owner; `notification.slack.mention` maps
  the owner through `cfg.slack_users` to `<@…>`, with plain-name fallback when
  unmapped. Preserve that fallback rather than inventing a recipient mechanism.
  A mapped owner must receive mention syntax; a plain display name is not a ping.
- Preserve the weekly window, token totals and breakdown, unknown-count caveat,
  one important-route post, and nonfatal delivery handling followed by the CLI
  bump. This ticket adds no channel-wide mentions, reminders, usage thresholds,
  cost calculations, or cross-repository aggregation. Do not post live Slack
  messages while verifying; capture the payload with a stubbed transport.
- Extend `tests/test_usage_report.py` to exercise the posting path and resulting
  Slack prefix, including a repository name other than `coga`, a mapped owner
  different from the current user, an absent period-ticket owner falling back
  to `cfg.current_user`, and the existing unmapped-name fallback.
  Update the producer's instructions in
  `coga/recurring/usage-report/ticket.md` and
  `coga/skills/coga/usage-report/post/SKILL.md` where needed. If shared
  notification behavior changes, update its owning topic and packaged twin in
  the same PR.
- The separate draft `usage-report-name-the-human-split-per-agent-show-c`
  covers naming the configured human inside the report, adding per-agent rows,
  and separating cache reads in the headline. This ticket concerns the Slack
  notification prefix and recipient; preserve any sibling changes that have
  landed when implementation begins.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
