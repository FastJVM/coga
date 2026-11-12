---
title: Classify read and report commands under the small-core rule
status: draft
owner: nicktoper
agent: codex
contexts:
  - coga-dev/microkernel/objectives
  - coga-dev/principles
  - coga/tickets
  - coga/lifecycle
  - coga/usage
  - coga/recurring
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

Move deterministic report and inspection policy into script command tickets
where the resulting command remains as quick, quiet and usable as today's
direct CLI. Keep shared readers, rendering and validation primitives in core
when they have real consumers. Refreshed proposal for owner scope review.

### Objectives advanced

Hackability: users can change a report by editing its owning script. Ticket
ownership: report heads become aliases to those scripts. Simplification:
remove redundant heads and repeated formatting/argument scaffolding while
reusing actual shared readers and checks.

### Premise check against main

Snapshot: `49b34b229` (2026-11-12), physical lines including blanks/comments.

1. All five surfaces remain: `show`, `status`, `validate`, `usage`,
   `recurring list`; the launch prompt diagnostic remains too.
2. Heads are `commands/show.py` (37), `status.py` (96), `validate.py` (116),
   `usage.py` (108); `list_recurring` is part of the 391-line recurring
   command module. Shared `views.py` is 701 lines, `validate.py` 2,039,
   `usage.py` 1,349. Those shared modules are not wholesale relocation totals.
3. Requirements and exclusions are self-contained here; old archive and
   retired-task pointers are unnecessary for implementation.
4. `show`/`status` already delegate to `views`; the launch diagnostic already
   avoids the CLI exit sweep. Drop those as missing extractions. Placement
   of the report heads remains open.

### Proposed boundary

| Surface | Proposed edge responsibility | Shared machinery to preserve |
| --- | --- | --- |
| `show` | Select and display a ticket and history | Target resolution and log readers; `views.render_show` where shared |
| `status` | Report selection, ordering and formatting | Ticket/checkout reads and `views.render_status`; determine actual rendering consumers before retaining it all |
| `validate` | CLI options and report formatting | `validate.run`, `validate_task`, `assert_task_valid` and launch/lifecycle checks; shared validation is not the Dream drift job |
| `usage` | Grouping choices and text/JSON presentation | Usage capture/storage and reused record readers/rollups |
| `recurring list` | Presentation of the effective catalog and schedule | Package-aware recurring catalog and selection; scheduling/admission remain elsewhere |
| `launch --prompt-report` | Read-only presentation from `compose_prompt_report` | Composition itself remains kernel; retain the existing flag as an adapter only if it avoids a needless compatibility break |

Propose stateless bootstrap scripts behind aliases, never an agent session or
a stateful task for each report. Existing commands accept ordinary CLI operands;
bootstrap scripts can receive argv, so the old "parameters need a Typer head"
argument no longer applies. Preserve each current surface: `validate` and
`usage` have JSON; do not invent a new JSON contract for `show`/`status`.

### Required stateless execution contract

The current heads load config with `require_user=False` and skip the CLI
state sweep. `launch` loads a normal user config and normally sweeps on exit.
Simply changing a default alias would publish unrelated dirty work and make
some read commands require user/agent setup. That is a behavior change, not
a completed migration.

The launch sibling owns the generic fix: no agent or TTY for scripts, no
checkout normalization or publication for a read invocation, clean stdout,
preserved integer exit codes, help and reads without a configured operator.
This ticket is the acceptance consumer for those requirements. Do not add
one command-name exemption per migrated report or bypass shared validation.

Keep `validate --fix` explicit and deterministic, including its existing safe
repair set and current publication semantics; pure reporting must remain
write-free. Existing `--check-slack` / `--check-github` remain explicit probes.
The prompt diagnostic's current generated-skill-view behavior must be
inventoried before claiming its whole path is write-free; its existing
non-sweeping behavior is already delivered.

### Acceptance and reduction evidence

- [ ] Compare original and aliased commands in disposable repos: same output,
      argv/refusals and exits, including no-user config, dirty state, no TTY,
      no agent and offline reads.
- [ ] Show through Git/content checks that read commands neither publish
      existing dirt nor rewrite lifecycle state; verify explicit fix/probe paths.
- [ ] Keep validator preflights directly callable in core and preserve JSON
      schemas and downstream automation.
- [ ] Remove replaced heads/wrappers, retain only demonstrated shared readers,
      and report whole-system counts with relocation separated from deletion.
- [ ] Update user contract owners and the CLI index in package resources and
      the local microkernel table. Carry forward commands/status/views/usage/
      validation/recurring/compose tests and required full-suite receipts.

## Context

Read `coga-dev/microkernel/objectives` and `coga-dev/testing`. User topics live
under `src/coga/resources/templates/coga/bootstrap/contexts/coga/`: `cli`,
`tickets`, `usage`, `recurring`, `prompt-composition`, `script-tickets` and
`state-publication`. The customization ticket owns a unified way to inspect
and copy definitions, not this ticket's task-report formatting.

Design can proceed now; implementation waits only for the necessary stateless
contract, not the whole launch decomposition. Defer interactive dashboards,
new report features, a separate read protocol and cosmetic renames.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Superseded designs

### 2026-11-12 — Design before the current-main refresh

Superseded by: the refreshed Description and Context above, proposed for owner review.
Reason: source, distribution and caller boundaries changed; the owner clarified
the objectives in `coga-dev/microkernel/objectives`. Historical commands,
paths, approvals and test receipts below are evidence, not current instructions.

#### Description

Settle the placement of the read/report heads: `coga show`, `coga status`,
`coga validate`, `coga usage`, and `coga recurring list`. Keep shared
rendering (`coga.views`) and validation infrastructure in core where they have
two or more consumers. Decide for each head whether it is a thin read-view
wrapper with a co-versioning proof, an edge command, or alias sugar.

Preserve quick read ergonomics and machine-readable output (`--json`).

##### Acceptance criteria

- [ ] Apply the group's [reduction objective](README.md#reduction-objective):
      identify redundant command/report wrappers and duplicated rendering or
      checking, reusing the existing views and validation primitives where
      they serve actual callers. Report code and dependency reduction across
      core and edge while preserving quick deterministic reads, JSON, and
      exit codes.

- [ ] Each head is classified as edge command, read-view wrapper with a
      written co-versioning proof, or alias sugar, and recorded in
      the local-only `coga-dev/microkernel` topic.
- [ ] Reusable render/check/report logic moves out of command files only
      where an existing edge shape supports it without hidden transient
      parameters.
- [ ] `validate` stays fail-loud with stable exit codes and JSON for
      automation (Dream, CI, `coga launch` preflights).
- [ ] `launch --prompt-report` gets its home decided here, as handed off by
      `v1/microkernel/03-launch-decomposition`.
- [ ] The row leaves the "Open command placements" table; tests and the
      `coga/cli` index are updated.

#### Context

Group: `microkernel/README.md` (v1 scope since 2026-10-16).

`show` and `status` already render through `coga.views`; verify the current
split before moving anything. A parameterized read must not smuggle hidden
launch-time input into a ticket: if a head keeps a tiny Typer layer to pass a
display parameter, say why and keep the substance outside the command file.

##### Premise check (2026-10-16, pull-forward to v1)

- Subject exists: `src/coga/commands/{show,status,validate,usage,recurring}.py`.
- Surfaces resolve; the old pointer to the pre-split extension-model table now
  lives in `docs/archive/cli-extension-audit.md`.
- Not delivered: the row is open in extension-model.

Previous ref: `microkernel/read-report-commands-as-ticket-workflows` (renamed 2026-10-27); earlier audit lines retain that ref. Parked by the owner for v2; this work does not gate v1.

Created under `v2/cleanup-core-commands/` as part of the command-surface breakdown.
