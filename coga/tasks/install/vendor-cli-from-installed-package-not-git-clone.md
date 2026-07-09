---
slug: install/vendor-cli-from-installed-package-not-git-clone
title: Vendor CLI from installed package not git clone
status: draft
mode: agent
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
  - dev/code
skills: []
workflow: code/with-review
secrets: null
script: null
---

## Description

`coga init` shallow-clones `https://github.com/FastJVM/coga` solely to vendor
the CLI into `coga/.coga/` (`refresh_cli` copies `src/coga` + pyproject +
requirements + README, then a venv pip-installs that copy). Post-PyPI this is
obsolete and actively harmful: the clone grabs **current main HEAD**, not the
version that ran init, so a fresh `pip install coga` (0.2.0) + `coga init`
produces a repo whose vendored CLI rejects the very `coga.toml` the same init
scaffolded (`[agents.claude] unknown key 'auto'` — every command including
`--help` exits 2), and the `~/.local/bin/coga` shim points at exactly that
broken copy. It also makes init require github.com git reachability for no
reason, and prints an unexplained `Cloning … (shallow)…` line.

Replace the clone with vendoring from the installed distribution:
`pip install coga==<running version>` into the vendored venv for wheel
installs; install-from-checkout-path for source installs (generalizing the
`COGA_REPO_URL=<local path>` workaround into the sanctioned path, keeping
`COGA_REPO_URL` as the explicit override). `COGA_PIN` becomes the package
version (a release is what you actually installed). Update the architecture
and cli contexts plus README wherever they describe the clone.

## Context

Found in the 2026-07-08 fresh-container retest (this conversation's report;
reproduced end-to-end in docker python:3.12). Supersedes the surviving half of
`install/retest-ssh-https-and-init-reclone-on-fresh-machine` (the init
re-clone surprise). Touchpoints: `src/coga/commands/init.py` (`_do_init`),
`src/coga/commands/update.py` (`clone_upstream`, `refresh_cli`, `write_pin`,
`resolve_coga_repo_url`), `install_venv`, packaging tests, and the
`coga/architecture` + `coga/cli` contexts describing init vendoring.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
