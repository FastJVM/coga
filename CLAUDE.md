# Claude Instructions

Primary references — read these first:

- [`relay-os/contexts/relay/`](/home/n/Code/relay/relay-os/contexts/relay/) — the agent-loaded mental model. `principles` (non-negotiables, fail-loud, classical mode), `architecture` (primitives, planes, composition, locking), `codebase` (where source lives + how to test), `current-direction` (open decisions), `project-stage` (stage-specific posture). These are the *same* contexts that get composed into every launched ticket — they are canon for day-to-day reasoning.
- [`README.md`](/home/n/Code/relay/README.md) — CLI surface: `relay init / create / launch / status / bump / delete / panic / slack / recurring`. One-screen reference per command.

Deeper reference (open when relevant):

- [`docs/spec.md`](/home/n/Code/relay/docs/spec.md) — reference contract: config schemas, frontmatter shapes, error/failure tables. Use when implementing config or CLI changes. The architecture context is canon if the two disagree.
- [`docs/vision.md`](/home/n/Code/relay/docs/vision.md) — public-facing essay. The `principles` context is the working form.

Implementation rules:
- Keep Typer command entrypoints in `src/relay/commands/` thin; move reusable logic into testable modules under `src/relay/`.
- Preserve the spec’s object model: projects are locations, agents are types, skills are process knowledge, contexts are domain knowledge, workflows define steps, and tickets/tasks hold execution state.
- Do not commit secrets. Shared config belongs in `relay.toml`; machine-local paths and credentials belong in `relay.local.toml` via `env:VAR_NAME`.
- When behavior changes affect task layout, prompt composition, or workflow semantics, update tests and the seeded `example/` fixture.

Useful commands:
- `python -m pip install -e .`
- `relay --help`
- `python -m pytest`
- `relay validate --json`
