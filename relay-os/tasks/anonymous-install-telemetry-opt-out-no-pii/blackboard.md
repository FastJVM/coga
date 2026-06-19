The blackboard is a notepad to be written to often as the human and agent works through a task.

## Design step — decisions (with nick, interactive)

### Endpoint
- **GCP serverless** (Cloud Run / Cloud Function) endpoint that we own and operate.
  Keep it tiny and inspectable. We control it, so we configure it to satisfy the
  no-PII line at the edge.
- **Drop client IP at the edge** — endpoint must not log the source IP (or strip
  it before any write). No geo derived. This is the strongest no-PII story; we
  accept losing any geo signal.

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
- CLI hook: top of `main()` in `cli.py` (~line 210), before dispatch — fires
  once per invocation.
- **CORRECTION:** `period_state.py` is NOT a generic once-per-period timer — it's
  recurring-task state snapshots. Does NOT fit. Throttle = our own
  `telemetry-last-ping` date file in machine-local state.
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

1. **GCP endpoint ownership & deployment.** Who provisions the Cloud Run/Function
   service + the IP-drop config + the storage sink (BigQuery?), and what's the
   prod URL the client ships with? Client is built against a configurable URL;
   the actual deploy needs cloud access — owner-driven. Until a URL exists, the
   client default URL is a placeholder.
2. **RESOLVED — payload fields.** Trimmed in review to exactly instance_id,
   tickets_total, last_run. All system fields (version/os/arch/python/ci) and
   the extra ticket counts (done, active_30d) are cut.
3. **"Active install" definition (analytics side).** Distinct instance_id with a
   last_run in the last N days — what N? (Default proposal: 30.) Dashboard work,
   out of scope to build but the definition should be agreed.
4. **PyPI/GitHub cross-check.** Worth doing as a cheap no-infra sanity check on
   the ping numbers? Tracked as a separate idea, not built here.
5. **Disclosure surface.** First-run stderr disclosure is specified. Also in
   README top? (Proposal: yes in README + telemetry doc; first-run stderr is the
   loud one.)
