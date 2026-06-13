---
name: relay/codebase
description: Where things live in the relay source tree, and how to run tests and validation. Read this before editing relay's own code.
---

# Relay codebase

The repo has two halves:

- **`src/relay/`** — the Python package. The CLI implementation.
- **`relay-os/`** — the user-facing OS layout (config, tasks,
  skills, workflows, contexts, prompts). What relay *operates on*,
  not relay itself.

Always be clear which half you're editing. They have different
review bars.

## Source layout

- `src/relay/commands/` — Typer entrypoints, one file per `relay
  <command>`. **Keep these thin.** No business logic.
- `src/relay/` (other modules) — testable logic. `compose.py`
  builds the prompt. `notification/` dispatches notifications with Slack as
  the first backend. `config.py` loads config.
  `commands/launch.py` / `commands/launch_script.py` run agents.
  `commands/slack.py` keeps the explicit FYI command spelling.
  `commands/panic.py` surfaces agent distress. `bump.py`
  advances workflow steps. `validate.py` checks repo consistency.
- `tests/` — pytest. Run with `python -m pytest`.
- `example/` — seeded fixture used by tests. **Update this when
  you change task layout, prompt composition, or workflow
  semantics** (CLAUDE.md rule).
- `docs/vision.md` — non-negotiables. See also `relay/principles`.

## relay-os layout

```
relay-os/
  relay.toml             ← shared config (committed)
  relay.local.toml       ← machine-local (NEVER committed; secrets here)
  rules.md               ← global-rules layer of the composed prompt
  context.md             ← repo-context layer of the composed prompt
  recurring/<name>/      ← recurring task template directories
                           (ticket.md + blackboard.md + log.md)
  bootstrap/<name>/      ← stateless launch shims
  bootstrap/skills/      ← package-backed core skills (overwritten on update)
  bootstrap/contexts/    ← package-backed bundled contexts (overwritten on update)
  tasks/<slug>/          ← live tickets (top-level: bare leaf slug)
  tasks/<group>/<slug>/  ← grouped live tickets (ref'd as <group>/<slug>)
  skills/<ns>/<name>/    ← project-local process knowledge / overrides
  contexts/<ns>/<name>/  ← project-local domain knowledge / overrides
  workflows/<ns>/<name>.md ← step definitions
  scripts/cron.sh        ← entry for recurring scheduler
```

Relay resolves skills and contexts from project-local roots first, then from
the package-backed bootstrap roots. Claude Code and Codex are pointed at the
generated `relay-os/.agent-skills/` view, which exposes the same effective
local-plus-bundled skill set. Optional Relay-owned domain skills are declared
in `src/relay/resources/managed-skills.toml` and installed into
`relay-os/skills/` through the public skill installer during init/update; they
are not copied from the template tree.

## Authoring bundled batteries

Bundled (package-backed) core skills and contexts are authored in the *source*
tree under `src/relay/resources/templates/relay-os/bootstrap/{skills,contexts}/`,
not in the live `relay-os/bootstrap/` of a working repo — that copy is
gitignored and overwritten wholesale on `relay init --update`. Optional domain
skills belong in a published skill source plus
`src/relay/resources/managed-skills.toml`, not under the packaged template
payload.

Two sharp gotchas live here:

- **Force-add new battery files.** `src/relay/resources/templates/relay-os/.gitignore`
  ignores `bootstrap/` (it is the `.gitignore` shipped *into* generated repos,
  where `bootstrap/` is materialized, not committed — but it also sits inside
  the source template dir, so it applies there too). A new bundled skill or
  context file therefore must be added with `git add -f`, or it silently never
  commits and ships nothing despite passing local validation and tests.
- **Skill Python deps via `requirements.txt`.** A skill declares its
  dependencies in a `requirements.txt` beside its `SKILL.md`.
  `install_skill_requirements` (the tail of `install_venv` in
  `src/relay/commands/update.py`) pip-installs every
  `relay-os/**/skills/**/requirements.txt` into `.relay/.venv` on `relay init`
  and `relay init --update`, after package-backed batteries are materialized
  into `relay-os/bootstrap/` and after managed optional skills have had a
  chance to install into `relay-os/skills/`. That ordering is what makes a
  bootstrapped or managed skill's deps land.

## Wheel packaging: force-include vs the package walk

`[tool.hatch.build.targets.wheel]` ships pure-data skill/context dirs (no
`.py` files) two ways, and they can collide. The `packages = ["src/relay"]`
filesystem walk and an explicit `force-include` of a template dir (e.g.
`skills/_template`) both try to add the same file — hatchling treats them as
two archive entries at one path and aborts:

```
ValueError: A second file is being added to the wheel archive at the same
path: `relay/resources/templates/relay-os/skills/_template/SKILL.md`.
```

Two non-obvious traps make this a clean-checkout-only failure that hides in dev:

- **It only fails on a pristine tree.** On a dev tree, `relay init` has created
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
  never runtime `requirements.txt` — relay never imports it at runtime) so the
  test actually runs.

Fix shape: exclude the colliding dir from the walk (`exclude` glob) and let the
`force-include` be its single deterministic shipper — mirroring the existing
`bootstrap/` exclude+force-include pairing. Don't just drop the force-include:
the walk silently omits pure-data (no-`.py`) skill dirs on some trees, so the
force-include is what guarantees they ship.

## Daily commands

- Install editable: `python -m pip install -e .`
- Run CLI: `relay --help`
- Tests: `python -m pytest`
- Validate config + tasks: `relay validate --json`
  (or `python -m relay.validate --json` if `relay` isn't on PATH).

If edits to `src/relay/` (especially the prompt templates under
`src/relay/resources/`) don't appear when you run the CLI, the venv likely
has a non-editable install.
Reinstall against the venv that backs your `relay` shim:
`<that venv's python> -m pip install -e .` from the repo root.

Sharper failure mode: an editable install's `.pth` can point at a
worktree that was later deleted. Then `relay` and `import relay` are
unimportable and pytest fails to even collect. Reinstalling fixes it, but
when you only need to run the suite, the proven workaround is to bypass the
broken `.pth` with an explicit `PYTHONPATH`:

```
PYTHONPATH=$PWD/src <repo>/.relay/.venv/bin/python -m pytest
```

Two non-obvious requirements:

- **`PYTHONPATH` must be absolute.** The script-launch subprocess tests run
  from a different cwd, so a relative `src` breaks them.
- **Use a 3.11+ interpreter.** relay needs `tomllib`, which is stdlib only
  on 3.11+.

## Secrets

Never commit. Shared config goes in `relay.toml`; per-machine paths
and credentials go in `relay.local.toml` via `env:VAR_NAME`
references. Secrets get injected as env vars at launch time by
`relay launch`.

## What this context does NOT cover

- The mental model of relay primitives — see `relay/architecture`.
- The principles for *why* the codebase is shaped this way — see
  `relay/principles`.
