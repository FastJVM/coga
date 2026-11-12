# Microkernel

V1 group for the microkernel cleanup: settling the permanent home
of every in-package command head that has no ratified kernel justification,
so that Coga is hackable and extensible at the edge.

## Status

Pulled back into v1 by the owner on 2026-11-12: hackability is a base promise
of the open-source 1.0, and a contributor got lost customizing the peer-review
step (the bundled workflow lived only in the package, and the hidden
`checkout_policy.py` table silently dropped a customized step to manual
checkout). The whole group gates `v1/43`: the "Open command placements" table
in `coga-dev/microkernel` must be empty before publication. This supersedes the
2026-10-27 deferral; the decision is recorded in `coga-dev/current-direction`.

The designs below are stale. `refresh-the-microkernel-designs-against-current-ma`
runs the premise check and refreshes every design first; no child
implementation resumes before the owner accepts that refresh.

At the October 16 pull-forward, each draft was
premise-checked against `main` @ `5d72ffe6e` with the `_v2/README.md`
procedure, reusing Dream 2026-W39 findings F46-F49 and F53 and the W40
correction to F49; each ticket's blackboard records its own outcome.

## Objectives (owner, 2026-11-12)

1. **Hackable.** A user can change any shipped behavior without touching the
   package: copy the owning file into their repo, edit it, and everything else
   keeps working. One command tells them where that file lives. First
   acceptance test: starting from a fresh repo, make the peer-review step work
   with a single agent without help (the case a contributor got stuck on).
2. **As much as possible in the ticket.** Behavior lives with the ticket that
   uses it (its body, workflow, skills, and `ticket.py`) rather than in core,
   so extending Coga means editing a ticket and the kernel surface needed to
   run it shrinks.
3. **Simplify on the way.** Each move deletes duplicated mechanics, redundant
   wrappers, and obsolete paths (see "Reduction objective"); relocation alone
   is not the goal.

These objectives decide scope: work that advances none of them waits.

## The boundary

The target is the **current** rule in `coga-dev/microkernel`, not the July
2026 direction that only `create` is irreducibly core. The owner confirmed on
2026-10-16 that the kernel stays: launch/compose and what launch calls
mid-flight (`mark`, `bump`, secret injection, notify dispatch), what must
exist before any launch (`create`, fresh `init`), the `block`/`unblock`
transitions, the fixed `runner.RECIPES`, and proven co-versioned commands.

This parked group's completion criterion is an empty "Open command placements" table in
`coga-dev/microkernel` is empty: every listed head is either moved to the edge
(command ticket, `ticket.py`, `src/coga_edge/`, alias) or carries a written
co-versioning proof.

It is a v1 release prerequisite (owner decision 2026-11-12).

## Reduction objective

Owner clarification (2026-10-22): alongside settling command placement,
reduce the kernel's surface and the total code and complexity we maintain.
Look for duplicated mechanics, redundant wrappers, and obsolete paths that
can be removed within each ticket's reviewed scope. Reuse existing shared
primitives; a new abstraction must replace real callers, not add another
layer around them.

Each design identifies concrete simplifications. Each implementation reports
before/after evidence at named revisions: production-code size across core,
edge, and ticket/skill scripts in its scope, plus the entrypoints, dependency
paths, or duplicate implementations removed. State the counting method and
report tests, documentation, and packaged copies separately. Distinguish code
relocated from code deleted or deduplicated: moving it to the edge does not
reduce the total maintenance burden by itself.

There is no arbitrary line-count quota. Preserve behavior, deterministic
execution, failure visibility, and meaningful test coverage. A justified
behavior-preserving extraction may be size-neutral; record its boundary gain
and hand any deferred simplification to a named sibling or follow-up instead
of claiming a code reduction. Classification-only work supplies that evidence
for the proposed change and leaves implementation to its reviewed follow-up.

## Ground rules

- Commands operate on durable tickets, not untracked side effects. Keep CLI
  entrypoints thin; move single-consumer substance to the edge.
- Moving logic out of the kernel moves it unchanged (extension-model
  "No inversion"): deterministic Python stays Python.
- When a placement changes, update in the same PR the local-only
  `coga-dev/microkernel`, `docs/archive/cli-extension-audit.md`, the
  `coga/cli` index, and the topic that owns the moved command. Update
  packaged twins only for user topics.
- Split implementation by command shape after design review; one PR per
  move.

## Child tickets and order

0. `v1/microkernel/refresh-the-microkernel-designs-against-current-ma` —
   premise-check and refresh every design below; goes first.
0. `v1/microkernel/declare-each-workflow-step-s-checkout-policy-in-th` —
   move step checkout policy from `checkout_policy.py` into workflow files.
   Independent of the command heads; may run in parallel with the refresh.
1. `v1/microkernel/launch-decomposition` — split
   `src/coga/commands/launch.py` into executor substrate plus caller policy.
   Goes first: the others need a stable executor API. Paused at the owner's
   `review-design` gate with a stale inventory; see its blackboard.
2. `v1/microkernel/lifecycle-verbs-to-ticket-operations` — narrowed
   to `block`/`unblock` (kernel by registration, not by the launch-closure
   test) and the `owner` head. `mark` and `bump` stay kernel.
3. `v1/microkernel/work-orchestration-commands-to-tickets` —
   `megalaunch`, `slack`; `retire` is split out to
   `microkernel/move-retire-to-a-command-ticket`.
4. `v1/microkernel/read-report-commands-as-ticket-workflows` —
   `show`, `status`, `validate`, `usage`, `recurring list`.
5. `v1/microkernel/support-commands-boundary` — `secret get`,
   `uninstall`.
6. `v1/microkernel/residual-command-surfaces` — narrowed to `ticket`
   and the `skill *` classification.

Tickets 3-6 can run in parallel once 1 lands.

## Related work

- `v1/microkernel/gigantic-refactor-move-recurring-recipes-out-of-co` (in progress) moves
  single-ticket recurring jobs out of `runner.RECIPES`; part of this group since
  2026-11-12. It owns the recipe registry; the tickets above own command heads. Neither edits the other's
  surface.
- `_v2/marketing/demo-hackability-ask-claude-to-add-a-command-live` (still parked) depends on
  this set: the demo shows a new command landing entirely at the edge.

## History

- 2026-07: created as the core-command breakdown; parked to `_v2/` on
  2026-07-27 as off the execution path.
- 2026-09-10: `coga digest` removed outright (`remov-digest-in-recurring`).
- `coga project` and `coga build`'s command were removed
  (`remove-coga-build-and-project`); `build` is now an alias.
- 2026-10-16: pulled forward into v1 and renamed from `cleanup-core-commands/`
  to `microkernel/`; older log lines and tickets use the old slugs.
- 2026-10-27: parked under `v1/microkernel/` to focus v1 on first users.
- 2026-11-12: pulled back into v1 as `v1/microkernel/` with the recurring-recipes
  refactor; the whole group gates the 1.0.
