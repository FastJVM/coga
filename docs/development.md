# Development

This page is for working on Coga itself — the Python package and the shipped
markdown OS — rather than using it. If you're contributing a fix or a feature,
start here.

## Run from a checkout

Clone the repo and install it editable into a virtualenv:

```sh
git clone https://github.com/FastJVM/coga
cd coga
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

That exposes the `coga` CLI pointing at your working tree. If pip's global
hash-checking mode blocks the editable install (`there is no single file to
hash`), install with `uv` or prefix the one command with `PIP_REQUIRE_HASHES=0`
— same escape hatches as a normal install (see [getting
started](getting-started.md#install)).

Fastest smoke check:

```sh
coga --help
python -m coga.cli --help    # equivalent, without the console script
```

Coga requires **Python 3.11+** (it uses the standard-library `tomllib`). Running
under an older interpreter fails loud with the version it found.

## Source layout

Core code lives in `src/coga/`:

- **`commands/`** — the CLI entrypoints, one module per command (`launch.py`,
  `create.py`, `bump.py`, …). Keep these thin; push reusable behavior into the
  focused modules below.
- **`config.py`** — loads and validates `coga.toml` / `coga.local.toml` against a
  fixed schema (unknown keys fail loud).
- **`compose.py`** — assembles the composed launch prompt from its layers.
- **`tasks.py`, `taskfile.py`, `blackboard.py`** — reading and writing tickets
  and their blackboards.
- **`workflow.py`, `bump.py`, `step_gate.py`** — workflow steps, advancement, and
  step completion gates.
- **`validate.py`** — the `coga validate` checks.
- **`resources/`** — the shipped prompt/protocol templates and the packaged copy
  of the Coga OS (`resources/templates/coga/`).

Tests live in `tests/` as `tests/test_*.py`, named after the command or module
they cover (`tests/test_launch.py`). `example/coga/` is the seeded fixture used
for end-to-end behavior.

## Tests

```sh
python -m pytest
```

Install `pytest` in your dev environment first. When you change prompt
composition, workflow freezing, config loading, or task creation, update the
seeded `example/` repo or related fixtures so the smoke path stays
representative. And after config, workflow, or task-model changes, run:

```sh
coga validate --json
```

## The repo↔package sync rule

This is the single most common mistake in a Coga change, so it gets its own
section.

Much of the Coga OS lives in **two** places:

1. The **live copy** under `coga/` in this repo (what this repo's own agents
   load — the dogfood copy).
2. The **packaged copy** under `src/coga/resources/templates/coga/` (what `coga
   init` copies into a new repo).

When you change a shipped context, skill, workflow, or template that exists in
**both** places, **update both copies in the same PR** — unless the divergence
is intentional and you say so. Editing only one is how a fix lands for this repo
but never reaches new installs, or vice versa. Reviewers are told to check for
exactly this. It's the most common docs-only miss.

The nuance: the rule applies only to resources that have both copies. The
bundled **bootstrap batteries** (`resources/templates/coga/bootstrap/` — the
core skills, contexts, workflows, and interview targets) are **package-backed**:
`coga init` deliberately skips `bootstrap/`, and this repo carries no
`coga/bootstrap/` dogfood copy. Runtime resolvers read those package resources
directly (after checking for a local `coga/…` override). So a change to a
bootstrap battery lives in the single packaged location — there's no second copy
to sync.

## Coding style

- Target Python 3.11+, 4-space indentation, `from __future__ import
  annotations`, explicit type hints.
- `snake_case` for modules and functions; `PascalCase` for dataclasses and
  exceptions.
- Prefer standard-library solutions and keep command handlers small.
- Preserve the spec's distinctions between projects, skills, contexts,
  workflows, and tasks — they aren't interchangeable.

## Commit and PR conventions

Commit subjects are short and factual (`Add dream/ child-task workflows for
Dream's script steps`). Use a ticket-slug prefix only when a ticket exists for
the work. PRs should explain the behavior change, mention any fixture or spec
touchpoints, and list the exact commands you ran to verify.

Keep durable explanation where it belongs: if a change alters behavior, update
the matching context or spec doc in the *same* PR rather than leaving the
explanation in chat or a PR comment. Coga is meant to stay legible — a change
that hides state, moves logic into an opaque service, or blurs the
human-correction loop is usually the wrong direction.

## Configuration and security

Keep shared behavior in `coga.toml` and machine-specific paths or secrets in
`coga.local.toml`. Never commit real credentials — use `env:VAR` or `op://`
indirection (see [operations](operations.md#secrets)). Preserve compatibility
with the agent instruction files the spec expects, `AGENTS.md` and `CLAUDE.md`.

## Releasing

Cutting a release is covered separately in [releasing.md](releasing.md).
