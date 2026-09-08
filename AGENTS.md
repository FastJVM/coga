# Repository Guidelines

## Read First
Treat [docs/vision.md](docs/vision.md) as the product thesis and the `coga/contexts/coga/` contexts as the behavioral contract. Read the relevant context before changing behavior; if behavior changes, update the matching context or source doc in the same PR. Coga is intentionally markdown-first, git-backed, locally operated, and legible to humans; changes that hide state, move logic into opaque services, or blur the correction loop are usually the wrong direction.

Canonical Coga contexts:

- `principles/SKILL.md` defines the non-negotiables.
- `architecture/SKILL.md` defines primitives, planes, and prompt composition.
- `codebase/SKILL.md` defines source layout and test expectations.
- `current-direction/SKILL.md` and `project-stage/SKILL.md` capture live product posture.

Do not leave the durable explanation only in chat, PR comments, or task notes when it belongs in a context, template, README, or spec.

## Project Structure & Module Organization
Core code lives in `src/coga/`. Keep CLI entrypoints thin in `src/coga/commands/` and move reusable behavior into focused modules such as `config.py`, `compose.py`, `tasks.py`, and `validate.py`. Prompt/protocol templates live in `src/coga/resources/`. Tests live in `tests/`. Use `example/coga/` as the seeded fixture for end-to-end behavior.

### Keep core minimal — the microkernel rule
`src/coga/` holds **only two kinds of code**: (a) genuine **shared infra** — code with **≥2 real consumers** (compose, config, task/ticket IO, the launch machinery, shared parsers and gates); and (b) a reviewed command contract that must be co-versioned with the package. The second class contains the deliberately fixed `coga run` recipe registry (`open-pr`, `delete-task`, and the recurring jobs) plus a command only when its contract names the package-private invariant or atomic transaction that an edge implementation using stable CLI/filesystem interfaces could not preserve. Python logic or inability to use an alias does not establish that home. `coga digest` and `coga megalaunch` are current in-package implementations whose final classification remains owned by the active command-cleanup design; it must record that proof or migrate them.

**Everything else stays at the edge.** A single-consumer helper may live beside the ticket or skill that uses it and import only shared core infra. Agent instructions may invoke an attachment explicitly under any ordinary filename. When deterministic work is the ticket's own headless phase, reserve the exact sibling name `ticket.py`: `coga launch` subprocesses it before any agent phase, but core still never imports from a ticket or skill directory. No other attachment changes dispatch. **"Backs a CLI spelling" is not by itself a pass into core**: a launch-target command is an argv rewrite in `[aliases]` (`dream = "recurring launch dream"`), not a Typer command with logic. Deterministic behavior that needs a repository-independent `coga run` argv/stdout/exit contract remains a fixed name in `runner.RECIPES`; ticket-owned deterministic behavior can instead stay beside its ticket. Skills describe how to invoke commands rather than supplying executable launch plugins. See the `coga/codebase` context for the full rule.

When changing shipped Coga OS contexts or templates, check both the live repo copy under `coga/` and the packaged copy under `src/coga/resources/templates/coga/`. Keep them in sync unless the difference is intentional and documented. This is enforced, not remembered: `tests/test_packaging.py` derives every twin from the packaged tree — `templates/coga/<path>` pairs with `coga/<path>`, and a bundled battery under `templates/coga/bootstrap/{contexts,skills,workflows}/<path>` pairs with `coga/{contexts,skills,workflows}/<path>` — and requires byte-identity for every pair whose live counterpart exists. There is no list to register a new twin in; a packaged file with no live counterpart is simply not a pair. Generated installation directories (`.coga/`, `.venv/`), agent-tooling state (`.agent-skills/`, `.claude/`, `.codex/`), bytecode caches, and `coga.local.toml` are local artifacts outside this comparison. To make a difference intentional, add the live path to `INTENTIONALLY_DIVERGENT_TWINS` with the reason, and expect the test to tell you to drop that entry once the two copies match again.

## Build, Test, and Development Commands
- `python -m pip install -e ".[test]"` installs the package in editable mode with the declared test tools and exposes `coga`.
- `coga --help` or `python -m coga.cli` is the fastest CLI smoke check.
- `python -m pytest` runs the test suite after the test-extra install above.
- `coga validate --json` validates repo/task structure after config, workflow, or task-model changes.

## Coding Style & Naming Conventions
Target Python 3.11+, use 4-space indentation, `from __future__ import annotations`, and explicit type hints. Follow the current naming pattern: `snake_case` for modules/functions, `PascalCase` for dataclasses and exceptions. Prefer standard-library solutions, keep command handlers small, and preserve the spec’s distinctions between projects, skills, contexts, workflows, and tasks.

## Testing Guidelines
Tests use `pytest` and follow `tests/test_*.py`. Name tests after the command or module they cover, for example `tests/test_launch.py`. When you change prompt composition, workflow freezing, config loading, or task creation, update the seeded `example/` repo or related fixtures so the smoke path remains representative.

## Commit & Pull Request Guidelines
Recent commits use short, factual subjects, for example `Route recurring jobs through registered recipes` or `Drop redundant \`dream\` alias from coga.toml`. Use a ticket prefix only when one exists for the work. PRs should explain the behavior change, mention any fixture or spec touchpoints, and list the exact commands run for verification.

## Configuration & Security
Keep shared behavior in `coga.toml` and machine-specific paths/secrets in `coga.local.toml`. Never commit real credentials; use `env:VAR_NAME` indirection. Preserve compatibility with agent instruction files expected by the spec, including `AGENTS.md` and `CLAUDE.md`.
