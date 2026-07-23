---
slug: op/let-notification-webhooks-resolve-1password-refere
title: Let notification webhooks resolve 1Password references
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
    requires: pr
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 1 (implement)
---

## Description

Let `[notification.slack].webhook` and `important_webhook` accept an
`op://vault/item/field` reference, the same way a ticket's `secrets:` entries
already do. Today they understand only `env:VAR`.

The payoff is that a repo running unattended needs no secret plumbing of its
own. It puts the two references straight in its `coga.toml`, and the runner
only needs `OP_SERVICE_ACCOUNT_TOKEN` in its environment.

## Context

### Why it matters — the current workaround, per repo

An unattended `coga recurring` performs its own state transitions: it creates
the period task, activates it, launches it, and (for a script step exiting 0)
advances the step or marks it done. Each of those posts to the primary webhook,
and a post with no webhook resolved is fail-loud — `notification/slack.py:94`
writes the config error and exits 1. So a runner with no `SLACK_WEBHOOK_URL`
crashes on the first create/activate, before any scheduled work runs.

`[notification.slack].enabled = false` is not an escape hatch: that check sits
*before* `webhook_for`, so it suppresses `--important` too — which is usually
the whole reason for the run.

Every repo therefore has to hand its runner the URLs some other way. The
patents repo's answer (`repo/headless-secrets-service-account`) is an `op.env`
of references plus an `op run --env-file=coga/op.env -- coga …` wrapper. It
works, but it is a file and a wrapper per repo, and this repo's own
`coga/recurring/` set (dream, digest, branch-sweep, blocker-reminders, …) will
need the identical pair the day it runs unattended. Second customer, same
workaround.

### Where the gap is

All three webhook resolution sites — `config.py:874`, `883` (primary, current
and legacy tables) and `915` (important) — funnel through
`_resolve_secret_value` (`config.py:1151`), which handles only the `env:`
prefix and passes anything else through as a literal. So an `op://` value there
is treated as a webhook URL and POSTed to nothing.

`_resolve_op_reference` (`config.py:1234`) already exists in the same module
and already shells out to `op read` with the right fail-loud behavior (names
the key and reference, never the value). The architecture context names prefix
dispatch in `config.py` as the sanctioned seam for reference providers, so this
is an extension of an existing pattern rather than a new mechanism.

### The design problem — do not resolve at config-load time

`_resolve_secret_value` is called while loading config, which happens on
**every** coga command. Naively adding `op://` there would put an `op read`
subprocess and a 1Password round-trip in front of `coga status`, `coga show`,
and `coga validate`, and would make config load fail or hang whenever `op` is
missing or signed out.

That directly violates principle 6, which names `status` / `show` / `validate`
as commands that must not hit the network as a side effect of reading. So the
resolution has to be **lazy** — performed when a post is actually about to be
sent, not when config is read — or cached behind something equivalent. Working
out that shape is the substance of this ticket; the prefix branch itself is
small.

### Scope

- In: `op://` support for both webhook keys, lazy/deferred resolution, fail-loud
  errors that never name the value, tests, and a docs note.
- Out: changing ticket `secrets:` (already works), the reserved `COGA_` prefix
  rule (`config.py:1211` — intentional, keep it), and any per-repo config.

### Downstream

`patents` → `repo/headless-secrets-service-account` builds the `op.env` +
wrapper workaround. If this lands first, that ticket shrinks to "put the token
on the runner and point `coga.toml` at the two `op://` references." Not a
blocker in either direction — deleting the workaround later is a minute's work.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
