# Microkernel

Group directory for the v1 microkernel cleanup: settling the permanent home
of every in-package command head that has no ratified kernel justification.
Launch one of the child tickets below, not this file.

## Status

Pulled forward from the parked `_v2/` wish list into v1 scope by owner
decision on 2026-10-16 (recorded in `coga/current-direction`). Each draft was
premise-checked against `main` @ `5d72ffe6e` with the `_v2/README.md`
procedure, reusing Dream 2026-W39 findings F46-F49 and F53 and the W40
correction to F49; each ticket's blackboard records its own outcome.

## The boundary

The target is the **current** rule in `coga/extension-model`, not the July
2026 direction that only `create` is irreducibly core. The owner confirmed on
2026-10-16 that the kernel stays: launch/compose and what launch calls
mid-flight (`mark`, `bump`, secret injection, notify dispatch), what must
exist before any launch (`create`, fresh `init`), the `block`/`unblock`
transitions, the fixed `runner.RECIPES`, and proven co-versioned commands.

v1 is done here when the "Open command placements" table in
`coga/extension-model` is empty: every listed head is either moved to the edge
(command ticket, `ticket.py`, `src/coga_edge/`, alias) or carries a written
co-versioning proof.

## Ground rules

- Commands operate on durable tickets, not untracked side effects. Keep CLI
  entrypoints thin; move single-consumer substance to the edge.
- Moving logic out of the kernel moves it unchanged (extension-model
  "No inversion"): deterministic Python stays Python.
- When a placement changes, update in the same PR `coga/extension-model`
  (and its packaged twin), `docs/archive/cli-extension-audit.md`, the
  `coga/cli` index, and the topic that owns the moved command.
- Split implementation by command shape after design review; one PR per
  move.

## Child tickets and order

1. `microkernel/launch-decomposition` — split
   `src/coga/commands/launch.py` into executor substrate plus caller policy.
   Goes first: the others need a stable executor API. Paused at the owner's
   `review-design` gate with a stale inventory; see its blackboard.
2. `microkernel/lifecycle-verbs-to-ticket-operations` — narrowed
   to `block`/`unblock` (kernel by registration, not by the launch-closure
   test) and the `owner` head. `mark` and `bump` stay kernel.
3. `microkernel/work-orchestration-commands-to-tickets` —
   `retire`, `megalaunch`, `slack`.
4. `microkernel/read-report-commands-as-ticket-workflows` —
   `show`, `status`, `validate`, `usage`, `recurring list`.
5. `microkernel/support-commands-boundary` — `secret get`,
   `uninstall`.
6. `microkernel/residual-command-surfaces` — narrowed to `ticket`
   and the `skill *` classification.

Tickets 3-6 can run in parallel once 1 lands.

## Related work

- `gigantic-refactor-move-recurring-recipes-out-of-co` (in progress) moves
  single-ticket recurring jobs out of `runner.RECIPES`. It owns the recipe
  registry; these tickets own command heads. Neither edits the other's
  surface.
- `marketing/demo-hackability-ask-claude-to-add-a-command-live` depends on
  this set: the demo shows a new command landing entirely at the edge.

## History

- 2026-07: created as the core-command breakdown; parked to `_v2/` on
  2026-07-27 as off the execution path.
- 2026-09-10: `coga digest` removed outright (`remov-digest-in-recurring`).
- `coga project` and `coga build`'s command were removed
  (`remove-coga-build-and-project`); `build` is now an alias.
- 2026-10-16: pulled forward into v1 and renamed from `cleanup-core-commands/`
  to `microkernel/`; older log lines and tickets use the old slugs.
