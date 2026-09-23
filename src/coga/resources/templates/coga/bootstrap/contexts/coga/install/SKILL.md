---
name: coga/install
description: Prerequisites and installing the coga CLI (uv tool, pipx, virtualenv, editable checkout), common install failures, and the version check.
---

# Installing Coga

Coga is one CLI, installed once per machine, that operates every repo you
adopt it into. Installing the package never modifies a repo; `coga init` does
that, and init installs no software (see [coga/init](../init/SKILL.md)).

## Prerequisites

- **Python 3.11+.** The package declares `requires-python = ">=3.11"`
  (`pyproject.toml`) because config loading uses the standard-library
  `tomllib`. On an older interpreter, `pip install coga` fails with
  `Could not find a version that satisfies the requirement coga` plus
  `Requires-Python` notes, or it may succeed at installing the old `0.0.1`
  placeholder, which provides no `coga` command. Check `python3 --version`.
- **Git.** The only external tool `coga init` enforces
  (`src/coga/commands/init.py` `_check_external_dependencies`, driven by the
  `required_at_init` entries in `src/coga/dependencies.py`). Git is also
  Coga's sync layer: state changes are commits.
- **An agent CLI**, installed and authenticated: Claude Code or Codex. Needed
  by anything that launches an agent (`coga launch`, `coga ticket`,
  `coga build`); `coga init` does not require one.
- **GitHub CLI (`gh`)**, recommended but not required at init. PR workflows,
  the merged-ticket autoclose sweep, and `coga skill install` check for it at
  their point of use and fail with an install hint.
- **1Password CLI (`op`)**, only if a ticket declares an `op://` secret; it
  is checked when that launch resolves the reference
  ([coga/secrets](../secrets/SKILL.md)).

Coga does not own your identity. It uses tools you already authenticate
(`git`, your credential helper or `ssh-agent`, `gh`) and fails with an
actionable hint when one is not ready. It stores no tokens of its own.

## Install the CLI

The package is `coga` on PyPI. Preferred: an isolated tool install with
[`uv`](https://docs.astral.sh/uv/):

```sh
uv tool install coga
```

Alternatives:

```sh
pipx install coga                 # isolated, pipx-managed
python3 -m venv .venv && . .venv/bin/activate && pip install coga
python3 -m pip install coga       # deliberately into the current environment
```

Contributors working on Coga itself install the checkout editable with the
test extra: `python -m pip install -e ".[test]"`
([coga/codebase](../codebase/SKILL.md) covers the source-checkout loop).

**`Hashes are required in --require-hashes mode`.** The machine has pip's
hash-checking mode on globally (common on managed laptops). Either install
with `uv tool install coga` (uv ignores pip's config) or disable it for one
command: `PIP_REQUIRE_HASHES=0 pip install coga`.

## Verify

```sh
coga --help
coga --version     # prints "coga <version>"
```

`coga --version` reports the installed package version (`src/coga/cli.py`
`_print_version_and_exit`; `unknown` if package metadata is missing). One CLI
runs every repo, so there is no second, per-repo version.

## Upgrading and removing

Bundled batteries (packaged skills, contexts, workflows, bootstrap tickets)
resolve directly from the installed package, so an upgrade needs no per-repo
refresh. Upgrade with the installer that owns the CLI:

- `uv tool upgrade coga` for a uv tool install;
- `pip install --upgrade coga` in the CLI's Python environment (or
  `pipx upgrade coga`);
- `git pull && pip install -e .` for a source checkout.

Removing Coga from a repo, and optionally the global package, is
[coga/uninstall](../uninstall/SKILL.md).

## Next

Adopt Coga into a repository with [coga/init](../init/SKILL.md), then walk a
first ticket with [coga/first-task](../first-task/SKILL.md).
