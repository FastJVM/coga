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
