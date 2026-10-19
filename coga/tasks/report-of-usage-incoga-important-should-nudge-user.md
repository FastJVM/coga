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
step: 3 (open-pr)
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
- The implement session pushed original head `877a439f4` at base `cee89faab`.
  Its historical checks passed: 3808 full-suite tests, 7 Windows-only skips,
  and 106 focused composition/report checks. It sent no live Slack messages.
  Fresh review receipts after rebase are below.
- Implementation handed off without opening a PR; see the completed peer review below.

## Adjacent finding

The existing failure-audit claim in the producer comment and posting skill is
stronger than its behavior: the module-level `notification.post` call in
`coga/recurring/usage-report/ticket.py` omits `task_path`, while
`src/coga/notification/slack.py` / `SlackChannel.send` appends a Slack failure
audit line only when `task_path` is supplied. HTTP 503 remains visible on
stderr and the bump still runs, but there is no corresponding Slack failure
line in `log.md`. This predates the owner fix and was not changed. No existing
follow-up ticket was identified; carry this finding forward through Retro.

## Peer review

- **Completed:** direct Codex review of final head `7520b20675be5141e8e52ea6731b7f9330ac6d3f` against diff base
  `537352f8e50664ac657233ae69de6e6bdf2daf56`. No must-fix findings and no code fixes required.
  Both actual implementer and reviewer are Codex, so this is **self-review**;
  the configured peer did not establish independence. No child review CLI or
  delegated agent ran.
- Started on clean `main`, read the branch by name, then ran `git switch
  usage-report-owner`, `git fetch origin main`, and `git rebase FETCH_HEAD`.
  Main already contained the producer/script instructions in `a1d937e09`;
  the final diff has five paths. Re-read the final diff and affected contracts.
- Re-ran the full suite after rebase: **3808 passed, 7 Windows-only skips in
  522.77s**, Python 3.12.12. Exact command and revision receipts are in `## PR`.
  Canonical/package topic bytes and whitespace checks also passed.
- **Surface inspection:** ran the actual copied period script with captured
  transport in 80x24 and 120x40 PTYs. The outbound text began
  `[orbital-service] [<@U02ADA>] Agent usage — week of 2026-10-12 (Mon–Sun)`.
  The absent-owner and unmapped-owner cases produced `[<@U01MARC>]` and
  `[stranger]`; report content remained intact. One important-route attempt
  preceded the CLI bump even on HTTP 503. This checked captured outbound text,
  not a live Slack client; no live Slack messages were sent, per the ticket.
- Read-only source-repo configuration check confirmed project `coga` and a
  Slack mapping for the effective template owner `nicktoper`.
- Final freshness checks accepted newer control changes as non-overlapping
  Coga task/log state (`check_branch_contains_control`: `state-only-drift`).
  The receipts retain the actual tested/reviewed head and base. Pushed with
  an explicit force-with-lease; `origin/usage-report-owner` is `7520b20675be5141e8e52ea6731b7f9330ac6d3f`,
  with two commits ahead of main.
- Keep the pre-existing failure-audit omission on this blackboard for Retro. Recommend
  **skim** with self-review and the authorized test repair disclosed. No PR
  opened in this step. `COGA_LAUNCH_RETURNS_CHECKOUT=1`: hand off on the feature
  branch after loading control's ticket; launch owns the return to main.

## PR

```yaml
title: Cover owner mentions in weekly usage reports
author: codex
author_evidence: The implement handoff records Codex as the actual implementer, including the owner-authorized
  composition-test repair. The configured ticket agent is claude; that assignment is not authorship evidence.
head: 7520b20675be5141e8e52ea6731b7f9330ac6d3f
base: 537352f8e50664ac657233ae69de6e6bdf2daf56
depth: skim
rationale: Bounded regression coverage and documentation for the owner-prefix fix already on main. The
  full suite and captured outbound payloads pass. Read the description for the authorized composition-test
  repair and verification limits; the completed Codex review is self-review, not independent review.
implementation: The producer reads the generated period ticket owner, falls back to cfg.current_user,
  and lets the unchanged Slack backend render the repository name and mapped mention or plain-name fallback.
  Main already contains ticket.py and ticket.md from state-publication commit a1d937e09, so the final
  five-file diff adds delivery-path regression coverage, aligns the posting instructions and important-destination
  topic/twin, and repairs the stale root-instructions assertion. Six captured-transport cases preserve
  the full report body, important route, one delivery attempt, and CLI bump after HTTP 503.
deviations: The owner explicitly authorized repair of the unrelated full-suite failure caused by expecting
  root CLAUDE.md after main standardized on AGENTS.md. It remains a separate commit. No review fixes or
  design changes were needed. Rebase removed the two producer paths already present on main from the PR
  diff.
limitations: 'No independent reviewer ran: both implementer and this fresh direct reviewer are Codex,
  recorded as self-review. Verification used Python 3.12.12; Python 3.11 and native Windows were not exercised.
  Per the ticket, Slack transport was stubbed: the actual outbound text was inspected in 80x24 and 120x40
  PTYs, without a live Slack post or Slack-client rendering check. The pre-existing missing task_path
  still prevents a Slack failure audit line; stderr and bump behavior remain intact, and the adjacent
  finding is retained for Retro.'
files:
  coga/skills/coga/usage-report/post/SKILL.md: Document period-owner selection, the shared repository/mention
    prefix, and the added shared task-IO dependency.
  docs/contexts/coga/important/SKILL.md: Describe the weekly report as identifying its repository and
    addressing the period owner through the existing mapping.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/important/SKILL.md: Keep the packaged important-destination
    topic byte-identical to its canonical owner.
  tests/test_usage_report.py: 'Run the generated period script through the real notification renderer
    with captured transport: mapped owner distinct from current user, missing-owner fallback, and unmapped
    owner, each on HTTP 200 and 503; retain end-to-end completion coverage.'
  tests/test_compose.py: Apply the owner-authorized stale CLAUDE.md test repair by checking the canonical
    shared AGENTS.md.
review:
  reviewer: codex
  kind: self
  status: passed
  head: 7520b20675be5141e8e52ea6731b7f9330ac6d3f
  base: 537352f8e50664ac657233ae69de6e6bdf2daf56
  detail: Direct review completed in this fresh peer-review session, with no must-fix findings. Read the
    initial seven-file change and the final five-file diff after rebase, checked owner resolution and
    delivery/bump behavior against the shared contracts, inspected the captured rendered text, and verified
    the authorized composition-test repair. No child reviewer or delegated agent was used.
checks:
- command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -rs > /tmp/coga-usage-report-owner-peer-pytest.log
    2>&1
  status: passed
  head: 7520b20675be5141e8e52ea6731b7f9330ac6d3f
  base: 537352f8e50664ac657233ae69de6e6bdf2daf56
  detail: 3808 passed, 7 skipped in 522.77s on Python 3.12.12, after rebase on the committed tree. Two
    skips require Windows job objects and five require native Windows PowerShell 5.1.
- command: 'stty cols 80 rows 24

    PYTHONPATH=/home/n/Code/coga/src .venv/bin/python /tmp/coga-usage-report-owner-peer-preview.py

    stty cols 120 rows 40

    PYTHONPATH=/home/n/Code/coga/src .venv/bin/python /tmp/coga-usage-report-owner-peer-preview.py'
  status: passed
  head: 7520b20675be5141e8e52ea6731b7f9330ac6d3f
  base: 537352f8e50664ac657233ae69de6e6bdf2daf56
  detail: Manual captured-transport runs in both PTY sizes used a generated period in an orbital-service
    fixture. Observed [orbital-service] [<@U02ADA>], missing-owner fallback [<@U01MARC>], and unmapped
    [stranger], with the report body intact. Each run attempted exactly one important-route post then
    one stubbed CLI bump, including HTTP 503. Synthetic IDs only; no live Slack messages. Captured payloads
    are in /tmp/coga-usage-report-owner-peer-preview.json.
- command: git diff --check origin/main...HEAD
  status: passed
  head: 7520b20675be5141e8e52ea6731b7f9330ac6d3f
  base: 537352f8e50664ac657233ae69de6e6bdf2daf56
  detail: No whitespace errors in the final five-file diff.
- command: cmp docs/contexts/coga/important/SKILL.md src/coga/resources/templates/coga/bootstrap/contexts/coga/important/SKILL.md
  status: passed
  head: 7520b20675be5141e8e52ea6731b7f9330ac6d3f
  base: 537352f8e50664ac657233ae69de6e6bdf2daf56
  detail: Canonical and packaged important-destination topics are byte-identical after rebase; the full
    suite also passed packaging checks.
- command: coga validate --json
  status: not-run
  detail: Configuration, workflow semantics, task layout, and validation behavior are unchanged. The full
    suite exercises the seeded repository, generated period, and CLI completion.
```
