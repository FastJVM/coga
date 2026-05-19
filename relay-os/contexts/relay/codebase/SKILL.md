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
  builds the prompt. `slack.py` posts. `config.py` loads config.
  `launch.py` / `launch_script.py` run agents. `slack.py` (in
  `commands/`) posts an explicit FYI. `panic.py` surfaces agent
  distress. `bump.py`
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
  prompt.md              ← base prompt
  prompt-interactive.md  ← interactive mode block
  prompt-auto.md         ← auto mode block
  bootstrap/<name>/      ← stateless launch shims
  bootstrap/skills/      ← package-backed bundled skills (overwritten on update)
  bootstrap/contexts/    ← package-backed bundled contexts (overwritten on update)
  tasks/<slug>/          ← live tickets
  skills/<ns>/<name>/    ← project-local process knowledge / overrides
  contexts/<ns>/<name>/  ← project-local domain knowledge / overrides
  workflows/<ns>/<name>.md ← step definitions
  scripts/cron.sh        ← entry for recurring scheduler
```

Relay resolves skills and contexts from project-local roots first, then from
the package-backed bootstrap roots. Claude Code and Codex are pointed at the
generated `relay-os/.agent-skills/` view, which exposes the same effective
local-plus-bundled skill set.

## Daily commands

- Install editable: `python -m pip install -e .`
- Run CLI: `relay --help`
- Tests: `python -m pytest`
- Validate config + tasks: `relay validate --json`
  (or `python -m relay.validate --json` if `relay` isn't on PATH).

If edits to `src/relay/` (especially `resources/*.md` like `dream.md`) don't
appear when you run the CLI, the venv likely has a non-editable install.
Reinstall against the venv that backs your `relay` shim:
`<that venv's python> -m pip install -e .` from the repo root.

## Secrets

Never commit. Shared config goes in `relay.toml`; per-machine paths
and credentials go in `relay.local.toml` via `env:VAR_NAME`
references. Secrets get injected as env vars at launch time by
`relay launch`.

## What this context does NOT cover

- The mental model of relay primitives — see `relay/architecture`.
- The principles for *why* the codebase is shaped this way — see
  `relay/principles`.
