---
slug: coga-important/add-coga-slack-important
title: add-coga-slack-important
status: blocked
owner: zach
human: zach
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
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 1 (implement)
---

## Description

Add `--important` to `coga slack` so any script can post a human-action
notification to `coga-important`. It posts through the second webhook and @'s
the recipient set in coga.toml instead of the ticket owner.

## Context

- `coga slack` is `src/coga/commands/slack.py`; it calls `post` in `src/coga/notification/__init__.py`.
- `render_text` in `src/coga/notification/slack.py` builds the `[project] [@owner]` prefix.
- `--important` replaces the owner mention with the recipient; every post is tagged.
- The mention already renders as a real ping through `[notification.slack.users]`.
- The message carries the ticket slug, as `coga slack` already does.
- Depends on `coga-important/support-second-webhook` and `coga-important/add-toml-property-for-notification-recipient`.
- First consumer is the patents repo `repo/utility/maintenance-fee-sweep`.

<!-- coga:blackboard -->

## Correction: `--important` is on a branch, not on main (2026-07-16)

An earlier note here said the `--important` flag "landed in PR #553". It did not
land — **PR #553 (`important-webhook`) is OPEN**, opened 2026-07-15 22:20Z, and its
own ticket `coga-important/support-second-webhook` sits at `step: 4 (review)`
waiting on the owner. "Landed" reads as merged and would send the next agent to
branch from main and find nothing. `grep -rn important src/` on main returns only
unrelated prose hits.

What exists, and where:

- `coga slack --important`, `post(..., important=True)`,
  `SlackChannel.webhook_for(important=)`, `slack_important_webhook`,
  `_ALLOWED_LEGACY_SLACK_KEYS` — **only on `origin/important-webhook`** (#553).
- `important_recipient` — **nowhere**. Not on main, not on `important-webhook`,
  not on `important-context`; only in task/context planning prose. Independently
  spot-checked by the codex peer-review on `coga-important/context`.

## Blocked: both halves need work that isn't on main

Neither half of this ticket can be built from main:

- **Alert message shape** needs the `--important` flag to exist. It doesn't, on main.
  The change also lands in `render_text` / `send` — the exact hunks #553 rewrites.
- **Recipient mention** needs `[notification.slack].important_recipient`, owned by
  `coga-important/add-toml-property-for-notification-recipient`. That ticket is
  `status: blocked` on the same #553, with no branch and no code written.

So this ticket sits one level further downstream than its sibling: even if #553
merged now, the recipient half would still wait on the sibling's implementation.

The owner already answered this exact question on the sibling (2026-07-15,
option 1): wait for #553 to merge, then implement from main — don't stack on
`important-webhook`, don't duplicate the split. That reasoning applies here
unchanged (repo squash-merges; `open-pr` hardcodes `--base main` at
`coga/skills/code/open-pr/recipe.py:143` and fails loud on drift from the control
branch). Blocking rather than re-litigating it.

One action unjams all three tickets: review and merge #553.

## Order to implement, once unblocked

1. #553 merges → main has `--important` and `webhook_for`.
2. `add-toml-property-for-notification-recipient` implements `important_recipient`
   (its blackboard records the ready-to-implement shape).
3. This ticket spends both: give `--important` its own alert shape and @ the
   recipient instead of the ticket owner.

## Production notes

Message shape — from the 2026-07-15 rehearsal, which posted through the existing
`coga slack` path into the live channel:

```
coga APP  [coga] [@zach] 💬 claude on coga-notifications/create-coga-notification-channel
          "create-coga-notification-channel": dress rehearsal
```

That is the FYI shape and it is wrong for an alert. Nobody is "on" a maintenance-fee
alert, the `[coga]` prefix repeats the app name, and the title repeats the slug.
`--important` needs its own shape, closer to:

```
[@zach] ⚠️ patent-fake-widget #9999999 — Window 2 fee not recorded, closes 2027-01-15
```

Testable offline — `tests/test_notification.py` fakes the webhook with
`monkeypatch.setattr("coga.notification.slack.requests.post", fake_post)` and asserts
on the captured payload. Cover: `--important` posts to the second webhook, a bare
post still goes to `webhook`, and the recipient mention renders as `<@UID>`.

---

## Blockers

- [ ] [2026-07-15 18:39] [agent:claude] id=20260715T183957 Depends on unmerged PR #553 (support-second-webhook) and on the unimplemented sibling coga-important/add-toml-property-for-notification-recipient. Neither half is buildable from main: the alert-message-shape half needs the 'coga slack --important' flag, which exists only on the open important-webhook branch; the recipient half needs [notification.slack].important_recipient, which exists nowhere (the sibling that owns it is itself status:blocked on #553, no branch, no code). #553 is OPEN at its ticket's step 4 (review) awaiting your review. Owner already chose option 1 on the sibling (2026-07-15): wait for #553 rather than stack or duplicate; same reasoning applies here. Unblock with 'coga unblock add-coga-slack-important --answer "#553 merged and important_recipient landed"' once both land.

## Usage

{"agent":"claude","cache_creation_input_tokens":215853,"cache_read_input_tokens":1416042,"cli":"claude","input_tokens":54,"model":"claude-opus-4-8","output_tokens":22161,"provider":"anthropic","schema":1,"session_id":"aa887cda-0316-48e2-9e26-74eb8cf67744","slug":"coga-important/add-coga-slack-important","step":"implement","title":"add-coga-slack-important","ts":"2026-07-16T01:40:00.901989Z","usage_status":"ok"}
