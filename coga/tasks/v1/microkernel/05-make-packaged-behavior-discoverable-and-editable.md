---
title: Make packaged behavior discoverable and editable
status: in_progress
owner: nicktoper
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills:
    - code/peer-review
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 6 (open-pr)
contexts:
- coga-dev/microkernel/objectives
- coga-dev/principles
agent: claude
---

## Description

Provide one discoverable route from a command to the files that define its
behavior, and to a complete editable repository copy of the selected behavior.
This fills the accessibility gap in the original microkernel group: local-first
resolution exists, but users must still know package paths and follow Python
shims manually. New draft proposed by the refresh; owner scope review precedes
implementation.

### Objectives advanced

Hackability: users and their agents can find and change shipped behavior even
with a read-only installation. Ticket ownership: the path reaches the actual
script or composed instructions. Simplification: one resolver-based inspection
and copy path replaces separate package-location/copy recipes per capability.

### Premise check against main

Snapshot: `49b34b229` (2026-11-12).

1. The gap exists: bundled workflows/skills/contexts/command tickets and
   recurring definitions are package-owned, while this source repo has no
   live mirror of them for a contributor to discover by browsing `coga/`.
2. `paths.resolve_workflow_path`, `resolve_skill_path`, `resolve_context_path`,
   resource override helpers, `tasks.resolve_bootstrap`, and the recurring
   catalog supply the existing selection rules. `show` displays tickets;
   it is not a unified source/fork command. `skill status` is skill-specific.
3. The objective and first acceptance case are attached. The wheel's current
   fork/upgrade rules are owned by `coga/edge-code`; no missing retired task
   is needed to recover them.
4. Wheel-owned edge delivery shipped in `bc46823c4` and package-aware recurring
   selection in `d0f4e2c6f`. `phone-home` and `trim-log` use shims importing
   `coga_edge`. Keep that distribution support; add access to the effective
   definition and its real implementation.

### Proposed user path (owner-confirmed shape, 2026-11-14)

One stateless script command ticket, `bootstrap/fork`, exposed by two
default aliases whose dispatch policy is fixed by the alias, not inferred by
the kernel:

```toml
fork      = "launch --read-only bootstrap/fork -- inspect"
fork-copy = "launch bootstrap/fork -- copy"
```

`coga fork <target>` reports where a behavior's definition and
implementation live and where a local override would go. `coga fork-copy <ref>`
copies one packaged definition into its local override location. No new Typer
head, plugin registry or ticket field. One alias cannot carry both a
read-only and a write dispatch policy, so the owner chose two plain aliases
over a `--copy` argv adapter (2026-11-14). The owner also chose: fork-copy
copies **one artifact** and prints ready-to-run `coga fork-copy` commands for what
it references; returning to stock is a **documented procedure** that
`coga fork` prints and fixtures verify, not a restore operation.

### Acceptance criteria

Discovery (`coga fork`)

- [ ] `coga fork <target>` accepts a typed ref — `workflow:<ref>`,
      `skill:<ref>`, `context:<ref>`, `bootstrap/<name>` (or
      `bootstrap:<name>`), `recurring:<name>`, `resource:<name>`,
      `task:<slug>` — or an untyped word. An untyped word resolves in this
      order: effective alias (`{**DEFAULT_ALIASES, **cfg.aliases}`), built-in
      command (`aliases.BUILTIN_COMMANDS`), then task ref
      (`tasks.resolve_task`). Unknown or ambiguous targets exit 1 with the
      candidates checked on stderr.
- [ ] An alias reports its expansion and follows it: `launch bootstrap/<n>` →
      the bootstrap ticket; `recurring launch <n>` → the recurring job;
      `launch <slug>` → the task; `run <recipe>` → kernel recipe; any other
      head → kernel primitive. A built-in command or `runner.RECIPES` entry is
      reported as **kernel primitive (not an editable ticket)** with its
      package module, never as forkable.
- [ ] For each definition the report gives: kind, ref, selected origin
      (`local`/`package`), selected path, packaged path (or none), local
      override destination, and fork state — `stock` (no local entry),
      `fork (identical to installed package)`, `fork (modified)`,
      `local only` (no packaged counterpart) or `broken: <reason>` (the
      resolver's `LocalOverrideError`/`BootstrapOverrideError`/recurring
      `error` text, never a silent fallback to package text).
- [ ] References are listed with their own resolution: a workflow's step
      skills (and each step's `checkout:`); a bootstrap/recurring ticket's
      frontmatter `workflow`, `skills`, `contexts`; a recurring job's
      selection state (`enabled`/`disabled`/`unselected`/`parked`/error) and
      state carrier path.
- [ ] A `ticket.py` is classified by parsing its source with `ast` — never
      importing or running it: `edge shim` (only imports `main` from
      `coga_edge.<module>` plus a `__main__` guard) → implementation is the
      installed module file; `recipe adapter` (calls `coga.runner.run_recipe`
      with a literal name) → implementation is kernel recipe `<name>`, not
      forkable here; anything else → `full script` (it is the
      implementation).
- [ ] An edge module is checked by `ast` too: `coga.*` imports are listed as
      shared-core dependencies the fork must stay compatible with; a
      `coga_edge.*` or relative import, or a missing `__main__` guard, marks
      the implementation **not completely forkable** and names the cause.
- [ ] `task:<slug>` shows what is frozen in the ticket (workflow name and
      steps, each step's `checkout:`/`assignee:`/`requires:`) separately from
      what resolves live at launch (step skills, ticket skills and contexts,
      sibling `ticket.py`); the live workflow file is shown as "not used by
      this ticket's frozen snapshot".
- [ ] For a fork, the report prints the exact return-to-stock steps (below).
- [ ] `--json` emits the same records with stable keys; text goes to stdout,
      diagnostics to stderr; `--help` prints usage to stdout and exits 0.
- [ ] Read-only: runs through `launch --read-only` with no configured user,
      no TTY and dirty files; writes nothing, publishes nothing, runs no job,
      imports no implementation and invokes no agent. Exit 0 when the report
      has no broken definitions, 1 when the target is unknown or any reported
      definition is broken (the report is still printed), 2 for usage errors.

Copying (`coga fork-copy`)

- [ ] `coga fork-copy <ref>` accepts a typed ref or an alias that resolves to one
      bootstrap ticket or recurring job. It refuses (exit 1, no writes) task
      refs, kernel primitives, a ref with no packaged definition, and a ref
      already selected locally ("already a local override at <path>").
- [ ] It copies the whole packaged artifact to the resolver's local path:
      workflow → `paths.workflow_path`; skill → `paths.skill_dir`; context →
      `<contexts root>/<ref>/` (honours `[layout] contexts`); bootstrap →
      `paths.local_bootstrap_path`; recurring → the active parent dir;
      resource → `paths.resource_override_path`. Runtime caches
      (`paths.IGNORABLE_OVERRIDE_ENTRIES`) are not copied.
- [ ] Conflicts refuse before any write: any existing destination entry
      (file, dir, link), listing each conflicting path. The only exception is
      a recurring parent classified as a valid state-only carrier by
      `recurring_state.inspect_parent_dir`: fork converts it to a full
      definition by writing the packaged ticket's frontmatter and body above
      the blackboard fence followed by the carrier's existing blackboard
      region byte-for-byte, and keeps recognized runtime state (`retires.md`).
      An incomplete parent, a parked `_<name>/`, or both active and parked
      state refuses.
- [ ] Fork never edits `jobs.toml`, config or selection. Because a local
      definition with no `jobs.toml` entry is selected (`recurring._source_for`),
      the output states the job's resulting selection and, when it becomes
      enabled, that `<name> = false` under `[jobs]` keeps it off (owner,
      2026-11-14: no refusal needed).
- [ ] When the copied `ticket.py` is an edge shim whose module is completely
      forkable, the fork's `ticket.py` is the module's source (the real
      implementation), and the output says so. Otherwise the shim or recipe
      adapter is copied unchanged and the output states "implementation not
      forked: <reason>" — never claims a complete implementation fork.
- [ ] Ordering makes an interrupted copy visible: write every sibling first
      and the definition file (`ticket.md`, `SKILL.md`, workflow file)
      last, each with `atomicio.atomic_write_bytes`, so a partial copy is a
      definition-less directory that the existing resolvers already reject as
      a broken override.
- [ ] Never writes under the tasks root: existing (including running and
      parked) period tasks keep their frozen script and snapshot.
- [ ] After copying it prints the files written, what to edit, the
      `coga fork-copy <kind>:<ref>` command for each referenced definition that
      is still `stock`, and the return-to-stock steps.

Return to stock (documented, printed by `coga fork`, tested)

- [ ] Workflow/resource: delete the local file. Skill/context/bootstrap:
      delete the local directory. Recurring: replace everything above the
      blackboard fence in `ticket.md` with the exact carrier header from
      `coga/recurring/templates`, keep the blackboard and runtime state, and
      delete the other siblings. Frozen periods keep their own script until
      they finish. A fixture runs these steps and shows resolution back on the
      package with blackboard bytes unchanged.

End-to-end and distribution

- [ ] Peer review, from a wheel installed outside the source checkout into a
      fresh `coga init` repo: `coga fork code/with-review` (or
      `workflow:code/with-review`) leads to the workflow and its
      `code/peer-review` skill; `coga fork-copy workflow:code/with-review` and the
      printed `coga fork-copy skill:code/peer-review`; edit `peer-review` to
      `assignee: agent` and the skill text; a ticket created with that workflow
      freezes `checkout: reuse-required` for the step and launch (fake agent)
      reuses the recorded branch.
- [ ] Read-only installation: with the installed wheel tree made read-only,
      `coga fork-copy recurring:trim-log` produces a local `ticket.py` equal to the
      `coga_edge/trim_log.py` source; a marked edit to it is what a launched
      period runs; the installed tree's file hashes are unchanged.
- [ ] Upgrade: installing a newer wheel changes the stock definitions a repo
      resolves but not its forks; `coga fork` then reports the fork as
      `fork (modified)` relative to the new package.
- [ ] Coverage for local precedence, each broken-override shape, a custom
      contexts root, user alias overriding a default alias, alias to a kernel
      recipe, bootstrap and recurring siblings, carrier conversion, and the
      implicit enabling of a forked unselected recurring job.
- [ ] Native Windows receipt for the fork/read-only-install case per
      `coga-dev/testing`; no live definition mirror is created in this repo
      (`tests/test_packaging.py` stays green).
- [ ] Evidence reported per `coga-dev/microkernel/objectives`: lines added
      (script, aliases, tests, docs separately) versus instructions removed;
      the gain is one path replacing per-capability manual locate/copy
      procedures, not a core reduction.

### Proposed shape

1. **Dependency.** `launch --read-only` from
   `v1/microkernel/03-launch-decomposition` (PR #1233) must be on main
   first. If it is not, stop and report; do not reimplement it here.
2. **Command ticket** (package-owned, edge per the microkernel rule):
   `src/coga/resources/templates/coga/bootstrap/fork/ticket.md` owns the
   command contract (as `bootstrap/retire/ticket.md` does);
   `.../bootstrap/fork/ticket.py` implements it with `argparse`
   (`inspect`/`copy` subcommands, `--json`). It imports only shared core:
   `config.load_config(require_user=False)`; `paths` resolvers
   (`resolve_workflow_path`, `resolve_skill_path`, `resolve_context_path`,
   `resolve_resource_path`, the `*_path`/`bootstrap_*` helpers,
   `local_definition_entry`, `IGNORABLE_OVERRIDE_ENTRIES`);
   `tasks.resolve_bootstrap`/`resolve_task`/`read_ticket`;
   `recurring.resolve_template_source`; `recurring_state.inspect_parent_dir`;
   `workflow.Workflow`; `aliases.DEFAULT_ALIASES`/`BUILTIN_COMMANDS`;
   `runner.RECIPES` (names only); `atomicio`. No resolver logic is
   duplicated: the script asks the resolver what is selected and only
   computes the override destination from the same `*_path` helpers.
   Internal shape: `resolve_target(cfg, text) -> list[DefinitionRecord]`,
   `classify_script(path) -> ScriptKind` (AST only),
   `inspect_edge_module(path)`, `render_text`/`render_json`,
   `copy_definition(cfg, record) -> CopyResult`.
3. **Aliases.** Add `fork` and `fork-copy` to `aliases.DEFAULT_ALIASES` with
   the comment explaining the fixed read/write policy;
   `tests/test_aliases.py` covers them.
4. **Packaging.** Add the two files to `tests/required_package_resources.txt`.
5. **Docs (package-owned user topics)** — same PR:
   `coga/context-layout` (resolution section: discover with `coga fork`,
   override with `coga fork-copy`, return to stock); `coga/edge-code` ("Explicit
   local forks" uses `coga fork-copy recurring:<name>`); replace the manual
   *locate* and *create a fresh full fork* snippets in
   `edge-code/edge-code-upgrades.md` and the source-inspection pointer in
   `recurring/phone-home/operations.md` with the commands (the legacy
   adoption/migration procedure itself stays); `coga/workflows`,
   `coga/recurring/templates`, `coga/script-tickets` (point to the commands);
   `coga/extension-model` and `coga/cli` alias lists. Local
   `coga-dev/codebase` gets the new ticket in its source map.
6. **Tests.** `tests/test_source_command.py` for resolution/report/copy
   (in tmp repos built from the seeded fixture); extend
   `tests/test_edge_distribution.py` for the installed read-only wheel,
   upgrade and peer-review end-to-end cases.

### Out of scope

- Redesigning automatic publication. On a control checkout today the
  end-of-command sweep publishes a fresh fork with the ordinary launch; fork
  follows whatever the current rule is. The redesign is
  `redesign-coga-s-git-sync-around-explicit-session-e`.
- Forking under a new name (`--as`), copying referenced definitions in one
  operation (`--with-refs`), and a `--restore` operation (owner, 2026-11-14).
- Moving kernel recipes behind recipe-adapter shims to the edge — owned by
  `v1/microkernel/04-…`; this ticket only reports them honestly.
- Automatic merging of customized code with package updates; rewriting
  frozen or running periods; materializing the package at `coga init`.
- Changing `coga skill status`, `coga show`, or prompt composition.
- Forking or reclassifying built-in Typer commands.

## Context

Read `coga-dev/microkernel/objectives`, `coga-dev/packaging` and
`coga-dev/testing`. User owners under
`src/coga/resources/templates/coga/bootstrap/contexts/coga/` are
`context-layout`, `extension-model`, `edge-code` (including its upgrade
procedure), `workflows`, `script-tickets` and `recurring/templates`.

The launch sibling owns the generic stateless read/write dispatch distinction.
The checkout-policy sibling owns workflow declaration; the end-to-end peer-review
case joins these two capabilities. Recipe moves consume this forkability
requirement but own their job implementations and upgrade caller reconciliation.

### Premise refresh (2026-11-14, main `3b117b99c`)

- Checkout declaration shipped (`9aededac6`): `WorkflowStep.checkout` is
  parsed/frozen in `src/coga/workflow.py`, and packaged
  `code/with-review` declares `checkout: reuse-required` on `peer-review`.
- `launch --read-only` is implemented on branch
  `coga/v1-microkernel-03-launch-decomposition-6852fc` (PR #1233), not yet
  on main. Its draft contract already names this consumer
  (`inspect = "launch --read-only bootstrap/inspect"`) and requires mixed
  read/write commands to fix policy per alias — hence two aliases.
  It sets no marker the script can read, so `inspect` must itself write
  nothing; `copy` is reachable only through ordinary dispatch by alias.

### Code facts the implementer relies on

- `src/coga/paths.py`: `resolve_workflow_path` returns the local path if any
  entry exists there (the loader diagnoses it), else the bundled one;
  `resolve_skill_path` and `tasks.resolve_bootstrap` use
  `local_definition_entry(definition, owner=dir)`, which raises
  `LocalOverrideError` for a non-regular/dangling definition or supporting
  files without it — the basis for "broken" reports and for the
  definition-last copy order. `resolve_context_path` additionally applies
  `require_context_artifact` (symlink/tracking rules) at `cfg.contexts_root`.
  `resolve_resource_path` covers only the names in the top-level resource
  allowlist in the same module.
- `src/coga/recurring.py`: `resolve_template_source(cfg, name)` returns a
  `TemplateSource` (`definition_dir`, `origin` local/package, `state_dir`,
  `selection`, `reason`, `error`); `_source_for` selects a local definition
  with no `jobs.toml` entry as enabled, which is why fork reports the
  resulting selection. `recurring_state.inspect_parent_dir` classifies a parent as
  DEFINITION/CARRIER/STATE_ONLY/INCOMPLETE/ABSENT; `CARRIER_PREFIX` is the
  exact carrier header and `RUNTIME_STATE_FILES` the state kept beside it;
  `active_parent_dir(cfg, name)` is the destination. The carrier contract is
  owned by `coga/recurring/templates`.
- Shipped `ticket.py` shapes today: edge shims — `recurring/phone-home`,
  `recurring/trim-log` (import `main` from `coga_edge.phone_home` /
  `coga_edge.trim_log`; both modules import only `coga.*` plus stdlib and end
  with a `__main__` guard); recipe adapters — `recurring/skill-update`,
  `autoclose-merged`, `blocker-reminders`, `branch-sweep` (call
  `coga.runner.run_recipe`); full script — `bootstrap/retire/ticket.py`.
- Alias table: `coga.cli` merges `{**DEFAULT_ALIASES, **user_aliases}`;
  `recurring_runner` validates `{**DEFAULT_ALIASES, **cfg.aliases}`.
- Publication: the end-of-command sweep (`git.sync_coga_state`) publishes
  dirty eligible files under the Coga and contexts roots after state-changing
  commands; read-only launch never sweeps (`coga/state-publication`).

<!-- Ticket guide — keep this comment when filling in or updating the ticket.
It documents field shapes; these are examples, not values to copy into every
ticket. Omit optional fields and sections until needed. Editing rules come
from the base prompt; body regions from coga/tickets; blackboard conventions
(superseded designs, draft cleanup, oversized notes) from coga/blackboard.
Write requirements under ### subheadings of Description or Context; any other
level-two heading above the fence does not reach the launch prompt.

FRONTMATTER
The real values are in this ticket's YAML header. Required ordinary-ticket
keys are title, status, owner, and workflow. A minimal draft has workflow: null.

    title: Fix retry diagnostics           # What the work is called; identity comes from the file path.
    status: draft                          # CLI state: draft, active, in_progress, paused, blocked, done, canceled.
    owner: human-name                      # Accountable human; receives notifications and owner gates.
    agent: codex                           # Optional configured main agent; activation supplies the default if absent.
    contexts:                              # Optional facts to include in every launch; attach only what is needed.
      - service/retries
    skills:                                # Optional ticket-wide procedures, in addition to workflow step skills.
      - infra/testing-conventions
    workflow: code/with-review             # Draft reference or null; live tickets have the frozen mapping below.
    secrets:                               # Optional environment names mapped to references, never credentials.
      - API_TOKEN: env:LOCAL_API_TOKEN
      - SERVICE_KEY: op://automation-vault/service/api-key

The agent choice is not the current operator or the ticket interviewer.
Omit empty contexts, skills, and secrets lists. Each secrets entry has exactly
one unique name (no COGA_ prefix); env: reads the operator's environment and
op:// reads a 1Password item at launch, exposing the value under the left-hand
name. An unavailable reference prevents launch. Never put a literal secret here.

A workflow must be selected before activation. Creation with --workflow, or
activation of a draft reference, freezes its steps. CLI transitions manage step;
do not rewrite a live snapshot or advance it by editing YAML. Frozen example:

    workflow:
      name: code/with-review                # Selected workflow name.
      steps:
        - name: implement                  # Ordered step name.
          skills:                          # Optional procedures for this step; plural, never skill.
            - code/implement
          assignee: agent                  # Role: owner, agent, or other-agent (the configured peer).
          requires: branch                 # Optional completion gate: branch or pr.
    step: 1 (implement)                    # One-based position plus name; CLI removes this on completion.

An omitted step assignee inherits the previous role; the first defaults to
owner. The current step determines who holds the ticket. There is no top-level
assignment field. Removed keys slug, human, assignee, and watchers are invalid.
There is no execution-mode field: a sibling ticket.py supplies a script phase.

Repo extensions are string fields declared under [ticket.fields.<name>] in
coga.toml: description explains the field, values restricts its choices,
default seeds it, and required prevents activation while it is empty. Actual
values live below the extensions marker comment in the YAML header. Preserve
them; do not invent extension fields or change their definitions in config.

Machine-owned fields: delegate freezes a recurring parent's bootstrap/<name>
target; period_generation identifies its materialized run. Both belong only on
period tasks directly under tasks/recurring/. launch_generation is megalaunch's
session claim. Preserve these fields; do not add or clear them yourself.

BLACKBOARD (BELOW THE FENCE)
Keep current decisions and their reasons, verification, next actions, and
blockers here. Update current values in place instead of appending stale copies.

Optional ## Dev: branch: <name> when created; pr: <full /pull/ URL> when opened;
worktree: <path> only for a sandbox clone. One field per line, notes on separate
lines, omit unknown values. For multiple owned branches, the first branch is
the workflow branch.

Optional ## PR: one fenced YAML mapping of PR-preparation receipts (title,
author, head/base OIDs, review depth, files, review, checks). Record only actual
implementation and evidence, never placeholders; coga/pr-publication/
preparation owns the fields and the publishing workflow the review rules.

Optional ## Blockers and ## Blocker reminders are CLI-maintained. Preserve
blocker IDs, timestamps, actor names, resolved answers, and reminder fingerprints
with last_reminded timestamps; use lifecycle commands to block or resolve them.

Recurring parents (coga/recurring/<name>/ticket.md) take schedule and related
template settings owned by coga/recurring/templates; do not add them to an
ordinary ticket.
-->

<!-- coga:blackboard -->

## Dev

pr: https://github.com/FastJVM/coga/pull/1239
branch: coga/v1-microkernel-05-make-packaged-behavior-discove-156f8c


## Design session 2026-11-14 (attended, owner present)

Spec written above the fence. Owner decisions this session:
- Fork scope: one artifact per `coga fork-copy`, plus printed `coga fork-copy` hints for
  referenced definitions (no `--with-refs`, no `--as`).
- Return to stock: documented procedure printed by `coga fork`, verified by
  fixtures (no `--restore`).
- Publication: the problem is the sweep itself, not fork. Owner intuition is to
  return to "normal Git" with an explicit `coga sync` at session end; captured
  as draft `redesign-coga-s-git-sync-around-explicit-session-e` (to design, not
  decided). This ticket does not special-case fork's publication.

Hard dependency: `launch --read-only` (PR #1233, branch
`coga/v1-microkernel-03-launch-decomposition-6852fc`) is not on main.
**Owner decision 2026-11-15 (implement session): stack on #1233.** This branch
carries #1233's commit cherry-picked (`426a1c8f7` after rebase) under the
fork commit; this PR must not merge before #1233. If #1233 changes in review,
rebase this branch onto its final form (or onto main once merged; git drops
the patch-identical commit).

## Implement handoff 2026-11-15 (attended, owner approved result)

Commit `277f65c0e` "Add coga fork and fork-copy for packaged behavior" on
the branch (pushed). What changed:
- `bootstrap/fork/ticket.md` (contract) + `ticket.py` (argparse
  `inspect`/`copy`, `--json`): resolves typed refs or an untyped word
  (alias -> built-in -> task -> definition name), follows aliases, reports
  per-definition origin/selected/packaged/override/fork state/references,
  `ticket.py` classification by `ast` (edge shim / recipe adapter / full
  script) and edge-module forkability; copy writes definition-last, refuses
  conflicts, converts state-only carriers, expands forkable edge shims.
- Default aliases `fork` / `fork-copy` in `aliases.DEFAULT_ALIASES`.
- Docs: context-layout (new "Finding and forking packaged behavior"),
  edge-code + upgrades, workflows, recurring/templates, script-tickets, cli,
  extension-model, phone-home operations, coga-dev/codebase source map.
- Tests: new `tests/test_fork_command.py` (43), alias tests, packaging list,
  three installed-wheel cases in `tests/test_edge_distribution.py`.

Deviations from the spec (decide in review):
- Untyped word falls back to a definition name of exactly one kind, so
  `coga fork code/with-review` works as the acceptance case expects.
- Test file named `tests/test_fork_command.py` (repo naming rule), not
  `test_source_command.py`.
- `migration:locate` snippet kept in edge-code-upgrades.md: it is the tested
  input of the legacy guarded-replacement step; `coga fork` added beside it.
  Only the fresh template-fork snippet became `coga fork-copy` (period
  scripts still use the manual copy: fork-copy never writes periods).
- Peer-review launch-reuse is proven in-process (fake agent, real git);
  the installed-wheel case covers discovery, copy, edit and freezing.

Limitations / not done:
- No native Windows receipt (needs the Windows box per coga-dev/testing).
- Fork-state comparison is byte-exact: a CRLF checkout of a fork reads as
  `fork (modified)`.
- Size: ticket.py ~890 lines (778 non-blank/non-comment), ticket.md 125,
  tests ~785; docs +~60. Removed instructions: the fresh-fork cp snippet
  (partially) only. This is a new capability, not a core reduction; the
  owner's new draft `v1/why-is-the-code-so-big` is related.

## PR

```yaml
"title": "Add coga fork and fork-copy for packaged behavior"
"author": "claude/codex"
"author_evidence": "Claude (Claude Opus 5.5) implemented the feature in the attended\
  \ implement session. Codex authored the four approved review fixes in this peer-review\
  \ session. The patch-identical dispatch dependency belongs to PR #1233."
"head": "be2ee4d1f3693c9569df0304c6abdfacc3f2982a"
"base": "bf01531c818cc27add8d4b0ea3e87d63662ea0fb"
"depth": "deep"
"rationale": "Substantial new user-facing inspection and repository write path, stacked\
  \ on the still-open dispatch PR #1233. Merge #1233 first. Original implementation\
  \ independently reviewed; Codex fixes self-reviewed."
"implementation": "Adds a package-owned bootstrap/fork command ticket and two aliases\
  \ for read-only discovery and copying one artifact. Follows effective resolvers\
  \ and references, identifies implementations through AST, expands forkable edge\
  \ modules, preserves carrier state and executable attachments, and rejects traversal\
  \ refs. Includes patch-identical #1233 dispatch dependency as commit 18469b692."
"deviations": "Untyped names also resolve a unique definition kind to support code/with-review.\
  \ Tests are named test_fork_command.py. Legacy guarded migration and frozen-period\
  \ copy commands remain. Installed-wheel peer-review test covers discovery, editing\
  \ and freezing; complementary real-Git/fake-agent in-process test proves branch\
  \ reuse."
"limitations": "Must merge after #1233. Fork comparison is byte-exact, so CRLF copies\
  \ can report modified. Native Windows/macOS verification is deferred to release\
  \ under coga-dev/testing; this Linux receipt does not provide native evidence. No\
  \ second agent reviewed the Codex-authored fixes. This adds capability and makes\
  \ ownership discoverable; it does not reduce core code. Size follow-up: v1/why-is-the-code-so-big."
"files":
  "docs/contexts/coga-dev/codebase/SKILL.md": "Map the command ticket and shared readiness\
    \ helper to their source owners."
  "docs/contexts/coga-dev/internals/agent-spawn/SKILL.md": "Document shared agent\
    \ readiness from the stacked dispatch dependency."
  "docs/contexts/coga-dev/internals/state-publication/SKILL.md": "Document read-only\
    \ dispatch publication boundaries from the stacked dependency."
  "src/coga/aliases.py": "Expose fork and fork-copy with fixed read/write dispatch\
    \ policies."
  "src/coga/cli.py": "Withhold checkout, audit and sweep effects for read-only launch\
    \ (stacked #1233)."
  "src/coga/commands/launch.py": "Expose and forward read-only launch policy (stacked\
    \ #1233)."
  "src/coga/launch.py": "Dispatch bootstrap readers and share agent readiness (stacked\
    \ #1233)."
  "src/coga/launch_script.py": "Run read-only scripts without lifecycle or publication\
    \ effects (stacked #1233)."
  "src/coga/megalaunch.py": "Consume shared readiness without changing admission ordering\
    \ (stacked #1233)."
  "src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/SKILL.md": "Explain\
    \ the read-only exemption from checkout preparation (stacked #1233)."
  "src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md": "List\
    \ the new fork and fork-copy aliases."
  "src/coga/resources/templates/coga/bootstrap/contexts/coga/context-layout/SKILL.md": "Explain\
    \ discovery, local overrides and return to stock, linking the command contract."
  "src/coga/resources/templates/coga/bootstrap/contexts/coga/edge-code/SKILL.md": "Route\
    \ explicit implementation forks through fork-copy."
  "src/coga/resources/templates/coga/bootstrap/contexts/coga/edge-code/edge-code-upgrades.md": "Use\
    \ fork for discovery and fork-copy for fresh template forks; retain guarded legacy\
    \ migration and frozen-period copying."
  "src/coga/resources/templates/coga/bootstrap/contexts/coga/extension-model/SKILL.md": "List\
    \ discovery and fork commands in the extension model."
  "src/coga/resources/templates/coga/bootstrap/contexts/coga/launch/SKILL.md": "Document\
    \ read-only command dispatch (stacked #1233)."
  "src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/templates/SKILL.md": "Point\
    \ recurring customization to fork and fork-copy."
  "src/coga/resources/templates/coga/bootstrap/contexts/coga/script-tickets/SKILL.md": "Explain\
    \ read-only dispatch and discovering/forking script implementations."
  "src/coga/resources/templates/coga/bootstrap/contexts/coga/state-publication/SKILL.md": "Document\
    \ read-only dispatch withholding the state sweep (stacked #1233)."
  "src/coga/resources/templates/coga/bootstrap/contexts/coga/state-publication/launch-boundaries/SKILL.md": "Document\
    \ read-only dispatch outside ordinary launch publication (stacked #1233)."
  "src/coga/resources/templates/coga/bootstrap/contexts/coga/workflows/SKILL.md": "Show\
    \ discovery and copying of packaged workflows."
  "src/coga/resources/templates/coga/bootstrap/fork/ticket.md": "Own the discovery/copy\
    \ contract, including conservative shim classification and safe relative refs."
  "src/coga/resources/templates/coga/bootstrap/fork/ticket.py": "Implement resolver-based\
    \ inspection, AST classification and definition-last copying; preserve executable\
    \ attachments and reject traversal."
  "src/coga/resources/templates/coga/recurring/phone-home/operations.md": "Point operators\
    \ to source discovery through fork."
  "tests/required_package_resources.txt": "Require both package-owned fork ticket\
    \ files."
  "tests/test_aliases.py": "Verify the two fixed-policy alias expansions."
  "tests/test_cli.py": "Verify read-only sweep policy (stacked #1233)."
  "tests/test_edge_distribution.py": "Verify installed-wheel discovery, copying from\
    \ a read-only install, local period execution and upgrade behavior."
  "tests/test_fork_command.py": "Cover resolution, broken overrides, copying, carrier\
    \ restoration, customized checkout reuse and the four review fixes."
  "tests/test_launch_script.py": "Verify read-only admission, execution and absence\
    \ of lifecycle/publication effects (stacked #1233)."
  "tests/test_megalaunch.py": "Verify shared readiness and pre-publication refusal\
    \ ordering (stacked #1233)."
"review":
  "reviewer": "codex"
  "kind": "self"
  "status": "passed"
  "head": "be2ee4d1f3693c9569df0304c6abdfacc3f2982a"
  "base": "bf01531c818cc27add8d4b0ea3e87d63662ea0fb"
  "detail": "Direct review completed on the final diff, including the stacked dispatch\
    \ dependency. Codex independently reviewed Claude implementation and self-reviewed\
    \ its own fixes. Four findings resolved: lost executable bits, malformed ticket\
    \ reported healthy, overly broad shim detection, and traversal refs escaping the\
    \ repository. No unresolved must-fix findings. Plain CLI discovery and help output\
    \ driven manually; no raw-terminal UI introduced."
"checks":
- "command": ".venv/bin/python -m pytest -q -p no:cacheprovider --basetemp=/home/n/Code/coga-fork-peer-review-pytest-20261115"
  "status": "passed"
  "head": "be2ee4d1f3693c9569df0304c6abdfacc3f2982a"
  "base": "bf01531c818cc27add8d4b0ea3e87d63662ea0fb"
  "detail": "5032 passed, 33 skipped in 1206.86s (20m06s), Linux."
- "command": "PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m coga.cli fork workflow:code/with-review"
  "status": "passed"
  "head": "be2ee4d1f3693c9569df0304c6abdfacc3f2982a"
  "base": "bf01531c818cc27add8d4b0ea3e87d63662ea0fb"
  "detail": "Passed on the dirty checkout without TTY: inspected workflow, peer-review\
    \ skill, checkout policy and customization paths."
- "command": "PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m coga.cli fork --help"
  "status": "passed"
  "head": "be2ee4d1f3693c9569df0304c6abdfacc3f2982a"
  "base": "bf01531c818cc27add8d4b0ea3e87d63662ea0fb"
  "detail": "Passed, usage printed to stdout and exit 0."
- "command": "git diff --check"
  "status": "passed"
  "head": "be2ee4d1f3693c9569df0304c6abdfacc3f2982a"
  "base": "bf01531c818cc27add8d4b0ea3e87d63662ea0fb"
  "detail": "Passed."
- "command": "Native Windows/macOS verification"
  "status": "not-run"
  "detail": "Deferred to release per the 2026-11-12 owner policy in coga-dev/testing;\
    \ no native platform evidence claimed."
```

## Open Questions

None open. Resolved 2026-11-14 (owner): aliases are `fork` (read-only
inspection) and `fork-copy` (write); one alias cannot carry both dispatch
policies, and the owner preferred two plain aliases over a `--copy` argv
adapter. Unselected recurring jobs — no refusal, fork-copy reports the
resulting selection; `coga fork` exits 1 on broken definitions; edge-shim
expansion is the default for recurring forks.

## Peer review — completed (Codex, 2026-11-15)

Direct review **completed** at head `be2ee4d1f3693c9569df0304c6abdfacc3f2982a`,
base `bf01531c818cc27add8d4b0ea3e87d63662ea0fb`. Codex independently reviewed Claude's
implementation, then self-reviewed its own owner-approved fixes; no second
reviewer examined those fixes. No unresolved must-fix findings.

Resolved with regressions:
- Preserve POSIX executable attachment bits without copying read-only
  installation permissions into editable forks.
- Mark bootstrap/recurring YAML parse failures broken (exit 1).
- Require a plain main()/SystemExit(main()) guard before expanding an edge
  shim; custom guard behavior remains a full script.
- Reject absolute, drive-relative, backslash and dot-component refs before
  resolution/copying; invalid referenced refs are reported broken.
Blackboard byte-preservation concern dismissed after reading read_blackboard
(read_bytes/decode, no newline translation).

Full Linux check: `.venv/bin/python -m pytest -q -p no:cacheprovider
--basetemp=/home/n/Code/coga-fork-peer-review-pytest-20261115`: **5032 passed,
33 skipped in 1206.86s (20m06s)** on the final head/base above.
Focused regressions before the final traversal commit: 177 passed in 11.30s
(code subsequently committed unchanged). The interrupted earlier full run
is not a receipt. Historical implementation checks remain historical: the
implementer reported 4976 passed/33 skipped on pre-rebase tree 8a5665818,
and 199 focused passed on 277f65c0e; neither is re-stamped as current.

Manual plain CLI checks on final head: `PYTHONDONTWRITEBYTECODE=1
.venv/bin/python -m coga.cli fork workflow:code/with-review` and `... fork
--help` passed on the dirty checkout without TTY. Inspected workflow, skill,
checkout, override and customization output. No raw-terminal/pager UI added.
`git diff --check` passed. Native Windows/macOS deferred to release per
coga-dev/testing; no native receipt claimed.

Freshness: rebased unconditionally onto fetched main, preserving/restoring
the projected ticket byte-for-byte. Final fetch found main unchanged at the
base above. PR #1233 remains open at 0bf44d2a1ff5e5e846f29007f707c6d461cdee9e;
its stable patch-id equals this branch's dependency (18469b692),
46f0566827a807d5e35da017ff104fbc3f7b1066. **Merge after #1233**.

Size evidence: `git diff --numstat 18469b692..be2ee4d1f` (dependency
excluded; physical lines including blanks/comments): script +930/-0,
aliases +7/-1, command contract +130/-0, other docs +62/-10, tests and
resource manifest +834/-0. No implementation entrypoints, dependency paths,
or duplicate implementations removed. Legacy migration/period-copy commands
remain. Gain: one resolver-based discovery/copy path; no core reduction.
Deferred simplification: v1/why-is-the-code-so-big.

Branch pushed with `git push --force-with-lease` at be2ee4d1f.
Structured PR preparation validated through the publication formatter with
all 31 diff paths explained; recommendation deep. Next step is mechanical
PR opening; retain the merge-after-#1233 dependency notice.
