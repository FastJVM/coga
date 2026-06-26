---
slug: first-run-works-without-slack-configured
title: First run works without Slack configured
status: done
autonomy: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts:
- relay/principles
- relay/sync
- relay/codebase
- relay/current-direction
- relay/roadmap
skills: []
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
---

## Description

A stranger who just ran `pipx install relay-os` and `relay init` must be able to
run real commands without configuring a Slack webhook. Today the shipped
first-run posture selects Slack by default: generated `relay.toml` contains
`[notification] channels = ["slack"]` plus
`[notification.slack].webhook = "env:SLACK_WEBHOOK_URL"`, and
`src/relay/notification/slack.py::SlackChannel.send()` exits when that env var
is unset. That makes a missing Slack setup a launch-blocking wall before a new
user has created their first task.

Design decision: make "no notification channels configured" the fresh-install
default, and make Slack an explicit opt-in. A fresh repo should ship with
`[notification] channels = []` and no active Slack webhook entry. Users turn
Slack on by selecting the Slack channel and configuring the webhook:

```toml
[notification]
channels = ["slack"]

[notification.slack]
webhook = "env:SLACK_WEBHOOK_URL"
```

This uses the notification abstraction that already exists rather than teaching
new users to opt out of Slack with `enabled = false`. Once Slack is selected,
Relay must keep the fail-loud contract: enabled Slack with no webhook, a
network failure, or a revoked/bad webhook exits non-zero and logs the failed
post when a task path is available.

## Acceptance Criteria

- Fresh `relay init` output does not require Slack or warn that Slack is
  required: with `SLACK_WEBHOOK_URL` unset, a newly initialized repo can run
  `relay draft`, `relay mark`, `relay launch`, and `relay bump` on a normal
  first task without a missing-webhook crash.
- Fresh template config makes the default obvious: generated
  `relay-os/relay.toml` has no selected Slack channel and no active
  `[notification.slack].webhook` entry.
- Explicit Slack opt-in stays fail-loud. If a repo selects Slack with
  `[notification] channels = ["slack"]` and Slack is enabled but the webhook
  resolves empty, live notification posts and `relay validate --check-slack`
  fail with an actionable error. Bad Slack HTTP responses and network failures
  continue to exit non-zero and append a `log.md` line when `task_path` is
  present.
- Existing opt-out behavior still works: `[notification.slack].enabled = false`
  suppresses Slack-channel posts to stderr without crashing for repos that have
  otherwise selected or configured Slack.
- Legacy compatibility remains deliberate: existing repos that already opt in
  via `[notification.slack]`, legacy `[slack]`, or bare `SLACK_WEBHOOK_URL`
  should continue to resolve Slack as they do today, with the existing
  deprecation notes.
- README/onboarding and Relay contexts describe Slack as optional on first run
  and show the exact opt-in snippet above.
- Tests cover both sides of the contract: fresh/no-Slack first-run commands do
  not crash, while selected-but-misconfigured Slack still fails loudly.

## Proposed Shape

1. Update notification config resolution in `src/relay/config.py`.
   - Keep an explicit `[notification].channels` list authoritative. An explicit
     empty list means no notification channels and `notification.post()` uses
     its existing no-channel stderr branch without crashing.
   - When `[notification].channels` is absent, infer Slack only from opt-in or
     compatibility evidence: a `[notification.slack]` table, a legacy `[slack]`
     table, or a bare `SLACK_WEBHOOK_URL` fallback. If none of those exists,
     resolve `cfg.notification_channels` to `()`, not `("slack",)`.
   - Keep `cfg.slack_enabled` defaulting to `True` for selected/configured
     Slack so enabled-but-missing-webhook remains loud.
   - Adjust the missing-webhook error text in
     `src/relay/notification/slack.py` and `src/relay/validate.py` so it points
     opted-in users at the Slack opt-in snippet and no longer describes Slack
     as globally required.
2. Update shipped templates and fixtures.
   - Change `src/relay/resources/templates/relay-os/relay.toml` so fresh repos
     ship with `[notification] channels = []` and a commented Slack opt-in
     example.
   - Keep the live repo copy `relay-os/relay.toml` and
     `example/relay-os/relay.toml` aligned with the new first-run posture unless
     there is a documented reason for one to differ.
3. Update docs and durable behavior contracts.
   - Update `src/relay/commands/init.py::_print_notification_state()` so the
     end-of-init guidance matches the new first-run posture instead of saying
     Relay requires Slack before `bump`/`panic`/`launch` will run.
   - In `README.md`, the install/onboarding path should say Slack is optional
     and only needed for team notifications; show how to opt in.
   - Update `relay-os/contexts/relay/sync/SKILL.md` and the packaged mirror at
     `src/relay/resources/templates/relay-os/bootstrap/contexts/relay/sync/SKILL.md`
     so "notifications required by default" becomes "notifications optional on
     first run; configured Slack fails loud."
   - Update the packaged CLI context at
     `src/relay/resources/templates/relay-os/bootstrap/contexts/relay/cli/SKILL.md`
     where it still says `relay draft` posts to Slack or Slack is required.
     Refresh the materialized bootstrap copy if needed for local parity.
4. Add focused regressions.
   - In `tests/test_config.py` or `tests/test_notification.py`, cover a repo
     with no notification table and no `SLACK_WEBHOOK_URL`: channels resolve to
     empty and `post(cfg, "...")` does not crash.
   - Keep/extend coverage proving `[notification] channels = ["slack"]` plus
     an unset `env:SLACK_WEBHOOK_URL` raises from the live post path and reports
     `slack-misconfigured` under `relay validate --check-slack`.
   - Add an init/onboarding smoke in `tests/test_init.py` or the nearest command
     test that initializes from the packaged template with `SLACK_WEBHOOK_URL`
     removed, then exercises `draft`, `mark`, `launch` (with the agent execution
     stubbed or otherwise isolated), and `bump` without a Slack crash.
   - Keep the existing bad-webhook regression in `tests/test_notification.py`
     intact so HTTP 404 / `no_service` still fails loud and logs.

## Out of Scope

- Building another notification backend or changing the pluggable notification
  architecture beyond the default-channel selection described here.
- Removing legacy `[slack]` or bare `SLACK_WEBHOOK_URL` compatibility paths.
- Adding a persistent "one-time hint" mechanism; no hidden state is needed for
  this narrow first-run blocker.
- Changing notification retry policy, Slack message formatting, digest
  semantics, owner/watcher mention behavior, or inbound Slack behavior.
- Weakening fail-loud behavior for any repo that has explicitly selected Slack.

## Context

RC release-gate blocker (see `relay/roadmap`). Pairs with
`improve-readme-and-doc` and `relay-cli-shipping` — all three are about a
stranger getting from install to first task without hitting a wall. Relates to
`rename-slack-to-a-notification-system-with-pluggab` (the bigger notification
refactor); this ticket is the narrow "don't block first run" slice, not that
refactor.

<!-- relay:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Design notes

- Read the ticket, `docs/vision.md`, and the relevant Relay contexts:
  `relay/principles`, `relay/architecture`, `relay/codebase`,
  `relay/current-direction`, `relay/project-stage`, `relay/roadmap`, and
  `relay/sync`.
- Investigated the live implementation. The first-run wall comes from
  `src/relay/config.py`: channels default to `("slack",)` and Slack enabled
  defaults to `True`; `src/relay/notification/slack.py::SlackChannel.send()`
  exits when selected/enabled Slack has no webhook.
- Design decision recorded in `ticket.md`: fresh installs should have no
  selected notification channel (`[notification] channels = []`), and Slack
  becomes explicit opt-in. Selected Slack still fails loud on missing, revoked,
  or unreachable webhooks.
- Required implementation touchpoints named in the ticket: `config.py`,
  `notification/slack.py`, `validate.py`, packaged/live/example `relay.toml`,
  README, `relay/sync` live+packaged contexts, packaged `relay/cli` context,
  and focused tests around no-Slack first run plus fail-loud opt-in.
- Review-design pass found one missing onboarding touchpoint: `relay init`
  currently prints `_print_notification_state()` guidance that says Relay
  requires Slack before `bump`/`panic`/`launch` will run. Added that to the
  acceptance criteria/proposed shape; otherwise the design is ready to hand to
  implement.

## Open Questions

None. The design step chose the default posture: no notification channels by
default, Slack opt-in, configured Slack remains fail-loud.

## Dev

- branch: `first-run-no-slack`
- worktree: `/home/n/Code/codex/relay-first-run-no-slack`
- based on `main` (826b1e9).
- pr: https://github.com/FastJVM/relay/pull/394

### Implementation plan / decisions

- `config.py::_resolve_notification_channels`: explicit `channels` list
  (including empty) stays authoritative. When the key is absent, infer Slack
  only from opt-in evidence — a `[notification.slack]` table, a legacy
  `[slack]` table, or a bare `SLACK_WEBHOOK_URL` env var (new helper
  `_slack_opt_in_present`). No evidence → `()`, not the old `("slack",)`
  default. Call site now also passes the legacy `[slack]` tables.
- `slack.py` / `validate.py`: reword the missing-webhook errors so they say
  Slack is *selected* and misconfigured (not globally required), and point at
  removing slack from channels / setting the webhook / opting out.
- Templates: packaged `relay.toml` ships `[notification] channels = []` with a
  commented opt-in example. Decision on the other two:
  - `example/relay-os/relay.toml`: align to first-run posture (`channels = []`,
    commented opt-in) — it is the seeded fixture, should represent a fresh
    install. Conftest's autouse `_stub_slack` sets `SLACK_WEBHOOK_URL`, so any
    test exercising the example still infers Slack via env evidence; explicit
    `channels = []` overrides that, so verify example-driven tests still pass.
  - live `relay-os/relay.toml`: this team actually uses Slack (has a
    `[notification.slack.users]` table). Documented reason to differ — keep it
    opted in. Dropping the now-redundant explicit `channels = ["slack"]` line
    is fine since the `[notification.slack]` table infers Slack, but keeping it
    explicit is clearer for an opted-in repo. Decision: keep explicit.
- `init.py::_print_notification_state`: stop saying Slack is required before
  bump/panic/launch; say notifications are optional on first run and show the
  opt-in snippet.
- Contexts: `relay/sync` (live + packaged) and packaged `relay/cli` — reflect
  "optional on first run; configured Slack fails loud."
- Tests: no-table+no-env → empty channels + post no-crash; keep the
  selected-but-missing-webhook crash + validate `slack-misconfigured`; init
  smoke without `SLACK_WEBHOOK_URL`.

### Implemented (commit 9907eb2 on `first-run-no-slack`)

- `config.py`: `_resolve_notification_channels` now takes the legacy `[slack]`
  tables and, when no `channels` key exists, returns `()` unless
  `_slack_opt_in_present` finds evidence (new/legacy slack table or bare env).
- `slack.py` + `validate.py`: missing-webhook errors reworded to "Slack is
  selected … but no webhook" + remove-from-channels option (no longer "Relay
  requires it").
- Packaged + example `relay.toml`: `[notification] channels = []` with a
  commented opt-in snippet. Live `relay-os/relay.toml` kept opted in
  (`channels = ["slack"]`) — documented reason: this team uses Slack and has a
  `[notification.slack.users]` table.
- `init.py::_print_notification_state`: now a ✓ "optional on first run" banner
  with opt-in snippet; dropped the unused `local_toml` param.
- Contexts: live + packaged `relay/sync` ("optional on first run; configured
  Slack fails loud") and packaged `relay/cli` ("Slack is required" lines
  removed). Live `bootstrap/` mirror left for `relay init --update` to
  regenerate (gitignored).
- Tests added: 3 in `test_notification.py` (no-config→(), table-infer,
  env-infer), 1 in `test_validate.py` (slack-misconfigured when selected
  without webhook), 1 in `test_init.py` (packaged-template first-run smoke).

### Verification

- `python3.12 -m pytest` (3.11+ via PYTHONPATH): 777 passed, 1 skipped, plus my
  new tests pass.
- 2 pre-existing failures in `test_autoclose_sweep.py`
  (`..._creates_idempotently`, `..._live_and_packaged_copies_stay_in_sync`) are
  NOT mine — confirmed they fail identically on pristine base main (826b1e9).
  Cause: a date-sensitive `last_serviced_period: 2026-06-17` (today) baked into
  the committed live autoclose blackboard. Out of scope for this ticket.
- `relay validate` against `example/relay-os` (now `channels = []`): All good.
