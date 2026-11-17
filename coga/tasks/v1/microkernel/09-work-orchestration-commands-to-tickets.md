---
title: Move work orchestration commands to tickets
status: in_progress
owner: nicktoper
agent: codex
contexts:
- coga-dev/microkernel/objectives
- coga-dev/principles
- coga-dev/testing
- coga-dev/project-stage
- coga/script-tickets
- coga/state-publication
- coga/state-publication/launch-boundaries
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
    checkout: control
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
    checkout: control
  - name: review-design
    skills: []
    assignee: owner
    checkout: control
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
    checkout: create-or-reuse
  - name: peer-review
    skills:
    - code/peer-review
    assignee: other-agent
    checkout: reuse-required
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
    checkout: control
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
    checkout: reuse-required
step: 2 (evaluate-design)
---

## Description

Move `megalaunch` queue policy and the `slack` FYI procedure into editable
bootstrap command tickets and deterministic scripts, retaining shared launch,
admission, lifecycle, notification and verified completion machinery in core.
Keep `pick` and the existing command spellings through aliases where the
reviewed invocation contract permits them. `retire` already moved and is out
of scope. This ticket starts with design and cold evaluation, followed by the
owner's design gate; preparing this draft does not approve implementation.

Done means users can discover and fully fork each moved procedure, including
wheel-delivered implementation, without editing core; queue behavior and FYI
completion/failure guarantees remain intact; each remaining core operation has
a concrete invariant and real consumers; and the implementation reports
whole-system change and removed duplication at named revisions, with matching
contract updates and verification. A head that cannot safely move needs an
owner-reviewed co-versioning proof rather than a partial migration presented
as complete. Design owns the detailed acceptance checklist.

### Objectives and proposed boundary

Hackability: users can change selection, ordering, dependency-drain policy and
FYI formatting through ticket-owned files. Simplification: reuse the shared
executor and remove genuinely duplicated preparation or re-blocking; moving
code between directories alone is not a reduction.

| Responsibility | Current source symbols | Proposed home |
| --- | --- | --- |
| Picker, saved selection, owner filters and summary presentation | `commands.megalaunch`, `megalaunch.launchable_candidates`, `save_selection`, `load_selection` | Bootstrap megalaunch ticket and its script/edge implementation |
| Sweep, dependency drain, attempt budget, liveness defaults, stop classification | `megalaunch.run_megalaunch`, `_run_sweep`, `_drain_satisfied_blockers`, `_chain_stop_result` | Queue-owned deterministic policy |
| Activation, re-blocking, prospective agent preparation | `megalaunch._activate_for_launch`, `_reblock_unresolved`, `_preflight_agent_launch`, `_launch_until_stop` | Reuse reviewed shared operations while preserving caller transactions |
| Claims, held-child proof, release/admission and recovery | `megalaunch._revalidate_launch_claim_before_spawn`, `_admit_launch_claim_after_release`, shared launch reconciliation | Shared package invariant; expose only the operation needed by the queue |
| FYI operands, formatting and destination choice | `commands.slack.slack` | Bootstrap slack ticket over shared notification/audit operations |
| Successful bootstrap FYI releases the matching outer session | `commands.slack.slack`, `repl_supervisor.emit_done_marker` | Verified generic completion operation, subject to design review |

Ship whole policy implementations, not wrappers importing the old core command.
Core must not import edge or ticket implementations. Stateless command calls
create no tracking task merely to invoke a procedure. Preserve trailing argv,
cwd, streams, exits and publication behavior across the chosen alias boundary.

Megalaunch preserves refresh, saved selections, ordering, owner/human gates,
explicit-pick preparation and activation, exact-byte claim revalidation,
held-child admission, dependency resolution/rollback, attempt accounting,
failure evidence, summary delivery and POSIX/Windows terminal behavior. Its
current agent-only execution remains: adding a script/agent queue framework is
out of scope. Customization must not bypass the shared safety invariants.

Slack preserves ordinary-task non-terminal FYIs and bootstrap completion only
after successful delivery and durable audit. The script phase clears the outer
supervisor identity, so nesting a bootstrap invocation cannot currently replace
the whole head safely. Design must prove a matching-session completion path,
including mismatched targets and failed delivery/audit, before moving that head;
never copy ambient completion authority into a child. Preserve disabled-channel,
important-destination, failure/audit and output behavior too.

### Acceptance criteria

These criteria describe the proposed two-command program. At the owner gate,
restrict this ticket's implementation checklist to the approved single-command
scope and transfer the other command's criteria to its approved sibling. The
unmigrated command remains an explicit open placement until its own review.

- [ ] Owner approves the implementation split below, names primitive owners,
  and leaves this ticket with one implementation/PR scope (or explicitly
  approves a combined PR). No implementation follows from design completion.
- [ ] `megalaunch` policy, picker, selection persistence, dependency selection,
  budgets, liveness defaults, stop classification and summary formatting live
  in `bootstrap/megalaunch` and its complete wheel-owned edge implementation.
  Core imports neither that implementation nor a ticket attachment. Delete
  the old command head and policy module after migrating their consumers.
- [ ] `slack` operands, FYI formatting and route selection live in
  `bootstrap/slack` and its complete edge implementation, only after the
  completion dependency below is implemented and reviewed. Otherwise retain
  the entire existing head and record the owner-reviewed co-versioning proof;
  moving ordinary FYIs alone does not complete this command's migration.
- [ ] Both commands run without creating a tracking task or invoking an agent
  for the command itself. `megalaunch` still launches agent sessions for queued
  work; it never starts a queued ticket's deterministic phase.
- [ ] Aliases preserve all existing operands, option collisions, cwd, streams,
  help, exits, publication deadlines and terminal behavior. `pick` works with
  the current one-level alias validator. Neither command abuses `--read-only`
  to suppress writes. An unavailable required generic invocation contract
  blocks the affected move, rather than shipping a special-name bypass.
- [ ] Every megalaunch section in `coga/megalaunch` has parity coverage: refresh
  before selection; owner and human gates; bare versus explicit selection;
  saved selections and missing tasks; draft interview/check/deferred activation;
  service order; dependency drain and exact rollback; attempt counting and
  first-step override; eight-step bound, timeouts and no-progress failure;
  summary delivery after stdout. Skipped work and unreached picks stay untouched.
- [ ] The queue cannot bypass exact-byte claim publication, final local/control
  proofs, held-child release/admission, or `pending:`/`released:` recovery by
  changing selection or instructions. Publication failure distinguishes a
  definite refusal from an uncertain result and never overwrites a later edit.
  Queue admission keeps its existing separate publication deadlines.
- [ ] Consolidate unresolved agent-resume re-blocking for ordinary launch and
  megalaunch in one shared operation, migrating both real callers together.
  Keep deterministic resume's restoration behavior explicit. Readiness
  consolidation belongs to sibling 03 and is not counted again here.
- [ ] Ordinary FYIs never complete a task or enclosing session. A bootstrap FYI
  completes only the matching live bootstrap session, after successful channel
  handling, durable audit and command finalization. Mismatched root, identity,
  stale invocation, nonzero child, delivery failure, audit failure, or uncertain
  publication never signals completion. No outer sentinel, assist or expected
  step authority reaches `ticket.py`; stdout is never a completion channel.
- [ ] Preserve disabled-channel handling (diagnostic, audit and `posted`),
  important-route refusal rather than flow fallback, actor resolution, message
  validation, sanitized errors and one send attempt. A delivery followed by an
  audit failure reports the delivered-but-unrecorded state without automatic
  resend. Git-disabled completion requires successful local audit, not a claim
  of remote durability. Explicitly document the stricter audit gate below.
- [ ] Through sibling 05's discover/copy mechanism, fresh wheel users can find
  each effective command, obtain its ticket plus all implementation files, edit
  policy/formatting locally, and run the fork. Prove no import of its installed
  edge implementation remains; upgrading the wheel keeps the fork unchanged.
  Restoring stock files rejoins updates. Test a multi-file fork if used.
- [ ] Update contract owners and dependent links in the same command PR:
  package `coga/megalaunch`, `coga/notifications` and `producers`, `coga/cli`,
  `coga/edge-code`, `coga/script-tickets`, `coga/state-publication` and
  `launch-boundaries` where affected; local `coga-dev/microkernel` and launch
  claim/spawn internals. Preserve one package owner and pin packaged resources.
- [ ] Record physical Python lines at named before/after revisions across core,
  edge and ticket/skill scripts, including any new primitive/transport code.
  Use `len(bytes.splitlines())` consistently, with blanks/comments included;
  list the file set and removed entrypoints/import paths. Separate relocation,
  actual deletion/deduplication, tests, docs and resource wrappers. A larger
  completion mechanism cannot be hidden as launch-sibling savings.
- [ ] Extend existing tests and run the full Linux suite and scoped validation
  with exact receipts. Native Windows/macOS evidence is deferred to release;
  report the actual Python version and any missing 3.11-floor evidence.

### Proposed shape

#### Implementation split and order — proposal for the owner gate

1. Leave this ticket responsible for **megalaunch only** after owner approval.
   Its PR owns queue policy extraction, the bounded claim-operation extraction,
   and re-block deduplication. Consume merged readiness from sibling
   `03-launch-decomposition`; coordinate its admission API with that owner.
2. Propose a new sibling **Move Slack FYIs to a command ticket**. Do not create,
   activate or launch it during this design step. It owns the FYI move and its
   publication/completion integration after the generic completion prerequisite.
3. Sibling 03 owns the generic script invocation and parent-side completion
   transport. Sibling `10-lifecycle-verbs-to-ticket-operations` reviews verified
   identity and the shared completion finalizer. Their handoff must accept the
   contracts below before the Slack implementation begins. Sibling 05 owns
   effective-source discovery and complete forks for both moves. Depend on
   these specific operations, not completion of those siblings in full.
4. The owner may instead approve a combined PR, or retain Slack's small head
   with the proof below. Do not silently split the frozen workflow, repeat
   implementation cycles, or change CLI-owned frontmatter to enact this plan.

#### Editable command boundary

Package `templates/coga/bootstrap/{megalaunch,slack}/ticket.md` and exact sibling
`ticket.py`; use `src/coga_edge/megalaunch.py` and `src/coga_edge/slack.py` for
complete implementations with `main(argv) -> int`. A small private package of
edge-only helpers is acceptable only if sibling 05 copies its complete import
closure. Prefer one self-contained policy module per command to make forks
simple. The shim selects the implementation and propagates its exit once.
It must not import the old `coga.commands.*` head or `coga.megalaunch` policy.

Proposed defaults in `src/coga/aliases.py`, `DEFAULT_ALIASES`:
`megalaunch = "launch --command bootstrap/megalaunch --"`,
`pick = "launch --command bootstrap/megalaunch -- --pick"`, and
`slack = "launch --command bootstrap/slack --"`. `--command` is a proposed
generic invocation policy owned by sibling 03, not an existing flag.
Remove migrated names from
`BUILTIN_COMMANDS` and `src/coga/cli.py`, `_LAZY_COMMANDS` and related inventories.
`validate_aliases` requires a built-in first token: `pick = "megalaunch --pick"`
would become invalid. Never solve this with recursive alias dispatch.

The `--` keeps queue `--agent` and FYI `--task`/`--message` in script argv.
The edge parser owns the existing usage errors and `--help`; inherited terminal
streams remain attached and script framing stays on stderr. No new success
text or usage record may pollute stdout. Scripts currently run from
`task_env.host_repo_root`; characterize subdirectory invocations before moving
relative-path parsing. Keep configuration discovery and reloads rooted in the
invoking repository. The queue performs its own refresh before reading tickets,
then reloads config, retaining feature/detached behavior. The proposed
`--command` policy supplies the missing write-dispatch contract:

- Only stateless bootstrap targets with a regular exact `ticket.py` qualify;
  a missing/disappeared script, stateful target, read-only mode, agent override,
  prompt report or REPL option refuses with exit 2 before effects. This mode
  cannot fall through to an agent and does not change ordinary launch's
  classifier or stateful script chaining.
- For non-help execution, load writer config with the configured user,
  including reloads;
  require no configured agent for dispatch. Forward argv verbatim and inherit
  terminal streams. The script owns any agent/readiness requirement of its work.
- No launcher-owned activation, launch/exit audit, usage capture, skill-view
  refresh, push probe, checkout normalization, refresh or return. The procedure
  performs its existing refresh if needed. This preserves FYIs on dirty or
  feature checkouts and the queue's fetch-only behavior there.
- The outer CLI retains the original writer's one end-of-command sweep and
  retained-log diagnostics. Nonzero ordinary failures still sweep; exit 75 or
  a retained-state result withholds sweep and refresh. Scripts use the shared
  subprocess body, environment isolation and declared-secret resolution.
- `--help` after the script separator selects the edge parser's help without
  user/agent/secret requirements, refresh, audit or publication, matching the
  old built-in help. Help outside a configured repo must remain available from
  the packaged definition; local overrides win inside a valid repo. This is a
  required sibling-03 help-dispatch contract, not functionality proved here.
  It must distinguish parsed help from an operand equal to `--help` (for example
  the FYI message); never use an unqualified token scan to suppress publication.
  Require direct/alias help tests, including absent user/repo, before cutover.
  Do not reinterpret other operands after the separator as launcher options.

This is cooperative command dispatch, not an arbitrary-code sandbox. It adds
one generic policy rather than a command-name exemption; require explicit owner
acceptance and sibling 03 implementation before alias cutover. Avoid adding
per-command switches or a second subprocess executor. The Slack parent-owned
operation below is an additional reviewed capability of this invocation; it
is never inferred from the bootstrap name.

#### Queue/core API and transaction boundary

Proposed stable operation in `src/coga/launch.py`:
`run_claimed_agent_session(cfg, ref, *, source_bytes, prospective_ticket,
agent_name, activation=None, blocker_answers=None, idle_timeout=None,
max_session=None)`. Exact spelling may
follow sibling 03's reviewed API; the required semantic boundary is fixed:

- Input binds exact source bytes, prospective ticket and selected agent. Core
  constructs the generation and uses shared readiness to compose the exact
  claimed view and secret environment before writes. The caller cannot pass
  arbitrary proof/release callbacks or an already-admitted generation. Core
  derives the claim and rechecks routing/owner-gate validity. Queue policy
  chooses candidates and timeouts; it never manufactures admission authority.
- Prepare/freeze/validate activation without writes. After readiness succeeds,
  commit an optional exact activation (plus selected dependency answers) and
  strict claim separately, preserving current queue commit accounting. Compare
  local bytes under `git.state_lock` and publish against exact control bytes.
- Keep pending-seal validation, both pre-spawn proofs, the shared held-child
  barrier, release, local released witness, admission publication and process
  teardown inside core. Use existing `spawn_agent_session` and
  `repl_supervisor._admit_held_child`; no second executor or callback registry.
- Return a typed attempted/session/refusal outcome with whether execution was
  released and whether retryable evidence remains. Reclassification before a
  real attempt consumes no budget. Preserve interrupts and nonzero results;
  the queue maps outcomes to its existing rows and chaining policy.
- A definite failed write restores only bytes/audit owned by that transaction,
  after checking the current local postimage. Uncertain publication retains
  evidence; failed post-release admission kills the child and retains the
  released witness. Preserve the caller's exit contract: megalaunch currently
  reports these as failed rows and exits 1, with the pending seal/released
  publication refusal protecting retained evidence. Do not silently convert
  all such rows to exit 75 or abort later queued work. Existing launch/script
  exit-75 paths still withhold sweep and refresh. Any proposed change to queue
  exit/sweep behavior requires a separate explicit owner decision and contract
  update; relocation itself does not authorize it.

Extract the bounded substance from `src/coga/megalaunch.py`,
`_launch_until_stop`, `_revalidate_launch_claim_before_spawn`,
`_admit_launch_claim_after_release`, `_activate_for_launch`, and their exact
rollback helpers. Keep selection, dependency satisfaction/answer text and stop
classification in the edge. Partial dependency resolution uses shared guarded
blackboard/publication operations; preserve its postimage check on rollback.
Do not turn generic lifecycle's three-way reconciliation into queue admission:
queue source bytes remain a strict compare-and-set.

This operation has a **co-versioning** justification even with one queue
caller: publication's pending seal, held process release, released recovery
witness and ordinary launch recovery must agree as one package-private
transaction. A filesystem-only edge implementation cannot safely choose the
exception to the pending seal. Ordinary launch's recovery remains a real
consumer of the same generation/proof machinery, not a pretend queue caller.
Record this bounded proof in the microkernel owner; it does not justify keeping
picker, ordering, budgets or all of `_launch_until_stop` in core.

For concrete deduplication, propose
`src/coga/mark.py`, `reblock_unresolved_resume`: a shared operation that
rereads the current ticket/blockers, applies the existing in-progress-only
agent rule, and returns a structured reblocked/no-op/error result. Migrate
`src/coga/launch.py`, `_reblock_unresolved_resume`, and
`src/coga/megalaunch.py`, `_reblock_unresolved`, together. Caller-specific audit
wording and presentation remain parameters at the edge. Deterministic callers
must retain their explicit resume-step/fallback-byte restoration; do not make
an agent queue restore a terminal ticket. Reuse `mark_blocked` for validated
write/audit/notification/publication rather than duplicate it.

Retained shared operations and real consumers: `prepare_active` and
`mark_active` serve mark/launch/queue; `mark_in_progress` serves launch/queue;
`notification.post` serves lifecycle/FYI/queue summaries;
`spawn_agent_session` serves launch/authoring/queue/recurring; service order
serves queue/status; blocker parsing serves lifecycle/launch/queue. Readiness
is the ordinary-launch/queue consolidation owned by sibling 03. A new helper
must either migrate its real consumers together or carry the specific reviewed
transaction proof; an edge import alone does not establish shared status.

#### Remaining execution dependencies

`src/coga/megalaunch.py`, `run_megalaunch`, currently imports
`src/coga/recurring_runner.py`, `_recurring_idle_timeout` and
`_recurring_max_session`. Keep environment/config parsing shared with recurring,
but queue defaults belong to the queue. Extract the existing resolution into
public shared session-limit helpers (proposed `src/coga/session_limits.py`),
with explicit caller defaults and unchanged invalid/nonfinite/disarmed-value
semantics. Migrate recurring and queue callers together; count this as relocation
of already-shared code, not deduplication. Native console restrictions remain
in the shared process machinery. Likewise use a reviewed public TTY predicate
rather than retaining the queue's import of `launch._interactive_stdio_has_tty`.
Coordinate names with sibling 03 instead of adding compatibility re-exports.

`src/coga/megalaunch.py`, `_author_draft`, imports
`src/coga/commands/ticket.py`, `_authoring_ticket`, `_run_authoring_session` and
`AUTHORING_KICKOFF_EDIT`. Sibling 08 explicitly owns removing this dependency
when authoring moves. Its bounded handoff must provide the public deterministic
command-ticket invocation for an existing target and preselected agent, keeping
interview selection noninteractive and streams attached. Queue code must not
import that future edge coordinator. Consume the reviewed public invocation
(or the current public `coga ticket <ref> --agent <selected>` spelling after
proving its finalization/sweep parity), not a copied authoring executor. Missing
bootstrap remains a no-op; ordinary interview failures leave the draft for
checking. Coordinate retained-state exit 75 separately with sibling 08's
reviewed contract so it is not swallowed or swept as an ordinary draft miss.
Do not count sibling 08's coordinator deletion as savings in this ticket.

#### Slack completion dependency — proposed parent-owned protocol

Do not give the script the caller's sentinel or expected-task/assist variables.
Do not treat successful exit from `bootstrap/slack` as proof that a different
bootstrap session finished. Proposed minimal handoff to siblings 03 and 10:

- The invoking parent captures and validates the existing live outer-session
  identity before script isolation: repository identity, bootstrap slug and
  session generation/channel. Repository identity must permit a verified
  same-repository command from a separate checkout/clone, as existing slug
  completion does; an absolute checkout-path equality test is insufficient. With no verified outer session, ordinary FYIs
  still work but cannot end one. A matching string supplied by the child is
  insufficient. Existing supervisor identity checks must gain generation-bound
  verification where needed; no ambient-only new completion credential.
- Provide one fixed, invocation-scoped **audited notification operation**, not
  arbitrary RPC/plugin callbacks. The parent services a structured request
  carrying resolved target, formatted text, requested destination and audit
  message. It resolves target/root and actor itself, uses `notification.post`
  once, appends the audit and confirms required log publication with existing
  `git.sync_log`/strict publication semantics. Return a typed success/failure
  receipt bound to this invocation and target. The edge owns operands and
  formatting, and prints `posted` only after successful acknowledgement.
- Only the parent holds completion authority. For a successful request naming
  the exact captured bootstrap target in the same repository/generation, it
  records a deferred completion intent. Finish only after child exit zero,
  successful audit confirmation and final publication/retained-log checks.
  Use `repl_supervisor.deferred_done_marker`/`emit_done_marker` after those
  checks; do not request a marker merely because a notification was attempted.
- Ordinary task targets and different bootstrap targets may receive valid FYIs
  but never release the outer session. No replay across child invocations,
  nested unrelated scripts, roots or supervisor generations. A child crash,
  stale/duplicate receipt, broken request channel or parent interruption cannot
  authorize completion. Consume/close the one-invocation channel at teardown.
- Disabled notifications keep existing successful no-channel handling; delivery
  failures remain exit 1, invalid operands/config/target/agent remain exit 2.
  A new audit-publication refusal retains the delivered FYI and log, exits 75,
  suppresses sweep/refresh and gives strict-publication recovery. Recovery must
  not resend or replay a completion/transition. Log recovery alone never
  terminates a later session; any new explicit FYI is a new send.

The transport must work on POSIX and native Windows without terminal parsing,
inherit no completion capability into grandchildren, and contain no knowledge
of the Slack alias or command-ticket name. Lifecycle sibling 10 must consume
or explicitly accept the generic verified finalizer; do not count hypothetical
callers as two real consumers. Notification/audit operations retain their
co-versioning proof independently of whether that finalizer gains a second
caller. Add no queue, retry service, durable message spool or general RPC host.

**Tradeoff for owner decision:** this parent operation adds transport and
verification code to move a 94-line head. It is a proposed dependency, not an
existing safe API or an approved implementation. If siblings 03/10 cannot
supply this small bounded operation economically, retain `commands.slack.slack`
under an explicit reviewed proof: it joins delivery, audit and matching-session
completion inside the CLI's deferred finalization, and the script boundary
currently destroys the authority needed to preserve that transaction. Keep
its placement open until the owner accepts that proof; do not claim full Slack
forkability or a completed move. The preferred migration waits for the shared
operation rather than introducing a command-specific completion exception.

There is also a deliberate correctness tightening to approve: today the head
requests completion after local `append_log`, while `deferred_done_marker`
waits for the best-effort sweep but does not inspect whether publication
succeeded. The new durable-audit criterion must reject failed confirmation.
Do not describe this as existing exact remote-durability parity; update
`coga/state-publication`, `coga/script-tickets` and notification owners with
this behavior if approved.

### Out of scope

No retire work, recurring scheduling/admission migration, recipe inventory
change, script-aware queue, new queue executor, generic plugin framework,
prompt-assembly redesign, notification retry/digest policy, task creation per
command invocation or native-host allocation. Do not create the proposed split,
implement shared primitives or change shipped contracts during this design
step. All API names above are proposals until their named owners review them.

## Context

### Design investigation — 2026-11-16

Inspected clean control at `5edb1f9672d6c8d0d716fd8cdccd920ce3179c14`,
matching fetched `origin/main`. This ticket has no implementation branch or
linked PR; the branch is control, not a completed feature checkout. The
following are current source relationships, not assumptions from sibling notes:

- `src/coga/commands/megalaunch.py`, `megalaunch`, refreshes and reloads config
  before `_resolve_selection`, invokes `src/coga/megalaunch.py`,
  `run_megalaunch`, prints the summary, then posts. Its policy/terminal helpers
  and the engine currently account for 641 and 2,407 physical Python lines.
- `src/coga/megalaunch.py`, `_launch_until_stop`, calls
  `_preflight_agent_launch`, activation, strict start publication and
  `src/coga/launch.py`, `spawn_agent_session`; it passes exact claim validators
  and post-release admission callbacks to that shared executor. Policy and
  transaction are currently intertwined in this one loop.
- `src/coga/megalaunch.py`, `_reblock_unresolved`, and `src/coga/launch.py`,
  `_reblock_unresolved_resume`, both parse open asks and call
  `src/coga/mark.py`, `mark_blocked`. The ordinary-launch helper additionally
  handles script restoration. `src/coga/lifecycle.py` currently owns vocabulary
  only; the proposed shared mutation belongs with `mark` operations.
- `src/coga/commands/slack.py`, `slack` (94 physical lines), calls
  `src/coga/notification/__init__.py`, `post`, then `src/coga/logfile.py`,
  `append_log`, then `src/coga/repl_supervisor.py`, `emit_done_marker` for a
  bootstrap ref. `deferred_done_marker` defers the request to command exit but
  does not condition it on the result of `src/coga/git.py`, `sync_log`.
  That publisher returns `True`/`False` for confirmed state and `None` for a
  miss; checking truthiness would incorrectly reject an already-landed log.
- `src/coga/launch_script.py`, `run_script_phase`, resets supervisor/expected
  identity and sentinel, sets its own script identity, and uses inherited
  stdio with cwd `src/coga/task_env.py`, `host_repo_root`. A bootstrap script
  runs once; changing it must not acquire agent fallback.
- `src/coga/aliases.py`, `validate_aliases`, accepts only a built-in first
  token. The direct `pick` expansion in this proposal follows that constraint.
- `03-launch-decomposition` records an implementation of
  `launch.prepare_agent_launch`, but that symbol is absent from this inspected
  control tree. Verify the actual merged symbol and signature before consuming
  it. The readiness reduction remains credited to sibling 03.

### Verification map for implementation

Keep the existing executor tests and update imports after moving policy.
`tests/test_megalaunch.py`,
`test_megalaunch_launch_claim_cas_excludes_a_second_checkout`,
`test_pending_claim_blocks_remote_lifecycle_between_final_fetch_and_gate`, and
`test_failed_post_release_admission_retains_released_recovery_witness` exercise
load-bearing claim boundaries. Add local postimage-change rollback cases to
activation and partial dependency resolution. Preserve picker tests in that
file, including native-console mocks; actual native execution remains a
release check.

Extend `tests/test_commands.py`,
`test_slack_accepts_and_completes_stateless_bootstrap_target` and
`test_slack_on_durable_task_does_not_complete_session`, plus
`tests/test_notification_messages.py`, `test_slack_fyi_includes_title`, and
`tests/test_done_marker_emission.py`. Current ambient-sentinel fixtures are
insufficient proof of the proposed verified parent boundary: add real nested
script subprocess tests using fake agent seams, with matching/mismatching
slug, repository and generation, absent/stale identity, ordinary targets,
disabled channel, send/audit/publish failures, already-published audit,
child crash, duplicate request and channel loss. Assert no outer completion
variables or assist authority in the child's environment and no completion
on failure. Pair successful completion with an assertion that finalization
finished before the sentinel write. No real Slack or agent process is needed.

Use `tests/test_launch_script.py`, `tests/test_aliases.py`,
`tests/test_commands.py` and `tests/test_packaging.py` for direct/alias parity,
wheel invocation, ordered argv with whitespace and option-like operands,
subdirectory cwd, help, non-TTY refusal, stderr/stdout separation, exit 1/2/75,
script-only behavior with no configured agent, and complete local fork after a
wheel upgrade. Spy on refresh/publication to detect extra script-wrapper
boundaries. Required package resources belong in
`tests/required_package_resources.txt`; no live forwarding definitions.

### Current-main premise and dependency boundary

Checked against `e09df5126895e679ee1a1a26aefb33522c97773b` on 2026-11-16.
Physical source lines including blanks/comments: `commands/megalaunch.py` 641,
`megalaunch.py` 2,407, `commands/slack.py` 94 (3,142 total); these are inventory,
not promised savings. Both heads remain, megalaunch imports `coga.launch`,
and `retire` is already an alias to `launch bootstrap/retire --`.

`v1/microkernel/03-launch-decomposition` owns shared agent readiness and
stateless invocation. Its implementation proposes `launch.prepare_agent_launch`
for ordinary launch and megalaunch, but that symbol is absent from this main
snapshot. Before implementation, verify what actually merged and consume its
reviewed operation; do not duplicate or claim its reduction here. Design can
proceed now. Queue migration waits only for the specific stable admission/session
operations it uses, not completion of every launch refactor. Its shared-readiness
extraction alone does not settle queue claim/release or bootstrap FYI completion.

This design must specify the narrow session/admission and verified completion
contracts and their tests. Assign any missing generic primitive to launch or
lifecycle with a precise dependency and owner-reviewed handoff before migrating
the affected head. No weakened interim path. Identify at least one remaining
duplicated activation/re-block/preparation path to remove here, or name its
exact operation and owning sibling; do not count the launch sibling's readiness
work twice. Each retained operation needs its invariant and real callers.

`v1/microkernel/05-make-packaged-behavior-discoverable-and-editable` owns the
full local-fork mechanism: a copied shim alone is insufficient. Test the moved
procedures through that mechanism once available. Lifecycle operations belong
to sibling 10; recurring recipes to sibling 04; `recurring promote` to sibling
08. Recurring admission/scheduling, a new queue framework, removed digest/project
commands, and retire migration are excluded. The group asks for one PR per
command move, whereas this workflow has one implementation branch/PR. Design
must propose sibling implementation tickets for megalaunch and slack (with
the shared primitive ownership/dependencies), for explicit owner approval at
review-design. Do not create or activate that split during authoring. Before
advancing to implement, the owner must approve the split and leave this ticket
with one bounded implementation/PR scope, or explicitly accept a single-PR
combined migration. Do not invent repeated workflow cycles under this ticket.

### Contract reading and updates

The following editing targets and focused operating references are cited rather
than attached. Read the named sections before
design and again when implementing or reviewing their affected behavior; update
owners and dependent references in the same PR as each behavior/placement change.
Package-owned paths below are relative to
`src/coga/resources/templates/coga/bootstrap/contexts/coga/`.

- `coga/megalaunch`, `megalaunch/SKILL.md`: Sessions, Refresh first, Owner
  filter, Bare sweep, Explicit selection, Order, Dependency drain, Budget,
  agent, scope, summary. This is an editing target and the full parity contract.
- `coga/notifications`, `notifications/SKILL.md`: Surface and destination,
  When a post fails, No retry; `coga/notifications/producers`,
  `notifications/producers/SKILL.md`: Live surface and Silent. Explicit sends
  fail loud; a failed send must not emit completion; transitions and FYIs
  remain distinct, with no new retry/digest policy.
- `coga/launch`, `launch/SKILL.md`: Phases and routing, Options and exits;
  `coga/checkouts`, `checkouts/SKILL.md`: Start, work, end and invocation rules.
  Reuse process/checkout machinery without changing queue transport or admission.
- `coga/edge-code`, `edge-code/SKILL.md`: distribution, upgrades and overrides;
  `coga/cli`, `cli/SKILL.md`: Running work, integrations and alias inventory.
  Ship one package owner per definition and expose the complete implementation.
- `coga-dev/microkernel`, `docs/contexts/coga-dev/microkernel/SKILL.md`:
  Microkernel rule, Open command placements and Migrating a built-in to the
  edge. Update the megalaunch/slack placement row with the reviewed outcome.

The full `coga/script-tickets`, `coga/state-publication` and
`coga/state-publication/launch-boundaries` contracts are attached because the
planned steps rely on their distributed environment/completion and publication
rules. Preserve isolated script identity, explicit lifecycle completion,
exact-byte transactions, definitive rollback versus uncertain retained evidence,
exit 75 and the distinct queue publication deadlines. Any design that changes
these contracts must name and update their package owners in the same PR.

### Evidence required by the eventual implementation

Extend existing `tests/test_megalaunch.py`, launch/script, CLI/alias and
notification coverage rather than inventing a second executor test harness.
Exercise sweep and selection gates, saved selection, dependency drain,
concurrent claim changes, held-child release failures, publication conflicts
and rollback/uncertainty, terminal interaction, ordinary FYIs, matching and
mismatched bootstrap completion, delivery/audit failures and no added agent
fallback. Include packaged/installed command execution and a complete local
fork; test unchanged streams, argv and exit behavior through aliases.

Report physical production lines at named before/after revisions across core,
edge and ticket/skill Python, counting blanks/comments consistently; separate
relocation, deletion and deduplication, and report tests/docs/package owners
separately. Name removed entrypoints and dependency paths. A size-neutral
extraction may be justified by clearer ownership, but any deferred simplification
needs a named owner. Run the full Linux suite and scoped validation with exact
receipts per `coga-dev/testing`; native Windows/macOS verification is deferred
to release, including for picker changes. Linux checks do not prove native parity.

### Authoring verification — 2026-11-16

Independent cold evaluation cleared this ticket for the design step with no
remaining must-fix authoring findings. The implementation split, admission/
release and matching-session completion contracts, merged sibling APIs and
full-fork dependencies remain explicit design responsibilities above.

Ticket-only working tree on base `e09df5126895e679ee1a1a26aefb33522c97773b`;
Pop!_OS 24.04 LTS, Linux 7.2.15-76070215-generic, Python 3.12.12:
`TERM=dumb PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest --basetemp=/home/n/Code/coga-pytest-orchestration-authoring-20261116`
→ 4,900 passed, 33 skipped, 0 failed in 896.41 seconds. This verifies the
existing suite during authoring, not the proposed unimplemented migration.
Python 3.11 was not used; native Windows/macOS checks remain deferred to release.

<!-- coga:blackboard -->

### Design handoff — 2026-11-16

Owner authorized ticket-only design in this attended session. No code, branch,
PR, split-ticket creation or implementation approval. The Description now holds
the detailed acceptance checklist, proposed command split, queue transaction
API, concrete re-block deduplication and completion dependency. Current source
findings and a regression map are in Context. API names and the completion
transport are proposals for cold evaluation and the later owner gate.

### Design verification receipt

Base/source revision `5edb1f9672d6c8d0d716fd8cdccd920ce3179c14`;
Pop!_OS 24.04 LTS, Linux `7.2.15-76070215-generic`, Python 3.12.12.
Ticket-only prose changed during the run; production, tests and packaged
contracts stayed at that revision. This receipt verifies the existing suite,
not any proposed API or unimplemented migration.

- `env TERM=dumb PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest --basetemp=/home/n/Code/coga-pytest-orchestration-design-20261116 > /tmp/coga-orchestration-design-pytest.log 2>&1`
  → 4,900 passed, 33 skipped, 0 failed in 869.94 seconds; exit 0.
- `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m coga.cli validate --task v1/microkernel/09-work-orchestration-commands-to-tickets --json`
  → one ticket valid, no issues, exit 0.
- `git diff --check` → exit 0. Only this ticket changed; CLI-owned frontmatter
  is unchanged. No implementation branch, code change or PR was created.
- Final `git fetch origin main` confirmed control still at the full base SHA
  above. The pre-reconciliation ticket copy was preserved and byte-checked in
  `/tmp/coga-orchestration-design-before-reconciliation.md`; no drift needed
  merging. Python 3.11 was not used; native Windows/macOS checks are deferred
  to release. No native parity is claimed.

Ready for the independent evaluate-design step. The proposed split, new generic
invocation/completion operations and audit-gate tightening remain unapproved
until the owner gate; no sibling ticket was created or activated.

## Open Questions

1. Approve megalaunch as this ticket's one implementation/PR scope and create a
   Slack sibling at the owner gate, or explicitly approve a combined migration?
2. Accept the proposed parent-owned audited-notification/completion operation
   and its cost, with siblings 03/10 accepting ownership, or retain the Slack
   head under the explicit co-versioning proof? A retained head does not meet
   full Slack forkability; record that exception rather than call it migrated.
3. Approve the durable-audit tightening: publication failure after delivery
   retains evidence, exits 75 and withholds completion, instead of the current
   best-effort sweep followed by a marker. Disabled Git still uses local audit.
4. Sibling 03 must ratify the bounded queue admission API and the
   proposed `--command` invocation/help policy; sibling 05 must deliver complete-fork support.
   Which reviewed merged revisions satisfy these prerequisites at implementation
   entry? Current sibling implementation notes are not evidence of merged APIs.

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Superseded designs

### 2026-11-12 — Design before the current-main refresh

Superseded by: the refreshed Description and Context above, proposed for owner review.
Reason: source, distribution and caller boundaries changed; the owner clarified
the objectives in `coga-dev/microkernel/objectives`. Historical commands,
paths, approvals and test receipts below are evidence, not current instructions.

#### Description

Settle the placement of the in-package heads that orchestrate work:
`coga retire`, `coga megalaunch` (and its `pick` alias), and `coga slack`.
Move each head's single-consumer substance to the edge (command ticket,
`ticket.py`, `src/coga_edge/`) behind a thin creator/launcher/alias, or
record why it must be co-versioned with the package.

##### Acceptance criteria

- [ ] Apply the group's [reduction objective](README.md#reduction-objective):
      simplify duplicated launch/orchestration scaffolding and unnecessary
      wrappers in `megalaunch` and `slack` using the shared launch boundary.
      Count their edge implementations in the before/after total; moving
      queue policy out of core alone is a placement gain, not less code to
      maintain. Keep recurring recipes and the executor outside this scope.

- [ ] The design defines one shared creator/launcher/alias pattern for these
      heads, so they do not each invent a migration shape.
- [x] `retire` is split into a concrete follow-up with exact acceptance
      criteria: `microkernel/move-retire-to-a-command-ticket` (2026-10-16).
      Its state rule stays: a canceled ticket gets a retire task; a done
      ticket is deleted in place.
- [ ] `megalaunch` and `slack` are each moved or given a co-versioning proof
      in `coga-dev/microkernel`. Megalaunch's queue selection, liveness
      defaults and timeout classification are caller policy, not executor
      substrate.
- [ ] Implementation is split per command shape after design review.
- [ ] Human-visible side effects stay durable (blackboards, `coga/log.md`,
      sync commits, notifications).
- [ ] The three heads leave (retire through its follow-up) the "Open command placements" table (both
      copies); `coga/megalaunch`, `coga/checkout-cleanup`,
      `coga/notifications` and the `coga/cli` index match; tests pass.
      Retire's exit is implemented on branch `retire-command-ticket`
      (`microkernel/move-retire-to-a-command-ticket`, pending review and
      merge): the row there names only `megalaunch`, `slack`.

#### Context

Group: `microkernel/README.md` (v1 scope since 2026-10-16).

Prior art: `ticket` (command head plus `bootstrap/ticket` and
`coga.authoring` finalize), `bootstrap/recurring-scan`, the `delete-task`
recipe, `bootstrap/resolve-conflicts` and `bootstrap/address-pr-comments`
command tickets reached by aliases.

Depends on `v1/microkernel/03-launch-decomposition` for a public
one-session API (megalaunch currently imports the session runner out of
`commands/launch.py`). Does not touch `runner.RECIPES`: that registry is
owned by `v1/microkernel/04-gigantic-refactor-move-recurring-recipes-out-of-co`.

Out of scope: `skill *`, `create`, the launch executor, recurring recipes.

##### Premise check (2026-10-16, pull-forward to v1)

- Subject exists: `src/coga/commands/{retire,megalaunch,slack}.py`,
  `src/coga/megalaunch.py`.
- Stale surfaces removed (Dream W39 F47): `coga digest` (removed by
  `remov-digest-in-recurring`) and `coga project` (removed by
  `remove-coga-build-and-project`). Bare `coga recurring` is already a thin
  head over the `recurring-scan` recipe, so recurring maintenance left scope.
- Not delivered: all three heads are still listed in extension-model's
  "Open command placements".

Previous ref: `microkernel/work-orchestration-commands-to-tickets` (renamed 2026-10-27); earlier audit lines retain that ref. Parked by the owner for v2; this work does not gate v1.

Created under `v2/cleanup-core-commands/` as part of the command-surface breakdown.
