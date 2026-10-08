---
title: webhook for slack is public
status: draft
owner: nicktoper
workflow: maintenance/with-approval
---

## Description

Rotate the coga Slack state-transition webhook, because its full URL is
public. Before the redaction fix in PR #629 (2026-07-22), failed Slack posts
logged the raw `requests` ConnectionError, and that text contains the URL path
(hook id `B0B0KD0BTQB` plus its secret). Twenty-four such lines, written
2026-06-23 to 2026-07-11, sit in `coga/log.md` on `origin/main` of the
**public** `FastJVM/coga` repo and in its git history. Anyone can post into
the channel until the URL is revoked.

Done means all of the following:

- A new webhook is live, and every place that exported the old URL now
  exports the new one.
- `coga validate --check-slack`, run from a fresh login shell in both
  `/home/n/Code/coga` and `/home/n/Code/thinkpick`, reports no
  `slack-revoked`, `slack-unreachable`, or `slack-misconfigured` issues.
  Unrelated validate errors don't count, so judge the Slack issues, not the
  exit code.
- After that, the old webhook is revoked in Slack, and a probe of it is
  classified `revoked` (HTTP 404 / `no_service`).
- A pattern scan for `hooks.slack.com/services/` and
  `/services/T[A-Z0-9]+/B[A-Z0-9]+/` across tracked files finds nothing new
  beyond the known historical `coga/log.md` lines and the fake test URLs.

## Context

- **Which webhook leaked:** `SLACK_WEBHOOK_URL`, the state-transition
  channel. As of authoring it is exported from `~/.bashrc` and still contains
  the leaked hook id `B0B0KD0BTQB`. `COGA_IMPORTANT_WEBHOOK_URL`
  (`important_webhook`, the coga-important channel) does not appear in the log
  and is out of scope unless the inventory finds it exposed.
- **Who reads it:** `coga/coga.toml` (`webhook = "env:SLACK_WEBHOOK_URL"`) and
  `/home/n/Code/thinkpick/coga/coga.toml` (same variable; public repo, but it
  holds no copy of the URL). The tablet repo has Slack commented out.
- **Inventory bounds:** check this machine's shell rc and profile files,
  `coga.local.toml` in both repos, and GitHub Actions secret *names* for
  `FastJVM/coga` and `FastJVM/thinkpick` (`gh secret list`; values are
  unreadable). Then ask the owner about other machines and 1Password items.
  The agent cannot see those itself. Moving the URL into 1Password via an
  `op://` ref is optional; `coga/secrets` (`docs/contexts/coga/secrets/SKILL.md`)
  is cited here, not attached.
- **How the workflow runs:** this is `maintenance/with-approval`. The
  inventory step proposes the rotation plan, and the approve step is the
  owner signing off on it. In `cleanup-and-verify`, the **owner** performs the
  secret actions and the agent only verifies, pausing between phases to ask the
  attending owner. Order matters, so there's no notification gap:
  1. The owner creates the new webhook in Slack.
  2. The owner updates every exporter.
  3. The agent verifies the new webhook is live.
  4. The owner revokes the old webhook.
  5. The agent probes the old URL.
- **Secret handling:** never ask for the new URL in chat, the ticket, or the
  blackboard, and never print either URL. Check the env var with a silent
  boolean, e.g. `bash -lc '[[ $SLACK_WEBHOOK_URL == *B0B0KD0BTQB* ]] && echo
  still-old || echo rotated'`. Run every verification in a fresh login shell,
  because the agent's own env is stale after `~/.bashrc` changes.
- **Probing the old URL after revocation:** after rotation, the only copy is
  the historical lines in `coga/log.md`. Rebuild the URL from them inside a
  script, POST an empty JSON payload, and pass the status and body to
  `slack_response.classify_slack_response`. Print only the classification,
  never the URL.
- **The code is already fixed:** `slack_response.format_slack_request_error`
  logs only a fixed category (e.g. `ConnectionError: DNS/name-resolution
  failure`), and `slack_response.redact_slack_webhook_credentials` covers
  response bodies. Do not change code for this ticket.
- **Explicitly out of scope:** redacting the old lines in `coga/log.md`
  (append-only; the URL is dead once revoked) and rewriting git history.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
