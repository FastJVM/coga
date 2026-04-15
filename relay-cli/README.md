# relay-os (Python CLI)

The Python CLI for the Relay CompanyOS. Installs a `relay` command on
your PATH; reads the shared repo's `relay.toml` + per-machine
`relay.local.toml`; manipulates tasks, prompts, and the Slack feed.

This directory is the Python project. The rest of the parent repo
(skills, contexts, workflows, recurring templates, protocol, rules) is
the knowledge tree this CLI operates on.

## Requirements

- Python 3.11 or later (uses stdlib `tomllib`).
- macOS or Linux. Windows is untested.

## Install

From this directory:

```bash
pip install -e '.[dev]'
```

The `-e` flag installs in editable mode so source edits take effect
immediately without reinstalling. The `[dev]` extra pulls in `pytest`.

Verify the install:

```bash
relay --help
```

You should see all seven subcommands: `init`, `create`, `launch`,
`status`, `step`, `panic`, `feed`.

## Run the tests

```bash
pytest
```

The current test suite covers only the CLI scaffold (subcommands are
wired up, `--help` works, stubs print "not implemented"). Subsequent
tickets add real tests as they fill in `config`, `frontmatter`,
`composer`, and `slack`.

## Project layout

```
relay-cli/
  pyproject.toml
  README.md                   (this file)
  src/
    relay_os/
      __init__.py
      cli.py                  click entry point
      config.py               (stub — FJVM-1288)
      frontmatter.py          (stub — FJVM-1291)
      composer.py             (stub — FJVM-1293)
      slack.py                (stub — FJVM-1295)
      commands/
        __init__.py
        init.py
        create.py
        launch.py
        status.py
        step.py
        panic.py
        feed.py
  tests/
    __init__.py
    conftest.py               shared fixtures
    test_cli.py               scaffold smoke tests
```

Package name (PyPI-style): `relay-os`.
Python import: `from relay_os import cli`.
Console script: `relay`.

## Status

Every subcommand is stubbed — invoking one prints `not implemented`
and exits 0. Subsequent tickets fill in each piece. See each module's
docstring for which ticket is expected to complete it.
