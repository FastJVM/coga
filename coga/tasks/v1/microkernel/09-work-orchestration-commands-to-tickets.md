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
step: 1 (design)
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

## Context

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
