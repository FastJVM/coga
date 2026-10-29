---
name: coga/install
description: Prerequisites and installing the coga CLI (uv tool, pipx, virtualenv, editable checkout), common install failures, and the version check.
---

# Installing Coga

Coga is one CLI, installed once per machine, that operates every repo you
adopt it into. Installing the package never modifies a repo;
[`coga init`](../init/SKILL.md) does.

## Prerequisites

- **Linux or macOS for agent sessions.** In the development version after
  the native core port, Windows runs non-interactive commands, `ticket.py`
  phases, recipes and recurring scripts. Published PyPI 0.4.1 predates that
  port and fails to import on native Windows. Even the development version
  refuses agent sessions there until
  `v1/14-interactive-coga-launch-on-native-windows` lands
  ([coga/launch](../launch/SKILL.md#phases-and-routing)). WSL is the
  untested Windows route for agent sessions.
- **Python 3.11+.** The preferred uv install below can download a compatible
  Python for you; pip and pipx need an installed Python 3.11+.
- **Git.** The only external tool `coga init` enforces. Git is also Coga's
  sync layer: state changes are commits. On macOS, check that
  `git --version` works; the Xcode Command Line Tools are one way to obtain
  Git, but any working Git installation is sufficient (below).
- **An agent CLI**, installed and authenticated: Claude Code or Codex, for
  anything that launches an agent. `coga init` does not require one (below).
  Follow the [Claude Code CLI quickstart](https://code.claude.com/docs/en/quickstart)
  or [Codex CLI instructions](https://developers.openai.com/codex/cli/), then
  sign in with `claude` or `codex login`. Coga's install does not include
  these tools or authenticate an existing installation.
- **GitHub CLI (`gh`)**, recommended but not required at init. PR workflows,
  the merged-ticket autoclose sweep, and `coga skill install` check for it at
  their point of use and fail with an install hint.
- **1Password CLI (`op`)**, only if a ticket declares an `op://` secret; it
  is checked when that launch resolves the reference
  ([coga/secrets](../secrets/SKILL.md)).

One agent is enough for a session. A workflow with an `other-agent` review
step needs its configured peer as well; the [first-task walk](../first-task/SKILL.md)
explains the one-agent and peer-review choices and GitHub prerequisites.

In an interactive terminal, `coga init` offers to install a missing `git`,
`gh` (default yes, then `gh auth login` if the active github.com account is
not logged in) or `op` (default no) with the machine's package manager —
brew, winget, apt-get, dnf or pacman, with `sudo` on Linux — printing the
exact command first. Without a terminal, a known package manager or a package
for the tool, init prints the install link instead: a missing `git` still
stops init, a missing `gh` or `op` is a warning.

Agent CLIs take their own route. Interactive init, when neither `claude` nor
`codex` is on `PATH`, asks which to install (or skip); `coga build` offers
the onboarding ticket's missing agent CLI before failing. The installer is
the vendor's package, never a `curl | sh` script: on macOS the brew cask
(`claude-code`, `codex`), else `npm install -g @anthropic-ai/claude-code` or
`@openai/codex` when `npm` is on `PATH`, else only the install URL. The
command runs only on a yes, then offers the login (`claude`, which signs in
on first run, or `codex login`). Without a terminal, neither command
prompts. How init may change the default agent is in
[coga/init](../init/SKILL.md).

### macOS: check Git before init

Coga requires **working Git**, not Xcode. On a fresh Mac, `/usr/bin/git` may
be a stub: `git --version` can trigger installation of Apple's Xcode
Command Line Tools (CLT) instead of printing a version. The stub is on
`PATH`, so `coga init` may detect it as installed and fail at its first real
Git operation.

Run `git --version` before `git init` / `coga init`. If it prints a
version, there is no need to install CLT solely for Coga. Git installed via
Homebrew, MacPorts, or another working source is fine.

If Git is not working, Apple's CLT package is a standard option; **the full
Xcode app is not required**:

- **At the Mac's screen**, run `xcode-select --install` (or follow the
  prompt from `git --version`) and click **Install** in the dialog. Wait
  for it to finish, then re-run `git --version`.
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

The CLT install is machine-wide. A system `python3` may still be below
Coga's Python 3.11 floor; `uv tool install` manages its own Python.

Coga does not own your identity. It uses tools you already authenticate
(`git`, your credential helper or `ssh-agent`, `gh`) and fails with an
actionable hint when one is not ready. It stores no tokens of its own.

## Install the CLI

The package is `coga` on PyPI. Preferred: an isolated tool install with
[`uv`](https://docs.astral.sh/uv/). If `uv` is missing, install it first
on macOS or Linux with Astral's official installer:

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

See [other installation methods](https://docs.astral.sh/uv/getting-started/installation/)
if you prefer a package manager or want to inspect the installer. If
`uv` is not found after installation, open a new terminal or follow the
installer's `PATH` instructions.

```sh
uv tool install coga
```

By default uv finds a compatible Python or downloads a managed Python 3.11+,
so an older system `python3` need not be replaced (uv's
[Python management](https://docs.astral.sh/uv/concepts/python-versions/)).

Alternatives, using an already-installed Python 3.11+ (check
`python3 --version` first):

```sh
pipx install --python python3.11 coga  # isolated; python3.11 must be installed
python3 -m venv .venv && . .venv/bin/activate && pip install coga
python3 -m pip install coga       # deliberately into the current environment
```

### Install failures

**Python older than 3.11.** `pip install coga` fails with
`Could not find a version that satisfies the requirement coga` and
`Requires-Python >=3.11` diagnostics. Pinning `coga==0.0.1` installs a
yanked placeholder with no `coga` command, not a workaround. Use
`uv tool install coga` (or `uv tool install --python 3.11 coga` if uv is
configured for an older Python), or install Python 3.11+ and run
`pipx install --python python3.11 coga`. A venv made by an older Python does
not help.

**`Hashes are required in --require-hashes mode`.** The machine has pip's
hash-checking mode on globally (common on managed laptops). Either install
with `uv tool install coga` (uv ignores pip's config) or disable it for one
command: `PIP_REQUIRE_HASHES=0 pip install coga`.

### CLI older than the templates it sweeps

An install that predates clone scope ignores the `scope` key and services a
`scope: clone` template as an ordinary shared period task, with a log line and
no clone ledger ([scheduling](../recurring/scheduling/SKILL.md#repo-scope-and-clone-scope)).
This happens when the CLI lags the templates it sweeps, for example an editable
install whose source checkout sits behind `main`. The shipped clone scripts
tolerate it: with `COGA_TASK_SLUG` set they bump that task, so the period
closes instead of stalling. When a sweep creates a shared task for a template
already declaring clone scope, check `coga --version` and the editable source
checkout, then upgrade (below).

## Verify

```sh
coga --help
coga --version     # prints "coga <version>"
```

`coga --version` reports the installed package version (`unknown` if package
metadata is missing). One CLI runs every repo, so there is no per-repo
version. These commands check the CLI installation, not agent authentication
or a completed first task; continue with [coga/first-task](../first-task/SKILL.md).

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

Next: adopt Coga into a repository with [coga/init](../init/SKILL.md), then
walk a first ticket with [coga/first-task](../first-task/SKILL.md).

## Audit retention adoption

Fresh init installs the weekly trim-log job with default-on 30-day retention.
A wheel upgrade alone installs no new schedule into existing repos. After
upgrading every writer, use the feature-specific `python -m
coga_edge.trim_log --install` with the upgraded CLI's interpreter; follow the
[adoption and recovery guide](https://github.com/FastJVM/coga/blob/main/coga/recurring/trim-log/operations.md)
for the exact command, allowlist, customization/parking checks and compatible
two-phase rollout. The command installs only this feature's repo files.
