---
name: coga/codebase
description: Where things live in the coga source tree, and how to run tests and validation. Read this before editing coga's own code.
---

# Coga codebase

The repo has two halves:

- **`src/coga/`** — the Python package. The CLI implementation.
- **`coga/`** — the user-facing OS layout (config, tasks,
  skills, workflows, contexts, prompts). What coga *operates on*,
  not coga itself.

Always be clear which half you're editing. They have different
review bars.

## Source layout

- `src/coga/commands/` — Typer entrypoints, one file per `coga
  <command>`. **Keep these thin.** No business logic.
- `src/coga/` (other modules) — testable logic. `compose.py`
  builds the prompt. `notification/` dispatches notifications with Slack as
  the first backend. `config.py` loads config.
  `commands/launch.py` runs agents and composes trailing launch args into an
  ordered prompt block; `commands/launch_script.py` owns the separate
  `COGA_ARG_1..N` + `COGA_ARGC` environment channel for scripts.
  `commands/slack.py` keeps the explicit FYI command spelling.
  `commands/block.py` and `commands/unblock.py` own blocked-state
  handoffs. `commands/megalaunch.py` is the manual drain entrypoint;
  reusable drain logic lives in `megalaunch.py`. `bump.py` advances
  workflow steps. `validate.py` checks repo consistency.
- `tests/` — pytest. Run with `python -m pytest`.
- `example/` — seeded fixture used by tests. **Update this when
  you change task layout, prompt composition, or workflow
  semantics** (CLAUDE.md rule).
- `docs/vision.md` — non-negotiables. See also `coga/principles`.

## coga layout

```
coga/
  coga.toml             ← shared config (committed)
  coga.local.toml       ← machine-local (NEVER committed; secrets here)
  context.md             ← repo-context layer of the composed prompt
  recurring/<name>/      ← recurring task template directories
                           (single-file ticket.md; history in the
                           repo-global coga/log.md)
  tasks/<slug>/          ← live tickets (top-level: bare leaf slug)
  tasks/<dir>/.../<slug>/ ← tickets in sub-dirs at any depth (ref'd by path)
  skills/<ns>/<name>/    ← project-local process knowledge / overrides
  contexts/<ns>/<name>/  ← project-local domain knowledge / overrides
  workflows/<ns>/<name>.md ← step definitions (local-first over bootstrap/workflows/)
  .agent-skills/         ← generated local-plus-bundled skill view for agents
```

Coga resolves skills and contexts from project-local roots first, then from
the package-backed bootstrap roots inside the installed `coga` package. It
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

Two sharp gotchas live here:

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
  dependencies in a `requirements.txt` beside its `SKILL.md`.
  `install_skill_requirements` (the tail of `install_venv` in
  `src/coga/commands/update.py`) pip-installs every project-local
  `coga/skills/**/requirements.txt` and package-backed
  `bootstrap/skills/**/requirements.txt` into `.coga/.venv` on `coga init`,
  after managed optional skills have had a chance
  to install into `coga/skills/`. That ordering is what makes a bundled or
  managed skill's deps land.
- **Vendored venv interpreter.** `install_venv` uses `COGA_PYTHON` when set,
  otherwise the interpreter running Coga, and validates that choice against
  the install source's `requires-python` before touching the venv. An explicit override
  is an interpreter-identity choice, not just an X.Y choice: if `pyvenv.cfg`
  records another executable, the venv is rebuilt. Missing `venv`/`ensurepip`
  errors name the matching Debian/Ubuntu `pythonX.Y-venv` package.

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
- **The only wheel-building test silently skips.** `tests/test_packaging.py`
  opens with `pytest.importorskip("hatchling")`. With no build backend in the
  venv it skips, so the suite is green while the wheel is unbuildable. Keep
  `hatchling` a tracked **dev/test** dep (`[project.optional-dependencies].test`,
  never runtime `requirements.txt` — coga never imports it at runtime) so the
  test actually runs.

Fix shape: exclude the colliding dir from the walk (`exclude` glob) and let the
`force-include` be its single deterministic shipper — mirroring the existing
`bootstrap/` exclude+force-include pairing. Don't just drop the force-include:
the walk silently omits pure-data (no-`.py`) skill dirs on some trees, so the
force-include is what guarantees they ship.

## Daily commands

- Install editable: `python -m pip install -e .`
- Run CLI: `coga --help`
- Tests: `python -m pytest`
- Validate config + tasks: `coga validate --json`
  (or `python -m coga.validate --json` if `coga` isn't on PATH).

If edits to `src/coga/` (especially the prompt templates under
`src/coga/resources/`) don't appear when you run the CLI, the venv likely
has a non-editable install.
Reinstall against the venv that backs your `coga` shim:
`<that venv's python> -m pip install -e .` from the repo root.

Sharper failure mode: an editable install's `.pth` can point at a
worktree that was later deleted. Then `coga` and `import coga` are
unimportable and pytest fails to even collect. Reinstalling fixes it, but
when you only need to run the suite, the proven workaround is to bypass the
broken `.pth` with an explicit `PYTHONPATH`:

```
PYTHONPATH=$PWD/src <repo>/.coga/.venv/bin/python -m pytest
```

Two non-obvious requirements:

- **`PYTHONPATH` must be absolute.** The script-launch subprocess tests run
  from a different cwd, so a relative `src` breaks them.
- **Use an explicit 3.11+ interpreter — don't trust the default `python3`.**
  coga needs `tomllib`, stdlib only on 3.11+, but the ambient `python3` on
  these machines is often 3.9. Name a new-enough interpreter directly, e.g.
  `PYTHONPATH=$PWD/src python3.12 -m pytest`, rather than relying on `python3`
  or a stale/absent `.coga/.venv` (which may itself be 3.9 or missing on a
  fresh checkout).

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

- **Tests must not pin to live dogfooded state.** Coga dogfoods itself, so files
  under `coga/` mutate as the repo is used. A test that compares the live
  `coga/` copy against a packaged template, or asserts a baked-in value, fails as
  the live value drifts — the `recurring/autoclose-merged` `last_serviced_period`
  date did exactly this, independently re-diagnosed as a "pre-existing failure"
  across at least four dev tasks (a recurring verification tax). Strip
  runtime-mutated fields (`last_serviced_period:`, timestamped log lines — see
  `_strip_runtime_state`) or freeze the period before comparing; assert
  structure, not a hardcoded date.

- **`coga.config` and `coga.commands.launch` share one `subprocess` module
  object.** Patching `coga.config.subprocess.run` and
  `coga.commands.launch.subprocess.run` separately collides (they are the same
  object). Use a single argv-dispatching mock on `coga.config.subprocess.run`.

## Secrets

Never commit. Shared config goes in `coga.toml`; per-machine paths
and credentials go in `coga.local.toml` via `env:VAR_NAME`
references. Secrets get injected as env vars at launch time by
`coga launch`.

## What this context does NOT cover

- The mental model of coga primitives — see `coga/architecture`.
- The principles for *why* the codebase is shaped this way — see
  `coga/principles`.
