---
title: Classify support commands under the small-core rule
status: in_progress
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
launch_generation: c073499a-d826-4aa6-be22-d3014ff2ad89
---

## Description

Classify secret inspection and installation removal against the small-core
rule, preserving their operational boundaries. Move the human secret query
onto an editable deterministic command ticket after the generic stateless
runner ships; retain the bounded uninstall recovery command. Do not introduce
a second recovery launcher merely to move code out of the command directory.
These are proposals for owner review, not ratified placement decisions.

### Objectives advanced

The secret query becomes repo-customizable Python using the same resolver as
launch. Removing its Typer group and command-specific dispatch exceptions
simplifies the command surface. Uninstall retention avoids another loader,
configuration bypass and teardown policy for a single recovery procedure.
Relocation alone is not a reduction; measure the whole implementation.

### Acceptance criteria

- [ ] Record the reviewed placement of both heads in
      `docs/contexts/coga-dev/microkernel/SKILL.md`, with the concrete proofs
      below. Remove their open row only once the reviewed implementation
      settles both; leave other command placements untouched.
- [ ] Replace the built-in secret group with a packaged
      `bootstrap/secret/ticket.md` and exact sibling `ticket.py`, using the
      read-only stateless contract owned by
      `v1/microkernel/03-launch-decomposition`. Proposed alias:
      `secret = "launch --read-only bootstrap/secret --"`; the script parses
      `get <ref>`. Preserve the public `coga secret get <ref>` spelling.
      Do not migrate until that generic seam is implemented and verified.
- [ ] Preserve discovery of a valid repo, `require_user=False`, existing
      malformed-config failures, and invocation without agent configuration
      or TTY. A successful query prints only the resolved value and existing
      trailing newline to stdout. Framing/help failures use stderr; invalid
      subcommands, missing/excess operands, raw literals, missing env refs,
      missing op and failed op reads exit 2 with no value on stdout.
- [ ] Fake resolver/tool outputs, including a distinctive failure sentinel,
      and prove values never enter prompts, audit, notifications, reports,
      usage files or Git publication. Test direct read-only launch and alias
      invocation from a dirty repo, with no configured user/agent and no TTY.
      Capture stdin/stdout/stderr as separate streams; never acquire real
      credentials. Do not put returned values in a ticket's `secrets:` field.
- [ ] Retain `uninstall` as a built-in recovery entry before alias validation,
      tolerant of invalid shared/local config and absent local definitions,
      without user/agent/TTY requirements when `--yes` is supplied. Preserve
      preview, default-no confirmation, refusal with no deletion, guide
      backups, relocated-root warning/containment and external-root-first
      failure order, skill-link pruning, gitignore cleanup, and root-layout
      refusal. No publication, checkout refresh or audit follows removal.
- [ ] Exercise removal only in disposable fixtures. Cover malformed TOML,
      invalid aliases, absent definitions/local config, edited and unmodified
      guides, external contexts and failure before deleting coga.toml,
      confirmation refusal, plus fake uv/pipx/pip purge success/failure.
      Keep unresolved executable detection, UV_TOOL_DIR targeting and
      platform-specific quoted manual recovery commands intact.
- [ ] Classify launch-adjacent checks as below. Remove no preflight merely
      because a later subprocess can fail. Any proposed deletion must prove
      visible failure on ordinary, scripted and delegated recurring paths
      before their relevant activation/publication effects.
- [ ] Update package-owned `coga/secrets`, `coga/uninstall`, `coga/init`,
      `coga/cli` and relevant launch/extension guidance in the same PR for
      changed contracts; update packaging manifests for new/removed resources.
      No live twins, forwarding modules or second upgrade mechanism.
- [ ] Report before/after full revisions and physical production line counts
      (including blanks/comments) separately for core, edge and ticket scripts;
      list deleted entrypoints, exceptions and dependency edges. Report tests,
      docs and resource copies separately. Run focused secret/uninstall/init/
      CLI/launch/packaging tests, task validation and the full Linux suite with
      receipts per `coga-dev/testing`. Native Windows/macOS checks are deferred
      to release, not implementation gates.

### Proposed shape

1. Consume the reviewed generic read-only runner from launch-decomposition.
   Its contract must suppress launch and exit publication on success and
   refusal, inherit streams without capture, avoid composition/agent fallback,
   skip skill-view writes and checkout preparation, and clear outer lifecycle
   authority. Reuse its subprocess/environment machinery; add no secret-only
   mode or command-name allowlist. If it is unavailable at implementation,
   block on exact slug `v1/microkernel/03-launch-decomposition` rather than
   implement a second runner.
2. Author the secret procedure directly beside its packaged ticket. Parse its
   small argv with stdlib, reject literals with the existing human-facing
   error, call `config.select_launch_secrets(None, [{"value": ref}])`, catch
   `SecretError`, and print only the result. Do not duplicate configuration
   loading already owned by read-only dispatch. The ticket has no agent
   procedure or secret declarations. Use the dedicated customization ticket's
   local-first discovery/forking route; the script itself contains the editable
   behavior, rather than an import-only edge wrapper.
3. Remove `src/coga/commands/secret.py` and its lazy registration/group entry
   in `src/coga/cli.py`; add the alias in `src/coga/aliases.py`. Remove the
   obsolete secret-specific sweep branch once the generic invocation policy
   covers alias expansion and refusals. Keep help/argument behavior explicit
   in integration tests. Do not edit this repository's coga.toml.
4. Retain `src/coga/commands/uninstall.py` and `cli.main`'s early dispatch.
   The co-versioned invariant is recovery before config/alias admission and
   teardown without publishing after deleting the configuration/state roots.
   Ordinary ticket launch cannot supply this contract: it loads those roots,
   validates config and has lifecycle teardown. Moving the procedure behind
   another recovery loader increases mechanisms without an identified saving.
   Do not split the plan/executor or add core-to-edge imports.
5. Remove misleading dependency ownership within the retained recovery code:
   `commands.update.remove_host_gitignore`, `running_cli_location` and
   `COGA_PIPX_PACKAGE` have only uninstall as a production consumer; move
   their definitions into uninstall and update their tests/imports, without
   forwarding exports. Keep shared gitignore marker constants in update and
   the actual init/uninstall guide template shared as it is. No speculative
   install-helper module. Count these moves as relocation, not deletion.
6. Keep `launch._preflight_push_auth` and shared
   `github_preflight.check_git_auth` enforced at use; keep
   `agent_skills.refresh_agent_skill_view` shared by init and ordinary launch.
   The read-only runner deliberately skips materialization. No installed/source
   skew diagnostic implementation was found at the baseline; do not invent or
   resurrect one from stale prose. Correct stale diagnostic guidance only after
   verifying its absence again at implementation. No readiness check moves
   into agent instructions.

### Out of scope

Changes to secret acquisition providers, launch injection/scrubbing/redaction,
new secret stores, recovery plugins, uninstall customization loaders, package
upgrade commands, arbitrary recipe registration, the generic runner itself,
and implementation of resource discovery/forking. No real uninstall or secret
query against this live repository. No code, branch or PR in this design step.

## Context

Baseline: `850ad409c4e6a6dc50b725c9c168d292e8d90ddb` (2026-11-14),
clean main equal to fetched origin/main. Physical lines including comments
and blanks: `commands/secret.py` 75, `commands/uninstall.py` 413,
`commands/update.py` 408. These are inventory, not promised savings.

- `src/coga/commands/secret.py`, `get`: loads config without requiring user,
  rejects literals, calls `config.select_launch_secrets` and echoes its result.
  `src/coga/cli.py`, `_should_sweep_coga_state` excludes the secret group.
- `src/coga/cli.py`, `main`: tolerates config errors for uninstall and invokes
  its built-in before `_validate_aliases`; it returns without the ordinary
  sweep. This bypass must remain independent of local bootstrap definitions.
- `src/coga/commands/uninstall.py`, `_build_plan`, `_configured_contexts_root`,
  `_execute_plan`, `_handle_package`: inspect before removal, use
  `config.resolve_layout_contexts_path` for safe root resolution, remove the
  external root first and select installer-specific purge. The guide comparison
  consumes `commands.init.AGENT_GUIDE_TEMPLATE` and `_AGENT_GUIDE_FILES`, which
  init's `_write_agent_guides` also consumes. Verify symbol spelling if moved.
- `src/coga/commands/update.py`, `ensure_host_gitignore` and
  `remove_host_gitignore`: share marker constants, not one executable helper.
  `running_cli_location` is used only by uninstall in production; test calls
  in `tests/test_init.py` do not establish a second consumer.
- `src/coga/launch.py`, `_preflight_push_auth`: calls
  `github_preflight.check_git_remote` and `check_git_auth`; recurring runner
  also invokes this preflight. `github_preflight.run_preflight` and megalaunch
  also consume auth checks. `_refresh_agent_skills_for_launch` wraps the same
  `agent_skills.refresh_agent_skill_view` init uses when wiring links.
- `coga/tasks/v1/microkernel/03-launch-decomposition.md`, draft stateless
  invocation contract, owns `launch --read-only` (currently proposed, absent
  from `commands.launch.launch`).
  `coga/tasks/v1/microkernel/05-make-packaged-behavior-discoverable-and-editable.md`
  owns effective-source discovery and editable distribution.
- User contract owners are under
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/`; development
  classification belongs only in `docs/contexts/coga-dev/microkernel/`.
  Follow `coga-dev/packaging` and `coga-dev/testing`; the README Get started
  section owns installation, not a retired coga/install topic.

<!-- coga:blackboard -->

## Design handoff — 2026-11-14

Traced production callers at the baseline above. Proposed secret migration
consumes the not-yet-shipped read-only stateless seam; uninstall stays a
bounded recovery command. Single-consumer update helpers move beside their
actual caller, without claiming line reduction. No implementation changed.
The previous native-Windows implementation gate was stale: current testing
policy defers native checks to release.

## Open Questions

Owner scope review: accept the proposed retained uninstall recovery contract
and secret migration dependent on launch-decomposition? These are review
choices for the scheduled owner gate, not implementation authorization.


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
