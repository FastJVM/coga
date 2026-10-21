---
title: Classify support commands under the small-core rule
status: draft
owner: nicktoper
agent: codex
contexts:
  - coga-dev/principles
  - coga/secrets
  - coga/uninstall
  - coga/install
  - coga-dev/codebase
  - coga-dev/testing
  - coga-dev/current-direction
  - coga-dev/microkernel
  - coga-dev/project-stage
  - coga/cli
  - dev/checkouts
workflow: code/design-then-implement
---

## Description

Settle the placement of the support heads `coga secret get` and
`coga uninstall`. For each, record whether it is bootstrap substrate (must
work without an existing ticket or a working `coga/`), an edge command, or
external tooling, and move it if the answer is the edge.

Secret values never enter tickets, prompts, blackboards, logs or sync commits.
Acquisition is external (`op`, the environment); injection at launch is a
kernel hook and stays.

### Acceptance criteria

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

## Context

Group: `microkernel/README.md` (v1 scope since 2026-10-16).

`src/coga/commands/update.py` is `coga init`'s template-copy helpers, not a
command. Launch-time git push-auth preflight and installed-versus-source
warnings may be handed here by `microkernel/launch-decomposition`.

### Premise check (2026-10-16, pull-forward to v1)

- Subject exists: `src/coga/commands/{secret,uninstall}.py`.
- Passes all four questions per the Dream W40 correction to W39 F49: the
  "acquire outside, verify inside" text is now one bullet under extension-model
  "Parameters and trust boundaries", which covers acquisition vs. injection
  but leaves the `secret get` head itself in the open table.

<!-- coga:blackboard -->

Created under `v2/cleanup-core-commands/` as part of the command-surface breakdown.
