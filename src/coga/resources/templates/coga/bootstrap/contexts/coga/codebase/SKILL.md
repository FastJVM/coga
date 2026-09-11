---
name: coga/codebase
description: Where things live in the coga source tree, and how to run tests and validation. Read this before editing coga's own code.
---

# Coga codebase

The repo has two halves:

- **`src/coga/`** — the Python package. The CLI implementation.
- **`coga/`** — the core user-facing OS layout (config, tasks,
  skills, workflows, prompts, and contexts by default). `[layout] contexts`
  may place the contexts directory elsewhere in the checkout. This is what
  coga *operates on*, not coga itself.

Always be clear which half you're editing. They have different
review bars.

## Source layout

- `src/coga/commands/` — Typer entrypoints, one file per `coga
  <command>`. **Keep these thin.** No business logic.
- `src/coga/` (other modules) — testable logic. `compose.py`
  builds the prompt. `notification/` dispatches notifications with Slack as
  the first backend. `config.py` loads config. `runner.py` owns the fixed
  name-to-function registry behind `coga run`; recipes are ordinary
  importable functions in focused core modules, not discovered skill files.
  `task_env.py` builds the shared `COGA_TASK_*` contract for agents and
  deterministic subprocesses. `recurring_autofix.py` owns the sweep's run
  record and the post-run analysis call — the one text-only, PTY-less agent
  spawn in the tree, registered as the `autofix-analyze` recipe rather than
  added as a second launch seam. `launch_script.py` classifies and runs the
  reserved `ticket.py` sibling without importing edge code.
  `commands/launch.py` runs that deterministic phase before deciding whether
  to compose and spawn an agent; trailing launch args remain an ordered agent
  prompt block. Its strict publication invariants — recorded-checkout and
  PR-head proofs, leases, compare-and-set publication, compensation — are
  documented in the `coga/launch-internals` context, along with the recurring
  admission generations and the `requires: pr` gate's sync rules. Attach that
  context to any ticket changing those paths; `coga/architecture` deliberately
  keeps only the model. `commands/run.py` forwards ordinary trailing argv to
  `runner.py`.
  `commands/slack.py` keeps the explicit FYI command spelling.
  `commands/block.py` and `commands/unblock.py` own blocked-state
  handoffs. `commands/megalaunch.py` is the manual drain entrypoint;
  reusable drain logic lives in `megalaunch.py` and the drain order (age plus
  numbered sub-directories) in `service_order.py`. `bump.py` advances
  workflow steps and owns the one shared, pure operator resolver
  (`resolve_operator`) that every routing consumer reads — launch, transitions,
  script handoffs, status/show, notifications, and sweep eligibility. Nothing
  caches its answer: there is no stored assignment, so a new consumer must call
  the resolver rather than reading a field. `validate.py` checks repo consistency. `mark.py` owns the
  status transitions and splits each at one seam: `prepare_active` is the pure
  preparation boundary (validate the ticket, freeze its workflow ref, mutate an
  in-memory copy to `active`, write nothing) and `mark_active` is the durable
  wrapper around it that writes, validates, audits, and optionally syncs. The
  exception ladder divides along that seam, and the tuple
  `megalaunch._PREPARE_ACTIVE_ERRORS` encodes the division:
  `WorkflowMissing`, `WorkflowError`,
  `RequiredExtensionMissing`, `BlackboardNeedsSynthesis`, and
  `MainAgentUnavailable` are prepare-side
  refusals raised before any byte is written, while `TaskValidationError` comes
  from the post-write `assert_task_valid` and therefore belongs to the commit
  half alone. `prepare_active` also selects the main agent and re-derives the
  operator, so both land on the prepare side: a failed activation never writes a
  newly chosen agent to a real ticket. Two constraints a new caller must keep: megalaunch prepares on a
  *throwaway* copy (`_prepare_for_launch`), preflights the prompt, env, and
  agent off that prospective view, commits only after every refusal has passed,
  and then recaptures the ticket bytes and refuses if they moved — so a
  prepared-but-uncommitted `Ticket` never becomes the durable revision. And the
  dependency-drain call site activates *before* resolving open blockers on
  purpose: `mark_active` writes first so the blocker update can join the same
  mutation snapshot and exact control publication, leaving the next launch
  claim leasing resolved bytes instead of a local-only edit.
- `tests/` — pytest. Run with `python -m pytest`.
- `example/` — seeded fixture used by tests. **Update this when
  you change task layout, prompt composition, or workflow
  semantics** (CLAUDE.md rule).
- `docs/vision.md` — non-negotiables. See also `coga/principles`.

## What belongs in core vs a skill — the microkernel rule

Keep core (`src/coga/`) minimal, like a microkernel. Core holds **only two
kinds of code**:

1. **Genuine shared infra** — code with **≥2 real consumers**: the prompt
   composer, config loading, task/ticket IO, the launch machinery, the shared
   `## Dev` PR-link parsers and `gh` helpers in `autoclose.py`. If exactly one
   thing calls it, it is not shared infra.
2. **A reviewed, co-versioned command contract** — either a function in the
   deliberately fixed `coga run` registry, such as `open_pr.py` or
   `delete_task.py`, or a command whose contract names the package-private
   invariant or atomic transaction that an edge implementation using stable
   CLI/filesystem interfaces could not preserve. Python logic and inability to
   use a fixed alias are necessary to rule out alias sugar, but do not by
   themselves choose core over a command ticket or external CLI.

`coga megalaunch` (`megalaunch.py`) has no `RECIPES` entry and is the one
genuinely unclassified in-package implementation. Its placement is deferred to
a **parked** design, not an active one: `coga/tasks/v2/cleanup-core-commands/`
is one paused ticket (`launch-decomposition.md`) plus five drafts, and
`coga/tasks/v2/README.md` defines everything under it as real work deliberately
off the current execution path. Until that design is pulled forward,
`megalaunch` stays in core — read this as recorded status, not as a migration
in flight.

**Everything else stays at the edge.** A single-consumer helper may live beside
the ticket or skill that uses it and import **only shared core infra**. An agent
may invoke an ordinary attachment explicitly. A ticket-owned headless phase
uses the one reserved sibling `ticket.py`: launch subprocesses it before any
agent phase, while core still never imports from a ticket or skill directory.
No other filename changes dispatch. Deterministic behavior that needs a
repository-independent `coga run` argv/stdout/exit contract remains a fixed
`runner.RECIPES` entry in a focused `src/coga/` module; skills are never
executable launch plugins.

**"Backs a CLI command" is not by itself a pass into core.** First ask whether
it is just an alias to a launch target. If it owns Python logic, ask the separate
home question: which named package-private invariant requires co-versioning,
and why could stable CLI/filesystem interfaces not preserve it? Without that
proof, substantive logic belongs in a command ticket or external CLI. A
launch-target command is an argv rewrite in `[aliases]` (`dream = "recurring
launch dream"`, `chat = "launch bootstrap/orient"`), never a Typer command with
logic. The launch target itself may have a deterministic `ticket.py`; its scope
is that one selected ticket and it receives no operands in v1. A registered
`coga run` name is a deliberate package exception: its function has a public
argv, stdout/stderr, and integer-exit contract enforced by the closed package
registry. The fixed-path ticket classifier does not extend or discover entries
in it.

**The consumer test decides the split, and it can keep a symbol in core.** When
an edge implementation moves out, any helper it shares with another core
consumer stays — moving it would force core to import from a ticket or skill
directory, which is exactly the anti-pattern this rule forbids. The registered
`autoclose`, `blocker-reminders`, and `branch-sweep` implementations stay in
core for the different reason above: they are fixed `coga run` commands. Their
skills are invocation contracts and contain no executable Python.

PR #517 first exposed the line by moving open-pr's former edge implementation
out of core. PR #585 later turned `open-pr` into a registered command implementation,
so the same test placed it back in core under exception 2, and it now lives
there as the registered `open-pr` recipe (`open_pr.py`) — the fixed name is the
contract, so the implementation is importable. `delete-task` followed the same
path out of its former edge helper. The fixed `coga run` registry applies that
exception without turning skills into a plugin system. This stated rule
supersedes the softer "extend at the edges, not the core" phrasing.

## coga layout

```
coga/
  coga.toml             ← shared config (committed)
  coga.local.toml       ← machine-local (NEVER committed; user, agent types)
  context.md             ← repo-context layer of the composed prompt
  recurring/<name>/      ← recurring task template directories (ticket.md,
                           plus the exact sibling ticket.py when the job is
                           deterministic — copied into every period task;
                           history in the repo-global coga/log.md)
  tasks/<slug>/          ← directory-form ticket.md plus optional attachments;
                           exact sibling ticket.py is its deterministic phase
  tasks/<dir>/.../<slug>/ ← tickets in sub-dirs at any depth (ref'd by path)
  skills/<ns>/<name>/    ← project-local process knowledge / overrides
                           (installer-managed imports land flat: skills/<ref>/)
  contexts/<ns>/<name>/  ← default project-local domain knowledge / overrides
  workflows/<ns>/<name>.md ← step definitions (local-first over bootstrap/workflows/)
  .agent-skills/         ← generated local-plus-bundled skill view for agents
```

`<ns>/<name>/` is the convention for skills this repo *authors* — `code/`,
`coga/`, `direct/`, `marketing/`, and the repo-authored members of `browser/`.
It is not a requirement, and it is not the only shape in the tree. Four shapes
coexist under `coga/skills/`:

- **Repo-authored, namespaced** — `code/`, `coga/`, `direct/`,
  `marketing/write-post`, and `browser/dochub`; `_template/` sits beside them
  as the starter directory to copy. DocHub's Coga ref is `browser/dochub`,
  derived from that directory path, while its portable Agent Skills metadata
  deliberately keeps the standards-valid leaf `name: dochub`.
- **Installer-managed, flat and GitHub-backed** — `coga skill install` lays a
  Coga-managed skill down flat at `coga/skills/<ref>/` under its upstream ref
  name, so this repo also carries seven flat `google-agents-cli-*` directories,
  declared in `src/coga/resources/managed-skills.toml`. That file is the list
  of *optional GitHub refs `coga init` tries to fetch*, not the membership test
  for the flat shape — and **init is the only reader**:
  `install_managed_skills` / `reconcile_managed_skills` are called from
  `commands/init.py` alone. `update_skills` enumerates the skill directories
  that already exist on disk and delegates them to `gh skill update`; it never
  loads the manifest. A pack whose optional install failed at init (or that was
  later removed) is therefore **not** restored by `coga skill update --all` or
  the weekly job — it stays absent until someone reinstalls it explicitly — the directories themselves carry no Coga provenance
  file, because `gh skill` keeps its own metadata and `coga skill update`
  delegates their refresh to `gh skill update --dir coga/skills --all`.
- **Installer-managed, flat and URL-backed** — `coga skill install-url` lands
  the same flat `coga/skills/<ref>/` placement but marks it with a
  `.coga-source.json` (`schema: coga.skill-source.v1`) recording
  `source_type: "url"`, the `source_url`, source/tree digests, an `include`
  allowlist, and `local_adaptation_notes`. `clarity/` is the checked-in
  example, and it is deliberately **absent** from `managed-skills.toml`: an
  operator installed it directly. Its refresh posture differs from the
  GitHub-backed form — `coga skill update` walks `.coga-source.json` in Coga's
  own code rather than delegating to `gh`. **The `include` allowlist is inert
  documentation, not behavior**: `include` is never read anywhere in
  `skill_manager.py`. `_update_url_skill_dir` compares digests only — it
  materializes the complete upstream tree and then either reports a
  `conflict`/`skipped-local-adaptation` (when the installed tree no longer
  matches `installed_tree_digest`) or replaces the directory with that complete
  tree. So a deliberate pruning of upstream scaffolding is *not* reproduced on
  update: it either blocks the update as a local adaptation, or is undone
  wholesale, restoring every path the operator meant to exclude. Reproducing a
  pruning from the recorded allowlist is unimplemented work, not current
  behavior. `coga skill install-local` is a third installer path
  and is updated by neither: `gh skill` records it as `local-path` and skips
  it, and Coga's URL updater does not consume that metadata. **The presence of
  `.coga-source.json` — not an entry in `managed-skills.toml` — is what tells
  you a flat directory is on Coga's own update path.**
- **Hand-vendored upstream skills, verbatim or adapted** — committed under a
  namespace and carrying their upstream source, license, and modification /
  refresh record in `ATTRIBUTION.md` or `NOTICE.txt` plus `LICENSE.txt`.
  `anthropic/skill-creator/` is a verbatim pinned copy;
  `browser/playwright/` is an adapted derivative of
  `microsoft/playwright-cli` with a wrapper and local references. Neither is in
  `managed-skills.toml` and neither carries `.coga-source.json`: no installer
  placed them and none updates them.
  Refreshing a verbatim copy means re-copying the reviewed upstream revision;
  refreshing an adapted copy also means deliberately reapplying and reviewing
  its recorded local modifications. Preserve a standards-valid leaf `name:`
  from upstream when applicable; Coga derives the namespaced ref from the
  directory path, and a slash does not belong in upstream leaf metadata.

Nothing installs a skill's dependencies on its behalf — Coga builds no
environment to install them into — and two different declaration forms show up
in the tree, only one of which is a Coga convention:

- **Coga's convention: a `requirements.txt` beside the `SKILL.md`**, which the
  operator installs into whatever Python runs the script. This is the shape to
  write and the one a failing skill should name. Note that **no skill under
  `coga/skills/` actually carries one today**, so it is a convention with no
  in-tree example yet, not an observed pattern.
- **Upstream `metadata.requires.bins` / `metadata.requires.install` frontmatter
  blocks**, present in each of the seven managed `google-agents-cli-*` packs.
  **Coga reads these nowhere** — no code path parses `metadata.requires`, so
  they are documentation the reading agent may act on, never something the
  installer or launch honors. Do not add one expecting Coga to enforce it.

Skill resolution reads the directory path in all four cases. Prefer a
namespaced directory for anything you write, expect the flat form for anything
an installer imported, and use a namespaced directory plus attribution,
license, and modification history for anything you vendor by hand.

Repo-authored namespaced skills normally use the Coga ref
(`name: <namespace>/<name>`) established by the authoring template. A skill
also intended to satisfy the portable Agent Skills metadata grammar may keep a
standards-valid leaf `name:` while Coga derives its namespaced ref from the
directory path; DocHub is the checked-in example. Flat installer-managed
imports, GitHub- and URL-backed alike, retain their upstream metadata. A
hand-vendored import follows the same portable rule: preserve its
standards-valid upstream leaf `name:` when applicable even though Coga derives
a namespaced ref from its directory path, and make adaptations explicit in its
notice.

**A Coga-managed pack is refreshed only by `coga skill update` — never by the
pack's own upstream installer.** The weekly `recurring/skill-update` job runs
`coga skill update --all --pr` so every refresh lands as one reviewable PR.
Some upstream packs instruct the reading agent to bootstrap themselves anyway:
`coga/skills/google-agents-cli-workflow/SKILL.md` says to run
`uvx google-agents-cli setup` (twice) and `agents-cli setup --skip-auth`.
Inside this repo, following that would install a second, unmanaged copy of
those skills and bypass the reviewed weekly job entirely. That file is
upstream-owned and gh-managed, so the correction cannot be a local edit to it —
it has to be known here.

File-form `tasks/<slug>.md` tickets cannot carry attachments and therefore
cannot be script-backed. In a directory-form ticket, only `ticket.py` is
reserved for direct launch. A `run.py`, test, or other executable attachment is
untouched by the classifier and may still be invoked explicitly by agent
instructions. Coga's own bundled ticket scripts are exercised from `tests/`
against `example/`; a user repo may keep its script tests beside the ticket,
but Coga neither discovers nor runs them.

Coga resolves skills and contexts from project-local roots first — skills from
`coga/skills/`, contexts from the configured contexts directory
(`coga/contexts/` by default) — then from the package-backed bootstrap roots
inside the installed `coga` package. It
does the same for bundled reusable workflows and stateless bootstrap launch
tickets. `coga/bootstrap/` is not materialized into working repos. Claude Code
and Codex are pointed at the generated `coga/.agent-skills/` view, which
exposes the same effective local-plus-bundled skill set. Optional Coga-owned
domain skills are declared in `src/coga/resources/managed-skills.toml` and
installed into `coga/skills/` through the public skill installer during
init/update; they are not copied from the template tree.

## Authoring bundled batteries

Bundled (package-backed) core skills, contexts, and reusable workflows are
authored in the *source* tree under
`src/coga/resources/templates/coga/bootstrap/{skills,contexts,workflows}/`,
not in a live `coga/bootstrap/` working-tree mirror. The packaged resources
are the source of truth and runtime resolvers read them directly after checking
project-local overrides. Optional domain skills belong in a published skill
source plus `src/coga/resources/managed-skills.toml`, not under the packaged
template payload.

**Editing a bundled workflow changes what *this* repo freezes, not only what
downstream repos get.** `paths.resolve_workflow_path` is local-first: a live
`coga/workflows/<name>.md` wins, and only when none exists does it fall back to
the packaged `bootstrap/workflows/<name>.md`. This repo has **no live
`coga/workflows/code/`**, so every `code/*` workflow — `design-then-implement`,
`with-review`, `with-self-review` — resolves to
`src/coga/resources/templates/coga/bootstrap/workflows/code/*.md`, and that is
the file `mark_active` freezes into Coga's own future tickets. The other
direction holds too: a live `coga/workflows/<name>.md` shadows a packaged copy
of the same name, so editing the packaged one changes nothing here. General
rule, and it holds for skills and contexts too: **a live
`coga/<kind>/<name>` overrides the bundled copy, and where no live copy exists
the packaged file *is* what this repo resolves and freezes.** Check which side
is live before assuming an edit is downstream-only.

Three sharp gotchas live here:

- **Do not *repair* bundled resources by copying them into
  `coga/bootstrap/`.** If `bootstrap/orient`, `bootstrap/ticket`, a bundled
  skill, a bundled context, or a bundled `bootstrap/workflows/*` workflow
  cannot be found, the fix belongs in package resources, package data, or the
  local-then-package resolver — a repo-local mirror hides the packaging bug
  and will drift. *Deliberate* authoring under `coga/bootstrap/` is
  sanctioned and resolved local-first, exactly like skills/contexts: a repo
  mints its own command ticket (`coga/bootstrap/<verb>/ticket.md` plus an
  `[aliases]` line) or intentionally overrides a shipped bootstrap ticket.
  The line is intent — new/overriding behavior you own, never a copy standing
  in for a broken package.
- **Skill Python deps via `requirements.txt`.** A skill declares its
  dependencies in a `requirements.txt` beside its `SKILL.md`, and the operator
  installs them into whatever Python runs that skill's script. Coga does not
  install them: it builds no environment to install them into, and a skill
  script's `#!/usr/bin/env python3` resolves through the operator's own PATH.
  A skill whose import fails says which `requirements.txt` to install. This is
  the convention to write, but nothing in `coga/skills/` carries one yet, so do
  not go looking for an example. The declarations that *are* in the tree are
  upstream `metadata.requires.bins` / `metadata.requires.install` frontmatter
  blocks in the seven managed `google-agents-cli-*` packs, and Coga reads them
  nowhere — they inform the reading agent and nothing else.
## Wheel packaging: force-include vs the package walk

`[tool.hatch.build.targets.wheel]` ships pure-data skill/context dirs (no
`.py` files) two ways, and they can collide. The `packages = ["src/coga"]`
filesystem walk and an explicit `force-include` of a template dir (e.g.
`skills/_template`) both try to add the same file — hatchling treats them as
two archive entries at one path and aborts:

```
ValueError: A second file is being added to the wheel archive at the same
path: `coga/resources/templates/coga/skills/_template/SKILL.md`.
```

Two non-obvious traps make this a clean-checkout-only failure that hides in dev:

- **It only fails on a pristine tree.** On a dev tree, `coga init` has created
  gitignored symlink views under the templates tree
  (`.agent-skills/`, `.claude/skills/`, `.codex/skills/`); hatchling's walk
  dedups the collision away through them, so the build succeeds. A fresh
  `git clone` / `git worktree` (what a release or `pip install git+…` uses) has
  no symlinks, so the collision is fatal. Always verify a packaging fix against
  **both** tree shapes.
- **The only wheel-building test needs a build backend in the venv.**
  `tests/test_packaging.py::test_wheel_includes_bootstrap_batteries` shells out
  to `python -m pip wheel --no-build-isolation --no-deps .` and asserts exit 0
  before checking the archive's names. There is no `importorskip` guard: with no
  `hatchling` in the venv the build fails and the test **fails** rather than
  skipping — loud, but as environment noise that reads like a packaging
  regression. Keep `hatchling` a tracked **dev/test** dep
  (`[project.optional-dependencies].test`, never runtime `requirements.txt` —
  coga never imports it at runtime) so a failure here means what it says.

Fix shape: exclude the colliding dir from the walk (`exclude` glob) and let the
`force-include` be its single deterministic shipper — mirroring the existing
`bootstrap/` exclude+force-include pairing. Don't just drop the force-include:
the walk silently omits pure-data (no-`.py`) skill dirs on some trees, so the
force-include is what guarantees they ship.

## Daily commands

- Install editable with declared test tools: `python -m pip install -e ".[test]"`
- Run CLI: `coga --help`
- Tests: `python -m pytest`
- Validate config + tasks: `coga validate --json`
  (or `python -m coga.validate --json` if `coga` isn't on PATH).

If edits to `src/coga/` (especially the prompt templates under
`src/coga/resources/`) don't appear when you run the CLI, the venv likely
has a non-editable install.
Reinstall against the venv that backs your `coga` shim:
`<that venv's python> -m pip install -e .` from the repo root.

**Run the suite with an explicit `PYTHONPATH` whenever you are not in the
primary checkout — this is the default, not a recovery step.** A *healthy*
editable install is the trap: its `.pth` names one absolute path, the primary
checkout's `src`. Run `python -m pytest` from a feature worktree and pytest
collects that worktree's `tests/` while `import coga` resolves to the primary
checkout's unchanged package. Nothing errors; the suite is simply green against
source you did not edit, and a real regression in your branch is invisible.
Point the import path at the checkout you actually mean:

```
PYTHONPATH=$PWD/src python3.12 -m pytest
```

The same command is also the recovery for the sharper failure mode, where an
editable install's `.pth` points at a worktree that was later deleted: then
`coga` and `import coga` are unimportable and pytest fails to even collect.
Reinstalling fixes that one, but the same explicit `PYTHONPATH` runs the suite
now and is the right spelling in both situations.

Two non-obvious requirements:

- **`PYTHONPATH` must be absolute.** Some subprocess tests run from a different
  cwd, so a relative `src` breaks them.
- **Use an explicit 3.11+ interpreter — don't trust the default `python3`.**
  coga needs `tomllib`, stdlib only on 3.11+, but the ambient `python3` on
  these machines is often 3.9. Name a new-enough interpreter directly, e.g.
  `PYTHONPATH=$PWD/src python3.12 -m pytest`, rather than relying on `python3`
  (which is often 3.9 on these machines).

### CI posture: publish-only release workflow, no test gate

Do not re-derive this from `.github/`; it is recorded here so verification
plans start from the real premise.

- **The only GitHub Actions workflow is `.github/workflows/release.yml`, and it
  is publish-only.** It triggers on a published GitHub Release or a manual
  `workflow_dispatch`, runs `uv build`, runs `twine check` on the built
  artifacts, and publishes to PyPI (or TestPyPI for a manual dry run) via
  Trusted Publishing. `twine check` is the one automated check that exists,
  and it checks package metadata, not behavior. One-time setup and the
  release procedure are in `docs/releasing.md`.
- **There is no PR or push test job.** Nothing runs `pytest` or
  `coga validate` on any branch, PR, or tag. The local suite plus
  `coga validate --json` *are* the release gate: a release tag ships whatever
  the publisher's local run happened to cover. Because of that, a verifier
  (self-QA, peer review, or a release cut) must state the exact commands they
  ran and the resulting counts — for example
  `PYTHONPATH=$PWD/src python3.12 -m pytest` → `N passed, M skipped` — rather
  than "tests pass". A verification claim with no command and no count is not
  evidence here, since no CI log exists to fall back on.
- **The clean-checkout-only wheel collision above has no automatic PR or
  push gate.** `release.yml` builds from a pristine checkout and can catch the
  collision before uploading, but it runs only when a GitHub Release is
  published or the workflow is manually dispatched. There is no automatic
  build on a PR, push, or tag to catch it earlier. Verify packaging changes
  against a fresh `git clone` / `git worktree` by hand before tagging.

`coga/tasks/v2/minimal-ci-run-pytest-on-prs-and-tags.md` is the parked design
that would change this posture. When it lands, update this subsection.

## Installed-versus-source skew warning

`coga launch` and `coga validate` perform a warn-only diagnostic when they
operate on a Coga source checkout. The check compares the installed package's
file mtime with the latest committed change under `src/coga/`; if source is
newer, stderr names both timestamps and recommends upgrading or reinstalling
Coga. It never blocks the command and silently skips non-Coga repos, missing
git metadata, and implausible package timestamps.

A true editable source install is skipped even when its package comes from a
different checkout: package code under that checkout's `src/` is already live
source, whereas a frozen venv copy inside a checkout is still eligible for the
warning. Interpret the signal as a diagnostic rather than proof of skew. A
future-dated commit can cause a harmless clock-skew warning, and uncommitted
`src/coga` edits are invisible because the source side intentionally uses git
commit time.

## Sandbox and cross-machine dev loop

Running the suite or CLI inside a restricted agent sandbox (e.g. Codex's) hits
recurring walls that don't appear on a normal dev machine:

- **`codex review --base main` fails in-sandbox.** The app-server is read-only
  there, so the review can't complete. Rerun it unsandboxed.
- **Git sync operations fail when the sandbox can't write `index.lock`.**
  State-changing commands such as `coga create`, `coga bump`, and
  `coga mark ...` commit task/log changes through git sync, so they can error
  inside a sandbox that forbids creating `.git/index.lock`. Rerun those
  transitions unsandboxed (or grant `.git` write access).
- **Feature checkout creation can use an independent clone.** If
  `git worktree add` cannot create a branch lock because the primary `.git` is
  read-only, make a `git clone --no-hardlinks` under `/tmp`, repoint its
  `origin` to the real remote, fetch the control branch, and work there. Record
  that repo path as the ticket's `worktree:`; do not force writes through the
  protected metadata or stop at a conversational request when the clone
  fallback is available.
- **Scope validation with `--task`.** A repo-wide `coga validate` reports
  pre-existing, unrelated drift that isn't yours to fix and drowns the signal.
  `coga validate --task <slug>` is the meaningful per-ticket check.

### Which checkout you invoke coga from

Coga reads and publishes state through the checkout the command runs in, so the
wrong checkout silently produces wrong results in both directions:

- **A state-changing coga command run from a feature worktree sweeps your
  in-flight `coga/` edits onto the control branch.** The CLI's exit-boundary
  sweep (`sync_coga_state`) commits *everything* dirty under `coga/` and lands
  it on `main` — including the context and skill edits that are the doc half of
  the PR you have not opened yet. This really happened: `coga run` from a
  feature worktree pushed five `coga/` context/skill files to `origin/main` as
  `3779d340` before the PR existed, leaving `main`'s contexts describing
  behavior `main`'s code did not have, and leaving those files out of the PR
  diff entirely. Commit in-flight `coga/` edits onto the feature branch before
  running any state-changing coga command there, or expect them to reach `main`
  out-of-band. `cli._NON_SWEEPING_COMMANDS` is `status`, `show`, `validate`,
  `usage`, `init`, `uninstall`, and only the first four of those are read-only
  in the ordinary sense.

  **That list is not the whole exclusion set, so do not read it literally.**
  `_should_sweep_coga_state` also declines on options and subcommands:
  `--help`/`-h` anywhere, `bump --backward` / `--to` (a rewind publishes
  through its own scoped guard, and a refused one deliberately stays dirty),
  `recurring --all` (the parent dispatcher owns no repo state; each child
  sweeps its own repo), `secret` in every form, and any `skill` / `mark` /
  `recurring` subcommand outside its sweeping set. So `launch`, `megalaunch`,
  `run`, `create`, a plain `bump`, and the mutating `mark` /
  `skill` / `recurring` subcommands sweep — but a dirty `coga/` edit left
  around one of the excluded invocations stays local.
- **`coga launch <target> --prompt-report` is not read-only, despite reading
  like a diagnostic.** `cli._should_sweep_coga_state` classifies on `argv[1]`
  alone, and `launch` is in `_SWEEPING_COMMANDS`; the flag never reaches that
  decision. The report path itself also writes, calling
  `_refresh_agent_skills_for_launch` to regenerate `coga/.agent-skills/` before
  composing. So "just show me the prompt" publishes Coga state from whatever
  checkout it ran in — it has already committed three live doc edits straight to
  `origin/main`. To inspect composition in place with no writes at all, call
  `compose.compose_prompt_report` / `compose.compose_prompt` directly instead of
  going through the CLI.
- **Launch and megalaunch compose prompts from whatever the invoking checkout
  holds.** Run them only from a control checkout freshly synced to
  `origin/<control>`. A checkout parked behind `main` builds the prompt from a
  stale ticket copy and stale source, and will re-dispatch work that already
  merged — megalaunch re-picked a ticket eight minutes after its PR merged
  because the invoking checkout sat on a feature branch 75 commits behind
  `origin/main`, and composed from source that still contained the code the
  merged PR had deleted. The state-regression guard protects the control branch
  from the resulting write; it does not protect your session from the wasted
  run, and a stale `coga/log.md` in that checkout is a live hazard for any sync
  from it.

## Gotchas when editing coga's own code

- **Calling a Typer command function in-code passes `OptionInfo` sentinels.**
  A `@app.command` function only receives its real option *defaults* when Typer
  parses an actual CLI argv. Call it from Python — one command invoking
  `launch.launch(...)`, a recurring launcher running launch in-process — and any
  parameter you don't pass arrives as its `typer.Option(...)` sentinel (an
  `OptionInfo` object), **not** the default value. Downstream that explodes:
  `float >= OptionInfo` → `TypeError` in `repl_supervisor`'s timeout comparison,
  which crashed the on-demand launchers (`coga dream`, `coga recurring launch
  <x>`) and the old `setup.py`. Fixes: pass concrete values for **every**
  parameter, or (better) call a non-Typer helper so a newly-added option can't
  silently become a sentinel. An **alias** (argv rewrite, e.g.
  `build = "launch coga-build"`) sidesteps the bug entirely — it dispatches
  through real CLI parsing, so Typer fills every default.

- **Ask for the branch with `git branch --show-current`, never
  `rev-parse --abbrev-ref HEAD`.** When a tag shares a name with the branch,
  `rev-parse --abbrev-ref HEAD` disambiguates by returning `heads/<name>`
  instead of `<name>`. Any equality test against the control branch then
  silently fails — a checkout genuinely on `main` compares as `heads/main` and
  is treated as a feature checkout, or the reverse, depending on which side the
  guard protects. `branch --show-current` is unambiguous and returns empty on a
  detached HEAD, which is the honest answer. **Fail closed when the probe
  itself errors**: a non-zero `git` exit must not collapse into the empty string
  and be read as "not the control branch" — decide explicitly what an unknown
  branch means and refuse rather than assume. Today the reasoning survives only
  as a comment on `branchcleanup._current_branch`, which uses the correct
  spelling; `branchsweep._current_branch` and the two `rev-parse --abbrev-ref`
  call sites in `open_pr.py` still use the shadowable one and still map a failed
  probe to `""`.

- **Tests must not pin to live dogfooded state.** Coga dogfoods itself, so files
  under `coga/` mutate as the repo is used. A test that compares the live
  `coga/` copy against a packaged template, or asserts a baked-in value, fails as
  the live value drifts — the `recurring/autoclose-merged` serviced-period
  date did exactly this, independently re-diagnosed as a "pre-existing failure"
  across at least four dev tasks (a recurring verification tax). Strip
  runtime-mutated fields (run cursors, timestamped log lines — see
  `_strip_runtime_state`) or freeze the period before comparing; assert
  structure, not a hardcoded date.

- **Fixture shell scripts must be portable.** A test that writes a shell script
  for a subprocess runs on whatever `sh` the developer has. GNU-only
  `sed -i 's/…/…/'` fails on BSD/macOS, where `sed` reads the next token as the
  mandatory backup suffix. Prefer Python or a portable
  `sed … > tmp && mv tmp file` in fixture scripts, and treat any GNU-only flag
  (`sed -i`, `readlink -f`, `date -d`) as a platform bug waiting for the first
  non-Linux contributor.

- **Subprocess tests must scrub inherited launch metadata.** A pytest run inside
  `coga launch` inherits the outer session's `COGA_TASK_*` variables. A
  fixture worker that receives those values can write its report
  into the live outer ticket instead of its temporary task. This is now
  enforced, not remembered: `conftest.py::_clear_supervised_session_env` clears
  `LAUNCH_OWNED_ENV`, which is derived from `coga.task_env.TASK_ENV_KEYS`, so a
  new launch-owned variable is covered without a second edit — add it to
  `TASK_ENV_KEYS` and both sides follow. Do not re-introduce per-test
  `monkeypatch.delenv` opt-outs for that namespace; `test_env_isolation.py`
  proves the guard end to end by re-running one of its own tests in a child
  `pytest` with the whole namespace poisoned. On the reading side,
  `blackboard_from_env(coga_os_root)` refuses a blackboard outside the
  `tasks/` tree of the root the recipe is operating on — a report belongs to the
  repo under test, so pass the discovered root at every recipe call site. If
  the target root cannot be discovered, the writer fails closed to stdout
  rather than trusting an inherited path.

- **`coga.config` and `coga.commands.launch` share one `subprocess` module
  object.** Patching `coga.config.subprocess.run` and
  `coga.commands.launch.subprocess.run` separately collides (they are the same
  object). Use a single argv-dispatching mock on `coga.config.subprocess.run`.

- **A rebase carries a fix through a rename — never into a twin created fresh
  in the same commit.** The live↔packaged pattern (a file under `coga/` and its
  copy under `src/coga/resources/templates/coga/bootstrap/`) is exactly this
  shape. When a branch *moves* one copy, git's rename detection replays later
  `main` fixes onto it; when the same commit *creates* the other copy from
  scratch, that copy has no rename to follow and silently keeps the pre-fix
  bytes. This really happened: `main`'s `TERMINAL_STATUSES` fix (canceled
  tickets are terminal, not just `done`) reached the live branch-sweep copy and
  missed the packaged one — a regression that would have deleted branches
  recorded on canceled tickets. A clean rebase and a green suite both reported
  success. **After any rebase that touched a live/packaged pair, re-diff every
  pair by hand** and sync packaged from live. `tests/test_packaging.py` now
  derives the pairs rather than listing them: every packaged file whose live
  counterpart exists at the mapped path (`templates/coga/<path>` ->
  `coga/<path>`, and `templates/coga/bootstrap/{contexts,skills,workflows}/
  <path>` -> `coga/<area>/<path>`) must be byte-identical, so a new twin is
  covered the moment it exists and there is nothing to register. Discovery
  excludes local installation directories (`.coga/`, `.venv/`), agent-tooling
  state (`.agent-skills/`, `.claude/`, `.codex/`), bytecode caches, and
  `coga.local.toml`; those are not shipped twins. A deliberate difference goes
  in `INTENTIONALLY_DIVERGENT_TWINS` with its reason, and the
  suite fails if that entry outlives the divergence. That catches the drift
  after the fact; it does not catch it during the rebase, so still re-diff.

- **A recorded "rebases clean" has an expiry.** A design step that measured
  drift (`git diff --stat <merge-base>..main` over the branch-touched files, and
  found it empty) is describing one instant. The
  `agree-the-core-vs-skills-move-list-then-execute` design recorded exactly that
  and, by implement time, `main` had advanced **417 commits** and the rebase
  took four conflicts. Re-measure at implement time; never let an inherited
  "rebases clean, no conflicts expected" note stand in for running the rebase.

## Secrets

Never commit. Shared config goes in `coga.toml`; per-machine paths
and credentials go in `coga.local.toml` via `env:VAR_NAME`
references. Secrets get injected as env vars at launch time by
`coga launch`.

## What this context does NOT cover

- The mental model of coga primitives — see `coga/architecture`.
- The principles for *why* the codebase is shaped this way — see
  `coga/principles`.
