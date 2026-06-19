The blackboard is a notepad to be written to often as the human and agent works through a task.

## Design step — decisions (with nick, interactive)

### Architecture — REVISED 2026-06-19 (recurring task + GCP→Slack relay)
- **Client = a recurring task, NOT a CLI hook.** Daily `mode: script` recurring
  task `relay-os/recurring/telemetry/`, modeled on `recurring/digest`. Its script
  step runs `relay telemetry send`. Recurring + `period_state` give once-per-day
  + idempotency. Nothing hooks `main()`; nothing runs on every command. (Dropped:
  the detached subprocess, the telemetry-last-ping throttle file, the
  telemetry.log — failures land in the recurring task's own log.md/blackboard.)
- **Destination = GCP relay → internal Slack, NO BigQuery.** Client POSTs 3
  fields to a tiny GCP Cloud Function; the function drops IP and posts a one-line
  message to our internal Slack channel. At ~100 users the channel IS the
  dataset. Webhook held server-side in GCP (a secret), never in the shipped
  client. ("broadcast to internal slack (from the gcp)".)
- **Drop client IP at the edge** — function reads no IP header + a Cloud Logging
  exclusion filter keeps remoteIp out of request logs.
- **Sweep trigger:** ASSUME users already run the `relay recurring` sweep.
  Installs that don't service recurring tasks send nothing — accepted coverage
  limitation (nick's call).

### Payload — FINAL (trimmed in review 2026-06-19)
It's a PM tool to read product-market fit: how many real installs, are they
used, are they still active. Exactly three fields, nothing else on the wire:
```json
{
  "instance_id": "<uuid4, generated once, stored locally>",
  "tickets_total": 12,
  "last_run": "2026-06-19"
}
```

Field decisions:
- **instance_id** — random uuid4, per install, machine-local. Counts distinct
  installs. Not derived from anything.
- **tickets_total** — exact int, count of ticket.md files only. No status, no
  content. Answers "is it used?"
- **last_run** — UTC date (YYYY-MM-DD) of most recent run. Answers "still
  active?" Carried in payload so the endpoint stores only these 3 fields and
  needs no server-side timestamps.

**CUT in review (nick):** relay_version, os, arch, python_version, ci, event,
schema_version, tickets_done, tickets_active_30d. Earlier draft had all these;
nick trimmed to the minimum the PMF question needs. ("we only agreed on ticket
total + last run + some kind of unique id per instance.")

- **Hard NO (no-PII line):** repo name/path, git remote, cwd, username/hostname,
  ticket content/slugs/titles, command names/args, IP/geo, fine-grained timestamps.

### Behavior (from ticket, confirmed)
- On by default (opt-out). Loud first-run disclosure. One-line disable: config
  flag + env var. Document exactly what's sent + how to disable.
- At most once per period (daily) per install. Idempotent. Never blocks a command.
- Fail silent-for-user but never wrong: telemetry failure must not break/slow any
  `relay` command, and must be logged (not swallowed) so it can't hide a real bug.

### Plumbing facts (from mapping agent)
- ~~CLI hook at top of `main()`~~ — DROPPED; we use a recurring task now.
- `period_state.py` is recurring-task state snapshots — which is now exactly the
  right primitive (the telemetry recurring task uses it for once-per-period, like
  `digest`). Model the whole thing on `relay-os/recurring/digest/` (schedule cron
  + `mode: script` + workflow step whose skill `script:` runs a `relay` command).
- Config bool pattern: `_resolve_git_enabled()` (config.py ~864–879);
  Config dataclass ~115–150; `load_config()` ~222.
- No machine-local path helper exists today — add `machine_state_dir()` →
  `$XDG_STATE_HOME/relay` (default `~/.local/state/relay`) for the `instance_id`.
- Ticket enumeration for tickets_total: `len(tasks.list_tasks(cfg))`.
- Version not needed anymore (dropped). HTTP: `requests` (see
  `notification/slack.py` 94–121). Tests: `conftest.py` autouse `_stub_slack` is
  the model for stubbing the sender.
- Config bool pattern: `_resolve_git_enabled()` (config.py ~864–879);
  Config dataclass ~115–150; `load_config()` ~222.
- No machine-local path helper exists today — add `machine_state_dir()` →
  `$XDG_STATE_HOME/relay` (default `~/.local/state/relay`). All current paths are
  repo-relative.
- Ticket enumeration: `tasks.list_tasks(cfg)` → TaskRef; `Ticket.read().status`;
  done = `"done"`; recency via `logfile.last_activity(task_dir)`.
- Version: `importlib.metadata.version("relay-os")`. HTTP: `requests` (see
  `notification/slack.py` 94–121, timeout pattern). Tests: `tests/test_*.py`,
  `conftest.py` autouse `_stub_slack` is the model for stubbing the sender.

### Status
- [x] Spec written into ticket.md (Description / Acceptance Criteria / Proposed
      Shape / Out of Scope).
- [x] Spec-review PR (design only, no code) opened for GitHub review:
      https://github.com/FastJVM/relay/pull/408
      - Review-only: base `design-spec-base` (pre-spec commit), head
        `telemetry-design-spec` (= spec commit 4504e07). Don't merge; delete
        both branches after review.
      - NB: relay git-sync already committed+pushed the spec to origin/main on
        activation, so the PR base is pinned to surface the diff.
- [ ] relay bump (after nick reviews the spec — interactive).

## Open Questions (for review-design / owner)

1. **GCP deploy run + prod URL + Slack webhook.** Function code/deploy.sh/IP-drop
   config are IN scope (Part B). Owner-only bits: GCP `PROJECT_ID`/`REGION`, which
   internal Slack channel + its incoming webhook (held as a GCP secret), who runs
   `deploy.sh`, and pinning the printed URL into the client `TELEMETRY_URL`. Until
   then the client default URL is a placeholder (pings fail-silent).
2. **RESOLVED — payload fields.** Exactly instance_id, tickets_total, last_run.
3. **RESOLVED — destination.** GCP relay → internal Slack, no BigQuery (100-user
   scale; channel is the dataset).
4. **RESOLVED — sweep trigger.** Assume users run the recurring sweep; non-sweep
   installs send nothing (accepted coverage limitation).
5. **Recurring schedule.** What cron for the daily ping? Proposal: a daily slot
   offset from `digest` (e.g. `30 9 * * *`) so the two don't fire together.
6. **PyPI/GitHub cross-check.** Worth doing as a cheap no-infra sanity check on
   the Slack ping counts? Separate idea, not built here.
7. **Disclosure surface.** `relay init` output + README + telemetry doc. Confirm
   that's enough (no first-run stderr hook now that there's no CLI hook).
