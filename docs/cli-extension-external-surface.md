# Core boundary and external-script surface

**Status:** design only. This doc does not implement the verify hook, extract a
command, or change the CLI.

**Home:** `docs/`, paired with `coga-os/contexts/coga/extension-model/`. The
context is the durable rule agents should follow at launch; this document is the
design rationale and implementation contract for the open mechanism that context
names. The split matches `docs/cli-extension-audit.md`: evidence and design live
in `docs/`, while the ratified behavioral contract stays in the context.

## Decision

Coga's kernel remains `launch` and its dependency closure:

- `launch` / prompt composition / script dispatch.
- The state writes `launch` performs or depends on mid-flight: `mark` and
  `bump`.
- Secret injection at launch time.
- Notification dispatch used by launch/state transitions.
- The ticket factory `create` / `draft`, because `launch` runs on tickets.
- Fresh `init`, because no launch can run before `coga-os/` exists.
- Skill verify-at-compose, because trust is enforced at the moment a skill is
  loaded for use.

Everything a human, cron job, or alias calls to start work is movable unless it
is in that closure. `init --update` is therefore movable; fresh `init` is not.
`skill install` is movable; verifying a loaded skill before composing or running
it is not. `secret get` is movable; injecting scoped secret values into a task
process is not.

For Coga-authored stateless capabilities outside the kernel and ticket model,
the first-class surface is a local external CLI. For the lead case, the skill
acquirer, that CLI should be a `gh`-style extension because it wraps `gh skill`
and the README already makes `gh` a normal operator dependency. This is not a
general plugin registry and not a `coga-os/scripts/` dispatcher.

## Core boundary

The boundary test is operational:

> Does `launch` call it while running, or must it exist before any launch can
> run? If yes, it is kernel. If a human or scheduler calls it to start or inspect
> work, it is movable.

This keeps the kernel small for a reason. The kernel is the code that protects
the files-on-disk invariant and the moment-of-use trust boundary. It should not
grow because a command is important, convenient, or shipped by Coga today.

### Verify-at-compose

The open kernel item is skill verification at the moment of use. Today the skill
manager can record and compare skill tree digests during install/update/status,
but `compose_prompt` and `run_script_mode` resolve and read skills without
checking that a managed skill still matches its recorded provenance.

The follow-up hook should be shared by agent-mode prompt composition and
script-mode skill loading:

1. Resolve the skill path exactly as Coga does today, preserving local-over-
   bundled precedence.
2. If the skill directory has managed provenance, read it before loading the
   skill body or script.
3. Require a supported provenance schema and an `installed_tree_digest`.
4. Compute the current skill tree digest using the same rule as
   `hash_skill_tree`: include every file in the skill directory except the
   provenance sidecar itself, with paths and bytes hashed deterministically.
5. If the current digest differs from `installed_tree_digest`, refuse the
   launch before status mutation, prompt composition, secret injection, or
   script execution.
6. The error must name the skill ref, resolved path, expected digest, current
   digest, and remediation: reinstall/update the skill, run the external
   acquirer status command, or deliberately re-home the directory as a
   repo-authored skill by removing the provenance record in a reviewed diff.

Compare against `installed_tree_digest`, not `source_tree_digest`.
`source_tree_digest` describes the upstream materialized source. The installed
tree is the exact local content Coga is about to trust. Upstream freshness is
the acquirer's job and may require network; compose verification is local,
deterministic, and offline.

The v1 scope is any skill that claims managed provenance. Repo-authored skills
without provenance are trusted through git review and normal prompt visibility.
Bundled package-backed skills may later get a package manifest, but the first
hook should not invent one implicitly. Missing skills already fail loud; this
hook closes the narrower failure mode where a managed skill exists but its bytes
no longer match the provenance Coga recorded.

GitHub-backed installs need a normalized Coga provenance record before compose
can verify them. The current URL-backed path writes `.coga-source.json`; the
GitHub-backed path delegates to `gh skill`. The extraction follow-up should
either write the same Coga sidecar after every external install or translate a
stable `gh skill` metadata format into Coga's schema. Compose must not fetch
from GitHub or depend on preview-only metadata behavior.

## External-script boundary

An external script/service is a Coga-authored one-shot outside both the kernel
and the ticket lifecycle.

It belongs here when all of these are true:

- **Stateless in Coga terms:** it may mutate files, call tools, and print
  output, but it does not need a ticket directory, blackboard, log, workflow
  step, handoff, or review lifecycle.
- **Parameterized:** operands and flags drive the invocation.
- **Coga-authored:** Coga owns the wrapper logic, even if it shells out to
  `gh`, `git`, `op`, or another operator tool.
- **Not bootstrap/kernel:** `launch` does not call it mid-flight, and a fresh
  `coga-os/` does not need it to exist before launch can run.
- **Not a trust hook:** it may acquire a capability, but verification or secret
  injection at use stays in the kernel.

Use the other homes when one of those tests fails:

| Shape | Home | Example |
| --- | --- | --- |
| Existing third-party CLI | External tool | `gh`, `git`, `op` |
| Coga-authored stateless one-shot | External script | Skill acquirer wrapper |
| Stateful, reviewable work | Ticket / workflow | `retire`, recurring Dream work |
| Mid-flight launch dependency or fresh bootstrap | Kernel | compose, state writes, secret inject, fresh `init` |
| Fixed argv rewrite with no logic | Alias | `dream` -> `recurring launch dream` |

## Mechanism candidates

### `gh`-style extension

Shape: ship the Coga-authored acquirer as an installable GitHub CLI extension,
for example a future `gh coga-skill ...` command. The extension owns its argv,
shells out to `gh skill`, writes Coga provenance, and leaves normal git-visible
file changes in `coga-os/skills/`.

Strengths:

- Reuses an operator dependency Coga already documents.
- Keeps GitHub-specific skill acquisition next to the GitHub CLI it wraps.
- Lets argument parsing stay in a real command surface, not in `coga.toml` or
  launch-time parameters.
- Can be installed, upgraded, tested, and versioned independently from the
  launch kernel.

Costs:

- Adds another installed component and a version-skew boundary.
- Is a poor fit for non-GitHub external scripts if treated as the only mechanism.
- Bets on `gh skill` behavior stabilizing enough to wrap cleanly.

### Separate package or service

Shape: move stateless Coga helpers into another Python package, console script,
or hosted endpoint that Coga calls or asks the operator to install.

Strengths:

- Good for non-GitHub helpers and for sharing Python test fixtures.
- Avoids tying every external script to `gh`.
- Could carry common provenance code without keeping it in the launch kernel.

Costs:

- A separate local package is another install/update path for every Coga repo.
- A hosted service conflicts with Coga's local-first stance unless a real
  requirement demands the crossing.
- If the package imports too much of `coga`, the extraction is mostly cosmetic;
  if it duplicates too much, the schema and path logic drift.

### `coga-os/scripts/` dispatch target

Shape: put scripts in the repo and add a Coga dispatcher, or let `launch` call
script targets directly.

Strengths:

- Maximally inspectable and repo-local.
- Excellent for repo-owned operations that are not meant to be shared.
- Needs no new distribution channel for one-off local scripts.

Costs:

- A generic dispatcher becomes a worse Typer: command names, arg validation,
  defaults, and branching logic creep into TOML or ad hoc markdown.
- If wired through `launch`, it invites transient launch-time parameters, which
  break the prompt-is-files invariant.
- It gives Coga-authored shared tools no clean provenance or upgrade story
  across repos.

## Pick

Pick the `gh`-style extension for the first extraction: the skill acquirer.

This is deliberately narrow. The general external-script rule is "a normal local
CLI outside the launch kernel"; when the script exists to wrap an operator CLI,
ship it beside that CLI. The skill acquirer wraps `gh skill`, so a `gh`
extension is the least surprising home. A separate package remains available for
future non-GitHub helpers, and repo-local `coga-os/scripts/` remains just a
directory the operator can run directly, not a Coga command system.

The Coga CLI may keep a temporary compatibility shim, but only as raw argv
forwarding with a fail-loud installation hint. The canonical command should live
in the external CLI. If preserving `coga skill ...` requires reimplementing the
extension's option parsing in Typer, the shim should be dropped instead.

## Dispatch rules

- Parameters belong to the command being invoked. For the skill acquirer, that
  is the external `gh` extension's argv.
- Coga must not add transient `coga launch` parameters for external scripts.
- Coga must not grow a `[commands]` or `[scripts]` DSL in `coga.toml`.
- A compatibility shim may locate the external command and `exec`/subprocess the
  raw remainder, but it should not interpret command-specific flags.
- External scripts communicate by stdout, stderr, exit code, and git-visible file
  changes.
- External scripts may load Coga config for paths and shared settings, but they
  do not get a task blackboard, task log, workflow step, or composed prompt.

This preserves the key distinction: parameters for stateless one-shots stay at a
command layer; parameters for stateful work are materialized into ticket files at
creation time.

## Trust rules

Trust boundaries straddle the homes:

- **Acquire outside.** `gh skill`, URL downloads, local imports, `op`, and `env`
  lookup are acquisition mechanisms. Coga may author wrappers around them, but
  those wrappers are not the kernel.
- **Verify and inject inside.** Compose verifies managed skills at the moment
  they are loaded. Launch injects only the scoped secrets a task is allowed to
  receive. Secret values never enter tickets, prompts, blackboards, logs, git, or
  external-script provenance.

The skill acquirer is the worked example. Its external job is to fetch or update
skill files and write provenance. The kernel's job is to refuse to compose or run
that skill later if the local tree no longer matches the recorded installed
digest. Acquisition can be updated, replaced, or moved out of `src/coga/`
without weakening the moment-of-use check.

## Move plan

1. **Implement verify-at-compose first.** Add a shared verification helper used
   by `compose_prompt` and `run_script_mode`. Add tests for matching provenance,
   digest mismatch, invalid provenance, unmanaged repo-authored skills, and
   script-mode refusal before status mutation.
2. **Normalize provenance for all externally acquired skills.** Keep the
   `coga.skill-source.v1` shape or introduce a v2 deliberately. The acquirer
   must record the installed digest needed by compose. If `gh skill` gains a
   stable metadata contract, adapt it into Coga's schema rather than making
   compose parse preview internals.
3. **Extract the skill acquirer.** Move `install`, `install-local`,
   `install-url`, `update`, and `remove` to a `gh` extension while preserving
   the current deterministic Python behavior and tests. The extension owns
   `--force`, URL materialization, local-adaptation detection, conflict status,
   and PR-summary generation. Coga core may temporarily delegate raw argv.
4. **Leave read-view migration to Pass 2.** `skill status` is a read view in the
   companion plan. The acquirer may expose a status/debug command because it owns
   provenance, but the Coga CLI's read-view cleanup should stay with
   `status`/`show`/`recurring list` unless explicitly greenlit.
5. **Consider `init --update` after the acquirer moves.** Fresh `init` stays
   kernel. `init --update` is movable in principle because it refreshes an
   existing install, but it has broader packaging responsibilities: vendored
   templates, managed-skill reconciliation, venv dependency installation, and
   agent skill links. Move it only if a local external package can own those
   resources without hiding state or weakening update tests. Do not make it a
   hosted service.
6. **Do not move trust hooks or task-state writes.** Secret injection, skill
   verification, `mark`, `bump`, and launch notifications stay in the kernel.

## Risks

- **Extra installation step.** A `gh` extension gives operators one more thing
  to install. Mitigation: fail loud with a precise command and keep a temporary
  raw-forwarding shim only if it does not duplicate parsing.
- **`gh skill` preview churn.** If the wrapped command changes, Coga's acquirer
  can break. Mitigation: defer extraction until `gh skill` is stable enough or a
  second consumer makes extraction worth the boundary; keep tests around the
  wrapper's user-facing behavior.
- **Schema/version skew.** The kernel verify hook and external acquirer share a
  provenance contract. Mitigation: schema-version the sidecar, fail loud on
  unsupported schemas, and test old/new metadata intentionally.
- **Provenance split-brain.** GitHub-backed, URL-backed, local, bundled, and
  repo-authored skills can drift into different metadata stories. Mitigation:
  normalize externally acquired skills into one Coga sidecar and define what
  "no sidecar" means: repo-authored or package-backed content, not externally
  managed content.
- **Generic dispatcher creep.** `coga-os/scripts/` is tempting because it is
  local and legible. Turning it into a command registry recreates Typer badly and
  encourages hidden launch params. Mitigation: keep repo scripts directly
  runnable, and use tickets when work needs state.
- **Hosted-service drift.** External service is the rare case, not the default.
  Mitigation: require a concrete requirement that a local script cannot satisfy;
  otherwise keep the surface local.
