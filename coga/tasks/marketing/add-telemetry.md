---
title: Add PostHog phone-home telemetry for V1 product-market-fit signal
status: in_progress
owner: nicktoper
agent: claude
contexts:
- coga/period-task
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 6 (review)
---

## Description

Give Coga a basic product-market-fit signal: how many repos run it, how many
work tickets each has, and whether those tickets move. Ship a weekly,
deterministic `phone-home` recurring battery: one `coga_weekly_snapshot`
attempt per run, and no other event. Send it to the existing FastJVM PostHog
project `606347` shared with Multiply (see the 2026-09-22 decision below).
Telemetry defaults on; `[telemetry] enabled = false`
in shared or local config disables telemetry delivery and its Slack receipt.
Ordinary commands do not capture events.

**Owner decisions, nicktoper, attended session 2026-09-20:** reverse the
principles #5 telemetry ban; accept a small/biased sample; identify the repo
with committed state shared by clones; run weekly Monday morning; exclude
recurring housekeeping from counts and movement; accept lost events with no
retries; define movement as forward advances
plus completions because final `bump` and `mark done` have identical audit
messages. These choices are settled. No additional metrics.

**Owner decisions, nicktoper, attended session 2026-09-22:** Coga installs no
scheduler, so a recurring battery only reaches repos whose operator runs
sweeps; the owner accepts that it measures *repos with an active sweep*, not
the installed base. Accordingly, drop the `coga_installed` event (it could
only ever mean "first sweep") and all install-attempt state. The single event
is a weekly usage snapshot, not a liveness heartbeat, so it is named
`coga_weekly_snapshot`; it carries the version/platform fields
(`os_name`, `os_version`, `python_version`) that the install event used to
carry. A repo's first reporting run is its earliest snapshot row.
Disclosure and docs must say plainly that this is not an install count.

Same session: **reuse Multiply's PostHog project** instead of creating a Coga
one — both are temporary, low-volume trackers and the owner wants one
dashboard for now. Project: organization `FastJVM`
(`01a09710-ae22-0000-75fe-78a6a6f047f1`), US Cloud, project id `606347`
(currently named "Default project"), IP discard on and GeoIP transformation
disabled per `multiply/infra/posthog/README.md`. Capture key source:
`op://coga/multiply-posthog-project-key-production/password`. Accepted
tradeoff: Coga is a public AGPL repo, so embedding the constant publishes
Multiply's write-only capture key; anyone can then inject spam events into
the shared project, and rotating the key breaks already-shipped Multiply
builds. Coga rows are separated by the `coga_` event-name prefix. Moving to a
dedicated project later is a new key constant plus a Coga release; no config
option is added for it.

### Acceptance criteria

- [ ] Fresh installed-package `coga init` delivers the battery and disclosure.
  Every due operator sweep, including the first, attempts exactly one
  `coga_weekly_snapshot` without an agent. Schedule is `0 7 * * 1`, as for
  branch-sweep. Coga installs no scheduler; repos that never sweep never
  report, and nothing is sent by download or by `init` itself.
- [ ] The same random repo UUID survives subsequent runs and a synced clone.
  State remains legible in the recurring template blackboard. Quiet, disabled,
  failed-delivery, and development-suppressed runs update the run marker
  without a stale-state alert. Disabled/suppressed runs mint no identity.
- [ ] Counts cover non-recurring tasks in both supported task shapes, grouped
  into all seven lifecycle statuses with explicit zeros. Movement counts only
  the three documented forward/completion message forms. Tests pin scope,
  grammar, cursor baseline, quiet runs, and rewrite/truncation behavior.
- [ ] The actual HTTP serializer passes exact envelope/property-set assertions
  for the single event, including types and provenance. Sentinel private
  content seeded in tasks/config/logs appears nowhere in the request.
- [ ] Shared/local config precedence is tested, including local true overriding
  shared false; malformed tables, unknown keys, and non-boolean values fail
  at config load. False exits before identity, capture-worker creation, or
  telemetry Slack receipt. Existing git and lifecycle notifications retain
  their own switches; telemetry false is not a global network-off switch.
- [ ] Transport failures, including stalled DNS, return within the specified
  deadline, cause one bounded warning on the period blackboard, and do not
  fail the task. No retries, redirects, queue, or next-run replay. Slack
  failures cannot affect capture or task completion.
- [ ] Automated tests, CI, source/editable Coga installations, and targets
  inside a Coga development checkout (including `example/`) cannot deliver to
  production. Installed release verification uses a wheel outside those trees.
- [ ] Parent blackboard writes use fence-aware compare-and-swap under the
  publication barrier and explicitly sync the parent path. Tests with a local
  bare remote prove the committed state reaches the control branch and is
  read unchanged by a second checkout; unrelated dirty files stay untouched.
- [ ] Policy/context updates, disclosure, runbook, and every packaged twin
  land with implementation. The PR includes exact verification commands and
  the owner-run HogQL proof below. A capture HTTP success is not acceptance:
  the owner must query the snapshot rows in project `606347` at review.

### Proposed shape

#### Package, battery, and config

Add `src/coga/telemetry.py` with `run_phone_home_recipe(cfg, argv)`, a small
closed payload builder, cursor/state helpers, and bounded delivery helpers.
Register exactly `phone-home` in `src/coga/runner.py`, `RECIPES`. This is the
reviewed, co-versioned recurring recipe contract, not plugin discovery or
per-command instrumentation. `coga run phone-home` takes no public options,
uses the configured repo and its template state, and returns 0 on delivery
failure/suppression; unexpected argv or corrupt local state fails visibly
before sending. Outside a period task, reports go to stdout rather than
inventing a task. Do not add a Typer command or alias.

Add `coga/recurring/phone-home/{ticket.md,ticket.py}` and their exact packaged
twins under `src/coga/resources/templates/coga/recurring/phone-home/`.
The shim calls `runner.run_recipe(load_config(), "phone-home", [])`, checks
its result, then subprocesses `python -m coga.cli bump $COGA_TASK_SLUG`.
Add `coga/workflows/phone-home/run.md` and its packaged twin: one agent-owned
step, `send`, with `skills: []`; all deterministic work is in the shim.
Attach the new `coga/telemetry` contract to the template. Seed the parent
blackboard without an identity and declare only `state_keys: [period_state]`
(rendered as a multiline YAML list). No stable identity or boolean gets its
own state key, because those correctly remain unchanged across runs.

In `src/coga/config.py`, add `Config.telemetry_enabled`, resolution parallel
to `_resolve_git_enabled()`, shared and local top-level admission, and the
fixed nested schema containing only boolean `enabled`. Missing means true;
local wins. The implementation updates the shipped config template's
`[telemetry]` disclosure with the default, recipient, cadence, data boundary,
and opt-out. Do not edit this working repo's `coga.toml` or `coga.local.toml`:
this session's boundary remains in force; release-template edits provide the
fresh-init behavior. No key, host, cadence, or test endpoint config options.

#### Scope and movement

Use `src/coga/tasks.py`, `list_tasks()` / `read_ticket()`, excluding refs equal
to `recurring` or under `recurring/`. Keep drafts, parked v2 tickets, and
terminal tickets still on disk: this is the current inventory, not a lifetime
count. The discovery API already excludes template names, README files, and
attachments. Invalid tickets are not silently assigned an invented status:
report a local warning and skip that snapshot rather than send partial
counts.

Count one movement for a complete, valid audit-envelope line whose ref is
outside the recurring namespace and whose message starts with one of:

- `advanced to step <positive integer> (<step name>)`, with the producer's
  optional handoff/FYI suffix;
- `task done`, either ending there or followed by the standard ` — ` FYI;
- `auto-bumped on merge of PR #<integer> → done`, or the exact fallback
  `auto-bumped on merge of the linked PR → done`.

Ignore rewinds, creates, launches, marks other than done, blocks/unblocks,
prose containing these strings, malformed lines, and all housekeeping refs.
Count deleted tasks' transitions from the log even though they no longer
appear in inventory. Do not change any audit producer. Call this property
`movement_count`, not `bump_count`.

Persist a byte offset plus SHA-256 of the consumed complete-line prefix.
On the first enabled run, baseline at the current complete-line EOF and send
movement zero; do not label lifetime history as one week's activity. On
subsequent runs, verify the prefix and count new complete lines through the
captured EOF. Leave a trailing partial line for next time. Deduplicate exact
lines within that new suffix. If the file shrank or the prefix changed after
a merge/rewrite, baseline at its new EOF, send movement zero, and leave a
local warning. A missing log is an empty baseline. This deliberately loses
some movement around rewrites instead of recounting old history. Union
merges can still append old lines after a valid prefix, and identical real
transitions in the same minute can collapse: this is an approximate signal,
not an audit ledger or exactly-once count. Never transmit cursor hashes or
log data. Tests cover equal timestamps and out-of-order new timestamps.

#### Persistent state and ordering

Store a compact, readable single-line JSON value after `period_state:` in
the parent blackboard: schema version, monotonically increasing run number,
nullable repo UUID, and byte offset/prefix digest. No delivery outcome is
persisted: nothing is ever retried. Each invocation increments run number even when offset
cannot move; that is what satisfies the declared-state check on quiet runs.
Preserve unrelated blackboard prose and every byte above the fence.

Under `git.state_publication_barrier()`, capture the parent bytes, read with
`taskfile.read_blackboard(expected_bytes=...)`, and replace through
`taskfile.replace_blackboard(expected_bytes=...)`. The shipped template has
a fence; there is no reason to use the non-CAS `upsert_blackboard()` here.
Publish only this parent file with `git.sync_paths()` and the parent as anchor;
do not assume the period's later bump stages its parent. Ordinary sync's
no-git/disabled-git behavior still applies, with local state authoritative.

Ordering: gate delivery first; on disabled/development-suppressed runs update
only the local run marker and baseline cursor, sync, and return. On an enabled
run with valid input, mint a UUID v4 if absent, prepare the payload, and
persist cursor/run number before spawning transport, then attempt the one
snapshot. Nothing is written back after transport except the period report.
No failure rolls back the cursor or makes an event eligible for replay. A crash after reservation can
lose an event; this is the accepted no-retry tradeoff. Disabled runs baseline
the cursor, but no suppression marker is persisted (owner, 2026-09-22): the
first enabled run after re-enabling counts log lines appended since the last
disabled sweep, including ones from while telemetry was off. Only that
aggregate count leaks. Document this in the `coga/telemetry` context and the
disclosure ("disabling stops sending; movement from the gap may appear in the
first count after re-enabling"); test the behavior rather than prevent it.

Compare-and-swap/local locking and the sweep's existing control refresh
protect ordinary serialized runs. Committed identity makes synced clones
agree; independently run unsynced clones before the first identity is
published can still mint different identities. Do not promise distributed
exactly-once delivery or add distributed coordination in this PR. Preserve
local evidence of publication failure through the existing sync behavior.

#### Closed wire contract

Use a direct HTTPS POST to the US capture endpoint
`https://us.i.posthog.com/i/v0/e/`, with TLS verification and no redirects.
Embed project `606347`'s write-only capture key in one constant in
`src/coga/telemetry.py`. No SDK enrichment. The exact JSON envelope is
`api_key`, `event`, `distinct_id`, `timestamp`, `properties`: fixed event
name, persisted repo UUID, and UTC occurrence timestamp. Identity, event
name, timestamp, and routing key are protocol fields; measured properties
contain only the following counts and bounded version/platform strings.

| Event | Exact properties |
| --- | --- |
| `coga_weekly_snapshot` | `coga_version`, `os_name`, `os_version`, `python_version`, `tickets_draft`, `tickets_active`, `tickets_in_progress`, `tickets_blocked`, `tickets_paused`, `tickets_done`, `tickets_canceled`, `movement_count` |

Counts are nonnegative integers, never booleans. Coga version comes from
installed package metadata, Python version from numeric interpreter version,
OS name from the closed `linux`/`macos`/`windows`/`other` vocabulary, and OS
version from only the leading numeric dotted release component (empty when
unavailable). Never use `platform.platform()`, hostname, full kernel build
text, command arguments, environment values, or repository metadata. Bound
version strings to 64 ASCII characters; reject invalid package-version text
rather than passing arbitrary strings through. No dynamic property maps,
`$set`, owner/agent names, paths, slugs, titles, bodies, blackboards, remotes,
branches, Slack IDs, or raw log/error text. No extra `$lib` properties.

The project must discard client IP and have GeoIP disabled. The network
peer necessarily sees the connection's source IP; disclosure must not claim
otherwise. Do not opt into personless processing: retain a person keyed only
by the opaque repo ID so the documented persons deletion procedure applies.
No identify/alias calls or person attributes. Query stored properties during
manual acceptance to check server enrichment; never expand the client
allowlist to excuse unexpected fields.

#### Bounded transport, receipt, and test isolation

Run capture in a short-lived private Python worker with a parent-enforced
3-second wall deadline per event, including DNS/connect/read. Kill and reap
on expiry; a socket timeout alone is insufficient. Send the prepared payload
through stdin, not argv; the child reads the constant key, accepts only the
closed schema, and performs one POST. Keep the worker private to this module,
not an extra public recipe/config surface. Do not print credentials, request
bodies, response bodies, or raw exceptions. Return a small fixed outcome
(accepted, rejected, network-error, timed-out) to the parent. Bound any read
of response data. Maximum capture wait is three seconds per run, apart from
process teardown overhead.

After capture, format the same keyless event envelope, excluding only
`api_key`, as a single Slack receipt with the attempt's outcome. Say
"attempted / HTTP accepted", never "ingested". Use the existing notification
channel through `notification.post(..., fatal=False, record_failure=False)`
in a separately bounded worker (3 seconds); skip if Slack is disabled. A
receipt can fail or time out without undoing state or failing the task. The
parent writes one compact period report with counts/outcomes and at most one
aggregated delivery warning using `blackboard.append_blackboard_report()`.
Keep local validation/state errors distinct from tolerated transport errors.

Production admission must run both before worker creation and in the worker:
false config; presence of `PYTEST_CURRENT_TEST`; an active `CI` environment;
an imported module living under this project's `src/coga/` development tree;
or a target/cwd ancestor containing this project's `pyproject.toml`
(`project.name = "coga"`) plus `src/coga/runner.py` and `tests/` all suppress
production delivery. Resolve symlinks; check both import origin and target,
so a release wheel invoked against `example/` or a linked source worktree is
also suppressed. No development bypass environment variable or CLI switch.
Document that editable installs intentionally do not contribute PMF data.

Tests use injected fake sender/clock/identity providers and intercept the
transport's HTTP function; no test obtains a production credential. Add an
autouse production-transport rejection guard in `tests/conftest.py`, inherited
pytest/CI gates for subprocess tests, and direct tests of all admission cases.
Test worker hangs by substituting a local sleeping worker, not sinkholing the
real endpoint. Installed-artifact automation must preserve the CI/pytest gate
and use fake transport; manual live proof uses an ordinary installed wheel,
a fresh repo outside source trees, and no test/CI environment. This is a
transport seam, not another product configuration surface.

#### Documentation ownership and verification

Add `docs/contexts/coga/telemetry/SKILL.md` and its bootstrap twin as the
behavioral owner: wire boundary, admission, state/cursor, approximate metrics,
loss semantics, and recipe contract. `coga/principles` owns the dated policy
reversal (the historical 2026-06 rejection now lives in
`docs/archive/superseded-decisions.md` "Telemetry"; append the 2026-09-20
reversal); `coga/configuration` owns config changes and `coga/agents` ("Who
Coga acts as") owns identity changes (both formerly in `coga/architecture`).
Update their twins, the ban mentions in `coga/usage`, README disclosure, and
opt-out navigation in `docs/README.md` (`docs/operations.md` was deleted). Update recurring/code
contract inventories where they list fixed recipes. Grep active docs/contexts
for stale absolute bans and fix summaries in the same PR.

Add the lazy operator procedures (placed per `coga/knowledge`: a topic under
`docs/contexts/` or a skill; `docs/` outside `contexts/` now holds only
evidence, design and archive pages): project setup/read-back,
key source and release-based rotation, query commands, and the persons API
deletion procedure, all against shared project `606347`: link to Multiply's
runbook for project settings rather than restating them, filter every Coga
query by `event = 'coga_weekly_snapshot'`, and document the switch-to-a-
dedicated-project path (new constant + release). Link to the
context for the schema rather than duplicating it. Point marketing/distribution,
marketing/map, and build-the-launch-plan at the concrete contract if their
old placeholder descriptions remain. Existing marketing contexts have no
packaged twin. Keep every newly added or edited shipped twin byte-identical initially.
The parent template is the one deliberate runtime exception: this repo's
sweeps will change its blackboard while the packaged seed must stay identity-
free. Once those bytes diverge, document that live path in
`tests/test_packaging.py`, `INTENTIONALLY_DIVERGENT_TWINS`, with the runtime-
state reason; add a focused test requiring its above-fence bytes to match and
the packaged blackboard to remain an unused seed. Do not exempt any other
file or copy a real repo identity/cursor into the release. Follow the existing
stale-exemption check: do not add an exemption while the full files match.

Implement tests in `tests/test_telemetry.py`, plus config, init, runner,
recurring-shim, and packaging coverage in their existing test modules. Test
config false before identity/worker/receipt, source and CI suppression,
first/next/quiet/disabled/re-enabled runs, persisted clones, accepted/rejected/
hung sends, loss without replay, invalid task/state inputs, cursor changes,
exact serialization, and Slack independence. Finish with `python -m pytest`,
`coga validate --json`, and `git diff --check`; report baseline failures
separately. The design step itself changes only this ticket.

Project inputs are settled (2026-09-22 decision above); no new project or
vault item is created. At implement, source the constant with a checked
`op read 'op://coga/multiply-posthog-project-key-production/password'`
(nonempty; never echo it or pass it as a shell argument), or have the owner
paste it locally if desktop authorization is unavailable. Do not read or
expose the operator credential (`~/.posthog/credentials.json`); the capture
constant is deliberately public/write-only. Require `project-get` to report
project `606347` before any verification query or deletion. Multiply's
runbook lists the event kinds expected in the project; note as a follow-up
(separate repo, not this PR) that `coga_weekly_snapshot` rows now appear
there too.

At implementation/open-pr, prepare a clean wheel-install smoke procedure and
put exact `posthog-cli api call --json execute-sql '<JSON>'` commands in the
PR using single-quoted shell JSON (or a JSON file) so `$ip` is never shell
expanded. The owner runs a first eligible sweep, reads the repo UUID from
its template, then queries:

```sql
SELECT event, distinct_id, timestamp, properties,
       JSONExtractKeys(properties) AS property_keys
FROM events
WHERE distinct_id = '<repo UUID>'
  AND event = 'coga_weekly_snapshot'
ORDER BY timestamp
```

The first-run row must exist, match the prepared payload values (movement
zero), and contain no IP, GeoIP, or unallowlisted measured fields. Record any
service-owned routing metadata separately from client properties; unexpected
enrichment blocks acceptance until explained and corrected. Run a later
snapshot with a known advance/completion and confirm a second row with the
same repo UUID and the expected `movement_count`. Set local telemetry
false, run again, and query the same repo UUID over the new time window to
confirm no new capture row; pair this with the automated no-worker/no-HTTP
assertions, since absent rows alone do not prove absent requests. Record the
query text/results and wheel version in the PR. No dashboard build required;
at most one saved insight per agreed quantity. Snapshots, not a sum of all
historical status counts, supply each repo's current inventory.

### Out of scope

Per-command instrumentation; launches, agent/session/token metrics; recurring
housekeeping metrics; prompts/first-run consent dialogs; SDKs or queues;
retries/replay; exact distributed delivery or a new audit format; hosted
operational state; runtime endpoint/key options; new scheduler; retention or
deletion tooling; more than three saved insights; any install/init-time
event or installed-base count. A missed snapshot is accepted and must not grow
a retry system. This is one bounded implementation PR plus
owner setup and manual verification gates.

## Context

- `src/coga/runner.py`, `RECIPES` / `run_recipe()`, dispatch fixed recipe
  functions and record failures on the period blackboard. The shim in
  `coga/recurring/blocker-reminders/ticket.py` is the minimal existing caller.
- `src/coga/config.py`, `load_config()` / `_resolve_git_enabled()` /
  `_ALLOWED_SHARED_SECTIONS` / `_ALLOWED_LOCAL_SECTIONS`, show why both
  table admission and shared/local boolean resolution must change together.
- `src/coga/commands/bump.py`, `bump()`, passes intermediate `advanced to step`
  messages to `src/coga/bump.py`, `advance_step()`, and final `task done` to
  `src/coga/mark.py`, `mark_done()`. `src/coga/commands/mark.py`, `done()`, uses
  the same final message. `src/coga/autoclose.py`, `_try_bump_one()`, passes the auto-merge
  completion message to the same finalizer; its PR label is either `PR #N`
  or `the linked PR`. The seed's `completed` spelling was not the current grammar.
- `src/coga/logfile.py`, `append_log()`, owns the timestamp/ref/actor envelope;
  `iter_log_messages()` returns parsed ref/message pairs, not cursor positions.
  Its union-merge contract permits duplicates and unsorted timestamps.
- `src/coga/tasks.py`, `list_tasks()` / `read_ticket()`, handles file and
  directory tasks. `src/coga/lifecycle.py`, `VALID_STATUSES`, owns the seven
  statuses. Keep aggregation derived from these APIs, not a second discovery
  system or workflow-status approximation.
- `src/coga/period_state.py`, `write_snapshot()` / `parse_keys()` /
  `stale_keys()`, snapshots and compares single-line parent blackboard values.
  Stable flags declared separately would incorrectly warn every week.
- `src/coga/taskfile.py`, `replace_blackboard()`, checks `expected_bytes` and
  preserves the header. `src/coga/git.py`, `state_publication_barrier()` /
  `sync_paths()`, provides the explicit-path publication path; a period's
  `sync_task_state()` scopes its commit to its own files unless given extras.
- `src/coga/notification/__init__.py`, `post()`, dispatches existing Slack
  configuration and supports nonfatal, non-recording calls; its socket timeout
  in `src/coga/notification/slack.py`, `SlackChannel`, is not a DNS deadline.
- `docs/contexts/coga/recurring/templates/SKILL.md` (authoring/promoting a
  template, the `ticket.py` completion contract, cross-run state surfaces),
  `docs/contexts/coga/recurring/scheduling/SKILL.md` (first-firing and
  external scheduling), and `docs/contexts/coga/period-task/SKILL.md`
  (last-run state in the template's blackboard); formerly sections of
  `docs/contexts/coga/recurring/SKILL.md`. New templates are retroactively due on the first
  sweep, no agent runs if the shim closes its step, and scheduling is external.
- `docs/contexts/coga/knowledge/SKILL.md` (formerly the "Where a fact lives:
  docs vs contexts" section of `coga/architecture`) determines the new
  behavior-context / operator-runbook split. Principles,
  codebase, current-direction, project-stage, and `docs/vision.md` (now
  `product/vision`) informed
  the design. The telemetry reversal is an explicit owner amendment.
- Reference implementation and operations: `/home/n/Code/multiply/infra/posthog/README.md`
  (Settings, Keys, CLI, Deleting a person), and its
  `coga/tasks/v1/telemetry/posthog/3-client.md` and
  `4-embed-the-capture-key-as-a-constant.md`. Reuse its project `606347` and
  capture key (owner decision 2026-09-22); copy the operational shape, never
  its product payload or its operator credential.
- PostHog's current [API overview](https://posthog.com/docs/api) documents
  the public US capture host and project-token/private-credential split;
  verify concrete capture acceptance with the queried-row procedure above.
- Follow `code/implement` / `code/open-pr` for branch and PR bookkeeping; this
  design session creates neither. `tests/test_packaging.py` discovers twins
  from the packaged tree, and `tests/test_recurring_shims.py`,
  `test_shim_calls_the_registered_recipe_and_bumps_through_the_cli()`, pins
  the registry-to-bump shim shape.

<!-- coga:blackboard -->

## Design decisions — 2026-09-20

Owner confirmed in this attended session:
- Exclude recurring housekeeping from inventory and movement; no extra metrics.
- One lifetime install attempt and one heartbeat attempt per weekly run;
  accept lost events without retries. *(Superseded 2026-09-22, see below.)*
- Movement means forward advances plus completions, including explicit done
  and auto-close; keep the current audit format.

The existing approved reversal, weekly schedule, repo identity, default-on
switch, new Coga project (superseded 2026-09-22: reuse `606347`), and owner
verification gates remain settled.
The attached period-task context does not make this marketing ticket a
recurring period; its design notes belong on this blackboard.

## Revision — 2026-09-22 (owner, attended ticket edit)

A recurring battery cannot observe installs: Coga ships no scheduler, so only
repos whose operator sweeps ever report. Owner accepted that scope and:
- dropped `coga_installed` plus `installed_attempted`/`installed_sent` state;
- renamed `coga_heartbeat` → `coga_weekly_snapshot` (it is a usage snapshot,
  not a liveness ping);
- moved `os_name`, `os_version`, `python_version` onto the snapshot.
Body updated throughout (acceptance, state, wire table, transport wait now 3 s,
HogQL proof, out of scope). Evaluator finding 1 (no-backfill after
suppression) still stands; the "install-result write" and "skips install"
parts of the optional recommendations are now moot.
- Finding 1: owner accepts the re-enable backfill as minor; documented, not
  prevented.
- Reuse Multiply's PostHog project `606347` (one dashboard; both trackers are
  temporary/low volume); accepts publishing its write-only key in public Coga.
  Project ID/key-item prerequisites are therefore resolved.

## Handoff

Written specification is under Description (acceptance criteria, proposed
shape, out of scope) with symbol-based implementation references in Context.
Notable implementation traps: final bump and mark done both log `task done`;
union-merged logs invalidate timestamp-only cursors; declare only the changing
`period_state` key; explicitly publish parent state; bound DNS with a worker
deadline; gate both source imports and source targets against production.
The cursor reset/loss and unsynced-clone limitations are explicit, not claims
of exact delivery. No code, branch, PR, credential read, or capture request.
Pre-existing `coga/log.md` changes were left for CLI writers.

## Open Questions

Project prerequisites resolved 2026-09-22: reuse Multiply's project `606347`,
key at `op://coga/multiply-posthog-project-key-production/password` (see
Description). Evaluator finding 1 resolved 2026-09-22 by narrowing the
promise: the post-re-enable backfill is documented, not prevented (see
Persistent state and ordering). No open prerequisites remain.

## Design validation

- `git diff --check`: passed.
- `PYTHONPATH=src python` structural check: exactly Description and Context
  top-level headings above the single fence; fence-aware blackboard read passed.
  The initial check without PYTHONPATH could not import the local package;
  rerunning with the source path resolved that environment issue.
- `coga validate --json`: no issues for marketing/add-telemetry; 222 OK,
  52 unrelated warnings, four existing unsynthesized-draft-blackboard errors
  (clean-up-all-the-working-trees, v2/autotrigger-ticket-type,
  v2/measure-relay-prompt-scope-and-agent-precision,
  v2/use-worktree-when-starting-a-dev-task). No unrelated repairs made.
- Added the deliberate runtime-parent/packaged-seed divergence handling;
  packaged telemetry identity must remain empty even after this repo runs it.
- No runtime tests run for this ticket-only design edit. Ready for the
  independent evaluate-design step; owner setup remains at review-design.

## Evaluator review

Cold review, 2026-09-20. **Not ready for implementation until finding 1 is
resolved at owner review-design.** The settled telemetry policy reversal,
metrics, weekly cadence, and accepted delivery loss are not being reopened.
The project ID and 1Password item reference remain the separate, already
specified owner prerequisites.

### Must resolve before implementation

1. **The specified state cannot enforce no backfill after suppression.**
   Description → Persistent state and ordering requires that suppression
   followed by re-enabling not backfill the disabled interval, but its state
   fields contain no prior-admission/suppression marker. Example: an existing
   enabled repo runs disabled Monday (cursor baselined), advances a work ticket
   Tuesday while still disabled, then re-enables before the next Monday run.
   Scope and movement would count Tuesday's line. Incrementing the run number
   and moving the cursor only on disabled sweeps cannot distinguish this from
   an ordinary enabled interval. Config is read from current files by
   `src/coga/config.py::load_config`; `src/coga/logfile.py::append_log` records
   task transitions, not telemetry-toggle history.
   Specify a persisted suppression/resume state and zero-baseline the first
   resumed heartbeat (accepting loss of the intervening enabled portion), or
   explicitly narrow the no-backfill promise. Also document that an off/on
   toggle entirely between recipe invocations is unobservable without new
   instrumentation. Add a regression with movement *after* the last suppressed
   sweep and before re-enabling, rather than only movement before that sweep.

### Optional implementation recommendations

- **Make publication lock boundaries explicit.**
  `src/coga/git.py::sync_paths` acquires `state_publication_barrier` itself;
  the barrier opens a new descriptor and takes blocking `flock`, with no
  reentrancy handling. Calling it inside the proposed read/CAS/write barrier
  deadlocks. A disposable subprocess using the actual barrier acquired the
  outer lock and timed out entering the inner lock after two seconds; it was
  killed and reaped. State explicitly that CAS mutation exits its barrier
  before calling the public publisher, and that the install-result write
  re-reads current state under a fresh barrier rather than restoring a stale
  pre-transport snapshot. Include a bounded end-to-end publication test.

- **Pin the invalid-inventory transition.**
  Scope and movement says to warn and skip the heartbeat, while Persistent
  state says every invocation advances the run marker and only describes
  valid-input and suppressed paths. Specify whether invalid inventory also
  skips install, whether its cursor advances or stays, and whether the shim
  completes successfully. `src/coga/tasks.py::list_tasks` can itself raise
  `DuplicateTaskSlugError` before `read_ticket`; cover that case as well as an
  invalid status. `src/coga/period_state.py::parse_keys` / `stale_keys` compare
  the declared value, so a successful skip with unchanged state would produce
  an unrelated stale-state alert.

### Evidence and scope

Checked the ticket body independently, then its handoff; the frozen workflow
matches `src/coga/resources/templates/coga/bootstrap/workflows/code/design-then-implement.md`
and hands this step to owner review. Checked the principles, architecture
(including docs/context ownership), codebase microkernel contract, current
posture, recurring state/shim contract, config schema/resolver, task discovery,
audit producers/parser, notification API, fence-aware CAS API, publication
barrier/publisher, recurring-shim tests, and packaging twin/exemption checks.
The fixed recipe is an allowed co-versioned command contract. The documented
movement producer forms, Monday schedule, explicit parent publication, and
single changing state key match the source. The attached period-task context
is inapplicable to this marketing ticket, as the existing blackboard notes.

PostHog's [API overview](https://posthog.com/docs/api) and
[capture reference](https://posthog.com/docs/api/capture), checked 2026-09-20,
support the US public capture route, project-token/private-credential split,
and top-level distinct ID. HTTP acceptance does not prove ingestion, so keep
the owner query gate. Read Multiply's operator runbook for operational shape;
no credentials were read and no capture or project mutation was attempted.

Verification: actual nested-barrier timeout probe above; `git diff --check`
and a fence-aware check preserving all pre-review ticket/blackboard bytes.
No runtime suite was needed for this review-only change. No ticket-body edit,
implementation, branch, or PR was produced. Existing log edits were left to
CLI writers. Findings are the handoff, not a reason to block or rewrite the spec.

## Dev

pr: https://github.com/FastJVM/coga/pull/880
branch: phone-home
worktree: /tmp/coga-phone-home

## Implementation decisions — 2026-09-22

Owner confirmed implementation and invalid-inventory handling: increment the run
marker, preserve identity/cursor, warn and complete without a snapshot.
Current `src/coga/git.py::state_lock` is reentrant and `publish` is the explicit
path publisher; use these successors to the design's removed barrier/sync APIs.

## Implement handoff — 2026-09-22

Implemented and committed as `97ce27f2e` (Add weekly PostHog usage snapshots)
on `phone-home` in `/tmp/coga-phone-home`. Clean checkout, rebased onto
`origin/main` (`c2268b059`); the rebase added only unrelated task/log state.
No branch push or PR.

- Closed snapshot schema, default-on shared/local config, source/CI/test gates,
  cursor/UUID reservation, bounded capture and independent Slack worker.
- Parent-only publication uses current `git.state_lock` / `git.publish`;
  real bare-remote tests prove clone identity and unrelated dirty-file isolation.
- Deterministic battery/shim and unused identity-free packaged seed; all shipped
  twins match. No premature runtime-parent divergence exemption.
- Policy reversal, behavioral context, README/config disclosure and operator
  runbook landed. Marketing surfaces point to the concrete contract.
- Checked, owner-authorized 1Password read embedded the public capture constant
  directly without printing it. No production capture, project query, deletion,
  dashboard or remote project mutation was performed.

Verification (feature checkout unless noted):

- Isolated environment: `python -m venv /tmp/coga-phone-home-venv`, then
  `/tmp/coga-phone-home-venv/bin/python -m pip install -e '.[test]'`. Ambient
  Python lacked tomlkit; dependency install succeeded outside the network sandbox.
- `/tmp/coga-phone-home-venv/bin/python -m pytest`: **2813 passed**.
- After the state-only rebase:
  `/tmp/coga-phone-home-venv/bin/python -m pytest tests/test_telemetry.py tests/test_config.py tests/test_runner.py tests/test_recurring_shims.py tests/test_init.py tests/test_packaging.py -q`: **397 passed**.
- Includes an installed-wheel init/suppressed-first-snapshot smoke outside
  source trees, a real headless shim completion, HTTP serialization interception,
  hung-worker kill/reap, false-before-worker/identity/receipt, publication CAS,
  clone persistence, exact cursor grammar and private-content sentinels.
- `/tmp/coga-phone-home-venv/bin/coga validate --json` from feature `coga/`:
  237 OK, 50 warnings, two pre-existing unsynthesized-draft-blackboard errors
  (clean-up-all-the-working-trees and v2/autotrigger-ticket-type).
- `env -u SLACK_WEBHOOK_URL /tmp/coga-phone-home-venv/bin/coga validate --json`
  from feature `example/coga/`: 4 OK, zero issues. The unset removes an unrelated
  ambient legacy Slack variable, not a test/telemetry admission gate.
- `git diff --check`: passed. `git merge-base --is-ancestor origin/main HEAD`:
  passed. `git status --short`: empty.
- Earlier full-run failure was a collected template path removed during that
  run; the fresh full run above passed. No unrelated baseline repairs.

Open-pr/review handoff: copy the exact wheel smoke and single-quoted HogQL
commands from `docs/telemetry.md` into the PR. Owner must verify `project-get`
reports 606347, then supply first/later/disabled queried-row evidence, payload
receipt, wheel version/hash, and explain stored enrichment. HTTP acceptance
is not ingestion acceptance. This remains the owner review gate.
Separate-repo follow-up: Multiply's PostHog runbook event catalog should mention
`coga_weekly_snapshot`; that repo was not edited.


## Self-QA — 2026-09-22

Owner requested implementation review in the attended open-pr session. Direct
manual review of `origin/main...phone-home` returned with one P2 finding;
no external review remains in flight. Reviewed payload/schema, production
admission, worker deadlines, config precedence, parent CAS/publication,
recurring dispatch, tests, disclosure and operator proof instructions.

**P2 — movement parser rejects valid producer output.**
`src/coga/telemetry.py:46-48` disallows whitespace in the actor/ref envelope,
parentheses inside a step name, and whitespace in the handoff operator.
Current config accepts `user = "Jane Doe"`; `append_log` writes
`[human:Jane Doe] task done`, and the canonical `iter_log_messages` reader
returns that completion, but `_movement` returns false. Thus affected users'
completions/advances silently disappear from the PMF movement count. Workflow
step names also only require a nonempty string, so `review (owner)` produces a
valid advance the new regex rejects. Align the telemetry grammar with producer
accepted values while retaining full-line validation and recurring exclusion;
add producer-based regression coverage. This finding is unresolved; no code
was changed, no PR opened, and no workflow bump performed.

Verification in `/tmp/coga-phone-home`:
- `/tmp/coga-phone-home-venv/bin/python -m pytest tests/test_telemetry.py tests/test_config.py tests/test_runner.py tests/test_recurring_shims.py tests/test_init.py tests/test_packaging.py -q`: 397 passed (17.00s).
- `git diff --check`: passed; feature checkout clean.
- Disposable local config + actual `append_log` reproduction confirmed the
  spaced-actor omission. Unset the unrelated ambient legacy SLACK_WEBHOOK_URL
  for this local-only probe after config rejected it; no telemetry delivery or
  other network operation was invoked.

Owner live wheel/PostHog queried-row acceptance remains pending as designed.
Hold open-pr pending correction or explicit owner deferral of the P2 finding.


## Self-QA correction — 2026-09-22

Owner authorized correcting the P2 finding in this attended session. Fixed and
committed as `b35aa9777` (Count valid audit names in weekly telemetry).
The parser accepts spaced actor/handoff names and parenthesized step names;
blank fields, malformed envelopes and recurring movement remain excluded.
The regression creates a task and runs two actual CLI bumps, including the
handoff to Jane Doe and final completion, then verifies movement_count is 2.
Updated both telemetry-context twins. Direct follow-up review returned with
no further actionable findings; the earlier P2 is resolved and no review is
in flight. No production capture or query was performed.

Verification from `/tmp/coga-phone-home`:
- `/tmp/coga-phone-home-venv/bin/python -m pytest`: 2820 passed in 197.42s.
- `/tmp/coga-phone-home-venv/bin/coga validate --json` from `coga/`: 237 OK;
  existing unsynthesized-draft-blackboard errors for clean-up-all-the-working-trees
  and v2/autotrigger-ticket-type, plus unrelated warnings.
- `env -u SLACK_WEBHOOK_URL /tmp/coga-phone-home-venv/bin/coga validate --json`
  from `example/coga/`: 4 OK, no issues.
- `git diff --check`: passed; feature checkout clean.

Fetched origin/main; changes since implementation are generated task/log
state only. The PR body below carries the exact installed-wheel procedure and
single-quoted HogQL commands. Live PostHog evidence remains the owner review
requirement; it has not been claimed as complete.

## PR

Operator sweeps now attempt one weekly `coga_weekly_snapshot` with non-recurring ticket inventory, forward/completion movement, and bounded version/platform fields. The deterministic battery defaults on, persists a clone-shared UUID and cursor in its parent blackboard, and measures repos with active sweeps—not installations.

Delivery uses the existing FastJVM/Multiply PostHog project 606347, a closed payload, and separate three-second capture/Slack workers with no retries. Shared/local opt-out and source/test/CI suppression run before worker creation. The public write-only key is intentionally embedded under the owner's recorded decision.

Policy and behavioral contexts, packaged twins, init disclosure, and the operator runbook accompany the implementation. Review found and fixed dropped movement for spaced actor/handoff names and parenthesized step names; a regression now exercises real CLI advances and completion. Manual review and a follow-up pass over the fix have returned; no review remains in flight.

### Automated verification

Feature checkout: `/tmp/coga-phone-home`, isolated editable test environment: `/tmp/coga-phone-home-venv`.

- `/tmp/coga-phone-home-venv/bin/python -m pytest`: **2820 passed** in 197.42s.
- `/tmp/coga-phone-home-venv/bin/coga validate --json` from `coga/`: existing draft-blackboard errors for `clean-up-all-the-working-trees` and `v2/autotrigger-ticket-type`; no telemetry issue.
- `env -u SLACK_WEBHOOK_URL /tmp/coga-phone-home-venv/bin/coga validate --json` from `example/coga/`: 4 OK, zero issues. The unset removes an unrelated ambient legacy Slack variable.
- `git diff --check`: passed.

Coverage includes exact HTTP serialization/private-content sentinels, admission, deadlines, no replay, config precedence, a headless shim, installed-wheel init under test suppression, and parent-only publication to a real bare remote with second-checkout identity read-back.

### Owner acceptance still required

No production capture or PostHog query was run during implementation/review. Before any query, run:

```sh
posthog-cli api call --json project-get '{}'
```

Stop unless the returned project ID is 606347. At owner review, attach wheel version/hash, prepared payload receipt, exact query/results for first/later/disabled runs, and an explanation of any stored enrichment. HTTP success is not ingestion acceptance. The owner review gate remains open until this evidence is accepted.

### Clean installed-wheel proof

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
scratch repo before its first sweep, following [notification setup](operations.md).
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
run `coga run phone-home` directly from this installed wheel (or wait for the next
due sweep); it is the same recipe and reads the same parent. Query again with
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


Separate-repository follow-up: add `coga_weekly_snapshot` to Multiply's PostHog runbook event catalog.


## PR review assist — 2026-09-22

Owner approved the sole unresolved review request on PR #880: account for
phone-home in the sync notification inventory. Updated the live sync context
and packaged twin with the eighth template, weekly cadence, keyless receipt,
suppression and independent failure handling, linking to the telemetry contract.
Committed and pushed as `5336dddbfa2affb1d9144ed16eb306af0cf96a7e`; exact remote-tip
lease and post-push GitHub head equality verified. Replied to the review thread
without resolving it. No runtime change or production telemetry operation.

Verification in `/tmp/coga-phone-home`:
- `/tmp/coga-phone-home-venv/bin/python -m pytest tests/test_packaging.py -k 'live_and_packaged_copies_stay_identical or intentional_divergences_stay_real_and_explained' -q`: 2 passed, 15 deselected.
- `git diff --check`: passed. Inventory, relative context links, and receipt
  claims checked against the packaged templates and implementation.

Ticket remains in_progress on owner review; live wheel/PostHog acceptance
evidence remains pending. No bump, merge, or thread resolution.


## Owner review decision — 2026-09-22

Owner explicitly deferred the live wheel/PostHog acceptance proof: assume it
works for current review; owner will test later. This supersedes the requirement
to hold review pending first/later/disabled queried-row evidence. The live proof
has not been performed or passed; the documented procedure remains available
for the deferred check. Automated verification and the pushed review fix stand.
This instruction does not authorize a merge, thread resolution, or workflow
transition; the ticket remains on owner review.
