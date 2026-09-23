# Telemetry operations

The [telemetry context](contexts/coga/telemetry/SKILL.md) owns the event
schema, admission gates, cursor and loss semantics. This runbook owns operator
procedures. Weekly snapshots measure repos with active sweeps, not installs.

## Disable delivery

Add this to `coga/coga.local.toml` for this machine, or `coga/coga.toml` for the
shared default (local wins):

```toml
[telemetry]
enabled = false
```

Disabling stops sending; movement from the gap may appear in the first count
after re-enabling. Git sync and normal lifecycle notifications have independent
switches. Editable/source installations intentionally do not report.

## Project and key

Coga uses FastJVM US Cloud project **606347**, currently named Default project,
shared with Multiply. Before **any** query or deletion, run:

```sh
posthog-cli api call --json project-get '{}'
```

Stop unless the returned project ID is `606347`. Follow
[Multiply's project settings and read-back procedures](https://github.com/FastJVM/multiply/blob/main/infra/posthog/README.md#settings-that-must-stay-true)
for required IP discard and disabled GeoIP; do not infer compliance from HTTP
acceptance. The network peer necessarily sees source IP. The
[PostHog capture reference](https://posthog.com/docs/api/capture) describes the
US public capture endpoint and top-level identity fields.

The write-only capture key is in
`op://coga/multiply-posthog-project-key-production/password`. It is deliberately
public in `recurring/phone-home/ticket.py::POSTHOG_CAPTURE_KEY` (live and packaged copies); it cannot query or delete,
but publishing it enables spam injection into this shared project. Use a checked
`op read` (successful and nonempty) directly into the constant through a local
script; never echo it or pass its value as a shell argument. Do not read or
copy `~/.posthog/credentials.json`: that is the separate operator credential.
If desktop authorization fails, the owner can set the constant locally.

Rotation follows [Multiply's key procedure](https://github.com/FastJVM/multiply/blob/main/infra/posthog/README.md#rotation):
update the vault source and Coga constant and release. Resetting the shared key
breaks already-shipped Multiply builds too. Moving Coga to a dedicated project
requires a new constant and Coga release, not a config option. Follow-up in the
Multiply repo: its expected event catalog should mention `coga_weekly_snapshot`.
Do not edit that separate repo as part of this implementation.

## Clean installed-wheel proof (owner at review)

Automated tests use fake transport and preserve pytest/CI suppression. The live
proof below is owner-run from an ordinary shell with no test/CI environment,
outside all Coga source trees. Do not unset test gates inside automation to make
it deliver. Do not use an editable installation or target `example/`.

Build the reviewed checkout, then install its wheel in a fresh external venv:

```sh
python -m pip wheel --no-deps --no-build-isolation . -w /tmp/coga-telemetry-wheel
python -m venv /tmp/coga-telemetry-release
/tmp/coga-telemetry-release/bin/python -m pip install /tmp/coga-telemetry-wheel/coga-*.whl
mkdir -p /tmp/coga-telemetry-proof
cd /tmp/coga-telemetry-proof
git init -b main
# Use your real configured Git identity; init requires it.
/tmp/coga-telemetry-release/bin/coga init . --user nicktoper
cd coga
/tmp/coga-telemetry-release/bin/python -c 'from importlib.metadata import version; print(version("coga"))'
# Before this first run, configure the existing Slack channel for the receipt
# as described below (keep credentials as env: references).
/tmp/coga-telemetry-release/bin/coga recurring launch phone-home
```

For the live proof, enable the existing Slack notification channel in this
scratch repo before its first sweep, following [notification setup](contexts/coga/notifications/SKILL.md).
The receipt contains the exact prepared keyless envelope for comparison; retain
it in the PR along with the queried rows. Fresh init defaults to no notification
channels, so configure this explicitly. A failed receipt is not an ingestion
proof; obtain a successful receipt and matching row for the review evidence.

Use fresh unused paths (and exactly one candidate wheel). This named sweep
runs the newly due battery; ordinary operator sweeps also reach it. Coga installs
no scheduler. Read `repo_id` from the new parent
`recurring/phone-home/ticket.md` blackboard. Record wheel version/hash, prepared
payload values, period report, and UTC run window in the PR. The initial row
must exist, use that UUID, and have movement zero. A capture HTTP success alone
is not acceptance.

After verifying `project-get`, substitute the UUID in this exact query command.
JSON `\u0027` becomes a SQL single quote; the shell's single quotes preserve
`$ip` and any other dollar signs without expansion:

```sh
posthog-cli api call --json execute-sql '{"query":"SELECT event, distinct_id, timestamp, properties, JSONExtractKeys(properties) AS property_keys FROM events WHERE distinct_id = \u0027<repo UUID>\u0027 AND event = \u0027coga_weekly_snapshot\u0027 ORDER BY timestamp"}'
```

Compare every measured value with the prepared event and the context allowlist.
Check all returned keys for IP, GeoIP and other unexpected enrichment; record
service-owned routing metadata separately from client properties. Unexpected
fields block acceptance until explained and corrected. Keep persons keyed only
by opaque repo UUID; do not switch to personless capture to simplify deletion.

Perform a known forward advance/completion on a non-recurring work ticket using
the normal CLI. Record the exact qualifying audit lines. For a later snapshot,
run `/tmp/coga-telemetry-release/bin/python recurring/phone-home/ticket.py` from
`coga/` (or wait for the next due sweep); it runs the same ticket code, reads the
same parent and prints its report. Query again with
the command above: expect another row, the same UUID, and the known movement
count. Repeated direct runs are extra attempts, not a scheduler.

Set local telemetry false, note the UTC timestamp, and run the recipe again.
Use this query after the new window; expect zero rows:

```sh
posthog-cli api call --json execute-sql '{"query":"SELECT count() FROM events WHERE distinct_id = \u0027<repo UUID>\u0027 AND event = \u0027coga_weekly_snapshot\u0027 AND timestamp >= toDateTime(\u0027<disable-run UTC YYYY-MM-DD HH:MM:SS>\u0027)"}'
```

Absent rows alone do not prove absent requests: pair this with automated
no-worker/no-HTTP checks. Paste exact query text/results, wheel version and
all three observations in the PR at review. Use snapshots for each repo's
current inventory; summing historical inventory double-counts it. No dashboard
build is needed (at most one saved insight per agreed quantity).

## Delete one repo's person and events

Disable sending on every clone first and record the committed `repo_id`.
Verify `project-get` reports `606347` before proceeding. Confirm this is the
requested Coga repo UUID, not a Multiply install ID. Deletion is irreversible:

```sh
posthog-cli api call --confirm persons-bulk-delete '{"distinct_ids":["<repo UUID>"],"delete_events":true}'
```

This calls the persons bulk deletion API for project 606347 and queues deletion
of the person and its events. No identify calls or person attributes are needed.
Use [Multiply's deletion follow-through](https://github.com/FastJVM/multiply/blob/main/infra/posthog/README.md#deleting-a-person)
for asynchronous status checks; do not expose its operator credential. After
completion, verify `project-get` again, then:

```sh
posthog-cli api call --json execute-sql '{"query":"SELECT count() FROM events WHERE distinct_id = \u0027<repo UUID>\u0027 AND event = \u0027coga_weekly_snapshot\u0027"}'
```

Expect zero. Keep sending disabled to avoid recreating the person. Never delete
the shared project as a way to delete one repo's data.
