---
title: webhook for slack is public
status: in_progress
owner: nicktoper
workflow:
  name: maintenance/with-approval
  steps:
  - name: inventory
    skills: []
    assignee: agent
  - name: approve
    skills: []
    assignee: owner
  - name: cleanup-and-verify
    skills: []
    assignee: agent
step: 2 (approve)
agent: claude
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

## Inventory (step: inventory, 2026-10-08)

All checks were read-only and printed only counts and booleans. No URL value was printed or recorded.

### Exporters of `SLACK_WEBHOOK_URL` on this machine
- `~/.bashrc:150` `export SLACK_WEBHOOK_URL=...` is the **only** exporter found. It still holds the leaked id (`still-old` in a fresh login shell and an interactive shell). `~/.profile` sources `~/.bashrc`.
- `~/.bashrc:151` exports `COGA_IMPORTANT_WEBHOOK_URL`. It is a *different* hook, not the leaked id, and appears in no log. Out of scope.
- No other exporters: `~/.profile`, `~/.bash_profile`, `~/.zshrc`, `~/.bash_aliases`, `/etc/environment`, `~/.config/environment.d`, systemd user units and crontab hold nothing. The `~/.config` tree has no copy of the id.
- `coga.local.toml` in coga and thinkpick has no Slack keys. `tablet/coga/coga.local.toml` sets `webhook = "env:SLACK_WEBHOOK_URL"` (no literal), but tablet `coga.toml` has `channels = []`, so it is inert.

### Consumers (all read the env var; none store a literal)
- `coga/coga.toml` and `thinkpick/coga/coga.toml`: `webhook = "env:SLACK_WEBHOOK_URL"`. Both repos are PUBLIC and the in-scope validate targets.
- **Also found:** `xpllm/coga/coga.toml` (FastJVM/xpllm, PRIVATE) and `magicator/coga/coga.toml` (manycore-com/magicator2, PRIVATE, `channels=["slack"]`) use the same env var. They pick up the new URL from `~/.bashrc` automatically.
- tablet: the local toml points at the var but the channel is disabled.

### GitHub Actions secrets (names only)
- FastJVM/coga: none. FastJVM/thinkpick: none. FastJVM/xpllm: none.
- **manycore-com/magicator2: `SLACK_WEBHOOK_URL` (set 2026-02-26).** The value is unreadable. It may be the leaked hook, so the owner must confirm.
- FastJVM org secrets: 403 (needs an org admin). The owner should check.

### Exposure (where the full secret sits; out of scope to redact)
- FastJVM/coga (PUBLIC) `coga/log.md`: 24 lines with the full URL, all hook `B0B0KD0BTQB`, with no other hook ids. Same count on `origin/main`. The local clones `~/Code/claude/coga`, `~/Code/codex/coga` and `.coga/worktrees/build-week-readme.*` mirror it.
- **Additional exposure, not in the ticket:** FastJVM/xpllm `coga/log.md` (16 lines, plus 13 in each of 2 coga worktrees) and manycore-com/magicator2 `coga/log.md` (14 lines). Both repos are private, but anyone with read access can see the URL. Revocation neutralizes all of these, so no extra action is proposed beyond noting it.
- About 182 Codex and 8 Claude session transcripts under `~/.codex` and `~/.claude/projects` contain the id. They are local only and become dead once revoked.
- thinkpick and tablet: no tracked copies.
- Tracked-file scan in coga: besides `log.md`, the hits are this ticket's prose (pattern only, no secret), `docs/.../notifications/failures/SKILL.md` and its packaged twin, and tests. All of them are fake `TFAKE/BFAKE` or placeholder URLs, and 0 contain the leaked id.

### Proposed action list (each item can be approved separately)
Owner actions are marked [O] and agent verification is marked [A]. Run them in order.
1. [O] Create a new incoming webhook in Slack for the same state-transition channel. Do not paste it anywhere in chat or the ticket.
2. [O] Replace the value at `~/.bashrc:150` with the new URL. Leave line 151 (`COGA_IMPORTANT_WEBHOOK_URL`) untouched.
3. [O] If the magicator2 Actions secret `SLACK_WEBHOOK_URL` is the old hook (the owner knows; the agent can't read it), run `gh secret set SLACK_WEBHOOK_URL -R manycore-com/magicator2` and paste interactively. If it is a different hook, leave it alone.
4. [O] Confirm other exporters the agent cannot see: other machines or laptops, 1Password items, FastJVM org-level secrets (the agent got a 403), and any CI or cron elsewhere. Update every one that holds the old URL.
5. [A] In a fresh login shell, confirm `bash -lc '[[ $SLACK_WEBHOOK_URL == *B0B0KD0BTQB* ]] && echo still-old || echo rotated'` prints `rotated`.
6. [A] `bash -lc 'cd /home/n/Code/coga && coga validate --check-slack --json'` and the same in `/home/n/Code/thinkpick`. Judge only the `slack-revoked`, `slack-unreachable` and `slack-misconfigured` issue codes, not the exit code. Optionally run the same in xpllm and magicator as a sanity check.
7. [O] Revoke the old webhook (`B0B0KD0BTQB`) in Slack app settings. Do this only after step 6 passes, so there is no notification gap.
8. [A] Probe the old URL with a script that rebuilds it from a `coga/log.md` line in memory, POSTs `{}`, and prints only `classify_slack_response(status, body)`. The expected result is `revoked` (404 / `no_service`).
9. [A] Re-run the tracked-file pattern scan and confirm no hits beyond the 24 historical `log.md` lines, the fake test and doc URLs, and this ticket's prose.

### Preservation decisions
- Do not edit `coga/log.md` (append-only) and do not rewrite history in any repo, including xpllm and magicator2. Revocation makes every copy dead.
- No code changes. Redaction is already in `slack_response` (PR #629).
- Leave `COGA_IMPORTANT_WEBHOOK_URL` and the tablet local toml unchanged.
- Moving the URL to 1Password with an `op://` reference is optional. `op` is installed. Not proposed unless the owner wants it.

### Open questions for the owner (approve step)
- Is the magicator2 `SLACK_WEBHOOK_URL` Actions secret the leaked hook?
- Are there other machines, 1Password items or FastJVM org secrets that export the old URL?
