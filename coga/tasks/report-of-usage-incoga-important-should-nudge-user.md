---
title: Weekly usage report should mention its owner and identify the repo
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
step: 2 (peer-review)
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

## Dev

branch: usage-report-owner

## Implement handoff

- The owner approved the scoped owner-prefix change, then explicitly requested
  repair of the stale `CLAUDE.md` test exposed by the full suite.
- `coga/recurring/usage-report/ticket.py` now uses `tasks.resolve_task` and
  `tasks.read_ticket` to select the generated period ticket's owner, falling
  back to `cfg.current_user`, and passes it to `notification.post`. The shared
  Slack renderer supplies the configured repo name and mapped mention, with
  the existing plain-name fallback. The renderer and shared notification API
  are unchanged.
- Six transport-capture cases reproduced the missing owner prefix before the
  fix. They exercise a non-Coga repository name, mapped owner distinct from
  the current user, absent-owner fallback, and an unmapped owner on both HTTP
  200 and 503. The expected payload retains the entire report body and the
  call sequence proves one important-route post followed by the CLI bump.
- Producer instructions and the important-destination context/twin describe
  the owner prefix. The producer's canonical documentation link remains valid
  when the template body is copied into a generated period ticket.
- The initial full suite had one pre-existing failure: main commit `91d869c73`
  removed root `CLAUDE.md`, while
  `tests/test_compose.py::test_coga_repo_instructions_carry_the_minimal_core_boundary`
  still expected it. The owner-authorized repair checks the shared
  `AGENTS.md`, matching the existing packaging contract. The report fix and
  this test repair are separate commits (`0d340839c`, `877a439f4`).
- Reconciled with current main and pushed `usage-report-owner`. The final full
  suite passed on the committed tree: 3808 passed, 7 Windows-only skips.
  Focused composition/report checks also passed (106). Exact head/base and
  receipts are below. Verification sent no live Slack messages.
- Independent review is the next frozen workflow step. No PR was opened.

## Adjacent finding

The existing failure-audit claim in the producer comment and posting skill is
stronger than its behavior: the module-level `notification.post` call in
`coga/recurring/usage-report/ticket.py` omits `task_path`, while
`src/coga/notification/slack.py` / `SlackChannel.send` appends a Slack failure
audit line only when `task_path` is supplied. HTTP 503 remains visible on
stderr and the bump still runs, but there is no corresponding Slack failure
line in `log.md`. This predates the owner fix and was not changed. No existing
follow-up ticket was identified; carry this finding forward through Retro.

## PR

```yaml
title: Mention the owner in weekly usage reports
author: codex
author_evidence: Implemented by Codex in this attended session. The configured ticket agent
  remains claude; no delegated agents or code reviewers ran.
head: 877a439f4b3f9cc15611eac25fff909959251eab
base: cee89faabbd4d884dd64143e2aaaa615338aad52
depth: deep
rationale: The recipient change is bounded and covered by captured Slack payloads, but independent
  review belongs to the next peer-review step and has not run.
implementation: The repo-local usage-report script reads the generated period ticket and passes
  its owner, falling back to cfg.current_user, to notification.post. Existing Slack rendering
  supplies the project name, mapped mention, and plain-name fallback. Regression cases preserve
  the report body, important route, one delivery attempt, and CLI bump after HTTP 503.
deviations: 'The owner explicitly requested repair of an unrelated full-suite failure: the repository-instructions
  test still expected CLAUDE.md after main removed it. A separate commit checks the canonical
  AGENTS.md instead.'
limitations: Slack delivery was verified with a captured transport, without live messages. Verification
  used Python 3.12.12. An existing omission of task_path leaves usage-report delivery failures
  on stderr without a Slack failure audit line; see the adjacent finding on this blackboard.
files:
  coga/recurring/usage-report/ticket.py: Resolve the generated period owner and pass the existing
    current-user fallback to the shared notification API.
  coga/recurring/usage-report/ticket.md: Document owner selection and the repository/owner prefix;
    use a canonical link that survives copying into a generated period ticket.
  coga/skills/coga/usage-report/post/SKILL.md: Align the posting procedure and shared-infrastructure
    list with the owner-aware producer.
  docs/contexts/coga/important/SKILL.md: Describe the weekly report as identifying its repository
    and addressing the period owner through the existing mapping.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/important/SKILL.md: Keep the packaged
    important-destination topic byte-identical to its canonical owner.
  tests/test_usage_report.py: Execute the copied period script through the real notification
    renderer with captured transport, covering three recipient cases on success and HTTP 503,
    plus the existing end-to-end completion check.
  tests/test_compose.py: Repair the owner-authorized stale CLAUDE.md assertion after main standardized
    the root instructions on AGENTS.md.
review:
  reviewer: none
  kind: none
  status: not-run
  detail: Independent code review is the next frozen workflow step; this implement session does
    not perform self-QA.
checks:
- command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest tests/test_compose.py
    tests/test_usage_report.py
  status: passed
  head: 877a439f4b3f9cc15611eac25fff909959251eab
  base: cee89faabbd4d884dd64143e2aaaa615338aad52
  detail: 106 passed in 2.15s on Python 3.12.12 after the rebase.
- command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -rs > /tmp/coga-usage-report-owner-final-pytest.log
    2>&1
  status: passed
  head: 877a439f4b3f9cc15611eac25fff909959251eab
  base: cee89faabbd4d884dd64143e2aaaa615338aad52
  detail: '3808 passed, 7 skipped in 448.62s on Python 3.12.12. Skips: two native Windows job-object
    integration cases and five cases requiring Windows PowerShell 5.1. Ran on the committed
    tree b2c98cbb0f3be6cd7e692bcdece3cf1bdc4144b1.'
- command: git diff --check origin/main...HEAD
  status: passed
  head: 877a439f4b3f9cc15611eac25fff909959251eab
  base: cee89faabbd4d884dd64143e2aaaa615338aad52
  detail: No whitespace errors in the seven-file implementation diff.
- command: coga validate --json
  status: not-run
  detail: Configuration, workflow semantics, task layout, and validation behavior are unchanged;
    the seeded repository is exercised by the usage-report tests.
```
