---
title: Move lifecycle verbs to ticket operations
status: in_progress
owner: nicktoper
agent: codex
contexts:
- coga-dev/microkernel/objectives
- coga-dev/principles
- coga-dev/testing
- coga-dev/project-stage
- coga/git
- coga/extension-model
- coga/script-tickets
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
  - name: peer-review
    skills:
    - code/peer-review
    assignee: other-agent
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

Make the blocker-resolution procedure editable in adopting repositories.
Today single-ticket resolution and the interactive batch are both in
`src/coga/commands/unblock.py`. They already converge on one prepared write.
Moving that procedure into a command ticket exposes the selection, prompts,
and answer handling while keeping fresh-control reconciliation and publication
in the shared machinery. The owner accepted the parent scope on November 12.
This design goes through the child's own review before implementation.

### Proposed shape

1. Ship `bootstrap/unblock/ticket.md` and a sibling `ticket.py` with the
   complete procedure. Replace the built-in `unblock` registration in
   `src/coga/cli.py` and `src/coga/aliases.py` with a default rewrite to
   `launch bootstrap/unblock --`, using the existing script dispatch. Preserve
   the single-ticket, explicit answer, and interactive batch forms. Keep
   argument handling, selection, prompts, per-ticket failure reporting, and
   the operation that applies an answer together in the ticket. A local copy
   must expose the editable implementation. Require deterministic dispatch
   for this command. Verify the generic no-agent-fallback behavior before
   cutting over, including when a local definition is missing its script.
   Coordinate any missing generic dispatch support with the launch sibling.
2. Carry over the shared preparation used by `prepare_lifecycle_ticket()`
   and `reconcile_lifecycle_ticket()` in `src/coga/commands/common.py`, and
   use the same prepared ticket for the write and its publication. Keep
   `src/coga/commands/unblock.py`'s `_apply_unblock()` semantics. Its blocked
   path calls `src/coga/mark.py`'s `mark_active()` to preserve activation
   validation and workflow freezing. Its resolve-only paths call
   `src/coga/git.py`'s `write_ticket()` and `sync_task_state()` and keep
   status and step. Combine the two resolve-only paths into one write, one
   audit append, and one sync call, varying the status text and existing
   recurring-resume hint. Reuse preparation's existing Git fallback and
   review-conflict handling in both entry paths. Remove redundant local
   fallback handling only after confirming equivalent behavior for the
   call paths retained. The single and bulk procedures can call the same
   function inside the ticket. There is no need for a new recipe or kernel
   wrapper around it.
3. Keep `block`, `owner`, `mark` and `bump` direct. In
   `src/coga/commands/block.py`, `block()` prepares and appends the ask,
   passes the same ticket and preparation to `src/coga/mark.py`'s
   `mark_blocked()`, and then calls `emit_done_marker()` with the target
   slug. That path preserves recorded-assist or operator attribution and
   stops the matching session after saving. In `src/coga/commands/owner.py`,
   `owner()` keeps preparation, eligibility, prospective validation,
   local-byte comparison, write, audit and strict expected-control publication
   together under `git.state_lock()`. It rejects terminal and claimed
   tickets, its own supervised session, and an in-progress agent step.
   An in-progress owner gate requires `--assist-stopped`. Preserve the
   distinction between a definite failure (restore owned bytes and retract
   audit), uncertain publication (keep evidence), and Git soft-skip.
   This transaction justifies a co-versioned operation. A second command
   adapter would duplicate the argument boundary without giving the user an
   editable procedure of consequence.
4. Record the reviewed placement in
   `docs/contexts/coga-dev/microkernel/SKILL.md`. Update the packaged
   `coga/cli` and the owning user topics for changed dispatch or
   customization guidance. Keep the command contract beside the packaged
   implementation and update the required-resource inventory.

### Acceptance criteria

- [ ] From an installed checkout, `coga unblock --help`,
      `coga unblock <slug> --answer "…"`, interactive single-ticket use, and
      `coga unblock --all` work through the command ticket. A repo-local
      copy wins and a change to its prompt or selection is observable.
      Run the installed and local-override cases without a configured agent
      or checkout switch. Keep script framing off stdout. A missing script
      fails visibly before an agent can start.
- [ ] Resolve all open asks in one prepared write. Blocked becomes active
      under existing activation rules. An in-progress ticket or paused
      recurring period with open asks resolves in place. Preserve pause
      provenance, frozen step, user attribution, audit and notifications.
      Cover invalid statuses, missing asks, invalid activation, and legacy
      blocker text through the existing command and blocker tests.
- [ ] Neither single nor batch prompts hold the state lock. Before writing,
      reprepare and recheck after prompting. Batch selection still walks
      blocked tickets, supports blank skips, reports per-ticket failures and
      continues. An unreconcilable or changed ticket remains untouched and
      returns 75 without the generic sweep, including when another batch item
      succeeded. Cover ordinary Git fallback, merged review adoption, and
      the refusal path from a feature checkout.
- [ ] Exercise the real CLI under supervision. Resolving a current
      in-progress ticket lets its session continue. Direct `block` still
      stops only the matching session and preserves attribution. Retained
      `owner`, `mark`, and `bump` preserve their existing gate, conflict,
      publication, and completion behavior. Verify the owner operation's
      definite failure, uncertainty and soft-skip cases.
- [ ] Report before/after physical production lines (including comments and
      blanks) at named revisions. Include core, edge and executable ticket
      code for the changed path, including any touched dispatch code. Count
      relocation separately from removed duplication and list removed
      registrations or dependencies. Report tests, docs and package resource
      inventory separately. Run the full Linux suite per
      `coga-dev/testing`. Native Windows and macOS checks are deferred to
      release.

### Out of scope

Checkout and queue orchestration, new lifecycle states or flags, a generic
mutation language, and a new supervisor protocol belong outside this change.
Future movement of `block` requires a launch-owned completion seam with
tested identity, attribution and termination. Future movement of `owner`
requires preserving its supervised self-reassignment refusal across the
boundary. Keep those placement constraints in the microkernel topic.

## Context

- `src/coga/commands/common.py`'s `prepare_lifecycle_ticket()` adapts
  `reconcile_lifecycle_ticket()` for callers that exit on refusal.
  `_unblock_all()` in `src/coga/commands/unblock.py` uses
  `_apply_unblock()`, which can prepare afresh and raise a per-ticket
  error so the batch continues.
- `src/coga/commands/mark.py`'s `done()` and `canceled()` and
  `src/coga/commands/bump.py`'s `bump()` couple their guards and writes to
  the done marker. `src/coga/launch_script.py`'s `run_script_phase()`
  runs scripts with fresh task metadata and strips outer supervisor and
  expected-task/step authority. Ordinary bootstrap exit 75 reaches
  `src/coga/launch.py`'s `_LaunchInvocation` script handling, which
  withholds refresh and the sweep. Preserve this isolation.
- The packaged user topics `coga/lifecycle`, `coga/tickets`,
  `coga/state-publication`, and `coga/notifications/producers` own the
  operation contracts. The local microkernel topic owns placement.
- Baseline at `0eafc938304a1c3aef0e6e6173fa09b1922668c2` using `wc -l`
  on the named production modules. Under `src/coga/commands/`,
  `unblock.py` is 293 lines, `block.py` 106, `owner.py` 148,
  `common.py` 190, `mark.py` 329, and `bump.py` 523.
  Take the baseline for any additional touched production files at the same
  revision. The prior two-write blocker inventory predates prepared writes.

<!-- coga:blackboard -->

## Refresh handoff — 2026-11-12

The body now carries the current-main inventory and proposed boundary.
The parent refresh owns scope approval; this ticket's existing role,
status and workflow step are unchanged. No implementation was resumed.
The earlier design and review evidence remain below for deliberate reading.

## Design handoff — 2026-11-17

Checked the prepared-write paths and the parent scope acceptance against
current main. The proposed change moves the complete unblock procedure and
targets duplicated resolve-only effects. Block and owner stay direct for
distinct supervisor constraints. The launch sibling is the coordination
point for generic deterministic dispatch if the required fallback guard is
still missing at implementation.

## Open Questions

Should the owner approve moving both unblock forms behind the default alias
with launch framing on stderr, or limit the first migration to the
interactive batch if preserving the direct command experience is more
important? The proposed full move keeps one local implementation and avoids a
new public primitive or an operand-aware dispatch rule.

## Evaluator review

Reviewed 2026-11-17 at `0cc1ad583` from the position of an implementer who
did not write the design. Verdict: **not ready yet.** Two must-fix items need
a decision from the owner. Everything else checks out against the repo.

### Verified as stated

- At HEAD the baselines still match `0eafc938`: `unblock.py` 293, `block.py` 106,
  `owner.py` 148, `common.py` 190, `mark.py` 329, `bump.py` 523.
- `_apply_unblock` uses one prepared write. The blocked path goes through
  `mark_active`. The in-progress and paused-period paths share a single
  `write_ticket` call but keep separate `append_log`/`sync_task_state` branches,
  so step 2's dedup is real but small.
- `block()` calls `prepare_lifecycle_ticket`, then `mark_blocked`, then
  `emit_done_marker(session_id=ref.id_slug)`. `owner()` holds `git.state_lock`,
  refuses its own supervised session, a claim, and an in-progress gate without
  `--assist-stopped`, and covers the uncertain, retract, and restore branches.
  Step 3's claims are accurate.
- The bootstrap script path already does what the ticket needs here.
  `run_script_phase` inherits stdin, so interactive prompts work. Stateless
  runs write no log lines or failure notice. `Launch: task …` framing goes to
  stderr when an entry exists. Exit 75 sets `script_retained_state` and
  withholds the sweep (`launch.py` `_LaunchInvocation`). Bootstrap targets
  other than `bootstrap/orient` skip checkout normalization, and push preflight
  skips bootstrap. The alias shape copies `retire = "launch bootstrap/retire --"`.
- The ticket's Body regions are correct, and the workflow and attached
  contexts suit a kernel-boundary change. It is one coherent PR.

### Must resolve before implementation

1. **No mechanism exists to refuse a missing script, and no one owns building
   it.** AC1 requires "A missing script fails visibly before an agent can
   start." Under ordinary launch, `launch_script.run_script_phase` instead
   returns `ran=False` when `script_entry_point` is `None`, and launch hands
   off to an agent with the argv as a launch-arguments block. Only
   `--read-only` refuses. The launch sibling
   (`v1/microkernel/03-launch-decomposition`, at review, PR #1233)
   explicitly keeps "ordinary script-to-agent behavior … unchanged". It will
   not supply this guard, and `--read-only` is off-limits to a writer. So
   "Coordinate any missing generic dispatch support with the launch sibling"
   leaves the implementer to guess. The owner should choose one:
   (a) this PR adds a generic launch-side guard that refuses a missing script,
   such as a launch option the alias carries, with its contract in
   `coga/launch` and `coga/script-tickets` (a reviewed kernel surface);
   (b) drop the AC and accept the same fallback `retire` has today; or
   (c) open a separate launch ticket and make this one depend on it.
2. **"Carry over the shared preparation" can be read two ways.** It could mean
   *import* `reconcile_lifecycle_ticket` from core or *copy* its logic into
   `ticket.py`. Copying would duplicate review-conflict handling, which goes
   against the objectives. Importing means `ticket.py` imports from
   `coga.commands.common`, a CLI-head module. No bootstrap `ticket.py` does
   that today: retire, show, status, usage and recurring-list import only
   non-`commands` modules. Say which, and whether `reconcile_lifecycle_ticket`
   or `prepare_lifecycle_ticket` should first move to a non-CLI module. After
   the move it still has at least two consumers: bump, mark, block and owner.

### Should address (recommended)

3. **List what changes when unblock runs through launch instead of as a
   built-in.** None of these are stated:
   - after the script, `refresh_after_script` → `return_checkout` →
     `git.refresh` runs, because a bootstrap boundary is unarmed. A blocked-resume
     agent runs `coga unblock` mid-session (`launch.py` blocked-resume prompt
     text) and would now refresh the checkout under the live session. That
     is probably harmless on a feature branch and a fast-forward on control,
     but AC4 should name it as expected.
   - `coga unblock --help` now needs a configured workspace, as the retire
     ticket.md already documents for `retire --help`.
   - a repo `[aliases] unblock` entry stops colliding with a built-in.
     `BUILTIN_COMMANDS` changes, and `tests/test_aliases.py` checks it against
     Typer's registry.
4. **Name a test strategy.** About 30 `tests/test_commands.py` cases call the
   Typer `app` through `CliRunner` with `["unblock", …]` and `input=`. Once
   unblock leaves `_LAZY_COMMANDS`, those calls stop resolving: alias
   expansion happens in `cli.main`, and `CliRunner` input does not reach a
   subprocess's stdin. AC2's "through the existing command and blocker
   tests" therefore needs a translation. The `tests/test_retire.py` precedent
   loads the packaged script by path with `importlib` for behavior tests and
   runs `_run_coga` as a real subprocess for dispatch, stdout and stdin.
5. **Evidence for step 2's fallback caution.** The `except git.GitError`
   fallback in `_apply_unblock` is not fully redundant. In
   `reconcile_lifecycle_ticket`, the `except git.GitError` handler does not
   catch errors raised inside its own `except git.TicketConflictError` handler
   (`review_conflict.escalate`, the merged-review `git.prepare_ticket`). Today
   those errors reach `_apply_unblock`'s local fallback. Removing it changes
   what the batch does on those errors, so either keep it or decide the change
   deliberately.
6. **The microkernel topic needs an explicit line edit.** The "kernel tier and
   its edges" paragraph lists "the `block`/`unblock` state transitions" as
   kernel. Step 4 should say that paragraph changes, beyond adding a placement
   row.

### Owner question already open

The blackboard's Open Question asks whether to move both forms or only
`--all`. That is the owner's call. Item 1 bears on it: the full move puts
the more common single-ticket path, including the agent's mid-session call,
behind whatever missing-script behavior is chosen.

## Superseded designs

### 2026-11-12 — Design before the current-main refresh

Superseded by: the refreshed Description and Context above, proposed for owner review.
Reason: source, distribution and caller boundaries changed; the owner clarified
the objectives in `coga-dev/microkernel/objectives`. Historical commands,
paths, approvals and test receipts below are evidence, not current instructions.

#### Description

Settle the placement of the lifecycle heads that sit in the kernel by
registration rather than by the launch-closure test: `coga block` /
`coga unblock`, and the `coga owner` head (a `mark`-shaped locked write of
`owner:`).

`block`/`unblock` stay in the kernel: the owner-confirmed v1 kernel line in
`coga-dev/current-direction` (2026-10-16) includes them. This ticket writes their
co-versioning proof; it does not move them unless the owning context is
deliberately revised first. Only `owner` is open: assess and ratify the
co-versioning argument already recorded in `coga-dev/microkernel`, or reject
it with reasons and move the head to the edge without changing semantics.

`coga mark` and `coga bump` are **out of scope**: `coga-dev/microkernel`
keeps them in the kernel because launch calls them mid-flight, and the owner
confirmed that boundary for v1 on 2026-10-16.

##### Acceptance criteria

- [ ] Apply the group's [reduction objective](README.md#reduction-objective):
      identify redundant wrappers or duplicated state-write scaffolding in
      the three owned heads, reuse existing shared primitives where justified,
      and report the resulting code and dependency reduction separately from
      placement changes. Preserve the lifecycle invariants below and the
      confirmed kernel home of `block`/`unblock`.

- [ ] The design names, for `block`, `unblock` and `owner`, the internal
      state-write primitive each head calls, and separates the primitive from
      the user-facing head.
- [ ] `block` and `unblock` end with a written co-versioning proof (the
      package-private invariant or atomic transaction an edge implementation
      could not preserve) recorded in `coga-dev/microkernel`.
- [ ] `owner` ends either with its existing argument reviewed and ratified as
      such a proof, or moved to the edge with unchanged behavior.
- [ ] Lifecycle invariants are preserved: status transitions, blocker asks
      and their resolution, existing per-path `COGA_EXPECTED_TASK` /
      `COGA_EXPECTED_STEP` guards, session termination under a supervisor,
      owner-gate and launch-claim refusals, logging, git sync and notifications.
      Preserve concurrent edits and the distinct definite-failure rollback,
      uncertain-publication and soft-skip outcomes; do not assume every head
      implements the same transaction or guard coverage.
- [ ] The `owner` row leaves the "Open command placements" table in
      the local-only `coga-dev/microkernel` topic; the kernel bullet there
      states the reason `block`/`unblock` stay;
      `coga/lifecycle`, `coga/tickets` ("Owner and relationships") and the `coga/cli` index
      match.
- [ ] Tests cover the changed surface; the full suite and
      `coga validate --json` pass.

#### Context

Group: read `coga/tasks/v1/microkernel/README.md`, "Reduction objective".
Report production-code counts at named before/after revisions across core,
edge and ticket/skill scripts in scope; state the counting method, separate
tests, documentation and packaged copies, and distinguish relocation from
deletion or deduplication. There is no line-count quota. A size-neutral change
must identify its boundary gain and name a follow-up for deferred reduction.
The group's historical archive-audit instruction does not authorize archive
access or add an archive deliverable to this ticket.

##### Current source and remaining review (2026-10-28)

- `src/coga/commands/block.py`, `block`, combines
  `blackboard.append_blocker` with `mark.mark_blocked` and the task-scoped
  supervisor completion marker. Its blocker append is locked separately
  from the subsequent status transition.
- `src/coga/commands/unblock.py`, `_apply_unblock`, resolves asks under
  `git.state_lock`, then uses `mark.mark_active` for a blocked ticket or
  resolve-only audit/sync paths for `in_progress` and paused recurring tasks.
- `src/coga/commands/owner.py`, `owner`, holds `git.state_lock` across read,
  prospective validation, exact local-byte comparison, write, audit and
  `git.sync_task_state(strict=True, expect=...)`. It preserves concurrent
  edits, rolls back only its own bytes and audit on definite failure, retains
  uncertain publication for reconciliation, and exits 75 on those failures
  to suppress the sweep. Documented Git soft-skips keep the local result.
  `tests/test_owner.py` exercises these distinctions. The existing argument
  under microkernel's open-placement table is evidence to review, not a
  ratified classification; the `owner` row remains open.
- These heads are not interchangeable wrappers. Inventory their real
  primitives and guard coverage before selecting reductions. In particular,
  `commands.bump._assert_supervised_step_is_current` belongs to the
  out-of-scope `bump` head, not automatically to every lifecycle command.

##### Launch dependency

The group originally ordered `v1/microkernel/03-launch-decomposition` first. At
this premise check that ticket is paused at its owner `review-design` gate,
but its inventory is stale: `commands.launch.launch` already delegates to
`coga.launch`, and `src/coga/launch_script.py` has no `advance_step` or
`mark_done` calls. Work from current source rather than the sibling's old
description of script completion or lifecycle migration.

Design may proceed now. Before the owner approves implementation, identify
any concrete launch-service prerequisite and either verify that it has landed
or record it on the sibling and defer the dependent implementation. If none
is needed, record why the existing boundary suffices. This ticket does not
add launch hooks or take over the executor. The sibling's older proposal to
move `mark`/`bump` does not override their confirmed kernel placement.

Out of scope: `mark`, `bump`, `create`, `skill *`, launch execution and script
completion semantics. This ticket originated under
`v2/cleanup-core-commands/` and returned to v1 scope on 2026-10-16.

##### Required reads and owning topics

The following topics are cited rather than attached; read the named sections.
Editing targets must be opened from disk. Update any changed contract and its
packaged twin in the same PR; `coga-dev/` topics remain local-only.

- `coga-dev/microkernel`, `docs/contexts/coga-dev/microkernel/SKILL.md`:
  "The microkernel rule", "Open command placements", "Migrating a built-in
  to the edge", and "The kernel tier and its edges". A command needs a
  package-private invariant or transaction that stable CLI/filesystem access
  cannot preserve; registration or merely calling shared Python is not proof.
  Write the placement decisions here and remove the resolved `owner` row.
- `coga/lifecycle`, `docs/contexts/coga/lifecycle/SKILL.md`: "Status: whether
  work happens" and "Blocking and resume". Blocking retains the step;
  unblocking activates a blocked task but only resolves asks on an
  `in_progress` task or a paused recurring period. Preserve interactive
  blocked-resume behavior and supervised termination.
- `coga/tickets`, `docs/contexts/coga/tickets/SKILL.md`: "Owner and
  relationships". Reassignment preserves status, step and body, refuses
  terminal records, own supervised sessions and outstanding launch claims,
  and requires a stopped assist for an in-progress owner gate; an agent step
  must first stop and pause. This is the owner contract, not the nonexistent
  `coga/tickets/ownership` ref.
- `coga/cli`, `docs/contexts/coga/cli/SKILL.md`: "Tickets and state" and
  "Aliases and recipes". Keep the index aligned with the reviewed command
  spelling and contract owner; it does not substitute for those contracts.
- `coga-dev/current-direction`,
  `docs/contexts/coga-dev/current-direction/SKILL.md`: "In force", the
  2026-10-16 microkernel decision. V1 keeps `mark`/`bump` and
  `block`/`unblock` in core; only `owner` placement is open here.
- `coga-dev/codebase`, `docs/contexts/coga-dev/codebase/SKILL.md`: "Source
  map". CLI heads live in `commands/`; shared lifecycle, blackboard and Git
  behavior lives in `mark.py`, `blackboard.py` and `git.py`. The symbols above
  are the starting inventory, not a mandate to add another wrapper.
- `coga/workflows`, `docs/contexts/coga/workflows/SKILL.md`: "Frozen snapshot,
  live content" and "Roles are the routing". Preserve frozen step metadata
  and derived owner/agent routing, including inherited roles; reassignment
  does not rewrite the workflow or main agent.
- `coga/notifications/producers`,
  `docs/contexts/coga/notifications/producers/SKILL.md`: "Live surface" and
  "Silent"; and `coga/notifications`,
  `docs/contexts/coga/notifications/SKILL.md`: "When a post fails".
  Block posts to flow with the owner identified; ordinary activation and
  owner reassignment remain silent. A failed block announcement is reported
  without undoing the written transition or preventing session completion.

The attached publication topic supplies the strict/best-effort, expectation,
lock-scope and failure contracts required to assess the proof. The attached
extension and script-ticket topics govern the possible edge alternative:
preserve deterministic behavior and create no per-invocation task. If design
selects wheel-owned edge code, first read
`docs/contexts/coga/edge-code/SKILL.md` in full and attach `coga/edge-code`
for implementation; core must never import the edge implementation.

Previous ref: `microkernel/lifecycle-verbs-to-ticket-operations` (renamed 2026-10-27); earlier audit lines retain that ref. Parked by the owner for v2; this work does not gate v1.

## Superseded in part by plain-Git (2026-11-19)

Owner re-evaluation against `v1/03-use-git-like-everyone-remove-coga-s-publication-ab`.
Still valid: an editable unblock procedure. Superseded: reliance on fresh-control reconciliation, git.state_lock, expected-control publication and retraction (decisions 1, 3, 4). Decision 6 also changes unblock: launch never touches blocked; unblock --answer moves a ticket with a running session to in_progress.
Do not implement the superseded part; re-scope after that design lands.
