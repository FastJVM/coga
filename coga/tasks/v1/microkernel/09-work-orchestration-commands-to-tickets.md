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
step: 6 (open-pr)
---

## Description

Move the `megalaunch` queue procedure (picker, selection, ordering, dependency
drain, budgets and summary) into the editable stateless bootstrap command ticket
`bootstrap/megalaunch` and a complete wheel-owned edge implementation. Shared
launch, admission, lifecycle, notification and publication machinery stays in
core. `megalaunch` and `pick` stay as aliases over plain `coga launch`. `retire`
already moved and is out of scope.

Owner gate, 2026-11-16: this ticket now covers **megalaunch only**, with one
implementation branch and PR. `slack` keeps its core head under the recorded
co-versioning proof below. The new draft sibling
`v1/microkernel/move-slack-fyis-to-a-command-ticket` owns any future Slack
move, including the choice of completion mechanism.

Done means users can discover and fully fork the queue procedure, including
its wheel-delivered implementation, without editing core. Queue behavior, the
claim/admission invariants and exit/publication behavior stay intact. Each
remaining core operation has a concrete invariant and real consumers. The
implementation reports whole-system change and removed duplication at named
revisions, with matching contract updates and Linux verification.

### Objectives and proposed boundary

Hackability: users can change selection, ordering, dependency-drain policy,
budgets and summary formatting through ticket-owned files. Simplification:
reuse the shared executor, remove the duplicated unresolved-resume re-blocking,
and delete the `megalaunch` command head and `coga.megalaunch` policy module.
Moving code between directories alone is not a reduction.

| Responsibility | Current source symbols | Home after this ticket |
| --- | --- | --- |
| Picker, saved selection, owner filters and summary presentation | `commands.megalaunch`, `megalaunch.launchable_candidates`, `save_selection`, `load_selection` | `bootstrap/megalaunch` ticket and `src/coga_edge/megalaunch.py` |
| Sweep, dependency drain, attempt budget, liveness defaults, stop classification | `megalaunch.run_megalaunch`, `_run_sweep`, `_drain_satisfied_blockers`, `_chain_stop_result` | Edge queue policy |
| Activation, re-blocking, prospective agent preparation | `megalaunch._activate_for_launch`, `_reblock_unresolved`, `_preflight_agent_launch`, `_launch_until_stop` | Shared core operations below, preserving caller transactions |
| Claims, held-child proof, release/admission and recovery | `megalaunch._revalidate_launch_claim_before_spawn`, `_admit_launch_claim_after_release`, shared launch reconciliation | Core, under the co-versioning proof below; exposed through one operation |
| Interrupt delivery to a running command script | `launch_script.run_script_phase` (`subprocess.run`) | Generic launch rule (below) |

Ship whole policy implementations, not wrappers that import the old core
command. Core must not import edge or ticket implementations. Stateless command
calls create no tracking task. Preserve trailing argv, cwd, streams, exits and
publication behavior across the alias boundary.

Megalaunch preserves refresh, saved selections, ordering, owner/human gates,
explicit-pick preparation and activation, exact-byte claim revalidation,
held-child admission, dependency resolution/rollback, attempt accounting,
failure evidence, summary delivery and POSIX/Windows terminal behavior. Its
current agent-only execution remains: a script/agent queue framework is out of
scope. Customization must not bypass the shared safety invariants.

### Acceptance criteria

- [x] Queue policy, picker, selection persistence, dependency selection,
  budgets, liveness defaults, stop classification and summary formatting live
  in the packaged `bootstrap/megalaunch` ticket (exact sibling `ticket.py`
  shim) and the complete edge module `src/coga_edge/megalaunch.py`
  (`main(argv) -> int`). Core imports neither. `src/coga/commands/megalaunch.py`
  and `src/coga/megalaunch.py` are deleted after their consumers migrate; the
  shim imports neither.
- [x] `DEFAULT_ALIASES` maps `megalaunch = "launch bootstrap/megalaunch --"` and
  `pick = "launch bootstrap/megalaunch -- --pick"`. `megalaunch` leaves
  `BUILTIN_COMMANDS`, `cli._LAZY_COMMANDS` and related inventories. No new
  launch flag, no special-name branch and no recursive alias dispatch.
  `--read-only` is not used to suppress writes.
- [x] Generic stateless-script launch rules for every stateless bootstrap
  target (see Proposed shape): (a) a target classified as a script whose
  `ticket.py` vanishes before the child starts exits 2 instead of handing off
  to an agent; agent-only bootstrap targets (`resolve-conflicts`,
  `address-pr-comments`) keep their `## Launch arguments` behavior; (b) a help
  request (exact `--help` before any script-level `--`) is detected before
  config loading, runs the script without user, agent, secrets, refresh,
  audit, publication or sweep, works outside a repo through the packaged
  definition, and fails closed: under `COGA_SCRIPT_HELP=1` a script whose parse
  reaches its command body exits 2 without effects; (c) the interrupt rule.
  `coga retire` gains the same rules; `retire 1 --agent --help` and
  `megalaunch --agent --help` exit 2 with no effect, and existing retire
  tests still pass.
- [x] Interrupt rule: while a stateless bootstrap `ticket.py` runs, the parent
  launch never kills or terminates the child on its own interrupt. It installs
  a no-op Python SIGINT handler (and SIGBREAK on Windows), never `SIG_IGN` or a
  NULL console handler, forwards SIGTERM to the child once, and waits. A
  negative return code maps to `128 - code`; otherwise the child's status is
  returned unchanged; exit 75 still withholds sweep and refresh. A test proves
  the child's SIGINT disposition is default. Tests cover Ctrl+C between picks
  and inside a claim window through the alias. On POSIX the picker runs in raw
  mode, where Ctrl+C is the byte `\x03`, so picker-quit tests are the existing
  mocks and the Windows `_WindowsKeys` path; native Windows evidence is
  deferred to release.
- [x] The command runs without creating a tracking task or starting an agent
  for itself. It still launches agent sessions for queued work and never
  starts a queued ticket's deterministic phase. Each queued agent's
  environment is re-minted: `COGA_SCRIPT_TASK` and the empty script sentinel
  are cleared through `TASK_ENV_KEYS`, supervised witnesses are fresh, and
  lifecycle commands inside a queued session credit the agent, not `system`.
- [x] Aliases preserve operands, option collisions, cwd (including subdirectory
  invocation), streams, help, exits 0/1/2/75/130, publication deadlines and
  terminal behavior. No new success text or usage record reaches stdout. The
  new stderr framing (alias `→ coga …`, `Launch: task bootstrap/megalaunch`,
  `Script exited with N.`) is expected. `megalaunch` leaves
  `_SWEEPING_COMMANDS`; a user `[aliases]` entry expanding to `megalaunch …`
  fails `validate_aliases` with a message naming the new expansion (tested).
- [x] Every section of `coga/megalaunch` has parity coverage: refresh before
  selection; owner and human gates; bare versus explicit selection; saved
  selections and missing tasks; draft interview/check/deferred activation;
  service order; dependency drain and exact rollback; attempt counting and
  first-step override; eight-step bound, timeouts and no-progress failure;
  summary delivery after stdout. Skipped work and unreached picks stay
  untouched.
- [x] The queue cannot bypass exact-byte claim publication, final local/control
  proofs, held-child release/admission or `pending:`/`released:` recovery by
  changing selection or instructions. Publication failure distinguishes a
  definite refusal from an uncertain result and never overwrites a later edit.
  Queue admission keeps its separate publication deadlines and its current
  failed-row/exit-1 contract.
- [x] One shared `mark.reblock_unresolved_resume` replaces
  `launch._reblock_unresolved_resume` (all three call sites) and
  `megalaunch._reblock_unresolved`, with the parity table in Proposed shape.
  The deterministic `resume_step`/`fallback_ticket_bytes` behavior moves into
  the shared operation unchanged: the fallback `write_ticket`, then one
  `mark_blocked` write.
- [x] Through sibling 05's discover/copy mechanism, a fresh wheel user can find
  the effective `megalaunch` command, copy its ticket and the full edge
  implementation, edit policy locally and run the fork. The fork imports no
  installed edge module; upgrading the wheel leaves it unchanged; restoring
  stock files rejoins updates. If 05 is not merged at implementation entry,
  prove the same with a manual full copy and record the gap.
- [x] Update contract owners and dependent links in the same PR: package
  `coga/megalaunch`, `coga/cli`, `coga/launch`, `coga/edge-code`,
  `coga/script-tickets` (separator rules, interrupt rule, no agent fallback),
  `coga/state-publication` and `launch-boundaries` where affected; local
  `coga-dev/microkernel` (megalaunch placement settled; slack row records the
  retained-head proof and the sibling). Preserve one package owner and pin
  the packaged resources in `tests/required_package_resources.txt`.
- [x] Record physical Python lines at named before/after revisions across core,
  edge and ticket scripts, including new shared operations, using
  `len(bytes.splitlines())` with blanks/comments. List the file set and removed
  entrypoints/import paths. Report relocation, actual deletion/deduplication,
  tests, docs and resource wrappers separately.
- [x] Extend existing tests and run the full Linux suite and scoped validation
  with exact receipts. Native Windows/macOS evidence is deferred to release;
  report the actual Python version and any missing 3.11-floor evidence.

### Proposed shape

#### Owner decisions — 2026-11-16

1. **Scope.** This ticket implements megalaunch only. The Slack sibling exists
   as a draft; it is not activated or launched by this ticket.
2. **Invocation.** The design-time `--command` flag is dropped: no ticket owns
   it, and plain `launch bootstrap/<x> --` already provides most of the
   needed effect policy (see the deltas below). This ticket's PR implements
   the three narrow generic rules itself.
3. **Interrupts.** The parent never kills a running stateless command script
   on its own interrupt; this ticket implements and tests it as a generic
   launch rule.

#### Prerequisites at implementation entry

- Sibling 03 (`03-launch-decomposition`, PR #1233) was in review and unmerged on
  2026-11-16. Before writing code, check what merged. If
  `launch.prepare_agent_launch` (or its reviewed successor) is on main, consume
  it for queue readiness. If 03 is still unmerged, implement against current
  main, keep readiness inside the shared queue operation, and record the
  overlap for whichever PR merges second. Never duplicate 03's readiness
  reduction in the line-count report. 03's branch
  (`coga/v1-microkernel-03-launch-decomposition-6852fc`, `0bf44d2a1`) also
  changes `run_script_phase` (read-only vanish raises `FileNotFoundError`,
  close to rule 1) and `cli.py`'s sweep predicate (`--`-aware slicing,
  `TOMLDecodeError`). Reuse those if merged; otherwise expect merge conflicts
  there.
- Sibling 05 supplies complete-fork discovery; see the fallback in Acceptance
  criteria.
- Sibling 08 owns `_author_draft`'s authoring dependency (below).
- Sibling 04 is restructuring `recurring_runner`; coordinate the
  `session_limits.py` home with 04 (below) before moving the parser.

#### Editable command boundary

Package `templates/coga/bootstrap/megalaunch/ticket.md` and exact sibling
`ticket.py`, mirroring `bootstrap/retire`. The shim imports
`coga_edge.megalaunch` and calls `sys.exit(main(sys.argv[1:]))` exactly once.
Prefer one self-contained policy module so forks stay simple; a private
edge-only helper package is acceptable only if sibling 05 copies its complete
import closure. The module must not import `coga.commands.*` or
`coga.megalaunch`.

The edge parser owns the existing usage errors, `--agent`, `--pick` and
`--help`. Inherited terminal streams stay attached, and script framing stays on
stderr. Scripts run from `task_env.host_repo_root`; characterize subdirectory
invocations before moving relative-path parsing. Configuration discovery and
reloads stay rooted in the invoking repository. The queue performs its own
refresh before reading tickets, then reloads config, keeping its
feature/detached behavior.

Plain launch already gives a stateless bootstrap script this policy (verified
by the evaluator against `launch_script.run_script_phase` and
`coga/checkouts/launch-boundary`): no checkout preparation or return for
non-orient bootstrap targets; no activation, launch/exit audit, push probe,
skill refresh or agent lookup; no configured agent required; one outer sweep;
exit 75 withholds sweep and refresh. The deltas this ticket adds, as generic
launch rules for any stateless bootstrap target:

1. **No agent fallback after script classification.** A target that
   `_align_and_classify` classified as a script (`entry is not None`) and whose
   `ticket.py` is gone by `run_script_phase` (today `ran=False`, which hands off
   to an agent; `launch_script.py` around 124-136 and 200-226) exits 2 before
   the child starts. Bootstrap targets without `ticket.py` are unchanged:
   launch cannot see whether the user typed `--` (Click consumes it), and the
   agent-only command tickets rely on trailing arguments becoming the
   `## Launch arguments` prompt block. Stateful chaining is unchanged.
2. **Script help, fail closed.** Help is the exact token `--help` among the
   launch's trailing arguments before a script-level `--` (Typer has no `-h`
   and no abbreviations). Detect it in `launch()` from raw argv before
   `load_config`, using one separator-aware predicate shared with
   `cli._should_sweep_coga_state` (today `cli.py:393` scans every token) and
   `main()`'s `help_invoked`. Resolve the bootstrap target with
   `require_user=False` inside a valid repo (local overrides win) or from the
   packaged definition outside one. Run it through the factored spawn helper
   (rule 3) with cwd = host repo root when a repo exists, else the invocation
   cwd; env = inherited, with `TASK_ENV_KEYS`, supervisor, sentinel and
   expected identity cleared, no secrets, plus `COGA_SCRIPT_HELP=1`. No refresh,
   audit, publication or sweep. Because Typer binds a value-taking option to
   `--help` (`--agent --help` sets `agent='--help'` and runs the body), help mode
   fails closed: each command script following this rule checks
   `COGA_SCRIPT_HELP` at its command body and exits 2 without effects. A repo
   with an invalid `coga.toml` must still print `coga megalaunch --help`
   (today `_needs_no_config` covers the built-in): `cli.main`'s
   non-"No coga.toml" branch resolves the alias from `DEFAULT_ALIASES` and the
   packaged definition for a help request; test it. The normal script phase
   pops any inherited `COGA_SCRIPT_HELP`. Tests:
   `megalaunch --help`, `pick --help`, `retire --help` with no user and no
   repo; `retire 1 --agent --help` and `megalaunch --agent --help` exit 2 with
   no effect; a help request makes no Git call.
3. **Interrupt rule.** Factor one spawn/wait/relay helper used by the normal
   script phase and help mode, reusing (or replacing) the relay in
   `recurring_runner.py` around 392-420 rather than adding a third. Share
   only the forwarding and code-mapping pieces; recurring keeps its return
   contract (`128+SIGTERM` whenever terminated, re-raised `KeyboardInterrupt`
   after waiting), and sibling 04 owns that file's restructuring. It uses
   `Popen`/`wait`. While the child runs, the parent installs a no-op Python
   SIGINT handler (SIGBREAK too on Windows). It never uses `SIG_IGN` or
   `SetConsoleCtrlHandler(NULL, TRUE)`, which children inherit and which would
   disable Ctrl+C in the queue. The terminal or console delivers Ctrl+C to the
   child directly. SIGTERM is forwarded to the child once; a group-wide SIGTERM
   arrives twice, and the duplicates are harmless or coalesce. The parent never
   kills the child on its own, maps a negative return code to `128 - code`
   (`oscompat.process_exit_status` passes negatives through today), and
   restores its handlers afterwards. This replaces the `subprocess.run`
   behavior (about 0.25 s wait, then kill) that bypasses the picker's quit
   handling and `repl_supervisor`'s deferred-signal windows.

This is cooperative command dispatch, not an arbitrary-code sandbox. Owner
acceptance is recorded above.

#### Queue/core API and transaction boundary

Stable operation in `src/coga/launch.py` (spelling approved as below):
`run_claimed_agent_session(cfg, ref, *, source_bytes, prospective_ticket,
agent_name, activation=None, blocker_answers=None, idle_timeout=None,
max_session=None)`. If sibling 03 has merged a reviewed readiness API by
implementation entry, adapt the spelling to it; the semantic boundary is fixed:

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

For concrete deduplication, add `src/coga/mark.py`,
`reblock_unresolved_resume(cfg, ref, *, slack_actor, log_message, echo_owner_text,
resume_step=None, fallback_ticket_bytes=None)` (callers supply all texts). It rereads
the current ticket bytes, parses open asks with `parse_blockers_text`, applies
the in-progress-only agent rule, and calls `mark_blocked` (reusing its
validated write, audit, notification and publication). It returns a structured
result: `reblocked(detail)`, `already_blocked(detail)`, `noop` or
`invalid(error)`. Migrate all three `launch._reblock_unresolved_resume` call
sites and `megalaunch._reblock_unresolved` together. Parity target, per caller:

| Divergence today | Ordinary launch keeps | Queue keeps |
| --- | --- | --- |
| Ticket source | Reread current bytes (unchanged) | Reread current bytes instead of the passed `after`; `after` was read just before, so the reread is equal or fresher. Test a concurrent edit between the two reads. |
| Blocker parser | `parse_blockers_text` on the reread blackboard | Same parser; drop `blackboard.open_blockers` here. Test identical results on resolved and unresolved asks. |
| Already `blocked` | `already_blocked` → `True` (ask stays parked) | `already_blocked` → no row; `_chain_stop_result` still reports `blocked` |
| Validation failure | `invalid` → `_bail` (exit 2) | `invalid` → `failed` row |
| Slack actor text | `blocker or cfg.current_user` | `cfg.current_user` |
| Audit wording | `...after resumed launch exited` | `...after resumed megalaunch pick exited` |
| Deterministic resume (`resume_step` given) | Today's behavior moved unchanged: on unreadable/missing bytes restore `fallback_ticket_bytes`; skip the `already_blocked` return after a fallback restore; re-block a ticket the script left paused or terminal; restore `step` in memory; keep the fallback `git.write_ticket`, then one `mark_blocked` write | n/a: the queue never passes `resume_step`, so an agent queue never restores a terminal ticket |

The queue maps results to rows with `launched=True` metadata as today.

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
Sibling 04 is restructuring `recurring_runner`; confirm the
`session_limits.py` home with 04's owner before moving the parser, so it is
not moved twice. If 04 has already relocated these helpers, consume its home.

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


#### Slack: retained head and its co-versioning proof

`src/coga/commands/slack.py`, `slack` (94 physical lines) stays a core command
head. Proof: it joins delivery (`notification.post`), audit (`append_log`) and
matching-session completion (`repl_supervisor.emit_done_marker` through
`deferred_done_marker`) inside the CLI's deferred finalization. The script
phase deliberately clears `COGA_SUPERVISED`, the sentinel and the expected
identity, so an edge script cannot preserve that transaction without a new
parent-owned completion mechanism. Moving ordinary FYIs alone would not
complete the migration. This ticket records the proof in the
`coga-dev/microkernel` open-placement row and names the sibling; it does not
claim Slack forkability.

The draft sibling `v1/microkernel/move-slack-fyis-to-a-command-ticket` holds
the full Slack design carried over from this ticket: the parent-owned
audited-notification protocol, the cheaper post-exit audit-line alternative
with its threat-model question, the durable-audit tightening, the failure
matrix and the test map. This ticket does not activate, launch or implement it.

### Out of scope

Slack migration and its completion mechanism (sibling above). No retire work
beyond adopting the generic launch rules (its `ticket.py` checks
`COGA_SCRIPT_HELP`), and no recurring scheduling/admission migration, recipe
inventory change, script-aware queue, new queue executor, generic plugin framework, new launch
flag, prompt-assembly redesign, notification retry/digest policy, task creation
per command invocation or native-host allocation. Do not change the queue's
exit/sweep contract; any such change needs a separate owner decision.

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

The Slack test map moved to the Slack sibling with its design (owner gate,
2026-11-16). Existing `tests/test_commands.py` Slack tests must still pass
unchanged here.

Use `tests/test_launch_script.py`, `tests/test_aliases.py`,
`tests/test_commands.py` and `tests/test_packaging.py` for direct/alias parity,
wheel invocation, ordered argv with whitespace and option-like operands,
subdirectory cwd, help with no user or repo, interrupt propagation, no agent
fallback, non-TTY refusal, stderr/stdout separation, exit 1/2/75/130,
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
Settled at the owner gate on 2026-11-16: megalaunch only here; Slack retained
under its proof, with the draft sibling `move-slack-fyis-to-a-command-ticket`.

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
  remain distinct, with no new retry/digest policy. Here only the queue
  summary's post is in scope; the Slack head is retained.
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
## Dev

pr: https://github.com/FastJVM/coga/pull/1244
branch: coga/v1-microkernel-09-work-orchestration-commands-to-b46008


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

All four design questions were answered at the owner gate on 2026-11-16 (see
"Owner gate — 2026-11-16" below). None remain open for implementation.

1. Scope: megalaunch only in this ticket; Slack sibling created as a draft.
2. Slack: head retained under the co-versioning proof; the sibling decides
   between the parent-owned operation and the cheaper audit-line check.
3. Durable-audit tightening: moved to the Slack sibling, still unapproved.
4. Prerequisites: no sibling API is required to merge first. Implementation
   checks 03/04/05/08 at entry and uses the fallbacks in Proposed shape.

## Evaluator review

Design findings were resolved at the owner gate below. The complete earlier
evaluation is retained under `## Superseded designs`; it is design evidence,
not independent review of the implementation.

## Owner gate — 2026-11-16

Attended review-design session with the owner. Decisions: megalaunch-only
scope; drop `--command` and use plain `launch bootstrap/megalaunch --` plus
three generic rules implemented here (no agent fallback, help without
user/repo, interrupt rule); Slack retained with a draft sibling. Ticket
Description rewritten accordingly.

Evaluator dispositions:

1. `--command` ownership/necessity (must-fix): resolved. Flag dropped; exact
   deltas from plain launch listed in "Editable command boundary"; this
   ticket's PR owns them. Help is recognized as Typer does (exact `--help`
   before a script-level `--`), so `pick --help` works and no unqualified token
   scan exists.
2. Interrupt semantics (must-fix): resolved. Generic interrupt rule and tests
   added to Acceptance criteria and Proposed shape.
3. Slack cheaper verification: transferred to the Slack sibling with the
   threat-model question.
4. Re-block parity: accepted; per-caller parity table added.
5. Queue environment re-minting: accepted; criterion added.
6. Session-limit coordination with sibling 04: accepted; note added.
7. Criteria finality: accepted; Slack criteria removed from this ticket and
   carried by the sibling.

Second cold evaluation (2026-11-16, subagent, read-only) returned not ready
with five must-fix items; all were fixed in the Description the same day:

- M1: no-fallback rule narrowed to the classified-then-vanished race;
  agent-only bootstrap targets keep launch arguments.
- M2: help made separator-aware in one predicate shared with the CLI sweep,
  and fail-closed through `COGA_SCRIPT_HELP` (Typer binds `--agent --help`).
- M3: help path detected before `load_config`, with cwd/env specified;
  invalid-config help covered.
- M4: no-op handlers instead of `SIG_IGN` (inherited), `Popen`/`wait`,
  negative-code mapping, one shared relay with `recurring_runner`.
- M5: deterministic `resume_step`/fallback behavior moved into the shared
  operation, with its own parity row.

Re-check of the fixes by the same evaluator: ready for implementation, no new
must-fix. Its three wording recommendations (fallback write order, recurring
relay contract, invalid-config help and retire scope) were applied.

Recommendations also adopted: sibling 03 branch overlap points, user-alias
migration and `_SWEEPING_COMMANDS`, picker raw-mode test scope, full re-block
signature, expected stderr framing.

Sibling 03 (PR #1233) was unmerged at this gate; implementation checks it at
entry (see Prerequisites).

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


### Evaluator review

Cold review, 2026-11-16, by claude (other-agent) at control `ef81e5ccc`. There is
no `src/` or `tests/` drift since the design base `5edb1f9`. Ticket structure is
sound: Acceptance criteria, Proposed shape and Out of scope are `###` sections
under `## Description`, and the design notes are under `## Context`. The cited
symbols exist with the stated roles (`megalaunch._launch_until_stop`,
`_revalidate_launch_claim_before_spawn`, `_admit_launch_claim_after_release`,
`_activate_for_launch`, `_reblock_unresolved`, `_preflight_agent_launch`,
`_author_draft`; `launch._reblock_unresolved_resume`, `spawn_agent_session`,
`_interactive_stdio_has_tty`; `recurring_runner._recurring_idle_timeout` and
`_recurring_max_session`; `repl_supervisor.emit_done_marker`,
`deferred_done_marker`, `_admit_held_child`; `git.sync_log -> bool | None`).
The line counts match (641 / 2,407 / 94), and so do the `aliases.validate_aliases`
first-token rule and the named regression tests. `launch.prepare_agent_launch`
is still absent from main because sibling 03's PR #1233 has not merged. The
queue transaction boundary, re-block deduplication, Slack completion analysis
and tightened audit gate are careful and implementable.

**Verdict: not ready for implementation as written.** Two must-fix items
affect the alias cutover that both moves depend on. The owner can settle both
at review-design without a redesign.

#### Must resolve before implementation

1. **`--command` has no owner that accepted it, and its necessity is not
   shown against plain launch.**
   - *Ownership.* The design makes the `--command` flag (and its help
     dispatch) "a required sibling-03 contract", and Open Question 4 says
     sibling 03 must ratify it. Sibling 03's reviewed contract ("Draft
     stateless invocation contract") defines only `--read-only`. For writers
     it explicitly keeps "Ordinary launch / write dispatch" unchanged. That
     ticket is now at step 5 (review), its PR is implemented, and its
     handoff says no further implementation obligation is deferred. Nothing
     there will deliver `--command`.
   - *Necessity.* The `retire` alias (`launch bootstrap/retire --`) shows
     that plain launch already gives a stateless bootstrap script most of the
     listed effect policy:
     - `checkouts/launch-boundary` exempts bootstrap targets other than
       `bootstrap/orient` from checkout preparation and return.
     - `launch_script.run_script_phase` writes no activation and no launch or
       exit audit when `stateless=True`.
     - The script phase skips the push probe, skill refresh and agent lookup.
     - A script-only bootstrap needs no configured agent.
     - The CLI keeps one sweep, and exit 75 withholds it.

     The real gaps appear to be: (a) a disappeared or missing `ticket.py`
     can fall through to an agent; (b) `--help` needs a configured user and
     repo; (c) the Slack parent-owned completion channel.
   - *Decision needed.* The owner should require the spec to list the exact
     deltas from plain `launch bootstrap/<x> --`, then either drop `--command`
     (using plain launch plus a narrow no-fallback and help rule) or keep it
     with that minimal scope. Either way, assign it to an owner that will
     actually implement it: this ticket's megalaunch PR, a new sibling, or a
     reopened 03 follow-up. As written, the alias cutover depends on a
     prerequisite that no ticket will deliver.

2. **Interrupt and termination semantics across the new parent/child
   boundary are not specified, and the obvious implementation breaks
   megalaunch.**
   - *What breaks.* Today `coga megalaunch` is one process. Its picker
     handles Ctrl+C itself (`commands.megalaunch._WindowsKeys` installs a
     flag-only SIGINT handler that treats Ctrl+C as `q`). The
     `repl_supervisor` claim, release and admission windows defer
     SIGINT/SIGTERM so retained evidence stays consistent. Under the alias,
     the queue runs as a child of `coga launch` through
     `launch_script.run_script_phase`, which calls a plain
     `subprocess.run([sys.executable, ticket.py, ...])`. A terminal Ctrl+C
     (POSIX foreground process group, or a Windows console control event)
     also reaches the parent. CPython's `subprocess.run` then waits about
     0.25 s and SIGKILLs or terminates the child. That bypasses the picker's
     quit handling, the deferred-signal windows and megalaunch's
     rollback/retention cleanup, so it can leave a pending claim or held
     child unsettled. The ordinary launch supervisor's `_on_signal` handler
     is installed only on the agent-chain path, not around this script
     phase. Short scripts such as `retire` never exposed this.
   - *What to add.* An acceptance criterion and design text: while a
     command script runs, the parent ignores or forwards SIGINT/SIGTERM
     (and Windows Ctrl+C/Ctrl+Break) and never kills the child on its own
     interrupt. It then propagates the child's exit status (130/`128+n`)
     unchanged. This is a generic launch rule, not a megalaunch special
     case.
   - *Tests.* Interrupt at the picker, between picks, and inside a claim
     window, each through the alias, asserting retained claim evidence and
     exit status. Native Windows evidence stays deferred to release.

#### Recommendations (optional, ordered by impact)

3. **Slack completion: weigh a cheaper verification before building a
   transport.** The proposed invocation-scoped request/receipt channel is,
   in effect, a new bidirectional IPC transport on POSIX and Windows, built
   to move about 20 lines of operand and formatting policy (the parent would
   own posting, audit and publication). Before siblings 03 and 10 commit to
   it, the owner may want a sketch of the transport (fd or handle
   inheritance, framing, Windows equivalent) and its line cost.
   - One cheaper alternative: the parent captures the session identity
     before isolation, runs the child, and after exit 0 confirms on control
     (or locally when Git is disabled) a new `slack:` audit line for the
     captured bootstrap slug written during this invocation. Only then does
     it request the marker.
   - That alternative trusts cooperative child output, which the spec
     rejects ("a matching string supplied by the child is insufficient").
     But the spec also says `--command` is cooperative dispatch, not a
     sandbox. Make the threat model explicit (accidental versus adversarial
     completion) so the owner can choose. Retaining the 94-line head under
     the co-versioning proof remains a reasonable outcome.
4. **Spell out the re-block parity differences.** `reblock_unresolved_resume`
   must reconcile real divergences:
   - Megalaunch acts on the passed `after` ticket and uses
     `blackboard.open_blockers`, while launch rereads the bytes and parses
     with `parse_blockers_text`.
   - Launch returns `True` for an already-`blocked` ticket; megalaunch
     returns no row.
   - Launch `_bail`s (exit 2) on `TaskValidationError`; megalaunch returns a
     `failed` row.
   - Slack text uses `blocker or current_user` versus `current_user`.

   Name which behavior each caller keeps, so the deduplication has a
   checkable parity target.
5. **Environment inheritance through the queue script.** The queue child runs
   with `COGA_SCRIPT_TASK=<bootstrap/megalaunch path>`, an empty sentinel and
   no `COGA_SUPERVISED`. Add a test that each queued agent's environment is
   re-minted (marker cleared through `TASK_ENV_KEYS`, fresh supervised
   witnesses) and that queued lifecycle commands credit the agent, not
   `system`.
6. **Session-limit helper coordination.** `_recurring_idle_timeout` and
   `_recurring_max_session` live in `recurring_runner`, which sibling 04 is
   restructuring. Name sibling 04 alongside 03 when choosing the home of
   `session_limits.py`, so the shared parser is not moved twice.
7. **Acceptance-criteria finality.** The checklist is written for the
   two-command program, with a note that the owner narrows it. That is
   acceptable for this gate. At review-design, physically move the Slack
   criteria (and the completion and audit-gate items) to the sibling, or
   mark them retained-head, so implement does not inherit criteria it cannot
   meet.

#### Ready elements

- Queue/core split: policy goes to the edge; claim, held-child and admission
  stay in core under a stated co-versioning proof with ordinary-launch
  recovery as a real consumer.
- Exit and sweep preservation for megalaunch rows.
- Exact-byte compare-and-set versus three-way lifecycle merge.
- `_author_draft` handoff to sibling 08.
- Slack mismatch and failure matrix and the honest audit-gate tightening.
- Line-count method and test map.

None of these needs change. No ticket body, code, branch or PR was produced
by this review.


## Implement decisions and evidence — 2026-11-16

Owner confirmed all three pending decisions in the attended session: one-line
repo pick alias migration, shared `session_limits.py` home coordinated before
moving sibling 04's helpers, and the narrow public authoring invocation adapter.
Those questions are resolved; no implementation decision remains pending.

### Implemented boundary

`bootstrap/megalaunch` selects the complete `coga_edge.megalaunch` implementation.
Picker, queue selection, owner filters, saved selection, service ordering,
dependency policy, budgets, liveness defaults, stop classification and summaries
are edge-owned. `launch.run_claimed_agent_session` enters the bounded
`claimed_session` transaction; generation/proof/release/admission callbacks
are constructed there, never supplied by policy. Activation and claim remain
separate publications. Existing pending/released recovery and failed-row/exit-1
behavior stay intact. Guarded activation rollback now preserves a changed or
deleted local postimage. The queue still launches agents, never task scripts.

The queue and ordinary launch use `mark.reblock_unresolved_resume`. Its
structured results preserve each caller's validation and already-blocked policy;
the deterministic fallback write, then `mark_blocked` write, remains intact.
Queue re-blocking rereads current bytes, rather than trusting its passed view.
`TASK_ENV_KEYS` clears script/help identity before queued supervision is minted.

Generic stateless script launch now recognizes separator-aware help before
ordinary launch setup, including absent user/repo and malformed TOML. Help is
fail-closed through `COGA_SCRIPT_HELP`; normal scripts clear inherited help.
A classified bootstrap script that vanishes refuses instead of starting an
agent. Agent-only bootstrap arguments are unchanged. `process_relay` shares
foreground forwarding/waiting with recurring: command parents use no-op Python
interrupt handlers, forward SIGTERM once, wait without killing, map negative
codes, and restore handlers. Recurring retains its distinct termination and
KeyboardInterrupt contracts. Retire gains these generic rules and body guard.

The approved authoring adapter invokes the public `ticket <ref> --agent <name>`
CLI, retaining its finalization and exit sweep. `cli.main`'s Python-only
`retained_state_exit` option maps withheld state to 75 before context cleanup;
there is no new CLI flag or copied executor. The queue propagates 75, while
ordinary interview failures leave the draft for checking. Real child-dispatch
regressions confirm argv, interview selection and ordinary/withheld sweep paths.

### Prerequisite/fork limitations

03's PR #1233 remains unmerged: readiness is in the shared claim transaction,
with overlapping `launch_script`/CLI changes identified for whichever PR merges
second. This ticket claims no sibling-03 readiness savings. 04's parsers moved
once into the owner-confirmed shared home, with both callers migrated. 08 still
owns the authoring coordinator's eventual placement; this ticket consumes the
public CLI rather than importing its command implementation. 05's discover/copy
command is unavailable on main: the approved manual complete-copy fallback is
specified in `coga/edge-code` and exercised from an isolated installed wheel.
A full fork survives wheel reinstall; restoring the shim selects stock behavior.
No Slack move, Slack audit tightening, new queue executor or script-aware queue
was implemented. Slack's retained-head proof names its draft sibling.

### Whole-system physical-line evidence

Before `f661ea965df0679ebbcc7397369138b7d6fbb30e`; after
`1a0b12c53586ac3945c679f03a491ea7efb29eb7`. Each count is
`len(bytes.splitlines())`, including blanks/comments, on the union of changed
production Python paths. Deleted/added files count zero at the absent side.
The set includes shared modules changed by the extraction, not only moved files.

| Production path | Before | After |
| --- | ---: | ---: |
| `src/coga/aliases.py` | 95 | 100 |
| `src/coga/argv.py` | 0 | 21 |
| `src/coga/authoring.py` | 352 | 378 |
| `src/coga/claimed_session.py` | 0 | 648 |
| `src/coga/cli.py` | 654 | 659 |
| `src/coga/commands/megalaunch.py` | 641 | 0 |
| `src/coga/commands/ticket.py` | 423 | 423 |
| `src/coga/config.py` | 2029 | 2029 |
| `src/coga/launch.py` | 4590 | 4540 |
| `src/coga/launch_script.py` | 620 | 674 |
| `src/coga/mark.py` | 756 | 856 |
| `src/coga/megalaunch.py` | 2407 | 0 |
| `src/coga/process_relay.py` | 0 | 52 |
| `src/coga/recurring_runner.py` | 5680 | 5601 |
| `src/coga/resources/templates/coga/bootstrap/megalaunch/ticket.py` | 0 | 8 |
| `src/coga/resources/templates/coga/bootstrap/retire/ticket.py` | 420 | 423 |
| `src/coga/session_limits.py` | 0 | 44 |
| `src/coga/task_env.py` | 167 | 168 |
| `src/coga_edge/megalaunch.py` | 0 | 2399 |

Core: 18,414 → 16,193 (−2,221); edge: 0 → 2,399; packaged Python
wrappers/retire script: 420 → 431 (+11). Combined production: 18,834 → 19,023
(+189). This is a boundary extraction with generic launch behavior added,
not a whole-system size reduction. Most of the 3,048-line old queue/head
relocates into the 2,399-line edge module and 648-line claim transaction.
The import-only command shim is 8 lines, counted separately above.

Concrete deduplication: the two old unresolved-resume functions occupy
91 + 42 = 133 physical lines; the new shared operation plus result dataclass
and two caller adapters occupy 75 + 4 + 15 + 12 = 106 (−27). These are AST
function/class spans, decorators and internal blank/comment lines included,
excluding separators between definitions. Session-limit parsing is relocation
of already-shared code, not deduplication. The foreground relay replaces the
existing recurring relay body and adds command-specific waiting semantics;
its net cost is not claimed as deletion. Deferred readiness, discovery and
authoring-coordinator simplification have the named owners 03, 05 and 08 above.

Removed entrypoints/dependencies: built-in megalaunch head and lazy registry;
`coga.megalaunch`; `coga.commands.megalaunch`; pick's alias-to-old-head expansion;
queue imports of `coga.commands.ticket` and `recurring_runner` private parsers;
old `launch._reblock_unresolved_resume`; duplicated queue re-block mutation.
No compatibility re-exports or core imports of edge/ticket code were added.

Separately, 16 changed test/fixture/manifest paths total 46,140 → 46,617 lines
(+477); 12 Markdown owner/navigation/resource paths total 1,508 → 1,642
(+134); two TOML files total 457 → 457. These are whole-file physical totals,
not production savings. The required-resource manifest pins both new bootstrap
owners; package ownership/navigation and isolated wheel tests remain authoritative.

### Final verification

Tested head `1a0b12c53586ac3945c679f03a491ea7efb29eb7`, merge-base
`f661ea965df0679ebbcc7397369138b7d6fbb30e`; Pop!_OS 24.04 LTS,
Linux `7.2.15-76070215-generic`, Python 3.12.12.

- Full suite → **4,940 passed, 33 skipped, 0 failed in 840.51 seconds**, exit 0:
  `TERM=dumb PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest --basetemp=/home/n/Code/coga-pytest-orchestration-implement-20261116 > /tmp/coga-orchestration-implement-pytest.log 2>&1`.
- `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m coga.cli validate --task v1/microkernel/09-work-orchestration-commands-to-tickets --json`
  → one valid ticket, no issues, exit 0.
- From `tests/fixtures/seeded-repo/coga`:
  `env -u SLACK_WEBHOOK_URL PYTHONPATH=/home/n/Code/coga/src /home/n/Code/coga/.venv/bin/python -m coga.cli validate --json`
  → five valid tickets, no issues, exit 0.
- `git diff --check` and `git diff --cached --check` → exit 0 before commit.

Production/test/docs tree is committed. Only the projected ticket is dirty.
A byte-verified copy at `/tmp/coga-queue-implement-ticket-before-rebase.md`
preserved it while rebasing onto current control; no source conflict occurred.
Native Windows/macOS verification remains deferred to release. Python 3.11
floor evidence is absent; Linux 3.12 does not establish native or floor parity.
Independent code review has not run: the later workflow step owns it.
Repo-wide `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m coga.cli validate --json`
also exited 0: 101 valid tickets, 21 warnings, zero errors (report at
`/tmp/coga-orchestration-implement-validate.json`).


## Peer review

Reviewer: Claude (Opus 5.5), configured peer, attended session; the implement
step was Codex, so this is independent review. Form: `/code-review` at
default effort (not ultra) against `main...HEAD`. It **returned** (completed)
before any fix. Covered head `5dffad16daf93815ede0acd78c68f197e250d05a`
(the implement commit rebased unchanged onto base
`657d6f5d65dd66e06800d86943a45660258552a4`; main had only gained Coga state
commits). Each finding was checked against the code before action; the owner
approved the fix scope in session.

Applied in `d68562ea8174d9825c550e1d28025a2ccd334381` (must-fix):

1. `cli.main(retained_state_exit=True)` mapped any withheld sweep to 75, so a
   pre-write refusal (unrepresentable agent command, `AgentCommandRefused`)
   aborted the whole queue. Now only `authoring.authored_state_retained`, set
   by the refused guarded finalization, maps to 75.
2. The adapter's public `coga ticket <slug>` scaffolded a new draft when a
   picked ref no longer resolved. The Python-only `existing_target_only` seam
   now refuses with exit 2; the queue leaves it to the check phase.
3. Setup-free script help raised an uncaught `TaskNotFoundError` or
   `BootstrapOverrideError` (a traceback). It now returns to ordinary launch,
   which reports it as before.
4. Claimed-session activation refusals all became `failed` rows. The
   `activation_error` is now returned and classified through the edge's
   `_activation_refusal`, restoring `skipped-unlaunchable` per `coga/megalaunch`.

Cleanups: a named queue-owned `QUEUE_IDLE_TIMEOUT_SECONDS` (the reviewer
suggested sharing recurring's constant, but the approved design gives each
caller its own default); the orphaned `PREPARE_ACTIVE_ERRORS` comment moved
beside its definition in `mark.py`.

Declined: help-mode cwd duplicating `host_repo_root` (help must work with no
loadable config); the `launch.run_claimed_agent_session` wrapper (spelling
approved in this ticket); unused `ClaimedSessionResult.released`/`retained`
fields (nit; leave for sibling 03's readiness consolidation).

Each new regression test failed with the source fixes stashed and passed with
them. No terminal-only surface changed in the fixes; the picker was not
modified by this step. Its raw-mode behavior stays covered by the existing
mocks, and native evidence is deferred to release. The fix commit was not
re-reviewed by another agent; receipts in `## PR` name which head each covers.
Full suite at `d68562ea8`: 4,945 passed, 33 skipped. Branch pushed with
`--force-with-lease` after the rebase.

## PR

```yaml
"title": "Move megalaunch queue policy to an editable command ticket"
"author": "codex"
"author_evidence": "Actual implement session used Codex; launch c50c7e56-efd4-418e-a79f-70ea1f95594b.\
  \ Owner confirmed the initial plan and three dependency decisions in attended chat."
"head": "d68562ea8174d9825c550e1d28025a2ccd334381"
"base": "657d6f5d65dd66e06800d86943a45660258552a4"
"depth": "deep"
"rationale": "This moves a large queue surface across a process boundary and preserves concurrent claim/release/admission\
  \ invariants. Independent peer review ran and its must-fix findings were applied; reviewers should still\
  \ read the claim transaction and the authoring adapter seams closely."
"implementation": "Complete edge queue/picker with direct launch aliases; bounded core claim transaction;\
  \ shared re-block and session-limit operations; generic setup-free help, no fallback after vanished\
  \ scripts and interrupt-safe foreground waits. Authoring uses the public CLI with retained-state mapping.\
  \ Peer review added two Python-only authoring-adapter seams (retained finalization only maps to 75;\
  \ a vanished pick is refused, not created), setup-free help falling through on unknown or broken bootstrap\
  \ targets, and activation-refusal classification carried to the edge."
"deviations": "Sibling 03 remains unmerged, so readiness stays in the claim transaction. Sibling 05 discovery\
  \ is unavailable; the approved manual full-copy fallback is tested. Owner approved the public authoring\
  \ adapter and one-line repo alias migration."
"limitations": "Linux Python 3.12 verification only; native Windows/macOS checks are deferred to release\
  \ and Python 3.11 floor evidence is absent. No real agent session was launched during tests. The independent\
  \ review covered the pre-fix head; the peer-review fixes were verified by regression tests and the full\
  \ suite but not re-reviewed by another agent. Net physical production growth was 189 lines before the\
  \ review fixes (the fixes add about 60); this is an ownership extraction plus generic launch behavior,\
  \ not a whole-system size reduction."
"files":
  "coga/coga.toml": "Apply the owner-approved one-line pick alias migration in this repository."
  "docs/contexts/coga-dev/codebase/SKILL.md": "Update the source map for edge policy and shared claim,\
    \ session-limit and foreground-wait modules."
  "docs/contexts/coga-dev/microkernel/SKILL.md": "Settle queue placement and document the bounded claim/authoring/Slack\
    \ co-versioning proofs and sibling ownership. Records the two authoring-adapter seams."
  "src/coga/aliases.py": "Replace the megalaunch built-in and pick target with direct launch aliases;\
    \ explain migration of user aliases."
  "src/coga/argv.py": "Share exact separator-aware help recognition between dispatch and publication."
  "src/coga/authoring.py": "Invoke the public ticket CLI with selected agent, isolated identity, retained-finalization\
    \ exit mapping and existing-target-only seams."
  "src/coga/claimed_session.py": "Own exact activation and claim transactions, readiness, held-child release/admission\
    \ and guarded rollback. Return refused activation errors for caller classification."
  "src/coga/cli.py": "Remove the queue head; preserve help exclusions and expose Python-only retained-finalization\
    \ mapping and existing-target-only seams before context reset."
  "src/coga/commands/megalaunch.py": "Delete the old built-in queue/picker command head."
  "src/coga/commands/ticket.py": "Consume the renamed public TTY predicate; mark retained finalization\
    \ and refuse creation under the queue adapter's existing-target-only seam."
  "src/coga/config.py": "Point shared limit resolution commentary at its new owner."
  "src/coga/launch.py": "Expose the bounded claimed-session operation, public TTY predicate, early script\
    \ help and shared re-block result adapter."
  "src/coga/launch_script.py": "Add stateless no-fallback, help isolation, foreground relay and exact\
    \ exit propagation. Unknown or broken bootstrap help falls through to ordinary reporting."
  "src/coga/mark.py": "Own the shared unresolved-resume operation, typed outcomes and activation refusal\
    \ tuple. Documents the prepare-half refusal tuple."
  "src/coga/megalaunch.py": "Old side of the rename into src/coga_edge/megalaunch.py; removes the former\
    \ core queue-policy import path."
  "src/coga/process_relay.py": "Share interrupt-safe foreground waiting and one-shot SIGTERM forwarding\
    \ with recurring."
  "src/coga/recurring_runner.py": "Migrate existing relay and limit-parser consumers while preserving\
    \ recurring-specific contracts."
  "src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md": "Update this contract owner\
    \ for editable queue dispatch, script help/interrupts, full forks or publication/authoring boundaries."
  "src/coga/resources/templates/coga/bootstrap/contexts/coga/edge-code/SKILL.md": "Update this contract\
    \ owner for editable queue dispatch, script help/interrupts, full forks or publication/authoring boundaries."
  "src/coga/resources/templates/coga/bootstrap/contexts/coga/launch/SKILL.md": "Update this contract owner\
    \ for editable queue dispatch, script help/interrupts, full forks or publication/authoring boundaries."
  "src/coga/resources/templates/coga/bootstrap/contexts/coga/megalaunch/SKILL.md": "Update this contract\
    \ owner for editable queue dispatch, script help/interrupts, full forks or publication/authoring boundaries."
  "src/coga/resources/templates/coga/bootstrap/contexts/coga/script-tickets/SKILL.md": "Update this contract\
    \ owner for editable queue dispatch, script help/interrupts, full forks or publication/authoring boundaries."
  "src/coga/resources/templates/coga/bootstrap/contexts/coga/state-publication/SKILL.md": "Update this\
    \ contract owner for editable queue dispatch, script help/interrupts, full forks or publication/authoring\
    \ boundaries."
  "src/coga/resources/templates/coga/bootstrap/contexts/coga/state-publication/launch-boundaries/SKILL.md": "Update\
    \ this contract owner for editable queue dispatch, script help/interrupts, full forks or publication/authoring\
    \ boundaries."
  "src/coga/resources/templates/coga/bootstrap/contexts/coga/tickets/authoring/SKILL.md": "Specify the\
    \ queue authoring adapter: retained finalization maps to 75, pre-write refusals continue, vanished\
    \ picks are refused."
  "src/coga/resources/templates/coga/bootstrap/megalaunch/ticket.md": "Ship the editable stateless command\
    \ definition and links to its contract owners."
  "src/coga/resources/templates/coga/bootstrap/megalaunch/ticket.py": "Select the complete installed edge\
    \ policy through the reserved script entry."
  "src/coga/resources/templates/coga/bootstrap/retire/ticket.md": "Update help behavior to the generic\
    \ setup-free stateless-script contract."
  "src/coga/resources/templates/coga/bootstrap/retire/ticket.py": "Fail closed when a help token was consumed\
    \ as a value."
  "src/coga/resources/templates/coga/coga.toml": "Seed the new direct pick alias in fresh repositories."
  "src/coga/session_limits.py": "Relocate existing env/config liveness parsing with caller-owned idle\
    \ defaults."
  "src/coga/task_env.py": "Clear inherited script-help identity with all other launch-owned task metadata."
  "src/coga_edge/megalaunch.py": "Provide the complete independently copyable queue policy, parser and\
    \ picker; consume shared core operations. Classify claimed activation refusals as before; queue-owned\
    \ idle default."
  "tests/fixtures/authoring_cancellation.py": "Migrate existing fixtures and mocks to the public TTY predicate;\
    \ preserve the existing behavior assertions."
  "tests/required_package_resources.txt": "Pin both new bootstrap command resource owners."
  "tests/test_aliases.py": "Test direct aliases, old-target migration errors and separator-consistent\
    \ sweep recognition."
  "tests/test_authoring.py": "Exercise the public invocation adapter, identity isolation, real CLI dispatch\
    \ with pre-write and finalization refusals, and refusal of a vanished pick without creating a draft."
  "tests/test_checkouts.py": "Migrate existing fixtures and mocks to the public TTY predicate; preserve\
    \ the existing behavior assertions."
  "tests/test_cli.py": "Update pick expansion and test that only retained authoring finalization maps\
    \ to 75."
  "tests/test_create.py": "Migrate existing fixtures and mocks to the public TTY predicate; preserve the\
    \ existing behavior assertions."
  "tests/test_git.py": "Migrate existing fixtures and mocks to the public TTY predicate; preserve the\
    \ existing behavior assertions."
  "tests/test_launch.py": "Migrate existing fixtures and mocks to the public TTY predicate; preserve the\
    \ existing behavior assertions."
  "tests/test_launch_restart.py": "Migrate existing fixtures and mocks to the public TTY predicate; preserve\
    \ the existing behavior assertions."
  "tests/test_launch_script.py": "Cover generic help, argv/cwd/streams/status, no-fallback and real alias\
    \ interrupt/claim retention, plus public TTY seams. Unknown bootstrap help reports without a traceback."
  "tests/test_megalaunch.py": "Migrate policy/transaction seams and preserve queue coverage; add guarded\
    \ rollback, routing, identity and authoring-exit regressions. Claimed activation refusal keeps skipped-unlaunchable."
  "tests/test_packaging.py": "Test isolated installed command execution, a complete local fork, wheel\
    \ reinstall and stock-shim restoration."
  "tests/test_period_state.py": "Migrate existing fixtures and mocks to the public TTY predicate; preserve\
    \ the existing behavior assertions."
  "tests/test_recurring.py": "Migrate TTY seams and parser tests to their shared owners with explicit\
    \ caller defaults."
  "tests/test_ticket.py": "Migrate existing fixtures and mocks to the public TTY predicate; preserve the\
    \ existing behavior assertions."
"review":
  "reviewer": "claude"
  "kind": "independent"
  "status": "passed"
  "head": "5dffad16daf93815ede0acd78c68f197e250d05a"
  "base": "657d6f5d65dd66e06800d86943a45660258552a4"
  "detail": "Claude /code-review (default effort) of main...HEAD returned 9 findings on a Codex-authored\
    \ diff. Four must-fix findings were applied in d68562ea8 with failing-then-passing regression tests;\
    \ two cleanups applied; three declined with reasons under Peer review. The fix commit itself was not\
    \ re-reviewed."
"checks":
- "command": "TERM=dumb PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q --basetemp=/home/n/Code/coga-pytest-orchestration-peer-review-fixes-20261116"
  "status": "passed"
  "head": "d68562ea8174d9825c550e1d28025a2ccd334381"
  "base": "657d6f5d65dd66e06800d86943a45660258552a4"
  "detail": "4945 passed, 33 skipped, 0 failed in 788.41s; exit 0. Pop!_OS 24.04 LTS, Linux 7.2.15-76070215-generic,\
    \ Python 3.12.12."
- "command": "TERM=dumb PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q --basetemp=/home/n/Code/coga-pytest-orchestration-peer-review-20261116"
  "status": "passed"
  "head": "5dffad16daf93815ede0acd78c68f197e250d05a"
  "base": "657d6f5d65dd66e06800d86943a45660258552a4"
  "detail": "Pre-fix rebased head; 4940 passed, 33 skipped, 0 failed in 796.47s; exit 0. Same platform\
    \ and interpreter."
- "command": "PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m coga.cli validate --task v1/microkernel/09-work-orchestration-commands-to-tickets\
    \ --json"
  "status": "passed"
  "head": "d68562ea8174d9825c550e1d28025a2ccd334381"
  "base": "657d6f5d65dd66e06800d86943a45660258552a4"
  "detail": "One ticket valid; zero issues; exit 0."
- "command": "cd tests/fixtures/seeded-repo/coga && env -u SLACK_WEBHOOK_URL PYTHONPATH=/home/n/Code/coga/src\
    \ /home/n/Code/coga/.venv/bin/python -m coga.cli validate --json"
  "status": "passed"
  "head": "d68562ea8174d9825c550e1d28025a2ccd334381"
  "base": "657d6f5d65dd66e06800d86943a45660258552a4"
  "detail": "Five tickets valid; zero issues; exit 0."
- "command": "git diff --check"
  "status": "passed"
  "head": "d68562ea8174d9825c550e1d28025a2ccd334381"
  "base": "657d6f5d65dd66e06800d86943a45660258552a4"
  "detail": "No whitespace errors before the fix commit; exit 0."
- "command": "Native Windows and macOS full suites"
  "status": "not-run"
  "detail": "Deferred to release under coga-dev/testing; no native hosts were allocated."
- "command": "Python 3.11 floor verification"
  "status": "not-run"
  "detail": "The available test environment uses Python 3.12.12; no floor evidence claimed."
```


## Implement handoff — 2026-11-16

Implementation complete at `1a0b12c53586ac3945c679f03a491ea7efb29eb7`, pushed to
`origin/coga/v1-microkernel-09-work-orchestration-commands-to-b46008` with upstream
tracking. Final `git fetch origin main` confirmed control unchanged at
`f661ea965df0679ebbcc7397369138b7d6fbb30e`, which this branch contains. The full
Linux receipt and all final validations above describe this exact committed
source/test/docs tree. Only the projected ticket is dirty; it was never staged
or committed. No PR was opened (`gh pr list --head <branch> --state all` returned
none); the later publication step owns it. Launch owns checkout return.

Review attention: exact claim/source and postimage guards, held-child release
and admission, generic parent/child signal behavior, setup-free help's fail-closed
body guard and separator rules, authoring finalization/75 propagation, and full
local-fork isolation. Existing claim/recovery/publication tests were migrated to
their new transaction owner, not replaced with a new executor harness. Physical
production growth and deferred sibling work are explicit above; independent
code review is still required. Native Windows/macOS checks remain release-only,
and Python 3.11 floor evidence is not claimed.

All requested implementation work and handoff preparation are complete. The
next command is the one workflow bump, after which this session stops.
