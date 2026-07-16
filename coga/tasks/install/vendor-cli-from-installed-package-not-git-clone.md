---
slug: install/vendor-cli-from-installed-package-not-git-clone
title: Vendor CLI from installed package not git clone
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts:
- dev/code
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 1 (implement)
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

## Dev
branch: vendor-cli-from-package
worktree: /home/n/Code/claude/coga-vendor-cli

## Plan (implement step)

Replace `coga init`'s shallow git clone with vendoring from the running
distribution. Design:

- New `InstallSource` (dataclass in `commands/update.py`): `kind`
  (`release` | `checkout` | `url`), `pip_spec` (what pip installs),
  `display` (redacted provenance for pin/echo), `requires_python`.
- `resolve_install_source()` resolution order:
  1. `COGA_REPO_URL` env override — existing dir ⇒ checkout install from
     that path (sanctions the old workaround); otherwise a git URL ⇒
     `pip install git+<url>` via existing `pip_git_source`.
  2. Running package imported from a source checkout
     (`src/coga/…` under a root with a `pyproject.toml` naming `coga`)
     ⇒ install from that checkout path. Covers `pip install -e .`.
  3. Otherwise ⇒ `pip install coga==<running version>` (PyPI release).
- `install_venv(coga_os, source)` no longer needs `.coga/pyproject.toml`;
  requires-python validation comes from the source (checkout pyproject /
  running dist metadata; skipped for git URLs — pip enforces there).
- `refresh_cli`, `clone_upstream`, `upstream_sha`, `resolve_coga_repo_url`,
  remote detection, and `read_pin_url` are deleted — nothing copies source
  into `coga/.coga/` anymore; `.coga/` holds only `.venv/`, `bin/`, COGA_PIN.
- `COGA_PIN` becomes `<source display>\n<installed version>` where the
  version is read back from the built venv (`vendored_cli_version`), so it
  records what pip actually installed. `coga --version` prints
  `vendored CLI <version> (from <source>)`.
- Docs: packaged `cli` context init + `--version` sections, README init
  notes, `docs/cli-extension-audit.md` init row. Architecture context only
  mentions offline-init in passing — checked, no clone description there.

Findings so far:
- `resolve_coga_repo_url`'s ssh-remote detection existed purely to pick a
  git transport for the clone; with pip there is no transport concern, so
  it goes away rather than being ported.
- `uninstall.py` imports the `COGA_REPO_URL` constant (kept) and
  `running_cli_location` (unchanged).
- Tests: `tests/test_init.py` `fake_clone` fixture + clone/pin/install_venv
  tests need rework; `_venv_fixture_coga_os` no longer needs the fake
  `.coga/pyproject.toml`.

## Implement step — done

Committed on `vendor-cli-from-package` (single commit, rebased onto
origin/main 3aeb6dfe). What landed, matching the plan above:

- `commands/update.py`: `InstallSource` + `resolve_install_source()` +
  `_running_checkout_root()` (filesystem probe: `coga.__file__` under
  `<root>/src/coga` with a pyproject naming `coga`) +
  `vendored_cli_version()` (reads the installed version back from the built
  venv). `clone_upstream` / `upstream_sha` / `refresh_cli` /
  `resolve_coga_repo_url` / remote detection / `read_pin_url` deleted;
  `read_pin_source` replaces `read_pin_url`. `install_venv(coga_os, source)`
  pip-installs `source.pip_spec` and validates requires-python from the
  source (skipped for git-URL sources — pip enforces); pip failure output
  redacts a credentialed URL spec.
- `commands/init.py`: source resolved before any writes (bad COGA_REPO_URL
  leaves nothing on disk); no tempdir/clone; pin written from
  source + actually-installed version; echoes
  `Vendored CLI coga <version> from <source>`.
- `cli.py --version`: `vendored CLI <version> (from <source>)`; old
  SHA-format pins still print (line 2 shown as-is, documented in
  `read_pin`).
- COGA_PIN format: `<source display>\n<installed version>`.
- Docs: packaged `coga/cli` context (init paragraph + `--version` section),
  live `coga/codebase` context (requires-python wording),
  `docs/cli-extension-audit.md` init row. README does **not** describe the
  clone anywhere (its only clone mentions are the dev-install instructions),
  and the architecture context never describes init vendoring beyond the
  still-true bundled-batteries bullet — checked both; no edits needed there.

Verification:
- `python3.12 -m pytest`: 1211 passed, 1 failed —
  `test_launch_script.py::test_bootstrap_script_launch_is_stateless` fails
  identically on untouched main (environment: the subprocess interpreter
  has no coga installed), pre-existing, not caused by this change.
- End-to-end smoke in a fresh temp git repo:
  `PYTHONPATH=src python3.12 -m coga.cli init --user tester` → no clone, no
  `Cloning …` line, venv pip-installed from the checkout path,
  COGA_PIN = `<checkout path>\n0.2.0`, `.coga/` contains only
  `.venv/ bin/ COGA_PIN` (no `src/`), and the vendored
  `./coga/.coga/bin/coga --version` / `coga status` run cleanly against the
  scaffolded coga.toml — the original 0.2.0 breakage scenario.

Note for review: the release path (`pip install coga==<version>` from PyPI)
is covered by unit tests only — it can't be exercised end-to-end until the
running version exists on PyPI. A non-editable `pip install /path/to/checkout`
(frozen copy in site-packages) resolves as a release install of its version;
`COGA_REPO_URL=<path>` is the explicit escape hatch there.

## Usage

{"agent":"claude","cache_creation_input_tokens":null,"cache_read_input_tokens":null,"cli":"claude","input_tokens":null,"model":null,"output_tokens":null,"provider":"anthropic","schema":1,"session_id":"d4fc4818-2e93-4555-ba84-775487e44866","slug":"install/vendor-cli-from-installed-package-not-git-clone","step":"implement","title":"Vendor CLI from installed package not git clone","ts":"2026-07-16T17:03:04.815847Z","usage_status":"unknown"}
