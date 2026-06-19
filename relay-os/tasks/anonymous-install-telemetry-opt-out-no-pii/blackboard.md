The blackboard is a notepad to be written to often as the human and agent works through a task.

## Design step — decisions (with nick, interactive)

### Endpoint
- **GCP serverless** (Cloud Run / Cloud Function) endpoint that we own and operate.
  Keep it tiny and inspectable. We control it, so we configure it to satisfy the
  no-PII line at the edge.
- **Drop client IP at the edge** — endpoint must not log the source IP (or strip
  it before any write). No geo derived. This is the strongest no-PII story; we
  accept losing any geo signal.

### Payload (the complete wire format — this exact list goes in the docs)
```json
{
  "schema_version": 1,
  "event": "ping",
  "install_id": "<uuid4, generated once, stored locally>",
  "relay_version": "0.2.0",
  "os": "linux",
  "arch": "arm64",
  "python_version": "3.11",
  "ci": false,
  "tickets_total": 12,
  "tickets_done": 5,
  "tickets_active_30d": 3
}
```

Field decisions:
- **Core (presence):** install_id, relay_version, os, event, schema_version.
- **System (nick to confirm at review-design):** arch, python_version (major.minor),
  ci (bool, detected from CI env vars). My recommendation = include all three.
- **Usage (engagement) — nick explicitly asked for these:**
  - tickets_total, tickets_done, tickets_active_30d (touched in last 30 days).
  - **Exact integers, NOT buckets.** Nick's call: it's opt-out + disclosed so the
    beacon is consented; buckets add code complexity for little gain.
  - Derived purely by counting ticket.md files + reading `status` frontmatter +
    mtime. No slugs, no titles, no body content, ever.
- **Hard NO (no-PII line):** repo name/path, git remote, cwd, username/hostname,
  ticket content/slugs/titles, command names/args, IP/geo, fine-grained timestamps.

### Engagement-telemetry note (principle tension)
Adding ticket counts moves the ping from *presence* to *engagement* telemetry
(watching an install's usage grow over time via the persistent install_id). This
is a bigger lean against principle 5 than the core ping. Nick (owner) made the
call consciously; mitigations (opt-out + loud disclosure + documented payload +
no content) hold. If those mitigations can't be kept, fall back to PyPI/GitHub
estimate per ticket.

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
- [ ] relay bump (after nick eyeballs the spec — interactive).

## Open Questions (for review-design / owner)

1. **GCP endpoint ownership & deployment.** Who provisions the Cloud Run/Function
   service + the IP-drop config + the storage sink (BigQuery?), and what's the
   prod URL the client ships with? Client is built against a configurable URL;
   the actual deploy needs cloud access — owner-driven. Until a URL exists, the
   client default URL is a placeholder.
2. **Confirm the three system fields.** arch, python_version (major.minor), ci —
   recommended IN. Last chance to trim before implement.
3. **"Active install" definition (analytics side).** Distinct install_id seen in
   last N days — what N? (Default proposal: 30.) Separate from the client-side
   `tickets_active_30d` window. Dashboard work, out of scope to build but the
   definition should be agreed.
4. **PyPI/GitHub cross-check.** Worth doing as a cheap no-infra sanity check on
   the ping numbers? Tracked as a separate idea, not built here.
5. **Disclosure surface.** First-run stderr disclosure is specified. Also in
   README top? (Proposal: yes in README + telemetry doc; first-run stderr is the
   loud one.)
