---
title: Anonymous install telemetry (opt-out, no PII)
status: active
mode: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
step: 1 (design)
---

## Description

Give us a count of **active installs** so we can tell whether anyone is
actually running Relay after launch, plus a coarse read on whether an install
is actually *used* (tickets created/done) vs. installed-and-idle. Strictly no
PII.

Shape: a single anonymized **opt-out** ping sent to a GCP serverless endpoint
that we own and operate.

- **On by default** (opt-out), with a loud first-run disclosure and a one-line
  disable (config flag **and** env var). The exact payload and the disable
  instructions are documented, and a `relay telemetry` command prints the exact
  payload that would be sent so a human or agent can read it before trusting it.
- Sends **only** the fields enumerated in Proposed Shape below. Nothing that
  identifies a user, repo, path, cwd, hostname, git remote, ticket content,
  slug, or title.
- Fires **at most once per day per install** — enough to estimate "active," not
  a background reporter. Never blocks or slows a `relay` command (fire-and-forget
  in a detached process).
- **Fail silent-for-the-user but never wrong:** a telemetry failure must not
  break or slow any `relay` command, and must not be swallowed in a way that
  hides a real bug — it is logged to a machine-local telemetry log, never
  crashes the command.

### What is sent (the complete wire payload)

This exact list is the documented payload — there is nothing else on the wire:

```json
{
  "schema_version": 1,
  "event": "ping",
  "install_id": "<uuid4, generated once, stored in machine-local state>",
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

- `install_id` — random UUIDv4, generated once and stored in machine-local
  state (not in the repo). The only join key; not derived from anything.
- `relay_version` — `importlib.metadata.version("relay-os")`.
- `os` — coarse platform (`linux` / `darwin` / `windows`) from `platform.system()`.
- `arch` — `arm64` / `x86_64` etc. from `platform.machine()`.
- `python_version` — major.minor only (e.g. `3.11`).
- `ci` — bool, true when standard CI env vars are present (`CI`, etc.).
- `tickets_total` / `tickets_done` / `tickets_active_30d` — **exact integer
  counts** derived only from counting `ticket.md` files and reading their
  `status` frontmatter + last-activity timestamp. No slugs, titles, or content.
  `tickets_active_30d` = tickets whose `log.md` last activity is within 30 days.

Counts are exact (not bucketed): the beacon is consented opt-out telemetry, and
bucketing adds code for little gain (owner decision — see blackboard).

### Endpoint (GCP serverless, owned by us)

- A small Cloud Run / Cloud Function (gen2) service that accepts `POST` of the
  JSON above and returns `204`. The client ignores the body.
- **Drops the client IP at the edge** — the service must not log or persist the
  source IP, and derives no geo. (Owner decision: strongest no-PII story; we
  accept losing any geo signal.)
- Persists one row per accepted ping: the payload fields plus a server-side
  `received_date` at **day** granularity (no finer timestamp, no IP). The sink
  (e.g. BigQuery) dedups by `(install_id, received_date)` so an occasional
  double-send is harmless.
- Endpoint URL is a constant in the client, overridable via env
  (`RELAY_TELEMETRY_URL`) so it can be pointed at a test sink.

## Acceptance Criteria

- [ ] A `relay` invocation sends **at most one** ping per UTC day per install,
      gated by a machine-local timestamp file; subsequent same-day invocations
      send nothing.
- [ ] The ping is **fire-and-forget**: it runs in a detached process and the
      foreground `relay` command returns without waiting on the network. A slow
      or unreachable endpoint adds no measurable latency to any command.
- [ ] The wire payload contains **exactly** the fields listed above and nothing
      else. A test asserts the serialized payload key set.
- [ ] No field is derived from repo path, cwd, hostname, username, git remote,
      ticket slug/title, or ticket body. A test asserts none of these leak.
- [ ] Telemetry is **on by default**. Setting `[telemetry] enabled = false` in
      `relay.toml`/`relay.local.toml`, OR `RELAY_TELEMETRY=0`, OR the standard
      `DO_NOT_TRACK=1`, disables it. Env overrides config; either disable path
      results in zero network calls.
- [ ] On the **first run** of an install (no `install_id` yet), a loud,
      one-time disclosure is printed to stderr: that telemetry is on, exactly
      what is sent, and how to disable it. Subsequent runs are silent.
- [ ] `relay telemetry` prints current status (enabled/disabled + why), the
      `install_id`, the endpoint URL, and the **exact payload** that would be
      sent — without sending it.
- [ ] A telemetry failure (network error, non-2xx, exception) never raises into
      the command, never prints a scary error to the user, and is recorded in a
      machine-local telemetry log so a real bug is not silently swallowed.
- [ ] `install_id` persists across repos and across commands (stored in
      machine-local state, generated once).
- [ ] Tests do not emit real pings (the test suite stubs the sender / forces
      telemetry off), mirroring the existing `_stub_slack` autouse pattern.
- [ ] Docs (README / a telemetry doc + the relevant `relay/` context) state the
      exact payload, the default-on behavior, and every disable mechanism.

## Proposed Shape

New module **`src/relay/telemetry.py`** holding the client. Order of work:

1. **Config flag** — in `src/relay/config.py`, add `telemetry_enabled: bool =
   True` to the `Config` dataclass (lines ~115–150) and a
   `_resolve_telemetry_enabled(shared, local)` helper modeled on
   `_resolve_git_enabled()` (lines ~864–879), wired into `load_config()`
   (line ~222). Reads `[telemetry] enabled`, default `True`, local overrides
   shared.

2. **Machine-local state** — add a `machine_state_dir()` helper (in `paths.py`
   or `telemetry.py`) returning `$XDG_STATE_HOME/relay` (default
   `~/.local/state/relay`). Files:
   - `install_id` — UUIDv4, created on first read if absent (atomic write via
     `atomicio`).
   - `telemetry-last-ping` — stores the last-ping UTC date string.
   - `telemetry.log` — append-only failure log.

3. **Payload builder** — `build_payload(cfg) -> dict` in `telemetry.py`:
   - version via `importlib.metadata.version("relay-os")`;
   - `os`/`arch`/`python_version` via `platform`;
   - `ci` from env;
   - counts via `tasks.list_tasks(cfg)` + `ticket.Ticket.read().status` +
     `logfile.last_activity()` for the 30-day window.

4. **Disable resolution** — `telemetry_disabled(cfg) -> bool`: true if
   `DO_NOT_TRACK` truthy, or `RELAY_TELEMETRY` falsy, else `not
   cfg.telemetry_enabled`. Env beats config.

5. **Throttle + first-run disclosure** — `maybe_ping(cfg)` called once at the
   top of `main()` in `cli.py` (~line 210, before dispatch):
   - if disabled → return;
   - ensure `install_id` exists; if it was just created, print the loud
     first-run disclosure to stderr;
   - read `telemetry-last-ping`; if it equals today's UTC date → return;
   - atomically write today's date to `telemetry-last-ping` (optimistic gate),
     then spawn the detached sender. Wrapped in a broad `try/except` that logs
     to `telemetry.log` and never raises.

6. **Detached sender** — hidden CLI subcommand `relay _telemetry-send` that
   reads the JSON payload from stdin and `requests.post(url, json=..., timeout)`
   (mirroring `notification/slack.py` lines ~94–121). `maybe_ping` spawns it
   with `subprocess.Popen(..., start_new_session=True)`, stdio to devnull, and
   does **not** wait. The subcommand logs failures to `telemetry.log`; it is
   hidden from `--help` and excluded from alias/builtin handling.

7. **`relay telemetry` command** — new command in `src/relay/commands/` that
   prints status (enabled/disabled + the deciding source), `install_id`,
   endpoint URL, and `json.dumps(build_payload(cfg), indent=2)` — read-only,
   sends nothing.

8. **Tests** — `tests/test_telemetry.py`: config default/override, env disable
   precedence (`RELAY_TELEMETRY`, `DO_NOT_TRACK`), exact payload key set,
   no-PII assertion, once-per-day gating, first-run disclosure fires once,
   counts correctness against a seeded repo. Add an autouse fixture (or extend
   conftest) so no test emits a real ping.

9. **Docs/contexts** — document the payload + disable in README and a telemetry
   doc; update the relevant `relay-os/contexts/relay/` context (principles /
   architecture) to record that Relay phones home by default and how that
   respects the legibility mitigations. Keep the live `relay-os/` copy and the
   packaged `src/relay/resources/templates/relay-os/` copy in sync.

## Out of Scope

- **Provisioning the GCP project/IAM and deploying the service.** This ticket
  builds the client against a configurable endpoint URL and specifies the
  endpoint contract; standing up the actual Cloud Run service, its IP-drop
  config, and the BigQuery sink is owner-driven infra (needs cloud access) —
  see Open Questions.
- **The analytics/dashboard side** — defining and computing "active installs"
  (distinct `install_id` in last N days) from the stored rows.
- **PyPI/GitHub download cross-check** — a cheap no-infra complement, tracked
  as a separate idea (Open Questions), not built here.
- **Per-event/usage telemetry beyond the single daily ping** (no command-name
  tracking, no timing, no error reporting).
- **Bucketing the counts** — explicitly decided against (exact ints).

## Context

This is a Wave 1 launch-gate item: post-launch we need to know if installs are
real and sticky.

Principle tension to respect (see `relay/principles`): phoning home introduces a
hosted backend, which cuts against principle 5 (own the substrate, local by
default) and the legibility ethos. The mitigations are non-negotiable: opt-out
**with** loud disclosure, fully documented payload, trivial disable, no PII, and
the agent/human can read exactly what's sent. If the design can't keep those, it
should fall back to the no-phone-home PyPI/GitHub estimate instead.

