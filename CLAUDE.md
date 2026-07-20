# Repository Guidelines

## Read First
Treat [docs/vision.md](docs/vision.md) as the product thesis and the `coga/contexts/coga/` contexts as the behavioral contract. Read the relevant context before changing behavior; if behavior changes, update the matching context or source doc in the same PR. Coga is intentionally markdown-first, git-backed, locally operated, and legible to humans; changes that hide state, move logic into opaque services, or blur the correction loop are usually the wrong direction.

Canonical Coga contexts:

- `principles/SKILL.md` defines the non-negotiables.
- `architecture/SKILL.md` defines primitives, planes, prompt composition, and locking.
- `codebase/SKILL.md` defines source layout and test expectations.
- `current-direction/SKILL.md` and `project-stage/SKILL.md` capture live product posture.

Do not leave the durable explanation only in chat, PR comments, or task notes when it belongs in a context, template, README, or spec.

## Project Structure & Module Organization
Core code lives in `src/coga/`. Keep CLI entrypoints thin in `src/coga/commands/` and move reusable behavior into focused modules such as `config.py`, `compose.py`, `tasks.py`, and `validate.py`. Prompt/protocol templates live in `src/coga/resources/`. Tests live in `tests/`. Use `example/coga/` as the seeded fixture for end-to-end behavior.

### Keep core minimal — the microkernel rule
`src/coga/` holds **only two kinds of code**: (a) genuine **shared infra** — code with **≥2 real consumers** (compose, config, task/ticket IO, the launch machinery, the shared `## Dev` PR-link parsers and `gh` helpers in `autoclose.py`); and (b) a real **command implementation** that genuinely needs Python logic and can't be expressed as an alias (e.g. `coga digest`, `coga megalaunch`). That is the whole kernel.

**Everything else is a skill recipe.** A single-consumer recipe — a user-facing workflow step (like `code/open-pr`) *or* a coga-internal recurring-maintenance sweep — lives in its skill dir as a sibling module beside `run.py` (by convention `recipe.py`), imports **only shared core infra**, and never lives in `src/coga/`. Being *internal* is not a license to sit in the kernel: a sweep only coga runs is still a skill recipe. **"Backs a CLI command" is not by itself a pass into core** — a launch-target command is an argv rewrite in `[aliases]` (`dream = "recurring launch dream"`), never a Typer command with logic; only a genuine Python implementation justifies core. The consumer test can *keep* a symbol in core: when a recipe moves out, a helper it shares with another core consumer stays put, because moving it would force core to import from a skill dir — the anti-pattern this rule forbids. (This supersedes the softer "extend at the edges, not the core" phrasing; see the `coga/codebase` context for the worked example.)

When changing shipped Coga OS contexts or templates, check both the live repo copy under `coga/` and the packaged copy under `src/coga/resources/templates/coga/`. Keep them in sync unless the difference is intentional and documented. A skill's `recipe.py` + `run.py` exist as both a dogfood copy under `coga/skills/` and a packaged copy under `src/coga/resources/templates/coga/bootstrap/skills/`; edit both together.

## Build, Test, and Development Commands
- `python -m pip install -e .` installs the package in editable mode and exposes `coga`.
- `coga --help` or `python -m coga.cli` is the fastest CLI smoke check.
- `python -m pytest` runs the test suite; install `pytest` in your dev environment first.
- `coga validate --json` validates repo/task structure after config, workflow, or task-model changes.

## Coding Style & Naming Conventions
Target Python 3.11+, use 4-space indentation, `from __future__ import annotations`, and explicit type hints. Follow the current naming pattern: `snake_case` for modules/functions, `PascalCase` for dataclasses and exceptions. Prefer standard-library solutions, keep command handlers small, and preserve the spec’s distinctions between projects, skills, contexts, workflows, and tasks.

## Testing Guidelines
Tests use `pytest` and follow `tests/test_*.py`. Name tests after the command or module they cover, for example `tests/test_launch.py`. When you change prompt composition, workflow freezing, config loading, or task creation, update the seeded `example/` repo or related fixtures so the smoke path remains representative.

## Commit & Pull Request Guidelines
Recent commits use short, factual subjects, for example `Add dream/ child-task workflows for Dream's script steps` or `Drop redundant \`dream\` alias from coga.toml`. Use a ticket prefix only when one exists for the work. PRs should explain the behavior change, mention any fixture or spec touchpoints, and list the exact commands run for verification.

## Configuration & Security
Keep shared behavior in `coga.toml` and machine-specific paths/secrets in `coga.local.toml`. Never commit real credentials; use `env:VAR_NAME` indirection. Preserve compatibility with agent instruction files expected by the spec, including `AGENTS.md` and `CLAUDE.md`.
