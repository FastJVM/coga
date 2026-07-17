---
slug: important-alerts-the-task-owner-drop-important-rec
title: important alerts @ the task owner; drop important_recipient
status: draft
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

Remove the `[notification.slack].important_recipient` config key. Important
Slack alerts @ the task owner, which is already how `render_text` behaves, so
no renderer change is needed. Update the `coga/sync` and `coga/important`
contexts to describe owner-based triage instead of a configured recipient.

## Context

`important_recipient` shipped in #575 but nothing in the renderer reads it —
main already @'s the ticket owner via `mention(cfg, owner)`. PR 578 would have
wired the key in and added a `⚠️` alert prefix; both are dropped, so close
PR 578 as part of this. Config loading fails loud on unknown keys, so the key
must be purged from the `coga.toml` template and the live `coga/coga.toml` in
the same change or the next command crashes. Keep the live `coga/contexts/`
copies and the packaged `src/coga/resources/templates/coga/` copies in sync.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Evaluator review

Verified against the code. The core premise is correct: `slack_important_recipient` is resolved in `config.py` (field, `_resolve_notification_slack_important_recipient`, `_ALLOWED_SLACK_KEYS` entry) but has **zero consumers** — the only non-config references are `tests/test_notification.py` and the `coga/sync` doc. `render_text` (`src/coga/notification/slack.py:39-40`) already `@`'s `owner`, and `commands/slack.py:58` passes `owner=ticket.owner or cfg.current_user`. So "no renderer change needed" holds.

1. **Description clarity.** Good on the *what* (remove the key; owner-mention already the behavior; update two contexts). The weak spot is removal *depth*: "remove the config key" plus a Context line about purging "the coga.toml template and the live coga/coga.toml" reads like a template-only edit. A shallow agent could delete two TOML lines and stop. The Config field, the resolver, and the `_ALLOWED_SLACK_KEYS` entry in `config.py`, plus the whole `important_recipient` test block (`tests/test_notification.py:628-712`), are all discoverable by grepping `important_recipient`, and peer-review + the test run will catch a partial — but the ticket doesn't say "config surfaces, not just templates."

2. **Workflow fit.** `code/with-review` fits. This is a deletion touching an allow-list and its tests; an other-agent peer-review plus `python -m pytest` is exactly the safety net you want for "did you find every reference." No mismatch. The only non-code item is "close PR 578," a GitHub action outside the implement step — fine to fold in, just note it isn't a code edit.

3. **Empty `contexts:`.** Should not be empty. `coga/sync` is the authoritative map of the config surfaces being deleted (it names `cfg.slack_important_recipient` and the resolver at `SKILL.md:236-254`), and it's also an edit target. Attaching `coga/sync` (and `coga/important`) to `contexts:` front-loads the surface list rather than making the agent rediscover it — this matches the repo's own rule that world-facts the agent needs go in `contexts:` frontmatter. Note the two contexts currently *over-claim*: `coga/sync` states the recipient is `@`'d "in place of the ticket-owner mention" as if live, which was never wired — so the update is well-motivated. (`coga/important:32` already hedges with "once that sibling config work lands.")

4. **Scope.** One PR. All edits serve removing one key: `config.py`, one test section, two `coga.toml` comment blocks (live + template), and two contexts × two copies each (sync + important, live + packaged). Cohesive, not bundled.

5. **Assumptions to question — two real ones:**

- **The `important_webhook` guardrail is missing and is the biggest risk.** `important_recipient` and `important_webhook` sit adjacent everywhere — neighboring Config fields, neighboring `_ALLOWED_SLACK_KEYS` entries, adjacent resolvers, adjacent `coga.toml` comment blocks, adjacent `coga/sync` bullets. An agent doing bulk deletion can easily over-delete the webhook. `important_webhook` is **actively consumed** by `webhook_for` (`slack.py:65`) and must stay. The ticket implies the distinction ("wire the key in") but never states "remove `important_recipient` only; leave `important_webhook`." Add that sentence to Context — it's a scope boundary, so it belongs in the ticket.

- **The "fails loud → purge template or crash" reasoning is inaccurate.** In both the live `coga/coga.toml:68` and the template `resources/.../coga.toml:89`, `important_recipient` appears **only as a commented example**, not an active key. TOML comments aren't parsed, so removing them prevents no crash, and leaving them causes none. The actual crash risk runs the other way: once the allow-list entry is gone, any coga.toml with an *active* `important_recipient = …` line (a downstream repo, or someone's `coga.local.toml`) fails config load. That real risk isn't mentioned; the stated one doesn't exist. Recommend rewording, and flagging the downstream/local check.

6. **Factual / missing.** Otherwise accurate. One uncalled surface: the comment at `config.py:401-406` uses `important_recipient` as an example of why the legacy/current key-sets are kept distinct — it should be updated when the key goes, or it'll dangle. Minor and grep-discoverable, but a peer-reviewer will flag it. The "keep live and packaged copies in sync" instruction is correct and load-bearing (four context files: sync + important, live + packaged, all currently identical).
