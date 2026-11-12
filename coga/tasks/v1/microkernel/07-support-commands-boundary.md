---
title: Classify support commands under the small-core rule
status: draft
owner: nicktoper
agent: codex
contexts:
  - coga-dev/microkernel/objectives
  - coga-dev/principles
  - coga/secrets
  - coga/uninstall
  - coga/init
  - coga-dev/codebase
  - coga-dev/testing
  - coga-dev/current-direction
  - coga-dev/microkernel
  - coga-dev/project-stage
  - coga/cli
  - coga/checkouts
workflow: code/design-then-implement
---

## Description

Settle `secret get` and `uninstall` by separating their user procedure from
shared secret and bootstrap/recovery machinery. Propose moves only when they
preserve the existing operational boundary and reduce the maintained surface.
This refreshed design awaits owner scope review.

### Objectives advanced

Ticket ownership and hackability: secret inspection and removal procedure
can be exposed as editable script behavior where the environment permits it.
Simplification: reuse actual shared resolver/install primitives and remove
redundant wrappers. Merely calling either head "bootstrap" is not a proof.

### Premise check against main

Snapshot: `49b34b229` (2026-11-12), physical lines including blanks/comments.

1. Both heads exist: `commands/secret.py` (75) and `commands/uninstall.py`
   (413). `commands/update.py` (408) remains init support, not `coga update`.
2. Secret resolution is `config.select_launch_secrets`; uninstall reads the
   footprint and imports helpers from init/update. The install guide is the
   project README's Get started section; the old `coga/install` pointer is stale.
3. This body carries the requirements; the owning user topics supply the
   contract. No archived audit or retired prerequisite is required.
4. Acquisition/injection separation and the broken-alias recovery path are
   already implemented. Classification/migration of these two heads is still open.

### Proposed boundary

`secret get` is a candidate script command ticket using the existing resolver.
Keep launch-time secret injection, environment scoping, redaction and errors
in shared core. Preserve the direct human request's stdout-only result; never
put values into agent prompts, task arguments stored as state, reports, logs
or notification messages. A failed lookup reports the reference, not the value.
The generic stateless runner must not compose an agent prompt or record the
returned bytes, and must retain no-user-config inspection behavior.

Recommend retaining a minimal `uninstall` recovery entry for now. It is
dispatched before ordinary alias validation, works with damaged Coga config,
and may remove the very tree a ticket would be loaded from. An ordinary
`launch bootstrap/uninstall` alias does not preserve those properties.
Its plan construction/removal procedure can move to packaged edge code only
if the entry still reads the selected implementation without trusting broken
config and performs no teardown publication after deletion. The design must
show a net simplification; otherwise retain the bounded recovery command with
a written proof rather than add a second recovery launcher.

Preserve the removal preview and confirmation/`--yes`, backups of edited guide
files, configured contexts handling and opt-in global `--purge`. Never run
uninstall or real secret acquisition against the live repository for validation.

### Launch-adjacent support

Classify push-auth readiness, installed/source diagnostics and agent-skill-view
refresh handed off by launch. Shared checks enforced at their point of use
remain shared infrastructure. This ticket may remove a redundant preflight
only with evidence that every affected execution path still fails visibly at
the right boundary; moving all checks into an agent prompt is not equivalent.

### Acceptance and reduction evidence

- [ ] Give each head a concrete retained/moved decision in the local
      microkernel topic and remove its open row only after review.
- [ ] Exercise `secret get` streams/errors with fake resolvers, empty operator
      config and no agent/TTY; prove no value enters audit or captured reports.
- [ ] Exercise uninstall with broken aliases/config, missing local definitions,
      edited guides, relocated contexts, confirmation refusal and purge plans
      in disposable fixtures; preserve recovery before normal dispatch.
- [ ] Identify actual shared init/uninstall helpers before extracting them;
      report whole-system wrapper/dependency reductions, not just moved lines.
- [ ] Update package-owned `coga/secrets`, `coga/uninstall`, `coga/init` and
      CLI guidance if changed. Run secret/uninstall/init/CLI/launch tests and
      the full Linux/native Windows receipts required for implementation.

## Context

Read `coga-dev/microkernel/objectives`, `coga-dev/testing` and
`coga-dev/packaging`. User owners resolve below
`src/coga/resources/templates/coga/bootstrap/contexts/coga/`.

The generic stateless seam is owned by launch-decomposition. Editable resource
discovery/forking is owned by the dedicated customization ticket; do not build
a second updater here. Drop stale twin and `coga/install` instructions. Defer
new upgrade commands and moving uninstall solely to improve a head count.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Superseded designs

### 2026-11-12 — Design before the current-main refresh

Superseded by: the refreshed Description and Context above, proposed for owner review.
Reason: source, distribution and caller boundaries changed; the owner clarified
the objectives in `coga-dev/microkernel/objectives`. Historical commands,
paths, approvals and test receipts below are evidence, not current instructions.

#### Description

Settle the placement of the support heads `coga secret get` and
`coga uninstall`. For each, record whether it is bootstrap substrate (must
work without an existing ticket or a working `coga/`), an edge command, or
external tooling, and move it if the answer is the edge.

Secret values never enter tickets, prompts, blackboards, logs or sync commits.
Acquisition is external (`op`, the environment); injection at launch is a
kernel hook and stays.

##### Acceptance criteria

- [ ] Apply the group's [reduction objective](README.md#reduction-objective):
      identify redundant support wrappers and duplicated bootstrap/tooling
      mechanics in this scope, and measure simplification across core and
      edge. Preserve secret handling and the ability to uninstall with a
      broken alias configuration; relocation alone is not code reduction.

- [ ] `secret get` and `uninstall` are each classified with a written reason
      in the local-only `coga-dev/microkernel` topic, not an implicit "already
      exists" reason.
- [ ] `uninstall`'s classification answers whether it is `init`'s symmetric
      bootstrap substrate (it must survive a broken alias config; see the
      extension-model alias guardrails).
- [ ] Any move preserves the secret boundary and launch-time injection.
- [ ] Upgrade/refresh documentation (`coga init --update`, package upgrade
      in `coga/install`) is checked for a missing support surface; no
      top-level `coga update` command is invented.
- [ ] The row leaves "Open command placements"; tests and the `coga/cli`
      index are updated.

#### Context

Group: `microkernel/README.md` (v1 scope since 2026-10-16).

`src/coga/commands/update.py` is `coga init`'s template-copy helpers, not a
command. Launch-time git push-auth preflight and installed-versus-source
warnings may be handed here by `v1/microkernel/03-launch-decomposition`.

##### Premise check (2026-10-16, pull-forward to v1)

- Subject exists: `src/coga/commands/{secret,uninstall}.py`.
- Passes all four questions per the Dream W40 correction to W39 F49: the
  "acquire outside, verify inside" text is now one bullet under extension-model
  "Parameters and trust boundaries", which covers acquisition vs. injection
  but leaves the `secret get` head itself in the open table.

Previous ref: `microkernel/support-commands-boundary` (renamed 2026-10-27); earlier audit lines retain that ref. Parked by the owner for v2; this work does not gate v1.

Created under `v2/cleanup-core-commands/` as part of the command-surface breakdown.
