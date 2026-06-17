---
title: Slack post ignores HTTP response so bad webhook fails silently
status: active
mode: interactive
owner: nick
human: nick
agent: codex
assignee: codex
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
step: 1 (implement)
---

## Description

Priority: HIGH. This is the most plausible root cause of the standing
"Slack notifications not firing in practice" bug (current-direction bug #1).

`slack.post` does `requests.post(cfg.slack_webhook, json=payload, timeout=5)`
and **ignores the response entirely** (`slack.py:97`). `requests` only raises on
transport errors, not on 4xx/5xx. A revoked / expired / wrong incoming-webhook
URL returns HTTP 404 or a `no_service` body — no exception is raised, so Relay
believes the post succeeded and the message is silently dropped. Every state
transition appears to "work" while nothing reaches Slack.

The classification logic already exists: `validate.probe_slack`
(`validate.py:765`) inspects the response and reports `revoked` on 404/
`no_service`. The live `post()` path should reuse it.

Fix: check `resp.status_code` (and Slack's text body) after the POST; on a
non-OK response, log to the task's `log.md` and raise `typer.Exit(1)` the same
way the missing-webhook branch already does, with a message that distinguishes
"revoked/invalid webhook" from "transient network error." Reuse / share the
`probe_slack` classification rather than duplicating it.

Acceptance: posting to a revoked or 404 webhook fails loud (non-zero exit +
clear message + `log.md` line), not silently; a new test in `test_slack.py`
covers a 404/`no_service` response (the current suite almost certainly mocks
`requests.post` and never exercises this).

## Context

Code: `src/relay/slack.py` (`post`, ~44-106; the ignored POST at :97),
`src/relay/validate.py:765` (`probe_slack`, the classifier to reuse),
`tests/test_slack.py`. Related: this likely closes the practical half of the
"Slack not firing" investigation in current-direction.
