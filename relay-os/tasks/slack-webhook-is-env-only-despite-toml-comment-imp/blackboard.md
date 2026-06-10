The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev
branch: slack-webhook-toml
worktree: ../relay-slack-webhook-toml
pr: (pending — opens in code/open-pr step)
commit: c22b09a

## Peer review

- `codex review --base main` ran from `../relay-slack-webhook-toml` after the
  sandboxed attempt hit `failed to initialize in-process app-server client:
  Read-only file system`.
- Must-fix finding: README still documented the old env-only Slack webhook
  setup, so users of older/minimal configs could export `SLACK_WEBHOOK_URL`
  without adding `[slack].webhook` and remain unconfigured.
- Fixed in commit `c22b09a`: README now documents
  `webhook = "env:SLACK_WEBHOOK_URL"` as the setup path, says the bare env var
  is not enough, and includes the older/minimal repo migration note.
- Verification after peer-review fix: `python -m pytest -q` from the feature
  worktree -> `634 passed, 1 skipped`.

## Implement done (step 1)

- Committed on branch `slack-webhook-toml`. Full suite green:
  `635 passed` (PYTHONPATH=<worktree>/src <venv>/bin/python -m pytest).
- `relay validate --json` against `example/relay-os` → `issues: []`.
- Verified `env:` indirection resolves at runtime, and template/example/live
  `relay.toml` all parse as valid TOML.

Notable catch beyond the ticket's listed touchpoints: this repo's OWN
`relay-os/relay.toml` had no `[slack].webhook` key (only `[slack.gifs]` /
`[slack.users]`). Under the new contract the relay team's own posts would have
gone silent, so I added `webhook = "env:SLACK_WEBHOOK_URL"` there too. Code +
this config land in the same PR, so there's no window where the loader requires
the key but the config lacks it.

Test-fixture blast radius: every test repo that posts live now declares
`[slack].webhook`. Added it to ~17 fixtures (conftest git repo + per-file `repo`
fixtures), inserted at fresh-TOML-block boundaries so blocks already carrying
`[slack.*]` config were untouched. `test_validate` left alone — it appends its
own `[slack]` table at runtime to drive the probe.

## Implement plan & decisions

Settled design (per ticket + evaluator): make `[slack].webhook` the single
canonical, TOML-backed way to configure the webhook. The bare process env var
is no longer an independent source — `SLACK_WEBHOOK_URL` only reaches relay when
referenced via `webhook = "env:SLACK_WEBHOOK_URL"`.

Changes:
- `config.py`: `slack_webhook` now from `_resolve_slack_webhook(shared, local)`
  (local overrides shared, `env:` resolved like secrets via a shared
  `_resolve_secret_value` helper). Unset env / empty literal → `None`.
- `slack.py` / `validate.py` / `init.py`: "not configured" messaging points at
  `[slack].webhook`, not the bare env var.
- `example/relay-os/relay.toml`: active `webhook = "env:SLACK_WEBHOOK_URL"` line
  (no commented no-op). Template `relay.toml` + `relay/sync` context (project-local
  and source-template copies) updated to document the TOML-backed contract.
- Tests: replaced the two "TOML webhook ignored" tests with the new contract;
  added `webhook` to shared fixtures.

## Bootstrap notes

- Attached `workflow: code/with-review` to the draft ticket per human direction.
- Applied evaluator recommendations: narrowed the ticket to the TOML-backed webhook contract, attached `relay/sync`, `relay/codebase`, and `dev/code`, refreshed stale code/example pointers, and made the durable context/template touchpoints explicit.
- Corrected `assignee:` to `claude` after activation. The frozen `code/with-review` workflow is at `step: 1 (implement)`, whose assignee token is `agent`; this ticket's `agent:` is `claude`.

## Evaluator review

**Review**

The ticket is understandable, but not quite launch-ready. The concrete bug is clear: [ticket.md](/home/n/Code/relay/relay-os/tasks/slack-webhook-is-env-only-despite-toml-comment-imp/ticket.md:19) says the loader reads only `SLACK_WEBHOOK_URL`, while the fixture config implies `[slack].webhook`. However, [ticket.md](/home/n/Code/relay/relay-os/tasks/slack-webhook-is-env-only-despite-toml-comment-imp/ticket.md:28) asks the agent to “pick one,” which leaves a product/config decision to the implementer.

### Findings

- **Objective / Done — GAP:** Acceptance allows two materially different designs. Two agents could both pass “make it consistent” while choosing opposite config contracts.
  **Recommendation:** Decide before launch: either “keep webhook env-only; remove stale TOML example and update docs/tests” or “support `[slack].webhook = "env:SLACK_WEBHOOK_URL"` as the canonical path.”

- **Knowledge — GAP:** `contexts: []` is missing the focused context. `relay/sync` already states the current contract: `$SLACK_WEBHOOK_URL` is the only webhook location and Relay never reads it from `relay.toml`.
  **Recommendation:** Attach `relay/sync`, `relay/codebase`, and `dev/code`. Add `relay/project-stage` only if choosing a breaking config change and you want the no-backcompat posture in prompt.

- **Context Placement — GAP:** If option (a) changes the webhook contract, the durable explanation belongs in `relay/sync`, not only the ticket or PR. If option (b) wins, `relay/sync` already has the right durable fact and the ticket should say the fixture drift is the target.
  **Recommendation:** Add a line: “If the webhook contract changes, update `relay-os/contexts/relay/sync/SKILL.md` and the packaged template copy; otherwise keep `relay/sync` unchanged and fix only stale examples.”

- **Facts — GAP:** The referenced example path is imprecise. The stale comment is in `example/relay-os/relay.toml:28-30`; the packaged template at `src/relay/resources/templates/relay-os/relay.toml` already documents env-only Slack setup.
  **Recommendation:** Replace `example/.../relay.toml:29-30` with exact paths and note whether the packaged template is intentionally already correct.

- **Scope — GAP:** Option (b) is a fixture/docs cleanup. Option (a) touches config parsing, secret resolution semantics, docs/templates, tests that currently assert TOML webhook is ignored, and probably init/validate wording.
  **Recommendation:** Narrow scope before launch, or switch to `code/design-then-implement` if the agent is meant to choose the config design.

### Workflow Fit

`code/with-review` fits once the product decision is made: this is a code/config/docs/test change with peer-review value. As written, `code/design-then-implement` would fit better because the first real task is deciding the contract, not implementing it.

### Assumptions To Question Before Launch

- Is `[slack].webhook` actually meant to become supported, or is env-only the intended security boundary?
- If TOML support is added, is a literal URL allowed, or only `env:` indirection?
- If both env var and TOML are present, which wins?
- Should webhook config live in shared `relay.toml`, machine-local `relay.local.toml`, or both?
- Should this launch wait for or coordinate with the active notification rename ticket, since that ticket changes the Slack config surface?
- Is the user-facing trap real in shipped templates, or only in the `example/` fixture?
