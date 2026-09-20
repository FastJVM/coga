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
step: 3 (review-design)
---

## Description

Give Coga a basic product-market-fit signal: how many repos run it, how many
work tickets each has, and whether those tickets move. Ship a weekly,
deterministic `phone-home` recurring battery: one `coga_heartbeat` per run,
plus one lifetime attempt at `coga_installed`. Use a new Coga PostHog project,
never Multiply's project. Telemetry defaults on; `[telemetry] enabled = false`
in shared or local config disables telemetry delivery and its Slack receipt.
Ordinary commands do not capture events.

**Owner decisions, nicktoper, attended session 2026-09-20:** reverse the
principles #5 telemetry ban; accept a small/biased sample; identify the repo
with committed state shared by clones; run weekly Monday morning; exclude
recurring housekeeping from counts and movement; accept lost events with no
retries, including a lost install event; define movement as forward advances
plus completions because final `bump` and `mark done` have identical audit
messages. These choices are settled. No additional metrics.

### Acceptance criteria

- [ ] Fresh installed-package `coga init` delivers the battery and disclosure.
  Its first due operator sweep attempts install and heartbeat without an
  agent; later runs attempt heartbeat only. Schedule is `0 7 * * 1`, as for
  branch-sweep. Coga installs no scheduler; install means first eligible
  telemetry run, not download or execution of `init` itself.
- [ ] The same random repo UUID survives subsequent runs and a synced clone.
  State remains legible in the recurring template blackboard. Quiet, disabled,
  failed-delivery, and development-suppressed runs update the run marker
  without a stale-state alert. Disabled/suppressed runs mint no identity and
  consume no install attempt.
- [ ] Counts cover non-recurring tasks in both supported task shapes, grouped
  into all seven lifecycle statuses with explicit zeros. Movement counts only
  the three documented forward/completion message forms. Tests pin scope,
  grammar, cursor baseline, quiet runs, and rewrite/truncation behavior.
- [ ] The actual HTTP serializer passes exact envelope/property-set assertions
  for both event kinds, including types and provenance. Sentinel private
  content seeded in tasks/config/logs appears nowhere in either request.
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
  the owner must query both rows in the Coga project at review.

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
report a local warning and skip that heartbeat rather than send partial
counts. Do not consume the install attempt until a valid payload is ready.

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
nullable repo UUID, byte offset/prefix digest, `installed_attempted`, and
`installed_sent`. The latter means HTTP acceptance only, never proven
PostHog ingestion. Each invocation increments run number even when offset
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
run with valid input, mint a UUID v4 if absent, prepare payloads, and persist
cursor/run number plus `installed_attempted=true` before spawning transport.
Then attempt install if newly claimed, followed by heartbeat regardless of
install failure. Save `installed_sent=true` only for an accepted install
response, without resetting the attempted flag. No failure rolls back the
cursor or makes an event eligible for replay. A crash after reservation can
lose an event; this is the accepted no-retry tradeoff. Suppression followed by
re-enabling must not backfill the disabled interval.

Compare-and-swap/local locking and the sweep's existing control refresh
protect ordinary serialized runs. Committed identity makes synced clones
agree; independently run unsynced clones before the first identity is
published can still mint different identities. Do not promise distributed
exactly-once delivery or add distributed coordination in this PR. Preserve
local evidence of publication failure through the existing sync behavior.

#### Closed wire contract

Use a direct HTTPS POST to the US capture endpoint
`https://us.i.posthog.com/i/v0/e/`, with TLS verification and no redirects.
Embed the new project's write-only capture key in one constant in
`src/coga/telemetry.py`. No SDK enrichment. The exact JSON envelope is
`api_key`, `event`, `distinct_id`, `timestamp`, `properties`: fixed event
name, persisted repo UUID, and UTC occurrence timestamp. Identity, event
name, timestamp, and routing key are protocol fields; measured properties
contain only the following counts and bounded version/platform strings.

| Event | Exact properties |
| --- | --- |
| `coga_installed` | `coga_version`, `os_name`, `os_version`, `python_version` |
| `coga_heartbeat` | `coga_version`, `tickets_draft`, `tickets_active`, `tickets_in_progress`, `tickets_blocked`, `tickets_paused`, `tickets_done`, `tickets_canceled`, `movement_count` |

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
of response data. Maximum capture wait is six seconds on the first run and
three on subsequent runs, apart from process teardown overhead.

After capture, format the same keyless event envelope(s), excluding only
`api_key`, as a single Slack receipt with each attempt's outcome. Say
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

Add `coga/contexts/coga/telemetry/SKILL.md` and its bootstrap twin as the
behavioral owner: wire boundary, admission, state/cursor, approximate metrics,
loss semantics, and recipe contract. `coga/principles` owns the dated policy
reversal (retain the historical 2026-06 rejection, append the 2026-09-20
reversal); `coga/architecture` owns config and identity changes. Update both
of their twins, the three ban mentions in `coga/usage`, README Values and
disclosure, and `docs/operations.md` opt-out navigation. Update recurring/code
contract inventories where they list fixed recipes. Grep active docs/contexts
for stale absolute bans and fix summaries in the same PR.

Add `docs/telemetry.md` for lazy operator procedures: project setup/read-back,
key source and release-based rotation, query commands, and the persons API
deletion procedure adapted from Multiply with Coga's project ID. Link to the
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

At owner review-design: create the Coga project in Multiply's organization,
confirm IP discard and disabled GeoIP, store its capture key in the 1Password
`coga` vault, and record project ID and exact item reference on this blackboard.
Implementation must not begin without those inputs. Do not read or expose
the operator credential; the capture constant is deliberately public/write-only.
The operator CLI's credential may still target Multiply: require `project-get`
to report the recorded Coga project before any verification query or deletion.

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
  AND event IN ('coga_installed', 'coga_heartbeat')
ORDER BY timestamp
```

Both rows must exist, match the prepared payload values, and contain no IP,
GeoIP, or unallowlisted measured fields. Record any service-owned routing
metadata separately from client properties; unexpected enrichment blocks
acceptance until explained and corrected. Run a later heartbeat with a known
advance/completion and confirm install is not repeated. Set local telemetry
false, run again, and query the same repo UUID over the new time window to
confirm no new capture row; pair this with the automated no-worker/no-HTTP
assertions, since absent rows alone do not prove absent requests. Record the
query text/results and wheel version in the PR. No dashboard build required;
at most one saved insight per agreed quantity. Heartbeats, not a sum of all
historical status counts, supply each repo's current inventory.

### Out of scope

Per-command instrumentation; launches, agent/session/token metrics; recurring
housekeeping metrics; prompts/first-run consent dialogs; SDKs or queues;
retries/replay; exact distributed delivery or a new audit format; hosted
operational state; runtime endpoint/key options; new scheduler; retention or
deletion tooling; more than three saved insights. A missed install is accepted
and must not grow a retry system. This is one bounded implementation PR plus
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
- `coga/contexts/coga/recurring/SKILL.md`: Dropping a new recurring task;
  Extend recurring with a task-specific workflow; Last-run state lives in the
  recurring task's blackboard. New templates are retroactively due on the first
  sweep, no agent runs if the shim closes its step, and scheduling is external.
- `coga/contexts/coga/architecture/SKILL.md`: Where a fact lives: docs vs contexts
  determines the new behavior-context / operator-runbook split. Principles,
  codebase, current-direction, project-stage, and `docs/vision.md` informed
  the design. The telemetry reversal is an explicit owner amendment.
- Reference implementation and operations: `/home/n/Code/multiply/infra/posthog/README.md`
  (Settings, Keys, CLI, Deleting a person), and its
  `coga/tasks/v1/telemetry/posthog/3-client.md` and
  `4-embed-the-capture-key-as-a-constant.md`. Copy the operational shape,
  never the project ID `606347`, key, or product payload.
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
  accept lost events without retries.
- Movement means forward advances plus completions, including explicit done
  and auto-close; keep the current audit format.

The existing approved reversal, weekly schedule, repo identity, default-on
switch, new Coga project, and owner verification gates remain settled.
The attached period-task context does not make this marketing ticket a
recurring period; its design notes belong on this blackboard.

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

No unanswered product questions from this design session. Owner prerequisites
at review-design remain: create/configure the Coga PostHog project, record its
ID here, and provide the exact 1Password item reference in the coga vault.
Those inputs gate implementation, not design evaluation.

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
