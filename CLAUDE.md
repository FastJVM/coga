# Repository Guidelines

## Read First
Treat [docs/vision.md](docs/vision.md) as the product thesis and the `relay-os/contexts/relay/` contexts as the behavioral contract. Read the relevant context before changing behavior; if behavior changes, update the matching context or source doc in the same PR. Relay is intentionally markdown-first, git-backed, locally operated, and legible to humans; changes that hide state, move logic into opaque services, or blur the correction loop are usually the wrong direction.

Canonical Relay contexts:

- `principles/SKILL.md` defines the non-negotiables.
- `architecture/SKILL.md` defines primitives, planes, prompt composition, and locking.
- `codebase/SKILL.md` defines source layout and test expectations.
- `current-direction/SKILL.md` and `project-stage/SKILL.md` capture live product posture.

Do not leave the durable explanation only in chat, PR comments, or task notes when it belongs in a context, template, README, or spec.

## Project Structure & Module Organization
Core code lives in `src/relay/`. Keep CLI entrypoints thin in `src/relay/commands/` and move reusable behavior into focused modules such as `config.py`, `compose.py`, `tasks.py`, and `validate.py`. Prompt/protocol templates live in `src/relay/resources/`. Tests live in `tests/`. Use `example/relay-os/` as the seeded fixture for end-to-end behavior.

When changing shipped Relay OS contexts or templates, check both the live repo copy under `relay-os/` and the packaged copy under `src/relay/resources/templates/relay-os/`. Keep them in sync unless the difference is intentional and documented.

## Build, Test, and Development Commands
- `python -m pip install -e .` installs the package in editable mode and exposes `relay`.
- `relay --help` or `python -m relay.cli` is the fastest CLI smoke check.
- `python -m pytest` runs the test suite; install `pytest` in your dev environment first.
- `relay validate --json` validates repo/task structure after config, workflow, or task-model changes.

## Coding Style & Naming Conventions
Target Python 3.11+, use 4-space indentation, `from __future__ import annotations`, and explicit type hints. Follow the current naming pattern: `snake_case` for modules/functions, `PascalCase` for dataclasses and exceptions. Prefer standard-library solutions, keep command handlers small, and preserve the spec’s distinctions between projects, skills, contexts, workflows, and tasks.

## Testing Guidelines
Tests use `pytest` and follow `tests/test_*.py`. Name tests after the command or module they cover, for example `tests/test_launch.py`. When you change prompt composition, workflow freezing, config loading, or task scaffolding, update the seeded `example/` repo or related fixtures so the smoke path remains representative.

## Commit & Pull Request Guidelines
Recent commits use short, factual subjects, for example `Add dream/ child-task workflows for Dream's script steps` or `Drop redundant \`dream\` alias from relay.toml`. Use a ticket prefix only when one exists for the work. PRs should explain the behavior change, mention any fixture or spec touchpoints, and list the exact commands run for verification.

## Configuration & Security
Keep shared behavior in `relay.toml` and machine-specific paths/secrets in `relay.local.toml`. Never commit real credentials; use `env:VAR_NAME` indirection. Preserve compatibility with agent instruction files expected by the spec, including `AGENTS.md` and `CLAUDE.md`.
