# Microkernel

V1 group for a ticket-centred microkernel: a small executor runs tickets,
which carry scripts or agent prompts and the workflows and skills they use.
Most user-facing commands become aliases to those tickets. Settling command
placement serves that architecture and a program more people can read.

## Status

Pulled back into v1 by the owner on 2026-11-12: hackability is a base promise
of the open-source 1.0, and a contributor got lost customizing the peer-review
step (the bundled workflow lived only in the package, and the hidden
`checkout_policy.py` table silently dropped a customized step to manual
checkout). The whole group gates `v1/14`: the "Open command placements" table
in `coga-dev/microkernel` must be empty before publication. This supersedes the
2026-10-27 deferral; the decision is recorded in `coga-dev/current-direction`.

The 2026-11-12 refresh proposed revised child scopes, and the owner accepted
them. By 2026-11-19 the refresh and ten children were done, retro'd and deleted;
[Done](#done) links their merged outcomes by commit permalink. Six children
remain under [Remaining](#remaining). Read the current open placements in
`coga-dev/microkernel` rather than inferring them from this index.

The [prompt assembly group](03-prompt-assembly/README.md) is also finished:
the current assembly was kept. Its index links the owners of that ruling.

## Objectives (owner, clarified 2026-11-12)

The [microkernel objectives](../../../../docs/contexts/coga-dev/microkernel/objectives/SKILL.md)
own this group's direction: hackable and accessible behavior, as much behavior
as possible in tickets, and a simpler program people can read. That context
also owns the fresh-repo peer-review acceptance case and the design criteria.

## The boundary

The implemented boundary is owned by `coga-dev/microkernel`. It is the
starting inventory, not a promise that every existing command, recipe, or
caller-specific policy must remain in core. The linked objectives
ask the refresh to propose the smallest useful executor and shared primitives,
with behavior carried by tickets wherever possible. Preserve completion and
failure visibility, but not the current transaction, claim and publication
guarantees: the plain-Git direction (owner, 2026-11-19,
`v1/03-use-git-like-everyone-remove-coga-s-publication-ab`) removes them. Apply
this when proposing smaller heads
or moving policy. The owner reviews the concrete retained set before any
child implementation resumes.

The "Open command placements" table in `coga-dev/microkernel` must be empty:
every listed head is moved to a ticket/alias or has a concrete reason to remain
a generic kernel primitive. Closing the table alone is insufficient: the
customization path and whole-program simplification must also meet the
objectives above. Wheel distribution by itself does not make behavior editable.

It is a v1 release prerequisite (owner decision 2026-11-12).

## Reduction objective

The 2026-10-22 reduction objective is retained in the standing context's
[simplification goal](../../../../docs/contexts/coga-dev/microkernel/objectives/SKILL.md#a-simpler-program-people-can-read)
and [evaluation criteria](../../../../docs/contexts/coga-dev/microkernel/objectives/SKILL.md#evaluating-a-proposed-change).
Use those criteria for each child's design and implementation evidence.

## Ground rules

- Commands operate on durable tickets, not untracked side effects. Keep CLI
  entrypoints thin; move single-consumer substance to the edge.
- Moving logic out of the kernel moves it unchanged (extension-model
  "No inversion"): deterministic Python stays Python.
- When a placement changes, update the local-only `coga-dev/microkernel`,
  the package-owned `coga/cli` index and the owning user contract. Shipped
  definitions have one package owner; local copies are deliberate overrides.
  Archive auditing is not part of this group and requires an explicit request.
- Split implementation by command shape after design review; one PR per
  move.

## Done

Each ticket link is a permalink to its last revision before deletion
(optional provenance). The merge commit is the durable outcome; current
contracts live in the topics that PR updated, chiefly `coga-dev/microkernel`.

| Ticket (historical) | Outcome |
| --- | --- |
| [01 Refresh](https://github.com/FastJVM/coga/blob/ad0776ce0f5cc0fe31a840a1a80a32d23d07d0d3/coga/tasks/v1/microkernel/01-refresh-the-microkernel-designs-against-current-ma.md) | Design only, no PR. Revised child scopes against `main` at `49b34b229`; the owner accepted them, and the rows below are its result |
| [02 Checkout declaration](https://github.com/FastJVM/coga/blob/73fad50db5b30caf134592f62f11045cae94b00a/coga/tasks/v1/microkernel/02-declare-each-workflow-step-s-checkout-policy-in-th.md) | [#1226](https://github.com/FastJVM/coga/commit/45347957b2c52a0c376a5f3c6ed14133d838db06): workflow steps declare their own checkout policy |
| [03 Launch decomposition](https://github.com/FastJVM/coga/blob/2535c5414dc315a0f1950580ad0325635f93dc23/coga/tasks/v1/microkernel/03-launch-decomposition.md) | [#1233](https://github.com/FastJVM/coga/commit/93c95405ea22ccbe82e0a7979e023f07ee7b9cab): read-only ticket dispatch and shared agent readiness |
| [04 Recipe migration, part 1](https://github.com/FastJVM/coga/blob/11ad4e95a4f1ba6f21f835a2f5810368c5508e48/coga/tasks/v1/microkernel/04-gigantic-refactor-move-recurring-recipes-out-of-co.md) | [#1245](https://github.com/FastJVM/coga/commit/133bb5feed7463ad7a9da9ac9d9acd05721b16fb): shared failure-root resolution and exit publication for edge entrypoints |
| [04b Recipe migration, part 2](https://github.com/FastJVM/coga/blob/32111514b9c25615a6b7f8ce6f86aa61b33d0bcd/coga/tasks/v1/microkernel/04b-move-blocker-reminders-and-skill-update-to-the.md) | [#1272](https://github.com/FastJVM/coga/commit/dcba1b1dcd4ffab1cb6573575b0b2660c2c8e384): blocker-reminders and skill-update jobs moved to the edge |
| [04d Recipe migration, part 4](https://github.com/FastJVM/coga/blob/ed0f2fd89c748e9182dc438c88839365e5f35007/coga/tasks/v1/microkernel/04d-move-dream-s-validate-drift-and-orphan-marker.md) | [#1265](https://github.com/FastJVM/coga/commit/3628703f7d2784d78f28d9d209705f3320b21e3c): Dream's validation and orphan-scan workers moved to the edge |
| [06 Read/report commands](https://github.com/FastJVM/coga/blob/4d93450c1d233c3f2155ee78dcd1e10b75b663ed/coga/tasks/v1/microkernel/06-read-report-commands-as-ticket-workflows.md) | [#1240](https://github.com/FastJVM/coga/commit/e7963f555d08d10af23795fb8774135588d23fba): read reports moved into editable command tickets |
| [07 Support commands](https://github.com/FastJVM/coga/blob/6d26a46ccb7085adc0f548755bc1482e6f42b1d4/coga/tasks/v1/microkernel/07-support-commands-boundary.md) | [#1246](https://github.com/FastJVM/coga/commit/f5cf6eb2099b911315e62ec274eaa221127795cd): secret authentication and uninstall recovery boundaries retained |
| [08 Residual commands](https://github.com/FastJVM/coga/blob/e88b1f3216c4af3fff531349a121456b39222958/coga/tasks/v1/microkernel/08-residual-command-surfaces.md) | [#1248](https://github.com/FastJVM/coga/commit/5bc202b4111548e8e626271e010ddc153e3b5f19): recurring promotion moved to a command ticket; authoring and skill tooling split into 13 and 14 |
| [09 Work orchestration](https://github.com/FastJVM/coga/blob/5feb101976e5d914378fee822ba29abd38acf2b9/coga/tasks/v1/microkernel/09-work-orchestration-commands-to-tickets.md) | [#1244](https://github.com/FastJVM/coga/commit/d5cd14a39cadc2dd61345da67295bfc9a6c536b0): megalaunch queue policy moved to an editable command ticket |
| [Slack FYIs](https://github.com/FastJVM/coga/blob/8ac1f9152a92758ac0bd93e40811b361d07b10e4/coga/tasks/v1/microkernel/move-slack-fyis-to-a-command-ticket.md) | [#1247](https://github.com/FastJVM/coga/commit/ac3f5a538761dd21e122afc88e369050017d8030): Slack FYIs moved to an editable command ticket; stateless commands end with `mark done` |

## Remaining

| Ticket | State (2026-11-20) | Objectives advanced |
| --- | --- | --- |
| [Editable packaged behavior](12-make-packaged-behavior-discoverable-and-editable.md) | At owner review; its PR #1239 was closed without merging | All three |
| [Ticket authoring](13-move-ticket-authoring-to-a-command-ticket.md) | Design awaiting owner review. Split from 08; moves `coga ticket` into `bootstrap/ticket` | All three |
| [Skill management](14-move-skill-management-to-command-tickets.md) | Design awaiting owner review. Split from 08; moves the `coga skill` family into one command ticket | All three |
| [Lifecycle operations](15-lifecycle-verbs-to-ticket-operations.md) | Design awaiting owner review. Retain proven transition/completion operations; separate bulk/procedure policy where useful | Smaller kernel responsibility, editable procedure, less duplicate state handling |
| [Recipe migration, part 5 (parked)](16-second-pass-move-branch-sweep-and-autofix-repl.md) | Design awaiting owner review. Branch-sweep and autofix replay adapters wait for a stateless publication contract | Ticket ownership, hackability, simpler registry/reporting |
| [Recipe migration, part 3](17-move-autoclose-to-the-edge.md) | At owner review; its PR #1273 was closed without merging | Ticket ownership, hackability, simpler registry/reporting |

Each child owns its detailed dependency and acceptance contract. There is no
blanket ordering among them beyond what those tickets state.

## Related work

- `_v2/marketing/demo-hackability-ask-claude-to-add-a-command-live` (still parked) depends on
  this set: the demo shows a new command landing entirely at the edge.
- `coga/edge-code` owns the already-shipped delivery/fork contract. Its retired
  implementation ticket is no longer a blocking design prerequisite.

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
- 2026-11-12: objectives moved to their standing Coga-dev owner; refreshed
  child scopes and the accessibility gap are proposed for owner review.
- 2026-11-18/19: the refresh and ten children finished and were retro'd and
  deleted; their rows moved to [Done](#done) with commit permalinks.
