---
schedule: "0 7 * * 1"
schedule_comment: "Every Monday at 7am, when an operator sweeps"
title: Weekly Coga usage snapshot
workflow: phone-home/run
state_keys:
  - period_state
---

## Description

Attempt one weekly usage snapshot from the sibling `ticket.py`, without an
agent. This template owns the snapshot's behavior and data boundary.

The snapshot is edge code, not a registered recipe. Its default implementation
is `src/coga_edge/phone_home.py`, shipped in the Coga wheel and called by the
repo-owned `recurring/phone-home/ticket.py` shim. It imports only shared core
and runs under `runner.run_reported` (the `## Recipe Failure` floor), then
bumps once through the CLI; bump failure propagates. `phone-home/run` has one
agent-owned `send` step with no skills, so normal completion needs no agent.
Run by hand outside a launch, it prints its report without advancing a task.
Upgrades, full local forks and legacy adoption are owned by
[coga/packaging](https://github.com/FastJVM/coga/blob/main/docs/contexts/coga/packaging/SKILL.md).
The schedule is declared in this template's frontmatter (operator-local time).
New templates are due on the first sweep, too. Coga installs no scheduler.
Downloads, init, and ordinary commands send no events. Repos that never sweep
never report: these are repos with active sweeps, **not install counts**.

### Admission and configuration

`[telemetry] enabled = false` suppresses both
capture and its Slack receipt before identity minting or worker creation.
This is not a global network-off switch: git sync and lifecycle notifications
retain their own switches.

Production admission is checked before creating each worker and again inside
it. Suppress for presence of `PYTEST_CURRENT_TEST`, active `CI` (anything other
than empty/0/false/no/off, case-insensitive), source/editable imports under a
Coga development tree, or a target or cwd inside such a tree. Both the installed `coga` dependency
and the selected implementation file are checked; with a stock shim the latter
is the wheel module, while repo/cwd checks still cover the launching repo.
Resolve symlinks;
a development ancestor has `project.name = "coga"` in `pyproject.toml`,
`src/coga/runner.py`, and `tests/`. A wheel targeting `tests/fixtures/seeded-repo/` or a linked
source checkout is suppressed too. Editable installations intentionally do not
contribute PMF data. There is no bypass flag, endpoint, host, or key option.
Automated installed-wheel tests preserve CI/pytest gates and fake transport;
manual ingestion proof uses a release wheel outside development trees.

### State, publication, and loss

The parent template blackboard holds exactly one readable single-line JSON
`period_state:` value: `schema` (1), `run` (nonnegative monotonic invocation
number), nullable `repo_id` (UUID v4), `offset` (byte offset), and `digest`
(SHA-256 of the consumed complete-line prefix). The unused seed has run/offset
zero, null identity, and the empty-prefix digest. Declare only `period_state`
in `state_keys`; quiet, disabled, failed and suppressed runs increment `run`.

Under `git.state_lock(cfg)`, capture parent bytes, read using
`taskfile.read_blackboard(expected_bytes=...)`, replace using
`taskfile.replace_blackboard(expected_bytes=...)`, and explicitly publish only
that parent via `git.publish(..., expect={parent: original_bytes})`. The current
lock is reentrant, so mutation and publication share one lock window. Preserve
all above-fence bytes and unrelated prose. No period bump is relied upon to
publish its parent. No-git/disabled-git runs keep authoritative local state;
publication failures retain state and ordinary local audit evidence.

Gate first. Disabled/development-suppressed runs increment the marker and
baseline the cursor, without minting identity or sending anything. Enabled
valid runs mint identity if absent, prepare the payload and reserve state
**before** spawning transport. No outcome is persisted. No retry, redirect,
queue, replay or post-transport state rewrite exists. A crash after reservation
can lose an event; capture failure cannot roll back the cursor.

Invalid inventory (including duplicate discovery, malformed tickets or invalid
status) warns locally and skips capture/receipt, advances only `run`, preserves
identity/cursor, and completes successfully. Corrupt state, unexpected argv,
and invalid payload/version values fail visibly before sending.

Disabling stops sending; movement from the gap may appear in the first count
after re-enabling. A disabled sweep baselines only through that moment; lines
appended later can count after re-enable. An off/on toggle between runs is
unobservable. No suppression marker is persisted. Synced clones share identity;
unsynced first runs can mint different identities. No distributed exactly-once
claim or coordination.

The live parent may acquire runtime state while its packaged twin must stay
unused and identity-free. Only when they diverge, add that live path with its
runtime-state reason to `INTENTIONALLY_DIVERGENT_TWINS`; the focused packaging
test still requires identical above-fence bytes and an unused packaged seed.
Never add a stale exemption while both files match.

### Scope and approximate movement

Inventory uses `tasks.list_tasks` and `read_ticket`: both ticket shapes, every
status, including drafts, parked v2 work and terminal tickets still on disk.
Exclude refs equal to `recurring` or starting `recurring/`; normal discovery
excludes templates, READMEs and attachments. Explicit zeros for all seven
`lifecycle.VALID_STATUSES`. Never send partial counts from invalid inventory.

Movement counts complete valid timestamp/ref/actor audit envelopes for work
refs (including deleted tasks), using the versioned/legacy decoding contract
in [coga/internals/spool-merge](https://github.com/FastJVM/coga/blob/main/docs/contexts/coga/internals/spool-merge/SKILL.md). The decoded
message is exactly one of:

- `advanced to step <positive integer> (<step name>)`, optionally followed by
  the producer's ` → <operator>` handoff and/or ` — <FYI>` suffix;
- `task done`, optionally followed by ` — <FYI>`;
- `auto-bumped on merge of PR #<integer> → done`, or
  `auto-bumped on merge of the linked PR → done`.

Actor and handoff names may contain spaces; step names may contain parentheses,
as permitted by the audit producers. An FYI suffix may contain line breaks. These names are parsed locally, never sent.

No rewinds, launches, creates, other marks, blocks, unblocks, embedded prose,
malformed lines or housekeeping. First enabled run baselines at complete-line
EOF and sends movement zero. Later runs verify the prefix hash and count only
new complete lines through captured EOF; leave a trailing partial line for
next time. Deduplicate exact lines within the new suffix. Shrink/rewrite resets
to new EOF with movement zero and a local warning. Missing log is empty.
Equal or out-of-order timestamps do not change counting. Union merges can
append old lines after a valid prefix; identical real transitions within one
minute can collapse. This is approximate activity, not an audit ledger.
Snapshots supply current inventory; never sum historical inventories.

### Closed wire contract

One `coga_weekly_snapshot` attempt per eligible valid run, HTTPS POST to
`https://us.i.posthog.com/i/v0/e/`, TLS verified, no redirects or SDK. Recipient:
FastJVM US Cloud project `606347`, shared with Multiply. Its public write-only
key is embedded only in the edge module's `POSTHOG_CAPTURE_KEY`. Publishing it permits
spam injection; rotation affects old Multiply builds too. Operational key source, rotation and project settings are in the
[maintenance runbook](https://github.com/FastJVM/coga/blob/main/coga/recurring/phone-home/operations.md).

Exact envelope: `api_key`, `event`, `distinct_id`, `timestamp`, `properties`.
Identity is the persisted UUID; timestamp is UTC occurrence time. Exact measured
properties:

| Property | Type and source |
| --- | --- |
| `coga_version` | Installed package metadata; numeric-leading ASCII version syntax, at most 64 characters; invalid input rejected |
| `os_name` | Closed `linux` / `macos` / `windows` / `other` vocabulary |
| `os_version` | Only leading numeric dotted release component, bounded to 64 ASCII characters; empty when unavailable |
| `python_version` | Numeric interpreter major.minor.micro, at most 64 ASCII characters |
| `tickets_draft`, `tickets_active`, `tickets_in_progress`, `tickets_blocked`, `tickets_paused`, `tickets_done`, `tickets_canceled` | Nonnegative integers, never booleans |
| `movement_count` | Nonnegative integer, never boolean |

No dynamic properties, `$set`, `$lib`, owner/agent names, paths, slugs, titles,
bodies, blackboards, remotes, branches, Slack IDs, environment values, raw logs,
errors, cursor digests, hostnames, or full kernel build text. Protocol fields
are not measured properties. Keep the default identified event/person keyed
only by opaque repo ID; no identify/alias calls or person attributes. IP discard
and disabled GeoIP are required project settings. The network peer necessarily
sees source IP. Query actual stored keys at acceptance; separately explain
service routing metadata, and block acceptance on unexpected enrichment.

### Transport and reports

A private short-lived Python worker (the selected implementation file re-run
with `--worker`, including a complete local fork) reads the prepared keyless event on stdin,
validates the closed schema, adds the constant key and does one POST. The parent
enforces a three-second wall deadline including stalled DNS/connect/read,
kills and reaps on expiry (plus teardown overhead). No response body is read.
Never print credentials, request/response bodies or raw transport exceptions.
Fixed outcomes: accepted, rejected, network-error, timed-out; admission may
return suppressed. HTTP accepted is not proof of ingestion.

After capture, a separately bounded three-second worker calls existing
`notification.post(..., fatal=False, record_failure=False)` with the same
keyless envelope and attempt outcome. Say `attempted / HTTP accepted`, never
`ingested`. Skip disabled Slack. Receipt failure cannot affect capture, state
or completion. A compact period report contains counts/outcomes and at most
one aggregated delivery warning via `blackboard.append_blackboard_report`;
outside a task it goes to stdout. Local validation failures remain distinct.

### Maintenance

For wheel verification, project read-back, key rotation or person deletion,
read the persistent template's
[operations.md](https://github.com/FastJVM/coga/blob/main/coga/recurring/phone-home/operations.md).
Those are separate operator procedures, not actions for a weekly run.
Supporting Markdown stays with the template; it is not copied into a period task.

<!-- coga:blackboard -->

This state is shared by synced clones. Do not copy runtime state into the
packaged seed. Only period_state changes each run; no delivery is retried.

period_state: {"schema":1,"run":5,"repo_id":null,"offset":2252675,"digest":"77675835c2c6ebe211be75437c8bc73140a8f764cf50049c2ef0928906f5b76d"}
