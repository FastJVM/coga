---
slug: anonymous-install-telemetry-opt-out-no-pii
title: Anonymous install telemetry (opt-out, no PII)
status: in_progress
autonomy: interactive
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
step: 3 (implement)
---

## Description

A **PM signal to gauge product-market fit** after launch: how many real
installs exist, whether they're actually used (any tickets in the repo), and
whether they're still active (recent run). Strictly no PII.

Shape: a single anonymized **opt-out** ping, sent once a day by a **recurring
task** to a tiny **GCP relay** that forwards it to our internal Slack.

- **Mechanism: a recurring task, not a CLI hook.** A daily `mode: script`
  recurring task (`relay-os/recurring/telemetry/`) builds the payload and sends
  it — modeled on the existing `digest` recurring task. The recurring system +
  `period_state` give "once per day" and idempotency for free; nothing hooks
  `main()`, nothing runs on every command.
- **Destination: GCP relay → internal Slack (no datastore).** The client POSTs
  the three fields to a small GCP function; the function drops the client IP and
  posts a one-line message to our internal Slack channel. At ~100 users the
  channel *is* the dataset (eyeball / count distinct instance IDs) — no
  BigQuery, no dashboard. The Slack webhook stays server-side in GCP, never in
  the shipped client.
- **On by default** (opt-out), with disclosure and a one-line disable (config
  flag **and** env var). The payload + disable are documented, and `relay
  telemetry show` prints the exact payload without sending it.
- Sends **only** the three fields documented below. Nothing that identifies a
  user, repo, path, cwd, hostname, git remote, ticket content, slug, or title.
- **Fail silent-for-the-user but never wrong:** the ping runs inside the
  recurring task, so it never touches a foreground `relay` command; a failure is
  recorded in the recurring task's own `log.md`/blackboard (never swallowed) and
  never crashes anything.

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

### Endpoint (GCP relay → internal Slack)

- A small Cloud Function (gen2) that accepts `POST` of the JSON above and returns
  `204`. The client ignores the body.
- **Drops the client IP at the edge** — the function reads no IP header, and a
  Cloud Logging exclusion filter keeps `remoteIp` out of the request logs.
  (Owner decision: strongest no-PII story.)
- **Forwards each ping to internal Slack** — posts a one-line message
  (`ping: instance=… tickets=… last_run=…`) to a channel via an incoming webhook
  held server-side as a GCP secret. No BigQuery, no other storage; the Slack
  channel is the record. A double-send is just a harmless duplicate line.
- Endpoint URL is a constant in the client, overridable via env
  (`RELAY_TELEMETRY_URL`) so it can be pointed at a test relay.

## Acceptance Criteria

- [ ] A daily `mode: script` recurring task (`relay-os/recurring/telemetry/`)
      builds and sends the ping; `period_state` ensures one send per scheduled
      period. No telemetry code runs in the `relay` foreground dispatch path.
- [ ] The wire payload contains **exactly** `instance_id`, `tickets_total`,
      `last_run` and nothing else. A test asserts the serialized payload key set.
- [ ] No field is derived from repo path, cwd, hostname, username, git remote,
      ticket slug/title, or ticket body. A test asserts none of these leak.
- [ ] Telemetry is **on by default**. Setting `[telemetry] enabled = false` in
      `relay.toml`/`relay.local.toml`, OR `RELAY_TELEMETRY=0`, OR the standard
      `DO_NOT_TRACK=1`, makes the recurring send a no-op. Env overrides config;
      either disable path results in zero network calls.
- [ ] Disclosure: `relay init`/onboarding output and the docs state plainly that
      telemetry is on, exactly what is sent, and how to disable it.
- [ ] `relay telemetry show` prints current status (enabled/disabled + why), the
      `instance_id`, the endpoint URL, and the **exact payload** that would be
      sent — without sending it.
- [ ] A send failure (network error, non-2xx, exception) is recorded in the
      recurring task's `log.md`/blackboard and never crashes the run — but is not
      silently swallowed.
- [ ] `instance_id` persists across repos and runs (stored in machine-local
      state, generated once).
- [ ] Tests do not emit real pings (the test suite stubs the sender / forces
      telemetry off), mirroring the existing `_stub_slack` autouse pattern.
- [ ] Docs (README / a telemetry doc + the relevant `relay/` context) state the
      exact payload, the default-on behavior, and every disable mechanism.
- [ ] The GCP function accepts the 3-field POST, ignores any extra key, posts a
      one-line message to internal Slack, and returns `204` even on malformed
      input (logging the error server-side).
- [ ] The function never persists the client IP — it reads no IP header and a
      Cloud Logging exclusion filter on its request logs is part of `deploy.sh`.
- [ ] `deploy.sh` is idempotent, parameterized by `PROJECT_ID`/`REGION` + the
      Slack webhook secret, and prints the function URL to pin into the client.

## Proposed Shape

Two deliverables, both built and committed in this ticket: the **Relay client**
(recurring task + sender in `src/relay/`) and the **GCP relay**
(`telemetry-endpoint/`). The only step left to the owner is running the deploy
with real cloud credentials and pinning the resulting URL into the client.

### Part A — Relay client (recurring task + sender)

1. **Config flag** — in `src/relay/config.py`, add `telemetry_enabled: bool =
   True` to the `Config` dataclass (lines ~115–150) and a
   `_resolve_telemetry_enabled(shared, local)` helper modeled on
   `_resolve_git_enabled()` (lines ~864–879), wired into `load_config()`
   (line ~222). Reads `[telemetry] enabled`, default `True`, local overrides
   shared.

2. **Machine-local instance id** — add a `machine_state_dir()` helper (in
   `paths.py` or `telemetry.py`) returning `$XDG_STATE_HOME/relay` (default
   `~/.local/state/relay`) and an `instance_id` file: a UUIDv4 created on first
   read if absent (atomic write via `atomicio`), persisting across repos. No
   throttle/last-ping file — the recurring period owns cadence.

3. **`src/relay/telemetry.py`** —
   - `build_payload(cfg) -> dict` returning exactly `{instance_id,
     tickets_total, last_run}`: `instance_id` from the id file; `tickets_total`
     = `len(tasks.list_tasks(cfg))` (count of `ticket.md` files — no status, no
     content); `last_run` = today's UTC date `YYYY-MM-DD`.
   - `telemetry_disabled(cfg) -> bool`: true if `DO_NOT_TRACK` truthy, or
     `RELAY_TELEMETRY` falsy, else `not cfg.telemetry_enabled`. Env beats config.
   - `send(cfg)`: no-op if disabled; else `requests.post(TELEMETRY_URL,
     json=build_payload(cfg), timeout=…)` (mirroring `notification/slack.py`
     ~94–121). Returns a result the caller logs; never invoked from foreground
     dispatch.
   - `TELEMETRY_URL` constant, overridable via `RELAY_TELEMETRY_URL`, set to the
     URL printed by Part B's deploy.

4. **`relay telemetry` command** — new `src/relay/commands/telemetry.py`,
   registered in `cli.py`, with two subcommands:
   - `show` — read-only: prints status (enabled/disabled + deciding source),
     `instance_id`, endpoint URL, and `json.dumps(build_payload(cfg), indent=2)`.
     Sends nothing.
   - `send` — calls `telemetry.send(cfg)`; this is what the recurring task runs.

5. **Recurring task** `relay-os/recurring/telemetry/` — mirror
   `relay-os/recurring/digest/`: `ticket.md` with a daily `schedule` (cron),
   `mode: script`, and `workflow: telemetry/send` whose single step references a
   new skill `relay/telemetry/send` whose `script:` runs `relay telemetry send`.
   Add the workflow file (`workflows/telemetry/send.md`) and the skill
   (`skills/relay/telemetry/send/SKILL.md`). `period_state` provides
   once-per-period + idempotency; failures land in the task's own
   `log.md`/blackboard, exactly like `digest`.

6. **Disclosure + docs/contexts** — state plainly in `relay init`/onboarding
   output and the README/telemetry doc that telemetry is on, exactly what is
   sent, and how to disable it. Update the relevant `relay-os/contexts/relay/`
   context (principles/architecture) to record the phone-home and its
   mitigations. Keep the live `relay-os/` copy and the packaged
   `src/relay/resources/templates/relay-os/` copy in sync — the recurring task,
   workflow, and skill ship in the template too.

7. **Tests** — `tests/test_telemetry.py`: config default/override, env disable
   precedence (`RELAY_TELEMETRY`, `DO_NOT_TRACK`), exact payload key set, no-PII
   assertion, `tickets_total` correctness against a seeded repo, `last_run` date
   format, and `send` is a no-op when disabled. Stub the sender (extend the
   `_stub_slack`-style autouse fixture) so no test emits a real ping.

### Part B — GCP relay (`telemetry-endpoint/`, new top-level dir)

A tiny, inspectable function we own. Everything except the credentialed deploy
run is delivered in this ticket.

8. **Function** — `telemetry-endpoint/main.py`: one HTTP handler (Cloud
   Functions gen2). On `POST /`:
   - Parse JSON and **accept only** `instance_id` (str, uuid4 shape),
     `tickets_total` (int ≥ 0), `last_run` (`YYYY-MM-DD`). Any other key is
     ignored — never forwarded (belt-and-suspenders on the no-PII line).
   - Post a one-line message to internal Slack
     (`ping: instance=… tickets=… last_run=…`) via an incoming webhook read from
     a server-side secret/env var. Return `204` (empty body). On malformed input
     or a Slack error, still return `204` but log server-side.
   - **Never reads `X-Forwarded-For` / client IP** and persists nothing else.
   - `requirements.txt`: `functions-framework` + `requests`.

9. **IP drop at the edge** — Cloud Functions request access logs include
   `httpRequest.remoteIp` by default. Add a **Cloud Logging exclusion filter**
   on the function's request logs (in `deploy.sh`) so `remoteIp` is never
   persisted, and confirm the handler reads no IP header. The load-bearing
   no-PII control — documented as such in the endpoint README.

10. **Deploy** — `telemetry-endpoint/deploy.sh`: idempotent `gcloud` commands —
    deploy the function `--allow-unauthenticated` (random installs POST without
    creds) with the Slack webhook wired as a secret/env var, apply the
    log-exclusion filter, and print the function URL (which becomes the client's
    `TELEMETRY_URL`). Parameterized by `PROJECT_ID` / `REGION` / webhook secret.

11. **Endpoint README** — `telemetry-endpoint/README.md`: what the function does,
    the 3-field contract, the IP-drop control, the Slack relay, how to deploy,
    and the abuse/cost posture (the function is the only holder of the webhook;
    optional Cloud Armor rate-limit noted, not required for v1).

## Out of Scope

- **The credentialed deploy run itself.** The function code, deploy script, and
  IP-drop config are all delivered here; the owner runs `deploy.sh` against a
  real GCP project (needs cloud credentials, a chosen `PROJECT_ID`, and the
  internal Slack webhook) and pins the printed URL into the client. See Open
  Questions.
- **A datastore / dashboard.** At ~100 users the internal Slack channel is the
  record — counting distinct `instance_id`s / recent `last_run`s is done by
  eye/search. BigQuery and any "active installs" dashboard are deferred.
- **Installs that never run the `relay recurring` sweep.** Telemetry rides the
  recurring system, so an install that never services its recurring tasks sends
  nothing — an accepted coverage limitation (see Open Questions).
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

<!-- coga:blackboard -->

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
