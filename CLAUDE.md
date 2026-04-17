# CLAUDE.md — operating notes for agents working on this repo

This is the Relay CompanyOS repo. Two concerns coexist here:

1. **The knowledge tree** at the repo root — `skills/`, `contexts/`,
   `workflows/`, `recurring/`, `rules.md`, `prompt.md`,
   `projects/*/relay-os/` — read and mutated by the `relay` CLI when
   humans and agents do work.
2. **The CLI itself** — under `relay-cli/`, a Python package (`relay-os`
   on PyPI, `relay_os` in Python imports) that produces the `relay`
   command.

If you're making changes, figure out which concern you're touching
first. Editing a context block or workflow is different from editing
`src/relay_os/config.py`.

## Code conventions (for `relay-cli/`)

- Python 3.11+. Use `tomllib` from stdlib (not `tomli`).
- `click` for CLI parsing. Each subcommand is a separate file under
  `src/relay_os/commands/` exporting a `@click.command()` function.
- Type hints on public functions. Use `from __future__ import
  annotations` at the top of every module so `|`-style unions work.
- `pyyaml` for YAML (frontmatter). No hand-rolled YAML parsing.
- Prefer editing existing files over creating new ones. Don't
  proliferate helper modules — most utility code belongs in the
  existing `config.py`, `frontmatter.py`, `composer.py`, or
  `slack.py`.

## Testing

- `pytest` runs from the `relay-cli/` directory. No `-v` needed by
  default.
- Tests go under `relay-cli/tests/`. Mirror the module structure:
  `test_config.py` tests `config.py`, etc.
- Use `CliRunner` from `click.testing` for command tests.
- Shared fixtures (temp repos, sample configs) live in
  `tests/conftest.py`. Prefer extending that file over making new
  `conftest.py`s in subdirectories.
- Do **not** mock the filesystem. Write real files to `tmp_path` and
  assert on disk state. Past incidents where mocked tests passed while
  real behavior broke inform this rule.

## What not to touch

- `relay.toml`, `relay.local.toml.example` — shared config, owned by
  the user. Edit only when the spec explicitly requires a new field.
- `projects/*/relay-os/tasks/*/log.md` — append-only task log, written
  only by CLI commands as side effects. Agents and humans never
  hand-edit these.
- `projects/*/relay-os/tasks/*/ticket.md` frontmatter fields other than
  `contexts` — status, assignee, step, workflow, etc. change via the
  CLI (`relay step`, manual edits for status/assignee), not by
  running code that mutates them in bulk.
- `prompt.md`, `prompt-interactive.md`, `prompt-auto.md` — these
  are the system prompt for every Relay-launched agent. Change them
  deliberately; they affect every task in every project forever.

## Stubs vs. implementations

Right now (ticket FJVM: Python project setup), every subcommand prints
`not implemented`. The module files `config.py`, `frontmatter.py`,
`composer.py`, and `slack.py` are empty stubs with a docstring
pointing at the ticket that will fill them in.

Do not preemptively implement those modules as a side effect of
another ticket. Each has its own ticket; jumping ahead creates review
churn and makes it harder to scope commits. If you discover you need
functionality from a not-yet-implemented module, flag it — don't
silently add it.

## Secrets

Credentials live in `relay.local.toml` (gitignored) and environment
variables. Never write secrets to committed files, log them to
stdout, or include them in test fixtures.

## Commits

- Every change goes through a PR. Direct pushes to `main` are banned
  by convention (GitHub branch protection requires a paid plan; we
  enforce this socially instead).
- Commit messages describe the *why*, not the *what*. The diff covers
  the what.
