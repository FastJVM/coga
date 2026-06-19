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

A **PM signal to gauge product-market fit** after launch: how many real
installs exist, whether they're actually used (any tickets in the repo), and
whether they're still active (recent run). Strictly no PII.

Shape: a single anonymized **opt-out** ping sent to a GCP serverless endpoint
that we own and operate.

- **On by default** (opt-out), with a loud first-run disclosure and a one-line
  disable (config flag **and** env var). The exact payload and the disable
  instructions are documented, and a `relay telemetry` command prints the exact
  payload that would be sent so a human or agent can read it before trusting it.
- Sends **only** the three fields documented below. Nothing that identifies a
  user, repo, path, cwd, hostname, git remote, ticket content, slug, or title.
- Fires **at most once per day per install** — enough to estimate "active," not
  a background reporter. Never blocks or slows a `relay` command (fire-and-forget
  in a detached process).
- **Fail silent-for-the-user but never wrong:** a telemetry failure must not
  break or slow any `relay` command, and must not be swallowed in a way that
  hides a real bug — it is logged to a machine-local telemetry log, never
  crashes the command.

### What is sent (the complete wire payload)

This is a **PM signal to gauge product-market fit**: how many real installs
exist, whether they're used, and whether they're still active. That needs
exactly three fields — this is the complete payload, nothing else on the wire:

```json
{
  "instance_id": "<uuid4, generated once, stored in machine-local state>",
  "tickets_total": 12,
  "last_run": "2026-06-19"
}
```

- `instance_id` — random UUIDv4, generated once and stored in machine-local
  state (not in the repo). The only join key; lets us count distinct installs.
  Not derived from anything — no machine, user, or repo identity.
- `tickets_total` — exact integer count of tickets in the repo, derived only by
  counting `ticket.md` files. No status, slugs, titles, or content. Answers
  "is this install actually used?"
- `last_run` — the date (`YYYY-MM-DD`, UTC) of the most recent `relay` run.
  Coarse day granularity, no finer timestamp. Answers "is this install still
  active?"

No version, OS, arch, Python, CI, or per-status/recency ticket breakdown — all
explicitly cut in review as more than the PMF question needs (owner decision —
see blackboard). Carrying `last_run` in the payload means the endpoint can store
exactly these three fields and needs no server-side timestamps to derive
activity.

### Endpoint (GCP serverless, owned by us)

- A small Cloud Run / Cloud Function (gen2) service that accepts `POST` of the
  JSON above and returns `204`. The client ignores the body.
- **Drops the client IP at the edge** — the service must not log or persist the
  source IP, and derives no geo. (Owner decision: strongest no-PII story; we
  accept losing any geo signal.)
- Persists exactly the three payload fields per accepted ping — no IP, no
  server-added fields. The sink (e.g. BigQuery) dedups by
  `(instance_id, last_run)` so an occasional double-send is harmless.
- Endpoint URL is a constant in the client, overridable via env
  (`RELAY_TELEMETRY_URL`) so it can be pointed at a test sink.

## Acceptance Criteria

- [ ] A `relay` invocation sends **at most one** ping per UTC day per install,
      gated by a machine-local timestamp file; subsequent same-day invocations
      send nothing.
- [ ] The ping is **fire-and-forget**: it runs in a detached process and the
      foreground `relay` command returns without waiting on the network. A slow
      or unreachable endpoint adds no measurable latency to any command.
- [ ] The wire payload contains **exactly** `instance_id`, `tickets_total`,
      `last_run` and nothing else. A test asserts the serialized payload key set.
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
      `instance_id`, the endpoint URL, and the **exact payload** that would be
      sent — without sending it.
- [ ] A telemetry failure (network error, non-2xx, exception) never raises into
      the command, never prints a scary error to the user, and is recorded in a
      machine-local telemetry log so a real bug is not silently swallowed.
- [ ] `instance_id` persists across repos and across commands (stored in
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
   - `instance_id` — UUIDv4, created on first read if absent (atomic write via
     `atomicio`).
   - `telemetry-last-ping` — stores the last-ping UTC date string (throttle).
   - `telemetry.log` — append-only failure log.

3. **Payload builder** — `build_payload(cfg) -> dict` in `telemetry.py` returns
   exactly `{instance_id, tickets_total, last_run}`:
   - `instance_id` from the machine-local id file (created on first read);
   - `tickets_total` = `len(tasks.list_tasks(cfg))` (count of `ticket.md`
     files — no status read, no content);
   - `last_run` = today's UTC date as `YYYY-MM-DD` (the ping fires on a run, so
     the send date is the last-run date).

4. **Disable resolution** — `telemetry_disabled(cfg) -> bool`: true if
   `DO_NOT_TRACK` truthy, or `RELAY_TELEMETRY` falsy, else `not
   cfg.telemetry_enabled`. Env beats config.

5. **Throttle + first-run disclosure** — `maybe_ping(cfg)` called once at the
   top of `main()` in `cli.py` (~line 210, before dispatch):
   - if disabled → return;
   - ensure `instance_id` exists; if it was just created, print the loud
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
   prints status (enabled/disabled + the deciding source), `instance_id`,
   endpoint URL, and `json.dumps(build_payload(cfg), indent=2)` — read-only,
   sends nothing.

8. **Tests** — `tests/test_telemetry.py`: config default/override, env disable
   precedence (`RELAY_TELEMETRY`, `DO_NOT_TRACK`), exact payload key set,
   no-PII assertion, once-per-day gating, first-run disclosure fires once,
   `tickets_total` correctness against a seeded repo, `last_run` date format.
   Add an autouse fixture (or extend conftest) so no test emits a real ping.

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
  (distinct `instance_id` with a `last_run` in the last N days) from the rows.
- **PyPI/GitHub download cross-check** — a cheap no-infra complement, tracked
  as a separate idea (Open Questions), not built here.
- **Per-event/usage telemetry beyond the single daily ping** (no command-name
  tracking, no timing, no error reporting).
- **Extra payload fields** — version, OS, arch, Python, CI, and per-status /
  recency ticket breakdowns were all considered and **cut in review**; the
  payload is the three fields above and nothing more.

## Context

This is a Wave 1 launch-gate item: post-launch we need to know if installs are
real and sticky.

Principle tension to respect (see `relay/principles`): phoning home introduces a
hosted backend, which cuts against principle 5 (own the substrate, local by
default) and the legibility ethos. The mitigations are non-negotiable: opt-out
**with** loud disclosure, fully documented payload, trivial disable, no PII, and
the agent/human can read exactly what's sent. If the design can't keep those, it
should fall back to the no-phone-home PyPI/GitHub estimate instead.

