# Claude Instructions

Read [docs/vision.md](/home/n/Code/relay/docs/vision.md) and [docs/spec.md](/home/n/Code/relay/docs/spec.md) before changing behavior. `vision.md` explains the non-negotiables: Relay is a markdown-first, git-backed, locally operated company OS optimized for legibility and a short human correction loop. `spec.md` is the contract for config layout, task structure, workflows, skills, contexts, and agent integration.

Implementation rules:
- Keep Typer command entrypoints in `src/relay/commands/` thin; move reusable logic into testable modules under `src/relay/`.
- Preserve the spec’s object model: projects are locations, agents are types, skills are process knowledge, contexts are domain knowledge, workflows define steps, and tickets/tasks hold execution state.
- Do not commit secrets. Shared config belongs in `relay.toml`; machine-local paths and credentials belong in `relay.local.toml` via `env:VAR_NAME`.
- When behavior changes affect task layout, prompt composition, or workflow semantics, update tests and the seeded `example/` fixture.

Useful commands:
- `python -m pip install -e .`
- `relay --help`
- `python -m pytest`
- `python -m relay.validate --json`
