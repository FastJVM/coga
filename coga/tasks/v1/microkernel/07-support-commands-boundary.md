---
title: Classify support commands under the small-core rule
status: done
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
---

## Description

Classify secret inspection and removal against the small-core rule. Owner
confirmed the revised implementation scope on 2026-11-16: retain `secret get`
in core to preserve the operator's 1Password authentication, retain uninstall
recovery, and move uninstall-only helpers beside their consumer. The earlier
secret-ticket proposal is superseded by this decision and the evaluator's
credential-preservation finding below.

### Objectives advanced

Settle both support command placements with concrete invariant proofs, avoid
a privileged ticket-child policy or a second recovery loader, and remove
misleading helper ownership. This gives up repo-editable secret-query behavior.
Relocation alone is not a code reduction; measure the whole implementation.

### Acceptance criteria

- [x] Record both reviewed retained placements and launch-adjacent checks in
      `docs/contexts/coga-dev/microkernel/SKILL.md`; remove only their open row.
- [x] Retain `coga secret get <ref>` in the parent process using the shared
      resolver. Prove fake OP auth reaches `op read` while ordinary task
      environments still scrub it. No secret-only runner, alias, bootstrap
      ticket, or provider/scrubbing change.
- [x] Preserve repo/config admission, `require_user=False`, operation without
      user/agent/TTY, exact value plus newline on successful stdout, and exit 2
      without values on stdout for invalid arguments, literals, missing env,
      missing op and failed op reads. Preserve help behavior: explicit help
      exits 0 on stdout; bare group usage exits 2 on stdout.
- [x] Use only fake credentials/tool outputs, including a failure stdout
      sentinel. Verify separate streams, no prompt/audit/notification/report/
      usage writes or Git publication, and dirty state preservation. Exercise
      the real CLI entrypoint and subprocess environment in disposable repos.
- [x] Retain uninstall's pre-alias recovery entry, including malformed shared
      and local TOML, invalid aliases and absent local definitions/config.
      No user/agent/TTY requirement with --yes, no publication/refresh/audit
      after removal. Cover preview, default-no/refusal, guide backups,
      safe relocated contexts and external-root-first failure, link pruning,
      gitignore cleanup and root-layout refusal in disposable fixtures.
- [x] Move `remove_host_gitignore`, `running_cli_location` and
      `COGA_PIPX_PACKAGE` from update to uninstall, with tests/imports and no
      forwarding exports. Keep shared marker constants and guide templates.
      Preserve fake uv/pipx/pip success/failure, unresolved executable detection,
      UV_TOOL_DIR targeting and platform-specific manual recovery hints.
- [x] Keep auth preflights and shared skill-view refresh in core. Reverify the
      absence of installed/source skew diagnostics and remove stale guidance.
- [x] Update package-owned user topics for the retained contracts; add no
      resources, live twins, manifest changes or second upgrade mechanism.
- [x] Report full before/after revisions, physical production line counts
      including blanks/comments separately for core, edge and ticket scripts,
      dependency changes, and separate test/docs/resource counts. Run focused
      secret/uninstall/init/CLI/launch/packaging checks, task validation and
      the full Linux suite with receipts. Native checks defer to release.

### Implementation shape

Retain `commands.secret.get`, its Typer registration and built-in name. Remove
only the redundant false-return sweep branch, keeping the generic nonmutating
outcome. Parent-side resolution preserves service-account verification without
passing OP auth to ticket code. Reconsider migration only after a separately
reviewed execution policy can preserve that boundary.

Retain `commands.uninstall` and `cli.main`'s early return. Config parsing
failures must reach the existing recovery admission alongside schema errors.
Keep plan/execution together and move its three sole-consumer definitions
from update without new modules or core-to-edge imports. No preflight moves
into agent instructions.

### Out of scope

Secret providers, launch injection/scrubbing/redaction, the generic read-only
runner, discovery/forking, recovery plugins and real secret/uninstall queries
against this live repository. No PR in this implementation step.

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

## Dev

pr: https://github.com/FastJVM/coga/pull/1246
branch: coga/v1-microkernel-07-support-commands-boundary-b684a3


## Design handoff — 2026-11-14

Traced production callers at the baseline above. Proposed secret migration
consumes the not-yet-shipped read-only stateless seam; uninstall stays a
bounded recovery command. Single-consumer update helpers move beside their
actual caller, without claiming line reduction. No implementation changed.
The previous native-Windows implementation gate was stale: current testing
policy defers native checks to release.

## Owner decision — 2026-11-16

Attended session proposed retaining `secret get` in core to preserve operator
1Password auth and completing uninstall/helper relocation; owner replied
"conf!". This supersedes the secret migration proposal. 03 remains unmerged
(PR #1233), but is no longer a dependency for the retained-command scope.
Checkout matches launch notice, no PR exists for this branch. Preserved and
verified the projected ticket across rebase onto origin/main
`db9f9a5643e6851c0c99a858a6dafea2de280313`; only linkage publication advanced
main from entry HEAD `54d9463b958a2e304cdf8b2edf9004dcff5129d2`.

### Implementation findings

The new malformed-TOML entrypoint tests exposed an existing parser exception
escaping `cli.main` before uninstall admission (shared and local config).
Catch that parser error with ConfigError at eager admission so recovery works
and secret queries exit 2 without stdout. Bare secret usage actually exits 2
on stdout, while explicit help exits 0 on stdout; preserve both. All test
credentials and provider values are artificial.

## Evaluator review

Cold review, 2026-11-14, at main `6e5067ecd` (equal to origin/main). The 03
read-only seam was checked on its open PR #1233 head `0bf44d2a1`
(`coga/v1-microkernel-03-launch-decomposition-6852fc`, unmerged, ticket on
`review`). No archive was read. Verdict: **the uninstall half is ready; the
secret half needs one owner decision before implementation.**

### Must resolve before implementation

1. **The read-only runner removes the credential that `op://` resolution needs.**
   Proposed shape 1–2 runs `select_launch_secrets` inside the `ticket.py`
   child. That child's environment comes from `config.build_launch_env`, which
   always calls `scrub_op_auth_env`. It removes `OP_SERVICE_ACCOUNT_TOKEN`,
   `OP_CONNECT_*` and `OP_SESSION_*`. On #1233,
   `launch_script.run_script_phase(read_only=True)` uses that same builder
   (03's contract: "Reuse task-environment isolation"). Today
   `commands/secret.py` resolves in the parent process, which still holds
   that auth. After the move:
   - The verification procedure `coga/secrets` prescribes ("verify with
     `coga secret get <ref>` in a clean environment where
     `OP_SERVICE_ACCOUNT_TOKEN` is the only credential") would fail even for a
     correct ref.
   - On a machine with a signed-in desktop app, it would silently fall back to
     the personal login. That is exactly the false pass the topic warns about.

   `env:VAR` refs still work, because a ticket with no declarations scrubs no
   `env:` source. None of the design's escapes is allowed by its own rules:
   - Declaring `OP_SERVICE_ACCOUNT_TOKEN: env:OP_SERVICE_ACCOUNT_TOKEN` on the
     ticket contradicts "no secret declarations". It would also make every
     query fail loudly when the variable is unset, including `env:` queries
     and personal-login use.
   - A secret-only unscrubbed mode is forbidden ("add no secret-only mode").
   - Resolving in the parent needs argv-aware secret logic in the kernel.

   The proposed AC tests (fake resolver, distinctive sentinel) would not catch
   this unless they assert the child's environment. The owner should choose
   one of:
   - (a) keep `secret get` in core and record the proof: it must resolve with
     the operator's unscrubbed auth, which no task child receives by design;
   - (b) add a reviewed read-only policy that keeps OP auth for this target,
     with the trust consequences recorded in `coga/secrets`;
   - (c) accept the regression and rewrite the `coga/secrets` verification
     procedure.

   Whichever is chosen, add an AC asserting the child's environment with
   `OP_SERVICE_ACCOUNT_TOKEN` set. Merely faking `op` is not enough.
2. **`secret` must leave `aliases.BUILTIN_COMMANDS`.** Proposed shape 3 adds a
   default `secret` alias. However, `validate_aliases` rejects any alias whose
   name is in `BUILTIN_COMMANDS` (`aliases.py`), and `secret` is listed there.
   `tests/test_aliases.py` pins that set to Typer's registry. Name the removal
   from the set (and from `cli._GROUP_COMMANDS` and `_LAZY` registration) in the
   shape so the implementer does not discover it as a failing
   default-alias validation.

### Verified as stated

- `commands/secret.py` (75 lines), `uninstall.py` (413), `update.py` (408)
  match the baseline counts. The `secret` branch in
  `cli._should_sweep_coga_state` is dead code: both its branches return False.
- In `cli.main`, `uninstall` tolerates `ConfigError` and dispatches before
  `_validate_aliases`, with no sweep. The retention proof holds, and it can be
  stated more sharply. An edge implementation cannot keep the
  `coga uninstall` spelling: an alias runs only after config load and alias
  validation, and an early dispatch would make core import `coga_edge`, which
  the microkernel rule forbids. Recommend writing that sentence into the
  microkernel record.
- Outside tests, `remove_host_gitignore`, `running_cli_location` and
  `COGA_PIPX_PACKAGE` are used only by `uninstall.py`.
  `tests/test_uninstall.py` already monkeypatches `uninstall_cmd.running_cli_location`.
  The four `tests/test_init.py` `running_cli_location` tests call
  `update_cmd.running_cli_location` and must move with the function.
  `AGENT_GUIDE_TEMPLATE`/`_AGENT_GUIDE_FILES` are shared with init's
  `_write_agent_guides`, so they correctly stay.
- No installed-versus-source skew implementation exists in `src/coga/`. The
  only reference is stale prose in `docs/contexts/coga-dev/testing` ("owned
  by coga/launch"), and `coga/launch` has no such section. Correcting that
  line is in scope under shape 6.
- On #1233, alias expansion gives `launch --read-only bootstrap/secret -- get
  <ref>`. The `--` keeps the operands out of policy detection. Malformed
  config still exits 2 through `cli.main`'s generic `ConfigError` path, and a
  missing repo still gets the init hint, because `_DEFAULT_ALIASES` count as
  known commands.
- The packaged `bootstrap/retire/ticket.{md,py}` is the precedent for a
  directory-form bootstrap with an exact `ticket.py`.

### Optional recommendations

- Shape 3 removes the secret-specific sweep branch. That branch is dead today,
  so delete it regardless of the generic policy; it is not contingent.
- The help AC is ambiguous. Today `coga secret get --help` prints to stdout
  and exits 0. Say whether successful help stays on stdout or moves to stderr,
  and which exit code bare `coga secret` returns.
- Step 2 says to "use the dedicated customization ticket's ... route". Clarify
  that 05 is not a gate: local-first bootstrap resolution already makes a
  repo copy effective.
- Record the trust consequence in `coga/secrets`: a repo-local override of
  `bootstrap/secret/ticket.py` runs on every human secret query, and it
  receives the resolved value.
- The two halves are independent. If 03 is still unmerged at implement time,
  allow shipping the uninstall/helper relocation and its microkernel record
  first, and leave the `secret get` row open, rather than blocking the whole
  ticket.

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


## Implementation evidence — 2026-11-16

Author: Codex in attended launch `5a54a5db-2fb1-47fb-8682-4d2482f9c8fa`;
no agent override used. Owner confirmed revised retained-secret scope in this
session. Implementation committed at
`10679e3b828985da6bca982d0a05803e110046a2`, based on
`db9f9a5643e6851c0c99a858a6dafea2de280313` (full before revision).

Both heads remain built-ins. Microkernel removes only their open placement
row and records authentication/recovery proofs. No bootstrap resources or
aliases were added; no manifests need changes. Uninstall owns its removal
helper, package name and installer detection; shared marker constants and
init's guide template stay shared. Generic script execution, auth scrubbing,
push preflights and skill-view materialization have no implementation changes.
Reverified absence of installed/source skew code and removed the stale testing
promise. User topics link the retained operational contracts.

New malformed shared/local TOML regressions initially failed: parsing raised
TOMLDecodeError before the CLI's recovery branch. CLI eager admission now
handles that alongside ConfigError. Uninstall therefore reaches its early
built-in and secret console queries exit 2 on stderr, with no value stdout.
This fix also gives other ordinary commands clean parser diagnostics and
existing init/cross-repo recovery the same admission treatment.

### Physical line counts

Method: `git show <full-revision>:<path>` bytes, counting physical lines with
`splitlines()`, including comments and blanks. Scope is the four production
modules inspected/changed for this boundary, not a claim about the entire
repository. Revisions are the full before/after OIDs above.

| Core module | Before | After |
| --- | ---: | ---: |
| `src/coga/cli.py` | 654 | 653 |
| `src/coga/commands/secret.py` (unchanged) | 75 | 75 |
| `src/coga/commands/uninstall.py` | 413 | 477 |
| `src/coga/commands/update.py` | 408 | 342 |
| Core total in scope | 1550 | 1547 |

Edge and ticket/skill scripts: 0 before/after in scope, none added or changed.
66 physical lines moved from update to uninstall; that is relocation, not
simplification by deletion. Net production delta is -3: import adjustments
and a redundant two-line false-return sweep branch removed while adding parser
error admission. No public entrypoint was deleted. Removed dependency edges:
uninstall no longer imports update's remove_host_gitignore,
running_cli_location or COGA_PIPX_PACKAGE; it now shares the end-marker data
constant too. No core-to-edge import, forwarding export, helper module,
privileged child policy or recovery loader was introduced.

Separately, changed tests total 4231 -> 4612 physical lines across test_init
(3603 -> 3508), test_secret (98 -> 312) and test_uninstall (530 -> 792).
Four installer-detection tests moved with their helper; new tests exercise
credential/environment separation, separate pipes, malformed config admission,
no publication from dirty repos, removal refusal/order/containment, purge
failures and managed-block cleanup. Local dev topics total 482 -> 519 lines;
five package-owned user topics total 564 -> 591. No copied resources or live
twins. All credentials/results are fake; destructive operations use fixtures.

### Verification complete

All receipts are for head `10679e3b828985da6bca982d0a05803e110046a2`
and merge base `db9f9a5643e6851c0c99a858a6dafea2de280313`.
Linux Pop!_OS 24.04 LTS, kernel 7.2.15-76070215-generic, Python 3.12.12.
Final focused suite: 673 passed, 1 skipped in 61.83s. Full suite:
4930 passed, 33 skipped, 0 failed in 813.50s. Both exit 0.
Task validation: 1 valid task, no issues/fixes. Seeded validation: 5 valid
tasks, no issues/fixes. Exact commands are in the structured record below.
No command-line test exclusions; native checks and Python 3.11 floor evidence
are deferred to release. Focused skip requires Windows PowerShell. No real
credentials or live installation removal/purge were exercised.

Final fetch/rebase confirmed origin/main unchanged and branch up to date;
rebase rewrote no commits. The projected ticket was preserved and verified
byte-for-byte outside the repository across rebase. Committed implementation,
tests and docs are identical to the full-suite tree. No independent code
review in implement; peer-review is the next workflow step. No PR opened.

## PR

```yaml
title: Retain secret authentication and uninstall recovery boundaries
author: codex
author_evidence: 'Implementation: attended Codex implement session, launch 5a54a5db-2fb1-47fb-8682-4d2482f9c8fa;
  no agent override used. Two fix commits (5e3774d77, 44bd81d0f) authored by Claude in attended peer-review
  launch 3f5a362a-afaf-4a64-8c25-fa7a6c02ef8b, approved by the owner in session.'
head: 44bd81d0fa993c2110a791f90c36ab0065105352
base: 4b4b6b12ee22f84f35d99630be4f41d4aad8bc82
depth: deep
rationale: Owner-approved boundary change plus a config-parse error contract change touching every load_config
  caller; deep review is warranted.
implementation: Retain secret get in the CLI parent and uninstall before alias validation; move uninstall-only
  helpers. config._read_toml now raises ConfigParseError (a ConfigError subclass naming the file) for
  TOML syntax or non-UTF-8 bytes, so recovery admission, secret refusal and every load_config caller get
  a file-naming ConfigError; recurring --all still dispatches malformed config to the child instead of
  skipping it as unconfigured. Scoped core physical lines (cli, config, recurring_runner, secret, uninstall,
  update) 9259 to 9266 at db9f9a564..44bd81d0f; 66 moved lines are relocation, not deletion.
deviations: Owner confirmed retaining secret get after evaluation showed ticket children scrub required
  OP authentication. No secret bootstrap or alias is added; launch-decomposition is not a dependency for
  this revised scope. Preserve existing bare-group usage on stdout with exit 2. Peer review replaced the
  implement step's cli.main-only TOMLDecodeError catch with the config-level ConfigParseError so non-UTF-8
  config is also admitted and errors name the file.
limitations: No real credentials, live-repo removal or real package purge exercised. Native Windows/macOS
  and Python 3.11 floor checks defer to release. No new packaged resources, manifests or seeded-fixture
  changes; dedicated disposable fixtures cover retained behavior.
files:
  docs/contexts/coga-dev/microkernel/SKILL.md: Settle only the two support heads with parent-auth and
    early-recovery proofs; retain shared launch checks.
  docs/contexts/coga-dev/testing/SKILL.md: Remove a promise of installed/source skew warnings that have
    no implementation.
  src/coga/cli.py: Remove the redundant secret false-return sweep branch; parse failures now arrive as
    ConfigError.
  src/coga/commands/uninstall.py: Own the three sole-consumer definitions formerly imported from update;
    preserve recovery mechanics. Also tolerate non-UTF-8 coga.toml when resolving a relocated contexts
    root.
  src/coga/commands/update.py: Remove uninstall-only helpers and package constant without forwarding exports.
  src/coga/config.py: Add ConfigParseError and raise it from _read_toml for TOML syntax or non-UTF-8 config,
    naming the file.
  src/coga/recurring_runner.py: Keep malformed config dispatched to the authoritative child under recurring
    --all rather than skipped as unconfigured.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md: Index the retained built-in
    support heads.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/extension-model/SKILL.md: Link retained secret/auth
    and recovery boundaries when choosing extensions.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/init/SKILL.md: Point broken-config removal
    guidance at uninstall recovery admission.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/secrets/SKILL.md: Document parent authentication,
    exact stream/help behavior and no-publication query contract.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/uninstall/SKILL.md: Own malformed or non-UTF-8
    config recovery admission and the no-publication teardown contract.
  tests/test_init.py: Move installer-detection tests to their actual consumer and drop empty installer
    headings.
  tests/test_recurring.py: Pin malformed and non-UTF-8 config as dispatched failures under recurring --all.
  tests/test_secret.py: Prove fake operator auth, separate pipes, dirty-state preservation, refusal behavior
    and absence of launch/publication effects. Pin file-naming parse errors and that secret never sweeps.
  tests/test_uninstall.py: Move installer tests and exercise recovery admission, refusal/order/containment,
    purge failures and managed-block cleanup in fixtures. Cover non-UTF-8 shared/local config admission.
review:
  reviewer: claude
  kind: independent
  status: failed
  head: 6156d16818018b54a1d094cea9c1bd9923c6f7b5
  base: 4b4b6b12ee22f84f35d99630be4f41d4aad8bc82
  detail: 'Claude /code-review (default effort) returned on head 6156d1681 (implementation rebased onto
    base 4b4b6b12e), 8 findings. Applied: non-UTF-8 config escaping recovery admission, parse errors not
    naming the file, cli-only catch altitude, unpinned secret no-sweep. Declined as nits/out of scope:
    module-attribute seam patches, alias-placeholder stub (subprocess test covers real path), pre-existing
    init/tomlkit import. The two fix commits on top were authored by the reviewer and are self-reviewed
    only; the full suite caught and drove the recurring regression fix.'
checks:
- command: TERM=dumb PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q --basetemp=/home/n/Code/coga-pytest-support-07-peerfull2
  status: passed
  detail: Pop!_OS 24.04 LTS, Linux 7.2.15-76070215-generic, Python 3.12.12. 4937 passed, 33 skipped, 0
    failed in 756.59s, exit 0. No exclusions. The previous run at 5e3774d77 failed 1 (test_recurring_all_isolates_malformed_config_during_remote_grouping),
    fixed in 44bd81d0f.
  head: 44bd81d0fa993c2110a791f90c36ab0065105352
  base: 4b4b6b12ee22f84f35d99630be4f41d4aad8bc82
- command: TERM=dumb PYTHONPATH=$PWD/src .venv/bin/python -m coga.cli validate --task v1/microkernel/07-support-commands-boundary
    --json
  status: passed
  detail: Pop!_OS 24.04 LTS, Linux 7.2.15-76070215-generic, Python 3.12.12. 1 valid task, no issues or
    fixes.
  head: 44bd81d0fa993c2110a791f90c36ab0065105352
  base: 4b4b6b12ee22f84f35d99630be4f41d4aad8bc82
- command: git diff --check 4b4b6b12e...HEAD
  status: passed
  detail: Pop!_OS 24.04 LTS, Linux 7.2.15-76070215-generic, Python 3.12.12. No whitespace errors.
  head: 44bd81d0fa993c2110a791f90c36ab0065105352
  base: 4b4b6b12ee22f84f35d99630be4f41d4aad8bc82
- command: Native Windows/macOS full suites and Python 3.11 floor verification
  status: not-run
  detail: Pop!_OS 24.04 LTS, Linux 7.2.15-76070215-generic, Python 3.12.12. Deferred to release per testing
    policy; Linux/Python 3.12 only.
  head: 44bd81d0fa993c2110a791f90c36ab0065105352
  base: 4b4b6b12ee22f84f35d99630be4f41d4aad8bc82
```


## Implement handoff

Pushed `coga/v1-microkernel-07-support-commands-boundary-b684a3` at
`10679e3b828985da6bca982d0a05803e110046a2`; upstream confirms that same OID.
Both support placements are settled under the owner's confirmed scope;
secret customization was explicitly declined to preserve parent auth.
All revised acceptance criteria are implemented and verified. New malformed
TOML admission fix is covered by initially failing shared/local regressions.
No unresolved implementation blocker, no new follow-up, and no PR opened.

Peer review should assess the retained-boundary proofs and small CLI parser
exception change as well as the helper moves. The complete scoped counts,
limitations and Linux receipts are above, and structured PR preparation covers
every diff path. Native checks remain release-only. This projected ticket was
never staged or committed; all other paths are clean. Ready for one bump to
peer-review; launch owns publication and checkout return.

## Peer review — 2026-11-17

Reviewer: Claude (attended launch 3f5a362a-afaf-4a64-8c25-fa7a6c02ef8b),
independent of the Codex implementation. Rebased onto origin/main
`4b4b6b12e` (ticket/log commits only; projected ticket preserved
byte-for-byte), then ran `/code-review` (default effort) on `6156d1681`; it
**returned** with 8 findings.

Applied with owner approval: `config._read_toml` raises `ConfigParseError`
(a `ConfigError` subclass naming the file) for TOML syntax or non-UTF-8
bytes, replacing the `cli.main`-only `TOMLDecodeError` catch. This makes
non-UTF-8 config reach uninstall recovery, which previously crashed, and
names the broken file for secret and every other command. Uninstall's
contexts-root probe also tolerates `UnicodeError`. Pinned `secret` as
non-sweeping. The first full run caught a regression: `recurring --all`
classified the new ConfigError as "unconfigured" and silently skipped it, so
it now treats `ConfigParseError` as a child-reported failure. Both cases are
pinned in tests. The other launch/sweep `except ConfigError` sites now warn
instead of tracebacking on malformed config.

Declined: module-attribute seam patches miss `from` imports (subprocess
dirty-state tests cover it); alias-placeholder stub (subprocess test covers
the real path); `uninstall` importing `init`/`tomlkit` (pre-existing,
declared dependency).

Final head `44bd81d0fa993c2110a791f90c36ab0065105352`, pushed; the fix
commits are self-reviewed only. Full suite 4937 passed, 33 skipped. Ready for
open-pr.

## Recipe Failure

Recipe: `open-pr`
Exit: 2
Task: `v1/microkernel/07-support-commands-boundary`
Recorded: 2026-11-17T07:58:53+00:00

    [open-pr] origin/main advanced only through non-overlapping Coga task/log state; branch is safe to publish
    PR presentation: author must be a compact identity (1–32 letters, digits, ./_-).

## Open PR handoff

Opened https://github.com/FastJVM/coga/pull/1246 from clean control via
`coga open-pr v1/microkernel/07-support-commands-boundary`; verified open,
non-draft, recorded under Dev, at reviewed/tested final head
`44bd81d0fa993c2110a791f90c36ab0065105352`. Fresh fetch confirmed only
non-overlapping ticket/log drift since the recorded base. All acceptance
items are checked; native and Python 3.11 checks remain release obligations
under testing policy, with no new task-specific outstanding work.

Publication initially refused the noncompact author field. Normalized it to
`codex`, retaining Claude fix authorship in author_evidence, and encoded the
returned review with findings as a historical failed receipt at its actual
reviewed head/base. Deep recommendation and disclosure that subsequent fixes
were self-reviewed remain visible; no new test or review receipt was claimed.
Ready for the owner review gate; no merge performed.
