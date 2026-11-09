# Repository Guidelines

## Read First
Start with [Coga's design principles](docs/contexts/coga-dev/principles/SKILL.md). When editing [README.md](README.md), keep it aligned with the principles. Read the relevant topic from the indexed library before changing behavior, and update it in the same PR. [docs/README.md](docs/README.md) indexes the library.

Exclude `docs/archive/**` from searches and reading unless the human explicitly requests archive use for the task. Follow [the archive access rule](docs/contexts/coga-dev/archive-access/SKILL.md#archive-access).

Canonical Coga topics (under `docs/contexts/`) have two audiences. User topics
under `coga/` are needed to operate Coga in adopting repos and ship
as fallbacks. Coga-dev topics under `coga-dev/` explain developing Coga itself
and stay local. [Context layout](src/coga/resources/templates/coga/bootstrap/contexts/coga/context-layout/SKILL.md#context-audiences)
owns the criterion; a shipped surface's required reading must be user knowledge.

- `coga/architecture/SKILL.md` is a short overview of the primitives and the correction loop plus a topic map; the detailed contracts live in the child topics it links (for example `coga/tickets`, `coga/lifecycle`, `coga/prompt-composition`, `coga/launch`).
- `coga/knowledge/SKILL.md` decides where a fact lives and when to attach versus cite a topic.
- `coga/extension-model/SKILL.md` owns repo extension choices; `coga-dev/microkernel/SKILL.md` owns the kernel rule summarized below.
- `coga-dev/codebase/SKILL.md` is the source map; `coga-dev/testing/SKILL.md` and `coga-dev/packaging/SKILL.md` own test and package ownership expectations.
- `coga-dev/current-direction/SKILL.md` and `coga-dev/project-stage/SKILL.md` capture live product posture.

Do not leave the durable explanation only in chat, PR comments, or task notes when it belongs in a topic, template, README, or spec. Which surface owns a fact — a topic under `docs/contexts/`, a skill, or a dated `docs/archive/evidence/`, `docs/archive/design/`, or `docs/archive/` page — is decided by `coga/knowledge` (`src/coga/resources/templates/coga/bootstrap/contexts/coga/knowledge/SKILL.md`): one owner per fact, other surfaces may summarize and link but never restate the specification, and the same PR that changes the owner fixes the other surface.

## Project Structure & Module Organization
Core code lives in `src/coga/`. Keep CLI entrypoints thin in `src/coga/commands/` and move reusable behavior into focused modules such as `config.py`, `compose.py`, `tasks.py`, and `validate.py`. Prompt/protocol templates live in `src/coga/resources/`. Tests live in `tests/`. Use `tests/fixtures/seeded-repo/coga/` as the seeded fixture for end-to-end behavior.

### Keep core minimal — the microkernel rule
Code earns a permanent home in `src/coga/` in **two ways**: (a) genuine **shared infra** — code with **≥2 real consumers** (compose, config, task/ticket IO, the launch machinery, shared parsers and gates); and (b) a reviewed command contract that must be co-versioned with the package. The second class contains the deliberately fixed `coga run` recipe registry (`runner.RECIPES`, listed in `coga/cli`) plus a command only when its contract names the package-private invariant or atomic transaction that an edge implementation using stable CLI/filesystem interfaces could not preserve. Python logic or inability to use an alias does not establish that home. Existing command heads with unresolved placement remain in the package pending review; [coga-dev/microkernel](docs/contexts/coga-dev/microkernel/SKILL.md#open-command-placements) owns their classification status and the parked cleanup tickets that settle them.

**Everything else stays at the edge.** A single-consumer helper may live beside the ticket or skill that uses it and import only shared core infra. Agent instructions may invoke an attachment explicitly under any ordinary filename. When deterministic work is the ticket's own headless phase, reserve the exact sibling name `ticket.py`: `coga launch` subprocesses it before any agent phase, but core still never imports from a ticket or skill directory. No other attachment changes dispatch. **"Backs a CLI spelling" is not by itself a pass into core**: a launch-target command is an argv rewrite in `[aliases]` (`dream = "recurring launch dream"`), not a Typer command with logic. Deterministic behavior that needs a repository-independent `coga run` argv/stdout/exit contract remains a fixed name in `runner.RECIPES`; ticket-owned deterministic behavior can instead stay beside its ticket. Wheel-owned edge implementations may ship in `src/coga_edge/`, selected by repo shims; upgrade and fork rules live in `coga/edge-code`. Skills describe how to invoke commands rather than supplying executable launch plugins. See the `coga-dev/microkernel` topic for the full rule.

Shipped definitions (user contexts, skills and their attachments, workflows, bootstrap tickets, recurring jobs with their scripts and runbooks, prompt resources) have one committed owner: the package under `src/coga/resources/` (user topics at `templates/coga/bootstrap/contexts/<ref>/`, reusable skills and workflows under `templates/coga/bootstrap/{skills,workflows}/`, recurring jobs at `templates/coga/recurring/<name>/`). Edit the package copy; repos, this one included, resolve it local-first and a local copy of the same ref is a deliberate override. This repo has completed its package-definition cutover. `tests/test_packaging.py` rejects every unapproved live counterpart, even a byte-identical copy; `tests/required_package_resources.txt` independently requires the package owners. Physical scaffolds, validated state-only recurring carriers and any reviewed local override have explicit reasons in that test. Carrier blackboards are repo state and never belong in package resources. Do not recreate live definitions or forwarding files. Ignored authoring starters may be materialized locally but must remain untracked. Scaffold divergences stay in `INTENTIONALLY_DIVERGENT_TWINS` with current reasons. `REQUIRED_BOOTSTRAP_CONTEXT_REFS` lists the bootstrap topics that must ship. The entire `coga-dev/` audience is local-only under `LOCAL_ONLY_CONTEXT_NAMESPACES`, and no development topic may be packaged. Machine-local state (`.coga/` run records and the megalaunch selection, `.venv/`), agent-tooling state (`.agent-skills/`, `.claude/`, `.codex/`), bytecode caches, and `coga.local.toml` are local artifacts outside this comparison. `coga-dev/packaging` (`docs/contexts/coga-dev/packaging/SKILL.md`) owns the full mapping.

## Build, Test, and Development Commands
- `python -m pip install -e ".[test]"` installs the package in editable mode with the declared test tools and exposes `coga`.
- `coga --help` or `python -m coga.cli` is the fastest CLI smoke check.
- `python -m pytest` runs the test suite after the test-extra install above.
- `coga validate --json` validates repo/task structure after config, workflow, or task-model changes.

## Coding Style & Naming Conventions
Target Python 3.11+, use 4-space indentation, `from __future__ import annotations`, and explicit type hints. Follow the current naming pattern: `snake_case` for modules/functions, `PascalCase` for dataclasses and exceptions. Prefer standard-library solutions, keep command handlers small, and preserve the spec’s distinctions between projects, skills, contexts, workflows, and tasks.

## Testing Guidelines
Tests use `pytest` and follow `tests/test_*.py`. Name tests after the command or module they cover, for example `tests/test_launch.py`. When you change prompt composition, workflow freezing, config loading, or task creation, update the seeded `tests/fixtures/seeded-repo/` repo or related fixtures so the smoke path remains representative.

There is no hosted test CI. Platform-sensitive changes require a native Windows full-suite receipt before merge; [coga-dev/testing](docs/contexts/coga-dev/testing/SKILL.md#verification-tiers-and-receipts) owns the verification tiers, the platform-sensitive list, and the receipt fields.

## Commit & Pull Request Guidelines
Before publishing or handing off edits, follow [coga/checkouts/reconciliation](src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/reconciliation/SKILL.md), including in sessions outside `coga launch`.

Recent commits use short, factual subjects, for example `Route recurring jobs through registered recipes` or `Drop redundant \`dream\` alias from coga.toml`. Use a ticket prefix only when one exists for the work. PRs should explain the behavior change, mention any fixture or spec touchpoints, and list the exact commands run for verification.

## Configuration & Security
Keep shared behavior in `coga.toml` and machine-specific paths in `coga.local.toml`. Never commit real credentials: a ticket declares the secrets it needs in its `secrets:` frontmatter as `env:VAR` or `op://` references (see `coga/secrets`, `src/coga/resources/templates/coga/bootstrap/contexts/coga/secrets/SKILL.md`). In config, only the `[notification.slack]` webhook keys resolve `env:VAR`; every other value is taken literally. Preserve compatibility with agent instruction files expected by the spec, including `AGENTS.md` and `CLAUDE.md`.
