# Repository Guidelines

## Read First
Treat [product/vision](docs/contexts/product/vision/SKILL.md) as the product thesis and the topic library under `docs/contexts/` (this repo's `[layout] contexts` root) as the behavioral contract. Read the relevant topic before changing behavior; if behavior changes, update the owning topic in the same PR. Coga is intentionally markdown-first, git-backed, locally operated, and legible to humans; changes that hide state, move logic into opaque services, or blur the correction loop are usually the wrong direction. [docs/README.md](docs/README.md) indexes the library.

Canonical Coga topics (under `docs/contexts/`):

- `coga/principles/SKILL.md` defines the non-negotiables.
- `coga/architecture/SKILL.md` is a short overview of the primitives and the correction loop plus a topic map; the detailed contracts live in the child topics it links (for example `coga/tickets`, `coga/lifecycle`, `coga/prompt-composition`, `coga/launch`).
- `coga/knowledge/SKILL.md` decides where a fact lives and when to attach versus cite a topic.
- `coga/extension-model/SKILL.md` owns the microkernel rule summarized below.
- `coga/codebase/SKILL.md` is the source map; `coga/testing/SKILL.md` and `coga/packaging/SKILL.md` own test and twin expectations.
- `coga/current-direction/SKILL.md` and `coga/project-stage/SKILL.md` capture live product posture.

Do not leave the durable explanation only in chat, PR comments, or task notes when it belongs in a topic, template, README, or spec. Which surface owns a fact — a topic under `docs/contexts/`, a skill, or a dated `docs/evidence/`, `docs/design/`, or `docs/archive/` page — is decided by `coga/knowledge` (`docs/contexts/coga/knowledge/SKILL.md`): one owner per fact, other surfaces may summarize and link but never restate the specification, and the same PR that changes the owner fixes the other surface.

## Project Structure & Module Organization
Core code lives in `src/coga/`. Keep CLI entrypoints thin in `src/coga/commands/` and move reusable behavior into focused modules such as `config.py`, `compose.py`, `tasks.py`, and `validate.py`. Prompt/protocol templates live in `src/coga/resources/`. Tests live in `tests/`. Use `example/coga/` as the seeded fixture for end-to-end behavior.

### Keep core minimal — the microkernel rule
`src/coga/` holds **only two kinds of code**: (a) genuine **shared infra** — code with **≥2 real consumers** (compose, config, task/ticket IO, the launch machinery, shared parsers and gates); and (b) a reviewed command contract that must be co-versioned with the package. The second class contains the deliberately fixed `coga run` recipe registry (`open-pr`, `delete-task`, and the recurring jobs) plus a command only when its contract names the package-private invariant or atomic transaction that an edge implementation using stable CLI/filesystem interfaces could not preserve. Python logic or inability to use an alias does not establish that home. `coga megalaunch` has no `RECIPES` entry and is the one genuinely unclassified in-package implementation. Its placement is deferred to a parked design — `coga/tasks/v2/cleanup-core-commands/` is one paused ticket plus five drafts in a directory `coga/tasks/v2/README.md` defines as off the execution path — and it stays in core until that is pulled forward.

**Everything else stays at the edge.** A single-consumer helper may live beside the ticket or skill that uses it and import only shared core infra. Agent instructions may invoke an attachment explicitly under any ordinary filename. When deterministic work is the ticket's own headless phase, reserve the exact sibling name `ticket.py`: `coga launch` subprocesses it before any agent phase, but core still never imports from a ticket or skill directory. No other attachment changes dispatch. **"Backs a CLI spelling" is not by itself a pass into core**: a launch-target command is an argv rewrite in `[aliases]` (`dream = "recurring launch dream"`), not a Typer command with logic. Deterministic behavior that needs a repository-independent `coga run` argv/stdout/exit contract remains a fixed name in `runner.RECIPES`; ticket-owned deterministic behavior can instead stay beside its ticket. Skills describe how to invoke commands rather than supplying executable launch plugins. See the `coga/extension-model` topic for the full rule.

When changing shipped Coga OS contexts or templates, check both the canonical repo copy and the packaged copy under `src/coga/resources/templates/coga/`. Keep them in sync unless the difference is intentional and documented. This is enforced, not remembered: `tests/test_packaging.py` derives every twin from the packaged tree and requires byte-identity. Contexts pair with the canonical library under `docs/contexts/`: a bootstrap-fallback topic `templates/coga/bootstrap/contexts/<ref>/SKILL.md` pairs with `docs/contexts/<ref>/SKILL.md`, and an init-seeded scaffold `templates/coga/contexts/<path>` pairs with `docs/contexts/<path>`. For contexts the test is strict: every packaged context must have its canonical counterpart, `REQUIRED_BOOTSTRAP_CONTEXT_REFS` lists the bootstrap topics that must exist in both trees, and a canonical topic with no packaged copy must be named in `LOCAL_ONLY_CONTEXT_REFS` with its reason. Other template areas keep the `coga/<path>` mapping: `templates/coga/<path>` pairs with `coga/<path>`, and a bundled battery under `templates/coga/bootstrap/{skills,workflows}/<path>` pairs with `coga/{skills,workflows}/<path>`; there, a packaged file with no live counterpart is simply not a pair, and there is no list to register a new twin in. Machine-local state (`.coga/` run records and the megalaunch selection, `.venv/`), agent-tooling state (`.agent-skills/`, `.claude/`, `.codex/`), bytecode caches, and `coga.local.toml` are local artifacts outside this comparison. To make a difference intentional, add the live path to `INTENTIONALLY_DIVERGENT_TWINS` with the reason, and expect the test to tell you to drop that entry once the two copies match again. `coga/packaging` (`docs/contexts/coga/packaging/SKILL.md`) owns the full mapping.

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
