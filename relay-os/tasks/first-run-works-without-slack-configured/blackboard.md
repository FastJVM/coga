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
