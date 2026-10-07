---
name: coga/install
description: Prerequisites and installing the coga CLI (uv tool, pipx, virtualenv, editable checkout), common install failures, and the version check.
---

# Installing Coga

Coga is one CLI, installed once per machine, that operates every repo you
adopt it into. Installing the package never modifies a repo; `coga init` does
that, and offers to install missing external CLIs (see
[coga/init](../init/SKILL.md)).

## Prerequisites

- **Linux or macOS (POSIX).** Native Windows is unsupported:
  `src/coga/git.py` imports `fcntl` at module top for the state-publication
  lock, and `cli.py` imports `coga.git` eagerly, so every command, even
  `coga --help`, fails with `No module named 'fcntl'`. A port needs a
  portable substitute for that lock, not only guarded terminal imports. WSL
  is the untested Windows route.
- **Python 3.11+.** The package declares `requires-python = ">=3.11"`
  (`pyproject.toml`) because config loading uses the standard-library
  `tomllib`. On an older interpreter, `pip install coga` fails with
  `Could not find a version that satisfies the requirement coga` plus
  `Requires-Python` notes, or it may succeed at installing the old `0.0.1`
  placeholder, which provides no `coga` command. Check `python3 --version`.
- **Git.** The only external tool `coga init` enforces
  (`src/coga/commands/init.py` `_require_init_tools`, driven by the
  `required_at_init` entries in `src/coga/dependencies.py`). Git is also
  Coga's sync layer: state changes are commits. On macOS, Git comes from
  the Xcode Command Line Tools; install them first (below).
- **An agent CLI**, installed and authenticated: Claude Code or Codex. Needed
  by anything that launches an agent (`coga launch`, `coga ticket`,
  `coga build`); `coga init` does not require one, but interactive init and
  `coga build` offer to install one (below).
- **GitHub CLI (`gh`)**, recommended but not required at init. PR workflows,
  the merged-ticket autoclose sweep, and `coga skill install` check for it at
  their point of use and fail with an install hint.
- **1Password CLI (`op`)**, only if a ticket declares an `op://` secret; it
  is checked when that launch resolves the reference
  ([coga/secrets](../secrets/SKILL.md)).

In an interactive terminal, `coga init` offers to install a missing `git`,
`gh` (default yes, then `gh auth login` if the active github.com account
is not logged in) or `op` (default no)
with the machine's package manager — brew, winget, apt-get, dnf or pacman,
with `sudo` on Linux — printing the exact command first. The per-tool
packages live in `src/coga/dependencies.py`. Without a terminal, a known
package manager or a package for the tool, init prints the install link
instead: a missing `git` still stops init, a missing `gh` or `op` is a
warning.

Agent CLIs take their own route, shared by interactive `coga init` and
`coga build` (`src/coga/agent_cli_setup.py` `offer_agent_cli`, with the
packages and login commands in `src/coga/dependencies.py`). Init, when
neither `claude` nor `codex` is on `PATH`, asks which to install (or skip);
`coga build`, when the onboarding ticket's agent CLI is missing, offers that
one before failing. The installer is the vendor's package, never a
`curl | sh` script: on macOS the brew cask (`claude-code`, `codex`), else
`npm install -g @anthropic-ai/claude-code` or `@openai/codex` when `npm` is
on `PATH`, else only the install URL is printed. The exact command is printed
and runs only on a yes; a successful install then offers the login (`claude`,
which signs in on first run, or `codex login`). How init may change the
default agent is in [coga/init](../init/SKILL.md). Without a terminal,
neither command prompts.

> Owner reversal (2026-09-30): users read a missing `gh` as a broken,
> unprofessional install and churn. Interactive `coga init` now offers to
> install missing external CLIs; it still installs no Python package or
> skill, and never installs anything without a yes.
>
> Owner decision (2026-10-01): agent CLIs are offered too, through brew or
> npm only, and init may set or replace the default agent behind an explicit
> confirm.

### macOS: install the Command Line Tools first

A fresh Mac has no real Git. `/usr/bin/git` is a stub that the Xcode
Command Line Tools (CLT) replace, so the first `git` call, even
`git --version`, triggers the CLT install instead of running Git. That call
may be yours, a `git init`, or `coga init`'s. `coga init` cannot repair this:
the stub is on PATH, so its missing-`git` check (`_require_init_tools` in
`src/coga/commands/init.py`) passes and its install offer never runs. The
Git command init runs next then fails. Install the CLT before installing
Coga or running `git init` / `coga init`, and confirm `git --version` prints a
version:

- **At the Mac's screen**, run `xcode-select --install` (or any `git`
  command) and click **Install** in the dialog. Wait for it to finish, then
  re-run `git --version`.
- **Over SSH or another headless session**, no dialog can open. `git` exits
  1 with `xcode-select: error: No developer tools were found and no install
  could be requested (possibly because there is no active GUI session)`.
  Either finish the install once at the screen (or over screen sharing), or
  install it headless with an administrator account:

  ```sh
  touch /tmp/.com.apple.dt.CommandLineTools.installondemand.in-progress
  softwareupdate -l          # note the "Command Line Tools for Xcode" label
  sudo softwareupdate -i "<that label>"
  rm /tmp/.com.apple.dt.CommandLineTools.installondemand.in-progress
  ```

The CLT install is machine-wide, so one install covers every user. It
provides Python 3.9 as `/usr/bin/python3`, which is below Coga's 3.11 floor.
Install Python 3.11+ separately (`uv tool install` can manage its own Python).
The 2026-10-01 clean-install walk reproduced the SSH error on a fresh
macOS 27 host; the dialog path was not exercised. This topic owns the
headless steps; the clean-install runbook,
[coga/testing/clean-install/macos-aws](../testing/clean-install/macos-aws/SKILL.md),
applies them to its walk host.

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
