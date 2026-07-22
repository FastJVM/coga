---
slug: redact-slack-webhook-credentials-from-request-fail
title: Redact Slack webhook credentials from request failures and Coga logs
status: active
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
- coga/codebase
- dev/code
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

Coga can persist a configured Slack incoming-webhook credential in plaintext
when a request fails before Slack returns a response. `env:SLACK_WEBHOOK_URL`
keeps the value out of `coga.toml`, but Coga resolves the environment variable
before calling Requests. A `requests.RequestException` can include the request
URL in its string representation; depending on the failure, that may be the
full URL or a parsed relative path beginning with `/services/`. That path is
credential-bearing too.

The notification sender currently interpolates the raw exception into both
stderr and the repo-global audit log:

- `src/coga/notification/slack.py:126-130` passes `str(exc)` to `fail`.
- `src/coga/notification/slack.py:112-117` writes that detail through
  `append_log`, so it can land in tracked `coga/log.md`.
- `src/coga/validate.py:1041-1044` repeats the same unsafe formatting in the
  Slack connectivity probe, exposing it in human or JSON validation output.

This is not merely noisy logging. Coga's automatic Git sync can commit and
push `coga/log.md`, turning a transient DNS, connection, timeout, TLS, or proxy
failure into durable credential exposure in repository history.

Evidence from the Magicator2 incident, recorded without copying the secret:

- A DNS failure rendered a Slack webhook path in Coga's failure output and
  repo-global log.
- Four credential-path occurrences are already reachable from Magicator2's
  `origin/main` history; the earliest observed commit is
  `6f86590a3a9f290f1217356174f32d4ef2689f9f` from 2026-07-14.
- The affected webhook must therefore be treated as compromised even if the
  current file is later redacted.

The existing regression coverage does not reproduce the dangerous shape.
`tests/test_notification.py:807-842` raises
`ConnectionError("no network")`, then checks that an exception class was
logged, but never supplies a URL-bearing Requests error or asserts that the
webhook credential is absent.

### Required behavior

1. Introduce one safe Slack request-error formatter/redaction boundary and use
   it for notification posting and validation probing. Audit other Slack
   webhook call sites, including the important-webhook path, rather than
   patching only the incident's caller.
2. Never emit a Slack webhook credential or credential-bearing `/services/...`
   path to stderr, `coga/log.md`, validation text, validation JSON, or another
   Coga-owned diagnostic surface.
3. Preserve useful, non-secret diagnostics: at minimum the exception class and
   a safe network category or message sufficient to distinguish common DNS,
   timeout, connection, proxy, and TLS failures where Requests exposes it.
4. Add realistic regressions for exceptions containing both a full webhook URL
   and only a relative `/services/...` path. Assert that a distinctive secret
   value is absent from every output and log surface, while the safe failure
   information and fail-loud exit behavior remain.
5. Cover both configured webhook fields (`webhook` and `important_webhook`) and
   keep existing notification/task-state semantics intact.
6. Add an operator-facing remediation note: rotate or revoke any exposed Slack
   webhook, redact the current tracked log, and inspect reachable Git history
   and other copies such as forks, clones, CI logs, and caches.

### Security and recovery boundary

Credential rotation/revocation is an external Slack administration action and
cannot be completed by this code change. A normal redaction commit also does
not erase earlier commits. Rewriting published Git history and force-pushing
must be a separate, explicitly approved and coordinated operation because it
is destructive for collaborators and still cannot retract existing clones or
logs. Do not automate either action as part of this ticket.

### Acceptance criteria

- Focused tests demonstrate that neither a full Slack webhook URL nor its
  `/services/...` credential path can escape through the post or probe failure
  paths.
- Safe error context remains visible and Slack failures still fail loudly.
- The Slack call-site audit and operational remediation steps are documented.
- The full test suite passes, and no real credential is added to fixtures,
  ticket text, test output, or commits.

### Out of scope

- Rotating or revoking the already exposed webhook on the operator's behalf.
- Rewriting or force-pushing Magicator2 history.
- Changing the Codex sandbox/JDK mount profile; that missing host mount
  triggered the observed network fallback but is a separate configuration
  issue from Coga's unsafe exception rendering.


## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
